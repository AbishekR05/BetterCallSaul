# scripts/normalize_corpus.py
import os
import sys
import socket

# Force Python's socket to resolve IPv4 addresses only to avoid broken IPv6 connection timeouts on Windows
orig_getaddrinfo = socket.getaddrinfo
def forced_ipv4_getaddrinfo(*args, **kwargs):
    if len(args) >= 3:
        # if family is passed as positional argument, modify it
        args = list(args)
        args[2] = socket.AF_INET
    else:
        family = kwargs.get('family', socket.AF_UNSPEC)
        if family == socket.AF_UNSPEC or family == socket.AF_INET6:
            kwargs['family'] = socket.AF_INET
    return orig_getaddrinfo(*args, **kwargs)
socket.getaddrinfo = forced_ipv4_getaddrinfo

import json
import gzip
import hashlib
import io
import time
import tempfile
from pathlib import Path
from dotenv import load_dotenv

# Add absolute workspace root to python path
sys.path.append("d:/Abishek")

from scripts.acquire_open_india_law import authenticate_google_drive, GoogleDriveManager

# Load environment variables
load_dotenv()

# Setup paths
BASE_DIR = Path("d:/Abishek")
CONFIG_DIR = BASE_DIR / "config"
DOMAIN_MAPPING_PATH = CONFIG_DIR / "domain_mapping.json"
LOCAL_TEMP_DIR = BASE_DIR / "scratch" / "temp_process"
LOCAL_TEMP_DIR.mkdir(parents=True, exist_ok=True)

# Load domain mapping config
if DOMAIN_MAPPING_PATH.exists():
    with open(DOMAIN_MAPPING_PATH, 'r', encoding='utf-8') as f:
        DOMAIN_MAPPING = json.load(f)
else:
    DOMAIN_MAPPING = {}

def clean_text(text):
    """Normalize whitespace and basic cleaning of legal text without altering legal meaning."""
    if not text:
        return ""
    # Replace multiple spaces/newlines with single ones
    text = " ".join(text.split())
    return text.strip()

def calculate_hash(text):
    """Generate MD5 hash of text to help with deduplication."""
    if not text:
        return ""
    return hashlib.md5(text.encode('utf-8')).hexdigest()

def classify_domains(title, text):
    """Classify document into one or more domains based on keywords from config/domain_mapping.json."""
    matched_domains = []
    combined_content = f"{title or ''} {text or ''}".lower()
    
    for domain, keywords in DOMAIN_MAPPING.items():
        for kw in keywords:
            # Simple keyword matching
            if kw.lower() in combined_content:
                matched_domains.append(domain)
                break  # match found for this domain, check next domain
                
    return matched_domains

def normalize_jurisdiction(raw_jurisdiction, raw_level, raw_state):
    """Normalize jurisdiction fields into level, state, country format."""
    level = (raw_level or raw_jurisdiction or "unknown").lower().strip()
    state = raw_state or None
    country = "India"
    
    # Handle TRAI / other central bodies masquerading as states
    if state and state.lower() in ["trai", "moefcc", "mca", "cpcb", "law-commission"]:
        level = "central"
        state = None
        
    if level == "central" or level == "union":
        level = "central"
        state = None
    elif level == "state":
        level = "state"
    elif level in ["union_territory", "ut"]:
        level = "union_territory"
        
    return {
        "level": level,
        "state": state,
        "country": country
    }

def normalize_record(raw_record, filename):
    """Map raw record fields to normalizedLegalDoc schema."""
    raw_text = raw_record.get("text", "")
    cleaned_txt = clean_text(raw_text)
    txt_hash = calculate_hash(cleaned_txt)
    
    title = raw_record.get("title", "").strip()
    doc_type = raw_record.get("document_type", "unknown").lower().strip()
    
    # Jurisdiction normalization
    juris_info = normalize_jurisdiction(
        raw_record.get("jurisdiction"),
        raw_record.get("level"),
        raw_record.get("state")
    )
    
    # Domain mapping
    domains = classify_domains(title, cleaned_txt)
    if not domains and raw_record.get("domain"):
        domains = [raw_record.get("domain")]
        
    # Standardize record id (md5 hash of source file + title + text hash)
    record_id = hashlib.md5(f"{filename}_{title}_{txt_hash}".encode('utf-8')).hexdigest()
    
    # Determine date
    year = raw_record.get("year")
    date_str = f"{year}-01-01" if year else None
    
    normalized_doc = {
        "record_id": record_id,
        "source_type": doc_type,
        "title": title,
        "text": cleaned_txt,
        "jurisdiction": juris_info["level"],
        "level": juris_info["level"],
        "state": juris_info["state"],
        "court": raw_record.get("authority") if doc_type == "judgment" else None,
        "domain": domains,
        "document_type": doc_type,
        "date": date_str,
        "effective_date": None,
        "authority": raw_record.get("authority"),
        "citation": raw_record.get("citation"),
        "source_url": raw_record.get("source_url", ""),
        "original_source_id": raw_record.get("original_source_id", ""),
        "dataset_version": "1.0",
        "is_historical": False
    }
    
    # Quality audits
    quality_issues = []
    if not cleaned_txt:
        quality_issues.append("empty_text")
    elif len(cleaned_txt) < 100:
        quality_issues.append("extremely_short_text")
        
    return normalized_doc, txt_hash, quality_issues

from googleapiclient.http import MediaIoBaseUpload

def upload_file_to_drive(drive_service, local_path, file_name, folder_id, mime_type="application/json"):
    """Helper to upload a local file to a Google Drive folder using MediaIoBaseUpload.
    This guarantees the file stream is closed and not locked on Windows."""
    q = f"name = '{file_name}' and '{folder_id}' in parents and trashed = false"
    results = drive_service.files().list(q=q, fields="files(id)").execute(num_retries=5)
    files = results.get('files', [])
    
    with open(local_path, 'rb') as f:
        media = MediaIoBaseUpload(f, mimetype=mime_type, resumable=True)
        if files:
            file_id = files[0]['id']
            drive_service.files().update(fileId=file_id, media_body=media).execute(num_retries=5)
            return file_id
        else:
            file_metadata = {
                'name': file_name,
                'parents': [folder_id]
            }
            res = drive_service.files().create(body=file_metadata, media_body=media, fields='id').execute(num_retries=5)
            return res.get('id')

def process_single_file(drive, drive_service, file_info, folder_key):
    """Downloads, normalizes, deduplicates, and uploads a single file, returning stats."""
    file_id = file_info["id"]
    filename = file_info["name"]
    
    print(f"\nProcessing file: {filename} (ID: {file_id})")
    
    local_raw_path = LOCAL_TEMP_DIR / filename
    local_out_name = filename if filename.endswith(".jsonl.gz") else f"{filename}.gz"
    local_out_path = LOCAL_TEMP_DIR / f"normalized_{local_out_name}"
    
    # 1. Download file
    print(f"  Downloading {filename}...")
    content_bytes = drive.download_file_content(file_id)
    if not content_bytes:
        raise IOError(f"Failed to download {filename} from Google Drive")
        
    with open(local_raw_path, 'wb') as f:
        f.write(content_bytes)
        
    # 2. Open and process line by line
    print("  Normalizing and deduplicating records...")
    processed_count = 0
    retained_count = 0
    duplicate_count = 0
    quality_counts = {"empty_text": 0, "extremely_short_text": 0}
    domain_counts = {}
    
    # Set to track exact duplicates inside this file
    seen_hashes = set()
    
    # Choose file opener based on compression
    opener = gzip.open(local_raw_path, 'rt', encoding='utf-8') if filename.endswith('.gz') else open(local_raw_path, 'r', encoding='utf-8')
    
    # Output file compressed
    out_f = gzip.open(local_out_path, 'wt', encoding='utf-8')
    
    try:
        for line in opener:
            if not line.strip():
                continue
            try:
                raw_record = json.loads(line)
                processed_count += 1
                
                normalized, txt_hash, issues = normalize_record(raw_record, filename)
                
                # Check for duplicates
                if txt_hash in seen_hashes:
                    duplicate_count += 1
                    continue
                    
                seen_hashes.add(txt_hash)
                
                # Record issues
                for issue in issues:
                    quality_counts[issue] = quality_counts.get(issue, 0) + 1
                    
                # Track domains
                for dom in normalized["domain"]:
                    domain_counts[dom] = domain_counts.get(dom, 0) + 1
                    
                # Write normalized record
                out_f.write(json.dumps(normalized) + "\n")
                retained_count += 1
            except Exception as e:
                print(f"    Warning: Error parsing line in {filename}: {e}")
    finally:
        opener.close()
        out_f.close()
        
    # 3. Upload to Google Drive (folder_key is 'legislation' or 'judgments')
    parent_folder_id = drive.folders.get(folder_key)
    # Write normalized files to 02_normalized folder on Google Drive
    # Let's locate or create the 02_normalized folder on Google Drive
    norm_root_id = drive.get_or_create_subfolder("02_normalized", drive.root_id)
    norm_dest_folder_id = drive.get_or_create_subfolder(folder_key, norm_root_id)
    
    print(f"  Uploading normalized file {local_out_name} to Drive...")
    upload_file_to_drive(drive_service, local_out_path, local_out_name, norm_dest_folder_id, mime_type="application/gzip")
        
    # 4. Clean up local files
    local_raw_path.unlink()
    local_out_path.unlink()
    
    print(f"  Done. Inspected: {processed_count}, Retained: {retained_count}, Duplicates: {duplicate_count}")
    
    return {
        "processed_records": processed_count,
        "retained_records": retained_count,
        "duplicate_records": duplicate_count,
        "quality_counts": quality_counts,
        "domain_counts": domain_counts
    }

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Normalize Legal Corpus")
    parser.add_argument("--limit-files", type=int, default=None, help="Limit number of files to process")
    args = parser.parse_args()

    print("Initializing Normalization Pipeline...")
    drive_service = authenticate_google_drive()
    drive = GoogleDriveManager(drive_service)
    
    # Let's check for existing checkpoint file inside 03_metadata folder on Drive
    metadata_folder_id = drive.folders.get("metadata")
    checkpoint_file_id = None
    checkpoint_data = {"processed_files": {}}
    
    q = f"name = 'checkpoint_1b.json' and '{metadata_folder_id}' in parents and trashed = false"
    results = drive_service.files().list(q=q, fields="files(id)").execute()
    files = results.get('files', [])
    
    if files:
        checkpoint_file_id = files[0]['id']
        print("Found existing checkpoint_1b.json on Google Drive. Resuming...")
        content_bytes = drive.download_file_content(checkpoint_file_id)
        if content_bytes:
            checkpoint_data = json.loads(content_bytes.decode('utf-8'))
            
    # List all raw filtered files from Drive
    raw_filtered_root_id = drive.folders.get("legislation") # Wait, we need to inspect legislation and judgments
    raw_files = []
    
    for folder_key in ["legislation", "judgments"]:
        f_id = drive.folders.get(folder_key)
        res = drive_service.files().list(
            q=f"'{f_id}' in parents and trashed = false",
            fields="files(id, name, size)"
        ).execute()
        for f in res.get('files', []):
            raw_files.append({
                "id": f["id"],
                "name": f["name"],
                "size": int(f.get("size", 0)),
                "folder_key": folder_key
            })
            
    print(f"Found total {len(raw_files)} raw filtered files to process.")
    
    # Process files
    overall_stats = {
        "total_files_inspected": 0,
        "total_records_inspected": 0,
        "total_records_retained": 0,
        "total_duplicates_found": 0,
        "quality_counts": {"empty_text": 0, "extremely_short_text": 0},
        "domain_counts": {},
        "jurisdiction_counts": {"central": 0, "state": 0, "union_territory": 0, "unknown": 0}
    }
    
    # If checkpoint contains overall stats, load them to accumulate
    if "overall_stats" in checkpoint_data:
        overall_stats = checkpoint_data["overall_stats"]
        
    processed_this_run = 0
    for idx, file_info in enumerate(raw_files, 1):
        filename = file_info["name"]
        
        # Check if already processed
        if filename in checkpoint_data["processed_files"]:
            print(f"[{idx}/{len(raw_files)}] Skipping already processed file: {filename}")
            continue
            
        if args.limit_files is not None and processed_this_run >= args.limit_files:
            print(f"Reached file processing limit of {args.limit_files}. Stopping.")
            break
            
        print(f"[{idx}/{len(raw_files)}] Processing raw file...")
        try:
            stats = process_single_file(drive, drive_service, file_info, file_info["folder_key"])
            processed_this_run += 1
            
            # Update overall stats
            overall_stats["total_files_inspected"] += 1
            overall_stats["total_records_inspected"] += stats["processed_records"]
            overall_stats["total_records_retained"] += stats["retained_records"]
            overall_stats["total_duplicates_found"] += stats["duplicate_records"]
            
            for k, v in stats["quality_counts"].items():
                overall_stats["quality_counts"][k] = overall_stats["quality_counts"].get(k, 0) + v
                
            for k, v in stats["domain_counts"].items():
                overall_stats["domain_counts"][k] = overall_stats["domain_counts"].get(k, 0) + v
                
            # Update checkpoint state
            checkpoint_data["processed_files"][filename] = {
                "processed_records": stats["processed_records"],
                "retained_records": stats["retained_records"],
                "duplicate_records": stats["duplicate_records"],
                "processed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ")
            }
            checkpoint_data["overall_stats"] = overall_stats
            
            # Save checkpoint to Google Drive
            print("  Updating checkpoint_1b.json on Google Drive...")
            checkpoint_local_path = LOCAL_TEMP_DIR / "checkpoint_1b.json"
            with open(checkpoint_local_path, 'w', encoding='utf-8') as f:
                json.dump(checkpoint_data, f, indent=2)
                
            checkpoint_file_id = upload_file_to_drive(
                drive_service, checkpoint_local_path, "checkpoint_1b.json", metadata_folder_id, mime_type="application/json"
            )
                
            checkpoint_local_path.unlink()
        except Exception as e:
            print(f"Error processing file {filename}: {e}", file=sys.stderr)
            print("Stopping pipeline run to avoid silent errors. Resume when ready.")
            sys.exit(1)
            
    # Pipeline execution finished - Generate final reports
    print("\nNormalization Pipeline completed successfully!")
    print(f"Total inspected records: {overall_stats['total_records_inspected']}")
    print(f"Total retained records: {overall_stats['total_records_retained']}")
    print(f"Total duplicate records removed: {overall_stats['total_duplicates_found']}")
    
    # Save final report reports folder
    reports_folder_id = drive.folders.get("reports")
    
    # 1. corpus_statistics.json
    print("Uploading corpus_statistics.json...")
    stats_local_path = LOCAL_TEMP_DIR / "corpus_statistics.json"
    with open(stats_local_path, 'w', encoding='utf-8') as f:
        json.dump(overall_stats, f, indent=2)
    upload_file_to_drive(
        drive_service, stats_local_path, "corpus_statistics.json", reports_folder_id, mime_type="application/json"
    )
    stats_local_path.unlink()
    
    # 2. Generate PHASE_1B_REPORT.md
    print("Generating and uploading PHASE_1B_REPORT.md...")
    report_md_content = f"""# Phase 1B: Corpus Inspection & Normalization Report

## Execution Summary
* **Total files inspected**: {overall_stats['total_files_inspected']}
* **Total raw records inspected**: {overall_stats['total_records_inspected']}
* **Total records retained**: {overall_stats['total_records_retained']}
* **Total duplicates removed**: {overall_stats['total_duplicates_found']}
* **Processed at**: {time.strftime("%Y-%m-%d %H:%M:%S UTC")}

## Text Quality Audits
* **Empty text records**: {overall_stats['quality_counts'].get('empty_text', 0)}
* **Extremely short records (< 100 chars)**: {overall_stats['quality_counts'].get('extremely_short_text', 0)}

## Domain Distribution
"""
    for dom, cnt in sorted(overall_stats['domain_counts'].items(), key=lambda x: x[1], reverse=True):
        report_md_content += f"* **{dom}**: {cnt} records\n"
        
    report_md_path = LOCAL_TEMP_DIR / "PHASE_1B_REPORT.md"
    with open(report_md_path, 'w', encoding='utf-8') as f:
        f.write(report_md_content)
        
    upload_file_to_drive(
        drive_service, report_md_path, "PHASE_1B_REPORT.md", reports_folder_id, mime_type="text/markdown"
    )
    report_local_path = BASE_DIR / "Docs" / "PHASE_1B_REPORT.md"
    with open(report_local_path, 'w', encoding='utf-8') as f:
        f.write(report_md_content)
    report_md_path.unlink()
    
    print(f"Pipeline completed successfully. Local summary written to: {report_local_path}")

if __name__ == "__main__":
    main()

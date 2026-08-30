# scripts/chunk_corpus.py
import os
import sys
import socket

# Force Python's socket to resolve IPv4 addresses only to avoid broken IPv6 connection timeouts on Windows
orig_getaddrinfo = socket.getaddrinfo
def forced_ipv4_getaddrinfo(*args, **kwargs):
    if len(args) >= 3:
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
import time
import re
import argparse
from pathlib import Path
import pandas as pd
from dotenv import load_dotenv

# Add workspace to python path
sys.path.append("d:/Abishek")

from scripts.acquire_open_india_law import authenticate_google_drive, GoogleDriveManager
from googleapiclient.http import MediaIoBaseUpload

# Load environment variables
load_dotenv()

# Setup paths
BASE_DIR = Path("d:/Abishek")
LOCAL_CACHE_DIR = BASE_DIR / "Data" / "Normalized"
LOCAL_TEMP_DIR = BASE_DIR / "scratch" / "temp_process"
LOCAL_TEMP_DIR.mkdir(parents=True, exist_ok=True)
LOCAL_CACHE_DIR.mkdir(parents=True, exist_ok=True)
(LOCAL_CACHE_DIR / "legislation").mkdir(parents=True, exist_ok=True)
(LOCAL_CACHE_DIR / "judgments").mkdir(parents=True, exist_ok=True)

# Chunking defaults
MIN_CHUNK_SIZE = 100      # characters
PREFERRED_CHUNK_SIZE = 1500  # characters (approx 250-300 words)
MAX_CHUNK_SIZE = 3000      # characters (approx 500-600 words)
OVERLAP_SIZE = 200        # characters

def calculate_hash(text):
    """Generate MD5 hash of text to help with deduplication."""
    if not text:
        return ""
    return hashlib.md5(text.encode('utf-8')).hexdigest()

def upload_file_to_drive(drive_service, local_path, file_name, folder_id, mime_type="application/octet-stream"):
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

def parse_legislation_text(text):
    """Parses legislation record text to extract metadata attributes and clean text."""
    act = ""
    part = None
    chapter = None
    section = None
    section_title = None
    clean_text = text
    
    if not text.startswith("Act:"):
        return {
            "act": act, "part": part, "chapter": chapter, 
            "section": section, "section_title": section_title, "clean_text": clean_text
        }
        
    act_end = text.find(" | ")
    if act_end != -1:
        act = text[4:act_end].strip()
    else:
        act = text[4:].strip()
        return {
            "act": act, "part": part, "chapter": chapter, 
            "section": section, "section_title": section_title, "clean_text": clean_text
        }
        
    section_match = re.search(r'\bSection\s+([A-Za-z0-9\-]+):', text)
    chapter_match = re.search(r'\bChapter\s+([A-Za-z0-9\-]+):\s*##\s*([^\|]+)', text)
    part_match = re.search(r'\bPart\s+([A-Za-z0-9\-]+):\s*##\s*([^\|]+)', text)
    schedule_match = re.search(r'\bSchedule\s+([A-Za-z0-9\-]+):', text)
    
    if section_match:
        section = section_match.group(1).strip()
        remaining = text[section_match.end():].strip()
        
        # Check for repeated section number title pattern
        # Capped at first 500 characters to prevent catastrophic backtracking on long texts
        title_match = re.match(rf"^(.+?\.)\s*{section}\b", remaining[:500])
        if title_match:
            section_title = title_match.group(1).strip()
            clean_text = remaining
        else:
            clean_text = remaining
    elif schedule_match:
        section = "Schedule " + schedule_match.group(1).strip()
        clean_text = text[schedule_match.end():].strip()
    else:
        preamble_match = re.search(r'\bPreamble\b', text)
        if preamble_match:
            section = "Preamble"
            clean_text = text[preamble_match.end():].strip()
            if clean_text.startswith(":"):
                clean_text = clean_text[1:].strip()
            if clean_text.startswith("|"):
                clean_text = clean_text[1:].strip()
        else:
            in_force_idx = text.find("In Force")
            if in_force_idx != -1:
                clean_text = text[in_force_idx + 8:].strip()
                if clean_text.startswith("|"):
                    clean_text = clean_text[1:].strip()
            else:
                clean_text = text
                
    if chapter_match:
        chapter = "Chapter " + chapter_match.group(1).strip()
        chapter_title = chapter_match.group(2).strip()
        
    if part_match:
        part = "Part " + part_match.group(1).strip()
        
    return {
        "act": act,
        "part": part,
        "chapter": chapter,
        "section": section,
        "section_title": section_title,
        "clean_text": clean_text
    }

def parse_judgment_text(text):
    """Parses judgment record text to extract metadata attributes and clean text."""
    case_name = ""
    court = ""
    section_type = ""
    clean_text = text
    
    # Substring parsing (avoids wildcard regexes to prevent catastrophic backtracking on long texts)
    if text.startswith("Case:"):
        court_idx = text.find("Court:")
        if court_idx != -1:
            case_name_part = text[5:court_idx].strip()
            case_name = re.sub(r'\s*\(\d{4}\)\s*$', '', case_name_part).strip()
            
            section_idx = text.find("Section:", court_idx)
            if section_idx != -1:
                court = text[court_idx + 6:section_idx].strip()
                
                serial_idx = text.find("Serial No.", section_idx)
                if serial_idx != -1:
                    section_type = text[section_idx + 8:serial_idx].strip()
                    
                    # Match Serial No metadata block without backtracks
                    serial_text = text[serial_idx:serial_idx + 100]
                    serial_match = re.match(r'^Serial\s+No\.\s*\d+(?:\s*[\w\s\-]+List)?', serial_text, re.IGNORECASE)
                    if serial_match:
                        end_meta_idx = serial_idx + serial_match.end()
                        clean_text = text[end_meta_idx:].strip()
                    else:
                        list_idx = text.find("List", serial_idx)
                        if list_idx != -1 and list_idx < serial_idx + 50:
                            clean_text = text[list_idx + 4:].strip()
                        else:
                            clean_text = text[serial_idx + 15:].strip()
                else:
                    end_section_idx = -1
                    for keyword in ["[TITLE]", "[SECTION]", "#"]:
                        idx = text.find(keyword, section_idx)
                        if idx != -1:
                            if end_section_idx == -1 or idx < end_section_idx:
                                end_section_idx = idx
                    if end_section_idx != -1:
                        section_type = text[section_idx + 8:end_section_idx].strip()
                        clean_text = text[end_section_idx:].strip()
                    else:
                        section_type = text[section_idx + 8:].strip()
                            
    clean_text = re.sub(r'^\[TITLE\]\s*', '', clean_text)
    clean_text = re.sub(r'^\[SECTION\]\s*', '', clean_text)
    
    return {
        "case_name": case_name,
        "court": court,
        "section_type": section_type,
        "clean_text": clean_text
    }

def split_text_semantically(text, min_size=MIN_CHUNK_SIZE, preferred_size=PREFERRED_CHUNK_SIZE, max_size=MAX_CHUNK_SIZE, overlap=OVERLAP_SIZE):
    """Splits raw text at paragraph/sentence boundaries based on configurable size constraints."""
    if len(text) <= max_size:
        return [text]
        
    paragraphs = [p.strip() for p in text.split('\n') if p.strip()]
    chunks = []
    current_chunk = []
    current_len = 0
    
    for para in paragraphs:
        if len(para) > max_size:
            # Paragraph is too large. Flush current buffer first
            if current_chunk:
                chunks.append("\n\n".join(current_chunk))
                current_chunk = []
                current_len = 0
                
            # Split paragraph into sentences
            sentences = re.split(r'(?<=[.!?])\s+', para)
            curr_para_chunk = []
            curr_para_len = 0
            
            for sent in sentences:
                if len(sent) > max_size:
                    # Sentence is huge. Character split fallback
                    if curr_para_chunk:
                        chunks.append(" ".join(curr_para_chunk))
                        curr_para_chunk = []
                        curr_para_len = 0
                        
                    # Ensure overlap is smaller than max_size to prevent infinite loop
                    safe_overlap = min(overlap, max_size // 2)
                    step_size = max(1, max_size - safe_overlap)
                    start = 0
                    while start < len(sent):
                        end = start + max_size
                        chunk_part = sent[start:end]
                        chunks.append(chunk_part)
                        start += step_size
                else:
                    if curr_para_len + len(sent) + 1 > preferred_size:
                        chunks.append(" ".join(curr_para_chunk))
                        curr_para_chunk = [curr_para_chunk[-1], sent] if curr_para_chunk else [sent]
                        curr_para_len = sum(len(s) for s in curr_para_chunk) + len(curr_para_chunk) - 1
                    else:
                        curr_para_chunk.append(sent)
                        curr_para_len += len(sent) + (1 if curr_para_len > 0 else 0)
                        
            if curr_para_chunk:
                chunks.append(" ".join(curr_para_chunk))
        else:
            if current_len + len(para) + 2 > preferred_size:
                chunks.append("\n\n".join(current_chunk))
                # Start next chunk with paragraph overlap if small enough
                if len(para) < preferred_size // 2:
                    current_chunk = [current_chunk[-1], para] if current_chunk else [para]
                else:
                    current_chunk = [para]
                current_len = sum(len(p) for p in current_chunk) + (2 * (len(current_chunk) - 1))
            else:
                current_chunk.append(para)
                current_len += len(para) + (2 if current_len > 0 else 0)
                
    if current_chunk:
        chunks.append("\n\n".join(current_chunk))
        
    final_chunks = [c for c in chunks if len(c) >= min_size]
    if not final_chunks and len(text) > 0:
        final_chunks = [text]
        
    return final_chunks

def chunk_record(record, filename):
    """Processes a single normalized record and returns a list of chunk dictionaries."""
    doc_type = record.get("document_type", "unknown").lower().strip()
    raw_text = record.get("text", "")
    
    # 1. Parse text structure
    if doc_type == "legislation":
        parsed = parse_legislation_text(raw_text)
        act_name = parsed["act"] or record.get("title", "")
        chapter_name = parsed["chapter"]
        part_name = parsed["part"]
        section_name = parsed["section"]
        section_title = parsed["section_title"]
        clean_text = parsed["clean_text"]
        
        # Build contextual prefix
        prefix_parts = []
        prefix_parts.append(f"[Act: {act_name}]")
        if part_name:
            prefix_parts.append(f"[Part: {part_name}]")
        if chapter_name:
            prefix_parts.append(f"[Chapter: {chapter_name}]")
        if section_name:
            sec_display = f"{section_name} - {section_title}" if section_title else section_name
            prefix_parts.append(f"[Section: {sec_display}]")
            
        context_prefix = "".join(prefix_parts) + "\n\n"
        
        # Structure fields
        court = None
        case_name = None
        citation = record.get("citation")
        act = act_name
        chapter = chapter_name
        part = part_name
        section = section_name
        subsection = None
        clause = None
        paragraph_number = None
        
    elif doc_type == "judgment":
        parsed = parse_judgment_text(raw_text)
        case_name = parsed["case_name"] or record.get("title", "")
        court = parsed["court"] or record.get("court") or record.get("authority", "Court")
        section_type = parsed["section_type"] or "judgment"
        clean_text = parsed["clean_text"]
        
        # Build contextual prefix
        context_prefix = f"[Case: {case_name}][Court: {court}][Section: {section_type}]\n\n"
        
        # Structure fields
        citation = record.get("citation")
        act = None
        chapter = None
        part = None
        section = None
        subsection = None
        clause = None
        paragraph_number = None
        if section_type.lower() == "paragraph":
            paragraph_number = section_type
            
    else:
        # Other/Unknown types
        clean_text = raw_text
        context_prefix = f"[Title: {record.get('title', '')}]\n\n"
        court = record.get("court")
        case_name = record.get("title") if doc_type == "judgment" else None
        citation = record.get("citation")
        act = record.get("title") if doc_type == "legislation" else None
        chapter = None
        part = None
        section = None
        subsection = None
        clause = None
        paragraph_number = None

    # 2. Split text semantically
    text_chunks = split_text_semantically(clean_text)
    
    # 3. Build chunk objects
    chunks = []
    for idx, chunk_text in enumerate(text_chunks):
        # We store the contextualized text in 'text', but also keep parsed metadata fields.
        full_text = context_prefix + chunk_text
        chunk_id = hashlib.md5(f"{record['record_id']}_{idx}_{calculate_hash(full_text)}".encode('utf-8')).hexdigest()
        
        chunk_doc = {
            "chunk_id": chunk_id,
            "document_id": record["record_id"],
            "parent_id": record["record_id"],
            "chunk_index": idx,
            "source_type": doc_type,
            "title": record.get("title", ""),
            "domain": record.get("domain", []),
            "jurisdiction": record.get("jurisdiction", "central"),
            "level": record.get("level", "central"),
            "state": record.get("state"),
            "court": court,
            "act": act,
            "chapter": chapter,
            "part": part,
            "section": section,
            "subsection": subsection,
            "clause": clause,
            "case_name": case_name,
            "citation": citation,
            "paragraph_number": paragraph_number,
            "date": record.get("date"),
            "effective_date": record.get("effective_date"),
            "text": full_text,
            "source_url": record.get("source_url", ""),
            "original_source_id": record.get("original_source_id", ""),
            "dataset_version": record.get("dataset_version", "1.0"),
            "is_historical": record.get("is_historical", False)
        }
        chunks.append(chunk_doc)
        
    return chunks

def process_single_file(drive, drive_service, filename, folder_key, keep_local=False):
    """Downloads, chunks, and uploads a single file to Drive, saving chunks as Parquet."""
    # Resolve the actual filename with .gz if needed
    actual_filename = filename if filename.endswith(".gz") else f"{filename}.gz"
    
    print(f"\nProcessing file: {actual_filename} in folder '{folder_key}'...")
    
    # Determine local normalized cache path
    local_norm_path = LOCAL_CACHE_DIR / folder_key / actual_filename
    local_parquet_name = actual_filename.replace(".jsonl.gz", ".parquet")
    # In case the original had .jsonl and we appended .gz to get .jsonl.gz
    if local_parquet_name.endswith(".jsonl.gz"):
        local_parquet_name = local_parquet_name.replace(".jsonl.gz", ".parquet")
    elif local_parquet_name.endswith(".jsonl.parquet"):
        local_parquet_name = local_parquet_name.replace(".jsonl.parquet", ".parquet")
    local_parquet_path = LOCAL_TEMP_DIR / local_parquet_name
    
    # Check if normalized file is cached locally
    if local_norm_path.exists():
        print(f"  [CACHE HIT] Found normalized file locally at {local_norm_path}")
    else:
        # Download normalized file from Google Drive 02_normalized folder
        print("  [CACHE MISS] Downloading normalized file from Google Drive...")
        norm_root_id = drive.get_or_create_subfolder("02_normalized", drive.root_id)
        norm_dest_folder_id = drive.get_or_create_subfolder(folder_key, norm_root_id)
        
        q = f"name = '{actual_filename}' and '{norm_dest_folder_id}' in parents and trashed = false"
        results = drive_service.files().list(q=q, fields="files(id)").execute(num_retries=5)
        files = results.get('files', [])
        
        if not files:
            raise IOError(f"Could not find normalized file {actual_filename} in GDrive folder 02_normalized/{folder_key}")
            
        file_id = files[0]["id"]
        content_bytes = drive.download_file_content(file_id)
        if not content_bytes:
            raise IOError(f"Failed to download normalized file {actual_filename} from Google Drive")
            
        # Save to cache path
        with open(local_norm_path, 'wb') as f:
            f.write(content_bytes)
            
    # Process file line-by-line
    print("  Chunking records...")
    partition_chunks = []
    processed_docs = 0
    skipped_docs = 0
    duplicate_chunks_count = 0
    seen_chunk_hashes = set()
    total_chunks_created = 0
    partition_index = 1
    total_uploaded_size = 0
    
    # Google Drive destinations
    chunked_root_id = drive.get_or_create_subfolder("03_chunked", drive.root_id)
    chunked_dest_folder_id = drive.get_or_create_subfolder(folder_key, chunked_root_id)
    
    CHUNKS_PER_PARTITION = 250000  # 250k chunks per file (~50-100MB Parquet)
    
    # Track statistics
    stats = {
        "processed_records": 0,
        "legislation_chunks": 0,
        "judgment_chunks": 0,
        "other_chunks": 0,
        "chunk_lengths": [],
        "domains": {},
        "jurisdictions": {},
        "courts": {},
        "skipped_reasons": {}
    }
    
    def flush_partition(chunks_list, part_idx):
        nonlocal total_uploaded_size
        if not chunks_list:
            return 0
        part_name = actual_filename.replace(".jsonl.gz", f"_part_{part_idx:04d}.parquet")
        # In case the original had .jsonl and we appended .gz
        if part_name.endswith(".jsonl_part_{part_idx:04d}.parquet"):
            part_name = part_name.replace(".jsonl_part_{part_idx:04d}.parquet", f"_part_{part_idx:04d}.parquet")
        elif part_name.endswith(".jsonl.parquet"):
            part_name = part_name.replace(".jsonl.parquet", f"_part_{part_idx:04d}.parquet")
            
        temp_parquet_path = LOCAL_TEMP_DIR / part_name
        
        print(f"  Writing partition {part_idx} ({len(chunks_list)} chunks) to Parquet format...")
        df_part = pd.DataFrame(chunks_list)
        df_part.to_parquet(temp_parquet_path, index=False, compression='snappy')
        
        file_size = temp_parquet_path.stat().st_size
        total_uploaded_size += file_size
        
        print(f"  Uploading partition {part_idx} ({file_size / (1024*1024):.2f} MB) to Google Drive...")
        upload_file_to_drive(drive_service, temp_parquet_path, part_name, chunked_dest_folder_id, mime_type="application/octet-stream")
        
        # Clean up local file
        temp_parquet_path.unlink()
        return len(chunks_list)
        
    start_time = time.time()
    with gzip.open(local_norm_path, 'rt', encoding='utf-8') as f_in:
        for line in f_in:
            if not line.strip():
                continue
            try:
                record = json.loads(line)
                processed_docs += 1
                
                # Chunk this record
                record_chunks = chunk_record(record, actual_filename)
                
                if not record_chunks:
                    skipped_docs += 1
                    stats["skipped_reasons"]["no_valid_chunks"] = stats["skipped_reasons"].get("no_valid_chunks", 0) + 1
                    continue
                    
                for chk in record_chunks:
                    # Chunk level deduplication
                    text_hash = calculate_hash(chk["text"])
                    if text_hash in seen_chunk_hashes:
                        duplicate_chunks_count += 1
                        continue
                    seen_chunk_hashes.add(text_hash)
                    
                    # Accumulate in partition list
                    partition_chunks.append(chk)
                    total_chunks_created += 1
                    
                    # Update stats
                    chunk_len = len(chk["text"])
                    stats["chunk_lengths"].append(chunk_len)
                    
                    doc_type = chk["source_type"]
                    if doc_type == "legislation":
                        stats["legislation_chunks"] += 1
                    elif doc_type == "judgment":
                        stats["judgment_chunks"] += 1
                    else:
                        stats["other_chunks"] += 1
                        
                    for dom in chk["domain"]:
                        stats["domains"][dom] = stats["domains"].get(dom, 0) + 1
                        
                    juris = chk["jurisdiction"] or "unknown"
                    stats["jurisdictions"][juris] = stats["jurisdictions"].get(juris, 0) + 1
                    
                    court = chk["court"]
                    if court:
                        stats["courts"][court] = stats["courts"].get(court, 0) + 1
                        
                # Check if we should flush the partition
                if len(partition_chunks) >= CHUNKS_PER_PARTITION:
                    flush_partition(partition_chunks, partition_index)
                    partition_chunks = []
                    partition_index += 1
                    
            except Exception as e:
                skipped_docs += 1
                stats["skipped_reasons"]["parse_error"] = stats["skipped_reasons"].get("parse_error", 0) + 1
                print(f"    Warning: Error chunking record in {actual_filename}: {e}", file=sys.stderr)
                
    # Flush remaining chunks
    if partition_chunks:
        flush_partition(partition_chunks, partition_index)
        partition_chunks = []
        
    elapsed_time = time.time() - start_time
    
    print(f"  Done. Processed {processed_docs} documents, generated {total_chunks_created} chunks in {partition_index} partitions.")
    
    if not keep_local:
        local_norm_path.unlink()
        
    return {
        "processed_records": processed_docs,
        "total_chunks": total_chunks_created,
        "legislation_chunks": stats["legislation_chunks"],
        "judgment_chunks": stats["judgment_chunks"],
        "other_chunks": stats["other_chunks"],
        "duplicate_chunks": duplicate_chunks_count,
        "skipped_records": stats["skipped_reasons"].get("parse_error", 0) + stats["skipped_reasons"].get("no_valid_chunks", 0),
        "chunk_size_dist": stats["chunk_lengths"],
        "stats": stats,
        "file_size_bytes": total_uploaded_size,
        "processing_time": elapsed_time
    }

def merge_distributions(list_a, list_b):
    """Safely combine two numeric lists for size distributions."""
    return list_a + list_b

def main():
    parser = argparse.ArgumentParser(description="Legal-Aware Chunking Pipeline (Phase 1C)")
    parser.add_argument("--limit-files", type=int, default=None, help="Limit the number of files to process in this run")
    parser.add_argument("--keep-local", action="store_true", help="Keep local normalized JSONL.GZ files in cache")
    parser.add_argument("--poll", action="store_true", help="Poll continuously waiting for Phase 1B to complete")
    parser.add_argument("--poll-interval", type=int, default=60, help="Polling interval in seconds (default: 60)")
    args = parser.parse_args()

    print("Initializing Phase 1C Chunking Pipeline...")
    drive_service = authenticate_google_drive()
    drive = GoogleDriveManager(drive_service)
    
    metadata_folder_id = drive.folders.get("metadata")
    reports_folder_id = drive.folders.get("reports")
    
    # Initialize/load checkpoint 1c
    checkpoint_1c_id = None
    checkpoint_data_1c = {"processed_files": {}, "overall_stats": {}}
    
    q = f"name = 'checkpoint_1c.json' and '{metadata_folder_id}' in parents and trashed = false"
    res = drive_service.files().list(q=q, fields="files(id)").execute()
    files = res.get('files', [])
    if files:
        checkpoint_1c_id = files[0]['id']
        print("Found existing checkpoint_1c.json on Google Drive. Resuming...")
        content_bytes = drive.download_file_content(checkpoint_1c_id)
        if content_bytes:
            checkpoint_data_1c = json.loads(content_bytes.decode('utf-8'))
            if "processed_files" not in checkpoint_data_1c:
                checkpoint_data_1c["processed_files"] = {}
            
    # Setup overall stats with safe merging
    default_stats = {
        "total_files_chunked": 0,
        "total_records_consumed": 0,
        "total_chunks_created": 0,
        "legislation_chunks": 0,
        "judgment_chunks": 0,
        "other_chunks": 0,
        "duplicate_chunks": 0,
        "skipped_records": 0,
        "total_storage_size_bytes": 0,
        "total_processing_time": 0.0,
        "domain_distribution": {},
        "jurisdiction_distribution": {},
        "court_distribution": {},
        "chunk_lengths": []
    }
    
    loaded_stats = checkpoint_data_1c.get("overall_stats", {})
    overall_stats = {**default_stats, **loaded_stats}
    
    # Loop for polling
    run_continuous = args.poll
    while True:
        # Download checkpoint_1b.json to see what's completed
        print("Downloading checkpoint_1b.json from Google Drive...")
        q_1b = f"name = 'checkpoint_1b.json' and '{metadata_folder_id}' in parents and trashed = false"
        res_1b = drive_service.files().list(q=q_1b, fields="files(id)").execute()
        files_1b = res_1b.get('files', [])
        
        if not files_1b:
            print("Warning: No checkpoint_1b.json found! Phase 1B might not have written yet.")
            if run_continuous:
                print(f"Sleeping for {args.poll_interval}s before retry...")
                time.sleep(args.poll_interval)
                continue
            else:
                print("Exiting pipeline.")
                sys.exit(0)
                
        file_1b_id = files_1b[0]['id']
        content_bytes_1b = drive.download_file_content(file_1b_id)
        if not content_bytes_1b:
            print("Failed to download checkpoint_1b.json. Exiting.")
            sys.exit(1)
            
        checkpoint_data_1b = json.loads(content_bytes_1b.decode('utf-8'))
        completed_1b_files = checkpoint_data_1b.get("processed_files", {})
        
        # Identify files complete in 1B but pending in 1C
        pending_files = []
        
        # List raw filtered files to know original folder mappings
        file_folder_mappings = {}
        for folder_key in ["legislation", "judgments"]:
            f_id = drive.folders.get(folder_key)
            res_list = drive_service.files().list(
                q=f"'{f_id}' in parents and trashed = false",
                fields="files(name)"
            ).execute()
            for f in res_list.get('files', []):
                file_folder_mappings[f["name"]] = folder_key
                
        for filename, info in completed_1b_files.items():
            if filename not in checkpoint_data_1c["processed_files"]:
                folder_key = file_folder_mappings.get(filename)
                if not folder_key:
                    folder_key = "judgments" if "judgment" in filename else "legislation"
                pending_files.append({
                    "name": filename,
                    "folder_key": folder_key
                })
                
        print(f"Phase 1B completed files count: {len(completed_1b_files)}")
        print(f"Phase 1C already processed count: {len(checkpoint_data_1c['processed_files'])}")
        print(f"Pending files for Phase 1C: {len(pending_files)}")
        
        if not pending_files:
            if run_continuous:
                if len(completed_1b_files) >= 59:
                    print("All files processed by Phase 1B and Phase 1C is fully caught up! Exiting polling loop.")
                    break
                else:
                    print(f"No new files to process. Polling again in {args.poll_interval} seconds...")
                    time.sleep(args.poll_interval)
                    continue
            else:
                print("No pending files. Chunking is caught up.")
                break
                
        # Process files
        processed_this_run = 0
        for idx, file_info in enumerate(pending_files, 1):
            filename = file_info["name"]
            folder_key = file_info["folder_key"]
            
            if args.limit_files is not None and processed_this_run >= args.limit_files:
                print(f"Reached execution file limit of {args.limit_files}. Stopping this batch.")
                break
                
            print(f"\n[{idx}/{len(pending_files)}] Running Chunking...")
            try:
                stats = process_single_file(drive, drive_service, filename, folder_key, keep_local=args.keep_local)
                processed_this_run += 1
                
                # Accumulate overall stats
                overall_stats["total_files_chunked"] += 1
                overall_stats["total_records_consumed"] += stats["processed_records"]
                overall_stats["total_chunks_created"] += stats["total_chunks"]
                overall_stats["legislation_chunks"] += stats["legislation_chunks"]
                overall_stats["judgment_chunks"] += stats["judgment_chunks"]
                overall_stats["other_chunks"] += stats["other_chunks"]
                overall_stats["duplicate_chunks"] += stats["duplicate_chunks"]
                overall_stats["skipped_records"] += stats["skipped_records"]
                overall_stats["total_storage_size_bytes"] += stats["file_size_bytes"]
                overall_stats["total_processing_time"] += stats["processing_time"]
                
                # Combine size distributions (capped at 50,000 for memory sanity)
                overall_stats["chunk_lengths"] = merge_distributions(overall_stats["chunk_lengths"], stats["chunk_size_dist"])
                if len(overall_stats["chunk_lengths"]) > 50000:
                    overall_stats["chunk_lengths"] = overall_stats["chunk_lengths"][-50000:]
                    
                # Merge categorical stats
                for k, v in stats["stats"]["domains"].items():
                    overall_stats["domain_distribution"][k] = overall_stats["domain_distribution"].get(k, 0) + v
                for k, v in stats["stats"]["jurisdictions"].items():
                    overall_stats["jurisdiction_distribution"][k] = overall_stats["jurisdiction_distribution"].get(k, 0) + v
                for k, v in stats["stats"]["courts"].items():
                    overall_stats["court_distribution"][k] = overall_stats["court_distribution"].get(k, 0) + v
                    
                # Update checkpoint
                checkpoint_data_1c["processed_files"][filename] = {
                    "processed_records": stats["processed_records"],
                    "total_chunks": stats["total_chunks"],
                    "duplicate_chunks": stats["duplicate_chunks"],
                    "skipped_records": stats["skipped_records"],
                    "file_size_bytes": stats["file_size_bytes"],
                    "processed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ")
                }
                checkpoint_data_1c["overall_stats"] = overall_stats
                
                # Save checkpoint to Google Drive
                print("  Updating checkpoint_1c.json on Google Drive...")
                checkpoint_local_path = LOCAL_TEMP_DIR / "checkpoint_1c.json"
                with open(checkpoint_local_path, 'w', encoding='utf-8') as f_out:
                    json.dump(checkpoint_data_1c, f_out, indent=2)
                drive.upload_file(checkpoint_local_path, "checkpoint_1c.json", "metadata", mime_type="application/json")
                checkpoint_local_path.unlink()
                
            except Exception as e:
                print(f"Error chunking file {filename}: {e}", file=sys.stderr)
                print("Terminating Phase 1C run to avoid cascade failures. Resume when ready.")
                sys.exit(1)
                
        if not run_continuous:
            break
            
    # Pipeline execution finished - Compile reports
    print("\nChunking Pipeline completed successfully!")
    print(f"Total documents chunked: {overall_stats['total_records_consumed']}")
    print(f"Total chunks created: {overall_stats['total_chunks_created']}")
    print(f"Legislation chunks: {overall_stats['legislation_chunks']}")
    print(f"Judgment chunks: {overall_stats['judgment_chunks']}")
    print(f"Other chunks: {overall_stats['other_chunks']}")
    print(f"Total duplicate chunks removed: {overall_stats['duplicate_chunks']}")
    
    lengths = overall_stats["chunk_lengths"]
    avg_len = sum(lengths) / len(lengths) if lengths else 0
    sorted_lens = sorted(lengths)
    median_len = sorted_lens[len(sorted_lens)//2] if sorted_lens else 0
    max_len = max(lengths) if lengths else 0
    min_len = min(lengths) if lengths else 0
    
    # Save statistics report locally and upload to Drive
    stats_summary = {
        "overall_stats": overall_stats,
        "calculated_distributions": {
            "avg_chunk_size_chars": avg_len,
            "median_chunk_size_chars": median_len,
            "max_chunk_size_chars": max_len,
            "min_chunk_size_chars": min_len,
            "chunk_count": len(lengths)
        }
    }
    
    stats_local_path = LOCAL_TEMP_DIR / "chunking_statistics.json"
    with open(stats_local_path, 'w', encoding='utf-8') as f_out:
        json.dump(stats_summary, f_out, indent=2)
    drive.upload_file(stats_local_path, "chunking_statistics.json", "reports", mime_type="application/json")
    stats_local_path.unlink()
    
    # Generate Docs/PHASE_1C_REPORT.md
    print("Generating PHASE_1C_REPORT.md...")
    report_content = f"""# Phase 1C: Legal-Aware Chunking & RAG Indexing Report

## Execution Summary
* **Total files processed**: {overall_stats['total_files_chunked']}
* **Total normalized records consumed**: {overall_stats['total_records_consumed']:,}
* **Total chunks created**: {overall_stats['total_chunks_created']:,}
* **Legislation chunks**: {overall_stats['legislation_chunks']:,}
* **Judgment chunks**: {overall_stats['judgment_chunks']:,}
* **Other chunks**: {overall_stats['other_chunks']:,}
* **Duplicate chunks removed**: {overall_stats['duplicate_chunks']:,}
* **Skipped/invalid records**: {overall_stats['skipped_records']:,}
* **Total storage size (Parquet)**: {overall_stats['total_storage_size_bytes'] / (1024*1024):.2f} MB
* **Total processing time**: {overall_stats['total_processing_time']:.2f} seconds
* **Processing rate**: {overall_stats['total_records_consumed'] / (overall_stats['total_processing_time'] or 1):.2f} records/sec
* **Processed at**: {time.strftime("%Y-%m-%d %H:%M:%S UTC")}

## Chunk Size Distribution (Characters)
* **Minimum chunk size**: {min_len} chars
* **Average chunk size**: {avg_len:.2f} chars
* **Median chunk size**: {median_len} chars
* **Maximum chunk size**: {max_len} chars

## Domain Distribution
"""
    for dom, cnt in sorted(overall_stats['domain_distribution'].items(), key=lambda x: x[1], reverse=True):
        report_content += f"* **{dom}**: {cnt:,} chunks\n"
        
    report_content += "\n## Jurisdiction Distribution\n"
    for juris, cnt in sorted(overall_stats['jurisdiction_distribution'].items(), key=lambda x: x[1], reverse=True):
        report_content += f"* **{juris}**: {cnt:,} chunks\n"
        
    report_content += "\n## Court Distribution (Top 15)\n"
    for court, cnt in sorted(overall_stats['court_distribution'].items(), key=lambda x: x[1], reverse=True)[:15]:
        report_content += f"* **{court}**: {cnt:,} chunks\n"
        
    # Write to local Docs
    local_report_path = BASE_DIR / "Docs" / "PHASE_1C_REPORT.md"
    with open(local_report_path, 'w', encoding='utf-8') as f_out:
        f_out.write(report_content)
        
    # Upload to Google Drive
    temp_report_path = LOCAL_TEMP_DIR / "PHASE_1C_REPORT.md"
    with open(temp_report_path, 'w', encoding='utf-8') as f_out:
        f_out.write(report_content)
    drive.upload_file(temp_report_path, "PHASE_1C_REPORT.md", "reports", mime_type="text/markdown")
    temp_report_path.unlink()
    
    print(f"Pipeline completed successfully. Local summary report written to: {local_report_path}")

if __name__ == "__main__":
    main()

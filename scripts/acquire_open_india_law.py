# scripts/acquire_open_india_law.py
import os
import sys
import json
import hashlib
import argparse
import tempfile
import pandas as pd
from pathlib import Path
from dotenv import load_dotenv
from huggingface_hub import HfApi, hf_hub_download
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# Load environment variables
load_dotenv()

# Setup Paths
BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_DIR = BASE_DIR / "config"
DOMAIN_MAPPING_PATH = CONFIG_DIR / "domain_mapping.json"
CREDENTIALS_PATH = BASE_DIR / "Credentials.json"
TOKEN_PATH = BASE_DIR / "token.json"

# Google Drive API scopes
SCOPES = ['https://www.googleapis.com/auth/drive']

def get_hf_token():
    """Retrieve HF Token from environment."""
    token = os.getenv("HF_TOKEN")
    if token:
         token = token.strip().replace("'", "").replace('"', '')
    return token

def authenticate_google_drive():
    """Authenticate with Google Drive using Credentials.json and Desktop flow."""
    creds = None
    if TOKEN_PATH.exists():
        try:
            creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)
        except Exception as e:
            print(f"Warning: Could not load token.json: {e}. Re-authenticating.")
            
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("Refreshing expired Google Drive token...")
            try:
                creds.refresh(Request())
            except Exception as e:
                print(f"Refresh failed: {e}. Running full auth flow.")
                creds = None
                
        if not creds:
            if not CREDENTIALS_PATH.exists():
                print("Error: Credentials.json not found in the workspace root!")
                print("Please download it from Google Cloud Console and save it as Credentials.json.")
                sys.exit(1)
            print("Running Google Drive Desktop Authentication Flow...")
            flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_PATH), SCOPES)
            creds = flow.run_local_server(port=0)
            
        # Save token
        with open(TOKEN_PATH, 'w') as token_file:
            token_file.write(creds.to_json())
            
    return build('drive', 'v3', credentials=creds)

class GoogleDriveManager:
    """Manages files and folder structures inside Google Drive."""
    def __init__(self, drive_service):
        self.service = drive_service
        self.root_id = self.get_or_create_root_folder()
        self.folders = self.init_folder_structure()

    def get_or_create_root_folder(self):
        """Locates the 'BetterCallSaul Dataset' folder, creating it if missing."""
        q = "name = 'BetterCallSaul Dataset' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
        results = self.service.files().list(q=q, fields="files(id, name)").execute()
        files = results.get('files', [])
        
        if files:
            folder_id = files[0]['id']
            print(f"Found existing Google Drive root folder 'BetterCallSaul Dataset' (ID: {folder_id})")
            return folder_id
        else:
            file_metadata = {
                'name': 'BetterCallSaul Dataset',
                'mimeType': 'application/vnd.google-apps.folder'
            }
            folder = self.service.files().create(body=file_metadata, fields='id').execute()
            folder_id = folder.get('id')
            print(f"Created new Google Drive root folder 'BetterCallSaul Dataset' (ID: {folder_id})")
            return folder_id

    def get_or_create_subfolder(self, name, parent_id):
        """Locates or creates a subfolder within a parent folder."""
        q = f"name = '{name}' and '{parent_id}' in parents and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
        results = self.service.files().list(q=q, fields="files(id, name)").execute()
        files = results.get('files', [])
        
        if files:
            return files[0]['id']
        else:
            file_metadata = {
                'name': name,
                'mimeType': 'application/vnd.google-apps.folder',
                'parents': [parent_id]
            }
            folder = self.service.files().create(body=file_metadata, fields='id').execute()
            return folder.get('id')

    def init_folder_structure(self):
        """Initializes the complete dataset acquisition directory structure on Drive."""
        folders = {}
        raw_filtered_id = self.get_or_create_subfolder("01_raw_filtered", self.root_id)
        metadata_id = self.get_or_create_subfolder("03_metadata", self.root_id)
        reports_id = self.get_or_create_subfolder("04_reports", self.root_id)
        
        folders["legislation"] = self.get_or_create_subfolder("legislation", raw_filtered_id)
        folders["judgments"] = self.get_or_create_subfolder("judgments", raw_filtered_id)
        folders["metadata"] = metadata_id
        folders["reports"] = reports_id
        
        return folders

    def check_file_exists(self, file_name, folder_key):
        """Checks if a file exists in the specified folder. Returns file_id if yes, else None."""
        parent_id = self.folders.get(folder_key)
        if not parent_id:
            return None
        q = f"name = '{file_name}' and '{parent_id}' in parents and trashed = false"
        results = self.service.files().list(q=q, fields="files(id)").execute()
        files = results.get('files', [])
        return files[0]['id'] if files else None

    def download_file_content(self, file_id):
        """Downloads the content of a file from Google Drive as bytes."""
        try:
            return self.service.files().get_media(fileId=file_id).execute()
        except Exception as e:
            print(f"Error downloading file {file_id}: {e}")
            return None

    def upload_file(self, local_path, file_name, folder_key, mime_type="application/json"):
        """Uploads a local file to a Google Drive folder. Overwrites if already exists."""
        parent_id = self.folders.get(folder_key)
        if not parent_id:
            raise ValueError(f"Invalid folder key: {folder_key}")
            
        q = f"name = '{file_name}' and '{parent_id}' in parents and trashed = false"
        results = self.service.files().list(q=q, fields="files(id)").execute()
        files = results.get('files', [])
        
        if files:
            file_id = files[0]['id']
            print(f"File '{file_name}' already exists in folder '{folder_key}' (ID: {file_id}). Overwriting...")
            media = MediaFileUpload(str(local_path), mimetype=mime_type, resumable=True)
            self.service.files().update(fileId=file_id, media_body=media).execute()
            return file_id
            
        file_metadata = {
            'name': file_name,
            'parents': [parent_id]
        }
        media = MediaFileUpload(str(local_path), mimetype=mime_type, resumable=True)
        file = self.service.files().create(body=file_metadata, media_body=media, fields='id').execute()
        file_id = file.get('id')
        print(f"Uploaded '{file_name}' (ID: {file_id})")
        return file_id

def load_domain_keywords():
    """Load config/domain_mapping.json containing keywords per domain."""
    if not DOMAIN_MAPPING_PATH.exists():
        print(f"Error: domain_mapping.json not found at {DOMAIN_MAPPING_PATH}!")
        sys.exit(1)
    with open(DOMAIN_MAPPING_PATH, 'r') as f:
        return json.load(f)

def classify_text(text, domain_keywords):
    """Checks text against domain keywords, returns matching domain if any, else None."""
    if not text or not isinstance(text, str):
        return None
    text_lower = text.lower()
    for domain, keywords in domain_keywords.items():
        for kw in keywords:
            if kw in text_lower:
                return domain
    return None

def process_and_filter_file(local_file_path, filename, domain_keywords, dry_run=False, limit_rows=None):
    """Loads Parquet file locally, applies domain filtering, and cleans duplicates."""
    df = pd.read_parquet(local_file_path)
    original_row_count = len(df)
    
    # Determine document type
    is_judgment = "judgment" in filename
    doc_type = "judgment" if is_judgment else "legislation"
    
    # Extract state name from filename
    parts = filename.split('_')
    state_name = ""
    level = "central"
    if len(parts) >= 3:
        raw_state = parts[1]
        if raw_state == "central":
            level = "central"
        else:
            level = "state"
            state_name = raw_state.replace('-', ' ').title()
            
    filtered_records = []
    seen_hashes = set()
    
    # If dry_run or limit_rows, reduce dataset
    if limit_rows:
        df = df.head(limit_rows)
    elif dry_run:
        df = df.head(500)
        
    for idx, row in df.iterrows():
        classification_text = ""
        title = ""
        text_content = ""
        year = None
        source_url = ""
        authority = ""
        
        if is_judgment:
            title = row.get("title", "")
            text_content = row.get("text", "")
            classification_text = f"{title} {row.get('description', '')} {text_content}"
            year = row.get("year")
            source_url = row.get("source_url", "")
            authority = row.get("court", "Court")
        else:
            title = row.get("title", "")
            text_content = row.get("text", "")
            classification_text = f"{title} {row.get('section_title', '')} {text_content}"
            year = row.get("year")
            source_url = row.get("source_url", "")
            authority = row.get("source_publisher", "Legislative Department")
            
        # Classify domain
        matched_domain = classify_text(classification_text, domain_keywords)
        if not matched_domain:
            continue
            
        # Deduplication using content hash
        content_hash = hashlib.md5(text_content.encode('utf-8', errors='ignore')).hexdigest()
        if content_hash in seen_hashes:
            continue
        seen_hashes.add(content_hash)
        
        record = {
            "jurisdiction": "central" if level == "central" else "state",
            "level": level,
            "state": state_name,
            "domain": matched_domain,
            "document_type": doc_type,
            "title": title,
            "year": int(year) if pd.notna(year) else None,
            "authority": authority,
            "text": text_content,
            "source": filename,
            "source_url": source_url
        }
        filtered_records.append(record)
        
    return filtered_records, original_row_count

def upload_manifest_and_report(temp_path, manifest, drive):
    """Helper function to compile and upload current manifest.json and acquisition_report.md."""
    manifest_path = temp_path / "manifest.json"
    with open(manifest_path, 'w', encoding='utf-8') as m_f:
        json.dump(manifest, m_f, indent=2, ensure_ascii=False)
    drive.upload_file(manifest_path, "manifest.json", "metadata", mime_type="application/json")
    
    report_json_path = temp_path / "acquisition_report.json"
    with open(report_json_path, 'w', encoding='utf-8') as rj_f:
        json.dump(manifest, rj_f, indent=2, ensure_ascii=False)
    drive.upload_file(report_json_path, "acquisition_report.json", "reports", mime_type="application/json")
    
    total_original_rows = sum(f["original_records"] for f in manifest["files_processed"])
    total_filtered_rows = sum(f["filtered_records"] for f in manifest["files_processed"])
    total_size_bytes = sum(f["file_size_bytes"] for f in manifest["files_processed"])
    
    report_md_content = f"""# Phase 1A Dataset Acquisition Report

* **Acquisition Run Date:** {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}
* **Source Dataset:** [vaquill/open-india-law](https://huggingface.co/datasets/vaquill/open-india-law)
* **Dry Run:** {manifest.get('dry_run', False)}

## Summary Statistics

* **Total Records in Source Subsets:** {total_original_rows:,}
* **Total Domain-Filtered Records:** {total_filtered_rows:,}
* **Compression Rate (Filtering Efficiency):** {(100 - (total_filtered_rows / (total_original_rows or 1)) * 100):.2f}% of records filtered out
* **Total Upload Storage Size:** {total_size_bytes / (1024*1024):.2f} MB

## Processed Files Breakdown

| Source File | Output File (Drive) | Original Chunks | Filtered Chunks | Size (MB) | Drive Folder |
|-------------|---------------------|-----------------|-----------------|-----------|--------------|
"""
    for f_info in manifest["files_processed"]:
        f_size_mb = f_info["file_size_bytes"] / (1024*1024)
        folder = "judgments" if "judgment" in f_info["source_file"] else "legislation"
        report_md_content += f"| {f_info['source_file']} | {f_info['output_file']} | {f_info['original_records']:,} | {f_info['filtered_records']:,} | {f_size_mb:.2f} MB | {folder} |\n"
        
    report_md_content += "\n*Note: Private database credentials and Hugging Face tokens are fully protected and excluded from public code tracking.*"
    
    report_md_path = temp_path / "acquisition_report.md"
    with open(report_md_path, 'w', encoding='utf-8') as r_f:
        r_f.write(report_md_content)
    drive.upload_file(report_md_path, "acquisition_report.md", "reports", mime_type="text/markdown")

def run_acquisition(dry_run=False, limit_rows=None, target_files=None):
    """Main acquisition driver with checkpointing and skipping."""
    hf_token = get_hf_token()
    if not hf_token:
        print("Error: HF_TOKEN not configured in environment or .env file!")
        sys.exit(1)
        
    # 1. Load domain keywords
    domain_keywords = load_domain_keywords()
    
    # 2. Authenticate Google Drive
    print("Connecting to Google Drive...")
    drive_service = authenticate_google_drive()
    drive = GoogleDriveManager(drive_service)
    
    # 3. Pull existing manifest from Google Drive if it exists to resume progress
    manifest = {
        "dataset_name": "vaquill/open-india-law",
        "processed_at": pd.Timestamp.now().isoformat(),
        "dry_run": dry_run,
        "files_processed": []
    }
    
    existing_manifest_id = drive.check_file_exists("manifest.json", "metadata")
    if existing_manifest_id:
        print(f"Found existing manifest.json in Google Drive (ID: {existing_manifest_id}). Downloading to resume...")
        content_bytes = drive.download_file_content(existing_manifest_id)
        if content_bytes:
            try:
                manifest = json.loads(content_bytes.decode('utf-8'))
                print(f"Resuming acquisition. Already completed {len(manifest['files_processed'])} files.")
            except Exception as e:
                print(f"Warning: Could not parse existing manifest: {e}. Starting fresh.")
                
    # 4. Get HF Repository Details
    api = HfApi(token=hf_token)
    try:
        info = api.dataset_info("vaquill/open-india-law")
    except Exception as e:
        print(f"Error accessing vaquill/open-india-law dataset: {e}")
        print("Verify your HF_TOKEN has correct permissions and you accepted the gated repository agreement.")
        sys.exit(1)
        
    all_parquet_files = [f.rfilename for f in info.siblings if f.rfilename.endswith('.parquet')]
    print(f"Found {len(all_parquet_files)} files in vaquill/open-india-law repo.")
    
    # Filter files to target list if provided, otherwise filter by dry_run constraints
    if target_files:
        files_to_process = [f for f in all_parquet_files if any(tf in f for tf in target_files)]
    elif dry_run:
        # Dry-run: process only 2 small files
        files_to_process = ["in_central_legislation.parquet", "in_cpcb_regulations.parquet"]
    else:
        # Full run: process everything
        files_to_process = all_parquet_files
        
    print(f"Files scheduled for processing: {files_to_process}")
    
    # List of already completed filenames to skip
    completed_filenames = {f["source_file"] for f in manifest["files_processed"]}
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        for filename in files_to_process:
            output_filename = f"filtered_{filename.replace('.parquet', '.jsonl')}"
            folder_key = "judgments" if "judgment" in filename else "legislation"
            
            # CHECKPOINT: Skip if already marked completed in manifest AND exists on Google Drive
            if filename in completed_filenames:
                existing_file_id = drive.check_file_exists(output_filename, folder_key)
                if existing_file_id:
                    print(f"\n[SKIP] File '{filename}' is already processed and exists in folder '{folder_key}' (ID: {existing_file_id}). skipping.")
                    continue
                    
            print(f"\n--- Processing File: {filename} (Download & Local Filter) ---")
            
            # Step A: Download compressed Parquet file locally
            print("Downloading from HuggingFace...")
            try:
                local_file = hf_hub_download(
                    repo_id="vaquill/open-india-law",
                    filename=filename,
                    repo_type="dataset",
                    token=hf_token,
                    local_dir=str(temp_path)
                )
            except Exception as e:
                print(f"Error downloading {filename} from HuggingFace: {e}. Skipping.")
                continue
            
            # Step B: Read and filter locally in-memory (Incredibly fast)
            print("Filtering and classifying records locally...")
            records, orig_count = process_and_filter_file(
                local_file,
                filename,
                domain_keywords,
                dry_run=dry_run,
                limit_rows=limit_rows
            )
            
            filtered_count = len(records)
            print(f"Filtered down from {orig_count} to {filtered_count} unique matching records.")
            
            if filtered_count == 0:
                print(f"No records matched criteria for {filename}. Skipping upload.")
                manifest["files_processed"] = [f for f in manifest["files_processed"] if f["source_file"] != filename]
                manifest["files_processed"].append({
                    "source_file": filename,
                    "output_file": "",
                    "original_records": orig_count,
                    "filtered_records": 0,
                    "gdrive_file_id": "",
                    "file_size_bytes": 0
                })
                upload_manifest_and_report(temp_path, manifest, drive)
                os.remove(local_file)
                continue
                
            # Write only the filtered rows to a local JSONL file
            output_file_path = temp_path / output_filename
            with open(output_file_path, 'w', encoding='utf-8') as out_f:
                for rec in records:
                    out_f.write(json.dumps(rec, ensure_ascii=False) + '\n')
                    
            file_size = output_file_path.stat().st_size
            
            # Upload filtered JSONL to Google Drive
            print(f"Uploading filtered JSONL to Google Drive folder '{folder_key}'...")
            drive_id = drive.upload_file(output_file_path, output_filename, folder_key, mime_type="application/x-jsonlines")
            
            # Update manifest list
            manifest["files_processed"] = [f for f in manifest["files_processed"] if f["source_file"] != filename]
            manifest["files_processed"].append({
                "source_file": filename,
                "output_file": output_filename,
                "original_records": orig_count,
                "filtered_records": filtered_count,
                "gdrive_file_id": drive_id,
                "file_size_bytes": file_size
            })
            
            # Save checkpoint (manifest.json and report.md) after every successful upload
            print("Saving checkpoint files on Google Drive...")
            upload_manifest_and_report(temp_path, manifest, drive)
            
            # Clean up local temp files immediately to free space
            os.remove(local_file)
            os.remove(output_file_path)
            
    # Final Summary display
    total_original_rows = sum(f["original_records"] for f in manifest["files_processed"])
    total_filtered_rows = sum(f["filtered_records"] for f in manifest["files_processed"])
    total_size_bytes = sum(f["file_size_bytes"] for f in manifest["files_processed"])
    
    print("\n" + "="*50)
    print("PHASE 1A ACQUISITION RUN COMPLETE!")
    print("="*50)
    print(f"Total Filtered Records: {total_filtered_rows:,}")
    print(f"Storage Footprint on Google Drive: {total_size_bytes / (1024*1024):.2f} MB")
    print("All progress is securely persistent and checkpointed.")
    print("="*50)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="BetterCallSaul Phase 1A Dataset Ingestion")
    parser.add_argument("--dry-run", action="store_true", help="Processes only a small sample of records")
    parser.add_argument("--limit-rows", type=int, help="Limit number of rows processed per Parquet file (for debugging)")
    parser.add_argument("--files", nargs="+", help="Specific parquet files to process (e.g. --files in_central_legislation.parquet)")
    args = parser.parse_args()
    
    run_acquisition(dry_run=args.dry_run, limit_rows=args.limit_rows, target_files=args.files)

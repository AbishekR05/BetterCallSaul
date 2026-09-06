# scripts/run_production_indexing.py
"""
Phase 2.2 Production Embedding & Vector Indexing Pipeline.
Processes all 15.7M+ legal chunks using validated production configuration:
  - Model: BAAI/bge-base-en-v1.5 (768 dimensions)
  - Batch size: 256
  - Single worker (Baseline FP16 mixed precision)
  - Database: PostgreSQL + pgvector (bcs_tablespace on D: drive)
  - Checkpoint: manifest_phase2_2.json (Resumable & Idempotent)
  - HNSW Index: m=16, ef_construction=64 (Cosine)
  - Feature: Async Background Prefetching for Google Drive Downloads
"""

import os
import sys
import time
import psutil
import shutil
import functools
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import pandas as pd
import numpy as np
import torch
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv

# Force unbuffered stdout printing
print = functools.partial(print, flush=True)

sys.path.append("d:/Abishek")

from src.db_phase2 import (
    get_connection,
    init_db_schema,
    create_hnsw_index,
    create_metadata_indexes
)
from scripts.build_vector_index import process_batch, load_embedding_model
from scripts.manifest_manager import (
    load_manifest,
    save_manifest,
    reset_incomplete_batches,
    update_batch_status,
    is_batch_loaded
)
from scripts.acquire_open_india_law import authenticate_google_drive, GoogleDriveManager

load_dotenv()

LOCAL_CACHE_DIR = Path("d:/Abishek/scratch/temp_process")
LOCAL_CACHE_DIR.mkdir(parents=True, exist_ok=True)

def get_system_ram_gb():
    mem = psutil.virtual_memory()
    return mem.used / (1024 ** 3)

def download_batch_file(drive, batch_info, retries=5):
    """Worker function to download a parquet batch from GDrive asynchronously with retries."""
    batch_id = batch_info["batch_id"]
    local_parquet_path = LOCAL_CACHE_DIR / batch_id
    
    # Check if valid non-empty file already exists
    if local_parquet_path.exists() and local_parquet_path.stat().st_size > 0:
        return local_parquet_path

    # Clean up stale empty file if present
    if local_parquet_path.exists():
        try:
            local_parquet_path.unlink()
        except Exception:
            pass

    start_t = time.time()
    print(f"[PREFETCH] Downloading batch '{batch_id}' ({batch_info['size_bytes'] / (1024*1024):.2f} MB)...")
    content_bytes = None
    for attempt in range(1, retries + 1):
        try:
            content_bytes = drive.download_file_content(batch_info["file_id"])
            if content_bytes is not None and len(content_bytes) > 0:
                break
        except Exception as e:
            print(f"[PREFETCH WARNING] Attempt {attempt}/{retries} failed for '{batch_id}': {e}")
        print(f"[PREFETCH WARNING] Retrying download of '{batch_id}' in {2**attempt}s...")
        time.sleep(2 ** attempt)
        
    if content_bytes is None or len(content_bytes) == 0:
        raise IOError(f"Failed to download non-empty batch '{batch_id}' after {retries} retries.")
        
    tmp_path = local_parquet_path.with_suffix(".tmp")
    with open(tmp_path, "wb") as f:
        f.write(content_bytes)
    os.replace(tmp_path, local_parquet_path)
    print(f"[PREFETCH] Downloaded '{batch_id}' ({len(content_bytes) / (1024*1024):.2f} MB) in {time.time() - start_t:.2f}s.")
    return local_parquet_path



def run_production_indexing(limit_batches=None):
    print("==================================================")
    print("STARTING PHASE 2.2 FULL PRODUCTION INDEXING RUN")
    print("==================================================")
    print("Configuration:")
    print("  - Model: BAAI/bge-base-en-v1.5")
    print("  - Batch Size: 256 (Single Worker, FP16)")
    print("  - Storage: bcs_tablespace (D:/Abishek/pg_tablespace)")
    print("  - I/O Prefetching: Active (Background GDrive Download Thread)")
    print("==================================================\n")

    # 1. Initialize Database Schema & Extensions
    init_db_schema()

    # 2. Load Embedding Model
    model, device = load_embedding_model(device="cuda")

    # 3. Load & Clean Manifest Checkpoint State
    manifest = load_manifest()
    reset_count = reset_incomplete_batches(manifest)
    if reset_count > 0:
        print(f"Reset {reset_count} incomplete batches from transient states.")

    # 4. Authenticate Google Drive & Discover Phase 1C Input Files
    print("Connecting to Google Drive to list Phase 1C chunked parquet batches...")
    drive_service = authenticate_google_drive()
    drive = GoogleDriveManager(drive_service)
    chunked_root_id = drive.get_or_create_subfolder("03_chunked", drive.root_id)

    input_batches = []
    for folder_key in ["legislation", "judgments"]:
        f_id = drive.get_or_create_subfolder(folder_key, chunked_root_id)
        res = drive_service.files().list(
            q=f"'{f_id}' in parents and trashed = false",
            fields="files(id, name, size)"
        ).execute()
        for item in res.get('files', []):
            if item['name'].endswith('.parquet'):
                input_batches.append({
                    "batch_id": item['name'],
                    "file_id": item['id'],
                    "folder_key": folder_key,
                    "size_bytes": int(item.get('size', 0))
                })

    print(f"Discovered {len(input_batches)} Phase 1C Parquet batch files on Google Drive.")

    # Filter out already loaded batches
    pending_batches = [b for b in input_batches if not is_batch_loaded(manifest, b["batch_id"])]
    print(f"Batches remaining to process: {len(pending_batches)} / {len(input_batches)}")

    if not pending_batches:
        print("[OK] All batches are already LOADED in PostgreSQL!")
    else:
        executor = ThreadPoolExecutor(max_workers=2)
        
        # Submit prefetch for the first batch
        current_future = executor.submit(download_batch_file, drive, pending_batches[0])

        total_chunks_processed = 0
        total_time_elapsed = 0.0
        start_run_time = time.time()
        batches_completed_this_run = 0

        for idx, batch_info in enumerate(pending_batches, 1):
            if limit_batches is not None and batches_completed_this_run >= limit_batches:
                print(f"\nReached batch limit ({limit_batches}). Pausing run.")
                break

            batch_id = batch_info["batch_id"]

            print(f"\n--------------------------------------------------")
            print(f"[{idx}/{len(pending_batches)}] Processing Batch: '{batch_id}'")
            print(f"--------------------------------------------------")

            # Submit prefetch for the NEXT batch in parallel while current batch processes
            if idx < len(pending_batches):
                next_batch_info = pending_batches[idx]
                next_future = executor.submit(download_batch_file, drive, next_batch_info)
            else:
                next_future = None

            # Wait for current batch file download to complete
            local_parquet_path = current_future.result()

            update_batch_status(manifest, batch_id, "embedding")

            # Read Parquet DataFrame
            df_chunks = pd.read_parquet(local_parquet_path)
            batch_chunk_count = len(df_chunks)
            print(f"Loaded {batch_chunk_count:,} chunks from '{batch_id}'.")

            # Embed & Load into PostgreSQL
            batch_start_t = time.time()
            conn = get_connection(autocommit=False)
            try:
                num_chunks, peak_vram, throughput, copy_time = process_batch(
                    df_chunks, model, device, embed_batch_size=256, conn=conn
                )
                conn.commit()
                update_batch_status(manifest, batch_id, "loaded", num_chunks=num_chunks, peak_vram_gb=peak_vram)
                batches_completed_this_run += 1
                
                # Clean up local cache file to conserve D: drive space
                if local_parquet_path.exists():
                    local_parquet_path.unlink()

            except Exception as e:
                conn.rollback()
                update_batch_status(manifest, batch_id, "failed", error_message=str(e))
                print(f"[ERROR] Error processing batch '{batch_id}': {e}", file=sys.stderr)
                current_future = next_future
                continue
            finally:
                conn.close()

            # Update metrics & telemetry
            batch_elapsed = time.time() - batch_start_t
            total_chunks_processed += batch_chunk_count
            total_time_elapsed += batch_elapsed
            
            avg_throughput = total_chunks_processed / max(total_time_elapsed, 0.001)
            sys_ram_gb = get_system_ram_gb()
            
            # Calculate ETA
            remaining_batches_count = len(pending_batches) - idx
            est_remaining_chunks = remaining_batches_count * 150000  # Avg chunks per batch
            eta_hours = est_remaining_chunks / max(avg_throughput * 3600, 0.001)

            print(f"[OK] Batch '{batch_id}' Completed!")
            print(f"  Telemetry Summary:")
            print(f"    - Chunks Processed This Run : {total_chunks_processed:,}")
            print(f"    - Batch Throughput          : {throughput:.2f} chunks/sec")
            print(f"    - Sustained Throughput      : {avg_throughput:.2f} chunks/sec")
            print(f"    - Peak GPU VRAM             : {peak_vram:.2f} GB")
            print(f"    - System RAM Usage          : {sys_ram_gb:.2f} GB")
            print(f"    - Remaining Batches         : {remaining_batches_count}")
            print(f"    - Estimated Remaining Time  : {eta_hours:.2f} hours")

            # Advance prefetch future pointer
            current_future = next_future

        executor.shutdown(wait=False)

    # 6. Post-Load Vector & Metadata Indexing
    all_loaded = all(is_batch_loaded(manifest, b["batch_id"]) for b in input_batches)
    if all_loaded:
        print("\n==================================================")
        print("ALL BATCHES LOADED! BUILDING HNSW VECTOR & METADATA INDEXES...")
        print("==================================================")
        with get_connection(autocommit=False) as conn:
            create_hnsw_index(conn)
            create_metadata_indexes(conn)
        print("[SUCCESS] HNSW Vector Index and B-Tree Metadata Indexes Built Successfully!")

    print(f"\nExecution finished in {(time.time() - start_run_time)/60:.2f} minutes.")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit-batches", type=int, default=None, help="Limit number of batches to process in this run")
    args = parser.parse_args()
    
    run_production_indexing(limit_batches=args.limit_batches)

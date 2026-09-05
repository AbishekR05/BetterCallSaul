# scripts/build_vector_index.py
"""
Phase 2.2 Vector Index Construction & Production Pipeline.
Embeds legal chunks using BAAI/bge-base-en-v1.5 on NVIDIA RTX 5060 (FP16 mixed precision)
and bulk-loads vectors and relational metadata into PostgreSQL + pgvector (bcs_tablespace).
Supports resumability via manifest_manager.py.
"""

import os
import sys
import time
import argparse
from pathlib import Path
import pandas as pd
import numpy as np
import torch
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv

# Add workspace root to sys.path
sys.path.append("d:/Abishek")

from src.db_phase2 import (
    get_connection,
    init_db_schema,
    bulk_copy_domains,
    bulk_copy_source_documents,
    bulk_copy_document_domains,
    bulk_copy_chunks,
    bulk_copy_embeddings,
    create_hnsw_index,
    create_metadata_indexes
)
from scripts.manifest_manager import (
    load_manifest,
    save_manifest,
    reset_incomplete_batches,
    update_batch_status,
    is_batch_loaded
)

load_dotenv()

MODEL_NAME = "BAAI/bge-base-en-v1.5"
DEFAULT_EMBED_BATCH_SIZE = 256
DEFAULT_COPY_BATCH_SIZE = 5000

def parse_args():
    parser = argparse.ArgumentParser(description="Phase 2.2 Vector Index Construction Pipeline")
    parser.add_argument("--pilot", action="store_true", help="Run pilot benchmark on stratified sample (10,000 chunks)")
    parser.add_argument("--batch-size", type=int, default=DEFAULT_EMBED_BATCH_SIZE, help="GPU embedding batch size")
    parser.add_argument("--copy-batch-size", type=int, default=DEFAULT_COPY_BATCH_SIZE, help="PostgreSQL COPY transaction batch size")
    parser.add_argument("--build-hnsw", action="store_true", help="Build HNSW vector index after loading")
    return parser.parse_args()

def load_embedding_model(device="cuda"):
    """Load BAAI/bge-base-en-v1.5 on GPU with FP16 precision."""
    print(f"Loading embedding model '{MODEL_NAME}' on device '{device}'...")
    start_t = time.time()
    
    # Verify CUDA capability
    if device == "cuda" and torch.cuda.is_available():
        x1 = torch.randn(2, 2).cuda()
        x2 = torch.randn(2, 2).cuda()
        _ = x1 @ x2
        torch.cuda.synchronize()
        print(f"CUDA verified on GPU: {torch.cuda.get_device_name(0)}")
    else:
        device = "cpu"
        print("Warning: Running model on CPU.")
        
    model = SentenceTransformer(MODEL_NAME, device=device)
    print(f"Model loaded in {time.time() - start_t:.2f} seconds.")
    return model, device

def process_batch(df_chunks, model, device, embed_batch_size, conn):
    """
    Embed chunks and bulk-load into PostgreSQL in atomic transactions.
    Returns (num_chunks, peak_vram_gb, throughput_c_s, copy_time_s)
    """
    start_t = time.time()
    df_chunks = df_chunks.reset_index(drop=True)
    
    # 1. Prepare chunk texts (Passages embedded WITHOUT query prefix)
    texts = df_chunks['text'].tolist()
    chunk_ids = df_chunks['chunk_id'].tolist()
    num_chunks = len(texts)
    
    # 2. GPU FP16 Embedding Generation with OOM fallback
    print(f"Generating embeddings for {num_chunks} chunks (batch_size={embed_batch_size})...")
    current_batch_size = embed_batch_size
    embeddings_np = None
    
    while current_batch_size >= 16:
        try:
            if device == "cuda":
                torch.cuda.reset_peak_memory_stats()
                with torch.amp.autocast('cuda'):
                    embeddings_np = model.encode(
                        texts,
                        batch_size=current_batch_size,
                        show_progress_bar=False,
                        normalize_embeddings=True,
                        convert_to_numpy=True
                    )
            else:
                embeddings_np = model.encode(
                    texts,
                    batch_size=current_batch_size,
                    show_progress_bar=False,
                    normalize_embeddings=True,
                    convert_to_numpy=True
                )
            break  # Success
        except torch.cuda.OutOfMemoryError:
            print(f"CUDA OOM detected! Halving batch size from {current_batch_size} to {current_batch_size // 2}")
            current_batch_size = current_batch_size // 2
            torch.cuda.empty_cache()
            
    if embeddings_np is None:
        raise RuntimeError("Failed to generate embeddings due to persistent OOM.")

    embed_time = time.time() - start_t
    throughput = num_chunks / max(embed_time, 0.001)
    
    peak_vram_gb = 0.0
    if device == "cuda":
        peak_vram_gb = torch.cuda.max_memory_allocated() / (1024 ** 3)
    
    print(f"Embedded {num_chunks} chunks in {embed_time:.2f}s ({throughput:.2f} chunks/sec, Peak VRAM: {peak_vram_gb:.2f} GB)")

    # 3. Prepare relational data structures
    source_docs = []
    doc_domains_raw = []
    chunks_data = []
    embeddings_data = []

    # Domain name resolution
    all_domain_names = set()
    for pos_idx, (_, row) in enumerate(df_chunks.iterrows()):
        doms = row.get('domain', [])
        if isinstance(doms, (list, np.ndarray)):
            for d in doms:
                if d: all_domain_names.add(str(d))
        elif isinstance(doms, str) and doms:
            all_domain_names.add(doms)

    domain_mapping = bulk_copy_domains(conn, list(all_domain_names))

    # Format rows
    for pos_idx, (_, row) in enumerate(df_chunks.iterrows()):
        doc_id = str(row.get('document_id', f"doc_{row['chunk_id']}"))
        chunk_id = str(row['chunk_id'])
        
        # Source Doc
        doc_dict = {
            'document_id': doc_id,
            'source_type': str(row.get('source_type', 'legislation')),
            'title': str(row.get('act', row.get('case_name', ''))),
            'act': str(row.get('act', '')) if pd.notna(row.get('act')) else '',
            'case_name': str(row.get('case_name', '')) if pd.notna(row.get('case_name')) else '',
            'citation': str(row.get('citation', '')) if pd.notna(row.get('citation')) else '',
            'court': str(row.get('court', '')) if pd.notna(row.get('court')) else '',
            'jurisdiction': str(row.get('jurisdiction', 'central')),
            'level': str(row.get('level', 'central')),
            'state': str(row.get('state', '')) if pd.notna(row.get('state')) else '',
            'date': str(row.get('date', '')) if pd.notna(row.get('date')) else '',
            'effective_date': str(row.get('effective_date', '')) if pd.notna(row.get('effective_date')) else '',
            'is_historical': bool(row.get('is_historical', False)),
            'source_url': str(row.get('source_url', '')) if pd.notna(row.get('source_url')) else '',
            'dataset_version': '1.0',
            'original_source_id': str(row.get('original_source_id', ''))
        }
        source_docs.append(doc_dict)

        # Doc Domains
        doms = row.get('domain', [])
        if isinstance(doms, (list, np.ndarray)):
            for d in doms:
                if str(d) in domain_mapping:
                    doc_domains_raw.append((doc_id, domain_mapping[str(d)]))
        elif isinstance(doms, str) and doms in domain_mapping:
            doc_domains_raw.append((doc_id, domain_mapping[doms]))

        # Chunk
        chunk_dict = {
            'chunk_id': chunk_id,
            'document_id': doc_id,
            'parent_id': str(row.get('parent_id', '')) if pd.notna(row.get('parent_id')) else '',
            'chunk_index': int(row.get('chunk_index', 0)),
            'source_type': str(row.get('source_type', 'legislation')),
            'part': str(row.get('part', '')) if pd.notna(row.get('part')) else '',
            'chapter': str(row.get('chapter', '')) if pd.notna(row.get('chapter')) else '',
            'section': str(row.get('section', '')) if pd.notna(row.get('section')) else '',
            'subsection': str(row.get('subsection', '')) if pd.notna(row.get('subsection')) else '',
            'clause': str(row.get('clause', '')) if pd.notna(row.get('clause')) else '',
            'paragraph_number': str(row.get('paragraph_number', '')) if pd.notna(row.get('paragraph_number')) else '',
            'text': str(row.get('text', '')),
            'char_length': int(row.get('char_length', len(str(row.get('text', ''))))),
            'cross_references': str(row.get('cross_references', '')) if pd.notna(row.get('cross_references')) else ''
        }
        chunks_data.append(chunk_dict)

        # Embedding vector (formatted as PostgreSQL vector string '[0.1, -0.2, ...]')
        vec_list = embeddings_np[pos_idx].tolist()
        vec_str = "[" + ",".join(map(str, vec_list)) + "]"
        embeddings_data.append((chunk_id, MODEL_NAME, "1.0", vec_str))

    # 4. Perform PostgreSQL COPY bulk load in atomic transaction
    copy_start_t = time.time()
    with conn.transaction():
        bulk_copy_source_documents(conn, source_docs)
        bulk_copy_document_domains(conn, doc_domains_raw)
        bulk_copy_chunks(conn, chunks_data)
        bulk_copy_embeddings(conn, embeddings_data)
        
    copy_time_s = time.time() - copy_start_t
    print(f"Bulk loaded {num_chunks} rows to PostgreSQL in {copy_time_s:.2f}s ({num_chunks / max(copy_time_s, 0.001):.2f} rows/sec)")
    
    return num_chunks, peak_vram_gb, throughput, copy_time_s

def run_pilot(model, device, embed_batch_size, copy_batch_size, build_hnsw):
    """Run pilot indexing on sampled_chunks.parquet (1,000 stratified chunks)."""
    pilot_sample_path = Path("d:/Abishek/benchmark/phase_2_1/sampled_chunks.parquet")
    if not pilot_sample_path.exists():
        raise FileNotFoundError(f"Pilot sample not found at {pilot_sample_path}")

    print("==================================================")
    print("STARTING PHASE 2.2 PILOT INDEXING RUN")
    print("==================================================")
    
    # Load manifest and reset any incomplete states
    manifest = load_manifest()
    reset_incomplete_batches(manifest)

    batch_id = "pilot_sampled_chunks"
    if is_batch_loaded(manifest, batch_id):
        print(f"Pilot batch '{batch_id}' is already loaded in database. Skipping embedding.")
        return

    update_batch_status(manifest, batch_id, "embedding")
    
    df_sample = pd.read_parquet(pilot_sample_path)
    print(f"Loaded {len(df_sample)} stratified chunks for pilot run.")

    conn = get_connection(autocommit=False)
    try:
        num_chunks, peak_vram, throughput, copy_time = process_batch(
            df_sample, model, device, embed_batch_size, conn
        )
        conn.commit()
        update_batch_status(manifest, batch_id, "loaded", num_chunks=num_chunks, peak_vram_gb=peak_vram)
        print(f"\nPilot batch '{batch_id}' successfully embedded and loaded!")
    except Exception as e:
        conn.rollback()
        update_batch_status(manifest, batch_id, "failed", error_message=str(e))
        raise e
    finally:
        conn.close()

    # Build HNSW vector index if requested
    if build_hnsw:
        with get_connection(autocommit=False) as conn:
            create_hnsw_index(conn)
            create_metadata_indexes(conn)

def main():
    args = parse_args()
    
    # 1. Initialize DB schema
    init_db_schema()
    
    # 2. Load model
    model, device = load_embedding_model(device="cuda")
    
    # 3. Run pilot or full
    if args.pilot:
        run_pilot(model, device, args.batch_size, args.copy_batch_size, args.build_hnsw)
    else:
        print("Run with --pilot to execute the Phase 2.2 Pilot Run.")

if __name__ == "__main__":
    main()

# scripts/manifest_manager.py
"""
Resumable Checkpoint & Manifest Manager for Phase 2.2.
Tracks batch processing state:
  pending -> embedding -> embedded -> loading -> loaded / failed
Survivable against Ctrl+C, system crashes, and restarts.
"""

import os
import json
import time
from pathlib import Path

MANIFEST_DIR = Path("d:/Abishek/benchmark/phase_2_2")
MANIFEST_PATH = MANIFEST_DIR / "manifest_phase2_2.json"

def get_default_manifest():
    return {
        "phase": "2.2",
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "last_updated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "total_batches": 0,
        "completed_batches": 0,
        "failed_batches": 0,
        "batches": {}
    }

def load_manifest():
    """Load manifest from disk or return default if missing."""
    MANIFEST_DIR.mkdir(parents=True, exist_ok=True)
    if not MANIFEST_PATH.exists():
        manifest = get_default_manifest()
        save_manifest(manifest)
        return manifest
    try:
        with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Warning: Failed to load manifest ({e}). Creating new.")
        manifest = get_default_manifest()
        save_manifest(manifest)
        return manifest

def save_manifest(manifest):
    """Atomically save manifest to disk."""
    MANIFEST_DIR.mkdir(parents=True, exist_ok=True)
    manifest["last_updated"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    tmp_path = MANIFEST_PATH.with_suffix(".tmp")
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
    os.replace(tmp_path, MANIFEST_PATH)

def reset_incomplete_batches(manifest):
    """
    On pipeline startup, check for batches stuck in transient states
    ('embedding', 'loading') and reset them to 'pending' to ensure clean resumption.
    """
    reset_count = 0
    for batch_id, info in manifest.get("batches", {}).items():
        status = info.get("status")
        if status in ("embedding", "loading"):
            print(f"Resumability notice: Resetting batch {batch_id} from '{status}' to 'pending'.")
            info["status"] = "pending"
            info["error_message"] = "Interrupted run auto-reset"
            reset_count += 1
    if reset_count > 0:
        save_manifest(manifest)
    return reset_count

def update_batch_status(manifest, batch_id, status, num_chunks=0, peak_vram_gb=0.0, error_message=None):
    """Update and persist status for a specific batch file."""
    if "batches" not in manifest:
        manifest["batches"] = {}
    
    current = manifest["batches"].get(batch_id, {})
    current["status"] = status
    current["last_updated"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    
    if num_chunks > 0:
        current["num_chunks"] = num_chunks
    if peak_vram_gb > 0.0:
        current["peak_vram_gb"] = peak_vram_gb
    if error_message is not None:
        current["error_message"] = error_message
        
    manifest["batches"][batch_id] = current
    
    # Recalculate summary counters
    completed = sum(1 for b in manifest["batches"].values() if b.get("status") == "loaded")
    failed = sum(1 for b in manifest["batches"].values() if b.get("status") == "failed")
    manifest["total_batches"] = len(manifest["batches"])
    manifest["completed_batches"] = completed
    manifest["failed_batches"] = failed
    
    save_manifest(manifest)

def is_batch_loaded(manifest, batch_id):
    """Return True if batch file is completely loaded."""
    info = manifest.get("batches", {}).get(batch_id, {})
    return info.get("status") == "loaded"

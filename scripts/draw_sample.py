import os
import sys
import json
import random
import pandas as pd
from pathlib import Path

# Setup root directory paths
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from scripts.acquire_open_india_law import authenticate_google_drive, GoogleDriveManager

BENCHMARK_DIR = BASE_DIR / "benchmark" / "phase_2_1"
TEMP_DOWNLOAD_DIR = BENCHMARK_DIR / "temp_downloads"

# Target sample sizes
TARGET_LEGISLATION_SIZE = 5000
TARGET_JUDGMENT_SIZE = 5000
TOTAL_TARGET_SIZE = TARGET_LEGISLATION_SIZE + TARGET_JUDGMENT_SIZE

def draw_stratified_sample(df, target_size, source_type_name):
    """Draws a stratified sample from a dataframe based on the first domain element, ensuring rare domains have min representation."""
    if len(df) <= target_size:
        print(f"  Source pool size ({len(df)}) is smaller than target size ({target_size}). Returning entire pool.")
        return df
        
    def get_first_domain(domains_list):
        import numpy as np
        if isinstance(domains_list, np.ndarray) and len(domains_list) > 0:
            return domains_list[0]
        if not isinstance(domains_list, (list, tuple)) or len(domains_list) == 0:
            return "Unknown"
        return domains_list[0]
        
    df = df.copy()
    df['stratify_domain'] = df['domain'].apply(get_first_domain)
    
    # Calculate counts per domain
    counts = df['stratify_domain'].value_counts()
    print(f"  {source_type_name} pool counts per domain:")
    for dom, cnt in counts.items():
        print(f"    - {dom}: {cnt}")
        
    sampled_dfs = []
    total_pool = len(df)
    
    for dom, count in counts.items():
        # Proportional count, at least 15 chunks if available to preserve rare domains!
        prop_count = int(target_size * (count / total_pool))
        sample_count = max(15, prop_count)
        sample_count = min(count, sample_count) # cannot exceed pool
        
        dom_df = df[df['stratify_domain'] == dom]
        sampled_dom_df = dom_df.sample(n=sample_count, random_state=42)
        sampled_dfs.append(sampled_dom_df)
        
    sampled_df = pd.concat(sampled_dfs)
    
    # Adjust total sample to match exactly target_size
    if len(sampled_df) > target_size:
        sampled_df = sampled_df.sample(n=target_size, random_state=42)
    elif len(sampled_df) < target_size:
        remaining_indices = df.index.difference(sampled_df.index)
        needed = target_size - len(sampled_df)
        to_add = df.loc[remaining_indices].sample(n=needed, random_state=42)
        sampled_df = pd.concat([sampled_df, to_add])
        
    sampled_df = sampled_df.drop(columns=['stratify_domain'])
    return sampled_df

def main():
    print("Initializing benchmark sampling...")
    BENCHMARK_DIR.mkdir(parents=True, exist_ok=True)
    TEMP_DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
    
    # Authenticate Google Drive
    drive_service = authenticate_google_drive()
    drive = GoogleDriveManager(drive_service)
    
    # List files in GDrive 03_chunked folders
    chunked_root_id = drive.get_or_create_subfolder("03_chunked", drive.root_id)
    
    # --- 1. Identify completed files ---
    files_to_download = []
    
    # Fetch Legislation files
    leg_folder_id = drive.get_or_create_subfolder("legislation", chunked_root_id)
    q_leg = f"'{leg_folder_id}' in parents and trashed = false"
    res_leg = drive_service.files().list(q=q_leg, fields="files(id, name, size)").execute()
    leg_files = res_leg.get('files', [])
    print(f"Found {len(leg_files)} legislation chunked files on Drive.")
    
    # Fetch Judgment files
    jud_folder_id = drive.get_or_create_subfolder("judgments", chunked_root_id)
    q_jud = f"'{jud_folder_id}' in parents and trashed = false"
    res_jud = drive_service.files().list(q=q_jud, fields="files(id, name, size)").execute()
    jud_files = res_jud.get('files', [])
    print(f"Found {len(jud_files)} judgment chunked files on Drive.")
    
    # --- 2. Select representative files to download ---
    # We select a few small and large files to represent domains and courts
    selected_leg = sorted(leg_files, key=lambda x: int(x.get('size', 0)))[-8:] # take the 8 largest files to ensure domain diversity
    selected_jud = sorted(jud_files, key=lambda x: int(x.get('size', 0)))[-6:] # take the 6 largest judgment partition files
    
    print("\nSelected files for sampling:")
    print("Legislation:")
    for f in selected_leg:
        print(f"  - {f['name']} ({int(f.get('size', 0))/(1024*1024):.2f} MB)")
    print("Judgments:")
    for f in selected_jud:
        print(f"  - {f['name']} ({int(f.get('size', 0))/(1024*1024):.2f} MB)")
        
    # --- 3. Download selected files ---
    leg_dfs = []
    for f in selected_leg:
        dest_path = TEMP_DOWNLOAD_DIR / f['name']
        print(f"Downloading {f['name']}...")
        content = drive.download_file_content(f['id'])
        if content:
            with open(dest_path, 'wb') as f_out:
                f_out.write(content)
            leg_dfs.append(pd.read_parquet(dest_path))
            dest_path.unlink() # delete right after loading to save disk space
            
    jud_dfs = []
    for f in selected_jud:
        dest_path = TEMP_DOWNLOAD_DIR / f['name']
        print(f"Downloading {f['name']}...")
        content = drive.download_file_content(f['id'])
        if content:
            with open(dest_path, 'wb') as f_out:
                f_out.write(content)
            jud_dfs.append(pd.read_parquet(dest_path))
            dest_path.unlink() # delete right after loading to save disk space
            
    if not leg_dfs or not jud_dfs:
        print("Error: Could not load data from Google Drive.")
        sys.exit(1)
        
    # --- 4. Combine pools ---
    df_leg_all = pd.concat(leg_dfs, ignore_index=True)
    df_jud_all = pd.concat(jud_dfs, ignore_index=True)
    
    print(f"\nLegislation raw pool size: {len(df_leg_all)} chunks.")
    print(f"Judgment raw pool size: {len(df_jud_all)} chunks.")
    
    # --- 5. Draw stratified samples ---
    print("\nDrawing stratified sample for legislation...")
    df_leg_sampled = draw_stratified_sample(df_leg_all, TARGET_LEGISLATION_SIZE, "Legislation")
    
    print("\nDrawing stratified sample for judgments...")
    df_jud_sampled = draw_stratified_sample(df_jud_all, TARGET_JUDGMENT_SIZE, "Judgments")
    
    # --- 6. Combine and save final dataset ---
    df_final = pd.concat([df_leg_sampled, df_jud_sampled], ignore_index=True)
    
    # Quick sanity checks
    print(f"\nFinal stratified sample size: {len(df_final)} chunks.")
    print(f"  - Legislation chunks: {len(df_final[df_final['source_type'] == 'legislation'])}")
    print(f"  - Judgment chunks: {len(df_final[df_final['source_type'] == 'judgment'])}")
    
    output_path = BENCHMARK_DIR / "sampled_chunks.parquet"
    df_final.to_parquet(output_path, index=False)
    print(f"\nSampled chunks successfully saved to: {output_path}")
    
    # Clean up download directory
    try:
        TEMP_DOWNLOAD_DIR.rmdir()
    except Exception:
        pass
        
    print("Sampling complete!")

if __name__ == '__main__':
    main()

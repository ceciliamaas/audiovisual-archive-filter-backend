#!/usr/bin/env python3
"""
Upload embeddings for video_reconstrucción_jonathan to S3
"""

import sys
import pickle
import numpy as np
from pathlib import Path
import os

# Change to script's parent directory
script_dir = Path(__file__).parent
os.chdir(script_dir.parent)

sys.path.insert(0, '.')

from dotenv import load_dotenv
# Load .env before importing storage
load_dotenv('.env')

from src.storage import get_storage_manager

def main():
    print("="*70)
    print("Upload video_reconstrucción_jonathan embeddings to S3")
    print("="*70)
    
    # Get storage manager
    storage_mgr = get_storage_manager()
    storage = storage_mgr.get_storage()
    
    print(f"\nStorage type: {type(storage).__name__}")
    if type(storage).__name__ != 'S3Storage':
        print("ERROR: Not using S3 storage. Check your .env file.")
        return
    
    print(f"Bucket: {storage.bucket_name}")
    
    # Load local embeddings
    print("\nLoading LOCAL embeddings...")
    local_frame_emb = pickle.load(open('data/embeddings/frame_embeddings.pkl', 'rb'))
    local_frame_paths = pickle.load(open('data/embeddings/frame_paths.pkl', 'rb'))
    local_object_emb = pickle.load(open('data/embeddings/object_embeddings.pkl', 'rb'))
    local_object_paths = pickle.load(open('data/embeddings/object_paths.pkl', 'rb'))
    
    print(f"  Local frames: {len(local_frame_paths)}")
    print(f"  Local objects: {len(local_object_paths)}")
    
    # Load S3 embeddings
    print("\nLoading S3 embeddings...")
    s3_frame_emb = storage.download_pickle('embeddings/frame_embeddings.pkl')
    s3_frame_paths = storage.download_pickle('embeddings/frame_paths.pkl')
    s3_object_emb = storage.download_pickle('embeddings/object_embeddings.pkl')
    s3_object_paths = storage.download_pickle('embeddings/object_paths.pkl')
    
    if s3_frame_paths:
        print(f"  S3 frames: {len(s3_frame_paths)}")
        print(f"  S3 objects: {len(s3_object_paths)}")
    
    # Merge embeddings
    print("\nMerging embeddings...")
    
    # For frames
    if isinstance(local_frame_emb, dict) and isinstance(s3_frame_emb, dict):
        # Both are dicts - merge them
        merged_frame_emb = {**s3_frame_emb, **local_frame_emb}
        print(f"  Merged frame embeddings: {len(merged_frame_emb)} keys")
    elif isinstance(local_frame_emb, dict):
        # Local is dict, S3 is not - just use local
        merged_frame_emb = local_frame_emb
        print(f"  Using local frame embeddings: {len(merged_frame_emb)} keys")
    else:
        print("  ERROR: Unexpected embeddings format")
        return
    
    # For frame paths - merge lists
    merged_frame_paths = list(set(s3_frame_paths + local_frame_paths))
    print(f"  Merged frame paths: {len(merged_frame_paths)} paths")
    
    # For objects
    if isinstance(local_object_emb, dict) and isinstance(s3_object_emb, dict):
        merged_object_emb = {**s3_object_emb, **local_object_emb}
        print(f"  Merged object embeddings: {len(merged_object_emb)} keys")
    elif isinstance(local_object_emb, dict):
        merged_object_emb = local_object_emb
        print(f"  Using local object embeddings: {len(merged_object_emb)} keys")
    else:
        print("  ERROR: Unexpected embeddings format")
        return
    
    # For object paths
    merged_object_paths = list(set(s3_object_paths + local_object_paths))
    print(f"  Merged object paths: {len(merged_object_paths)} paths")
    
    # Check for jonathan in merged
    jonathan_frames = [p for p in merged_frame_paths if 'jonathan' in p.lower()]
    jonathan_objects = [p for p in merged_object_paths if 'jonathan' in p.lower()]
    print(f"\n  Jonathan in merged data:")
    print(f"    Frames: {len(jonathan_frames)}")
    print(f"    Objects: {len(jonathan_objects)}")
    
    # Ask for confirmation
    print("\n" + "="*70)
    response = input("Upload merged embeddings to S3? (yes/no): ")
    
    if response.lower() != 'yes':
        print("Cancelled.")
        return
    
    # Upload merged embeddings
    print("\nUploading to S3...")
    
    # Save to temp files first
    import tempfile
    with tempfile.NamedTemporaryFile(mode='wb', delete=False, suffix='.pkl') as f:
        pickle.dump(merged_frame_emb, f)
        temp_frame_emb = f.name
    
    with tempfile.NamedTemporaryFile(mode='wb', delete=False, suffix='.pkl') as f:
        pickle.dump(merged_frame_paths, f)
        temp_frame_paths = f.name
    
    with tempfile.NamedTemporaryFile(mode='wb', delete=False, suffix='.pkl') as f:
        pickle.dump(merged_object_emb, f)
        temp_object_emb = f.name
    
    with tempfile.NamedTemporaryFile(mode='wb', delete=False, suffix='.pkl') as f:
        pickle.dump(merged_object_paths, f)
        temp_object_paths = f.name
    
    try:
        print("  Uploading frame_embeddings.pkl...")
        storage.upload_file(temp_frame_emb, 'embeddings/frame_embeddings.pkl')
        
        print("  Uploading frame_paths.pkl...")
        storage.upload_file(temp_frame_paths, 'embeddings/frame_paths.pkl')
        
        print("  Uploading object_embeddings.pkl...")
        storage.upload_file(temp_object_emb, 'embeddings/object_embeddings.pkl')
        
        print("  Uploading object_paths.pkl...")
        storage.upload_file(temp_object_paths, 'embeddings/object_paths.pkl')
        
        print("\n✓ Upload complete!")
        print("\nYour video should now appear in search results.")
        print("You may need to restart your web app for changes to take effect.")
        
    finally:
        # Clean up temp files
        import os
        os.unlink(temp_frame_emb)
        os.unlink(temp_frame_paths)
        os.unlink(temp_object_emb)
        os.unlink(temp_object_paths)

if __name__ == '__main__':
    main()

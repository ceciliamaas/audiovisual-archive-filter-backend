"""
Script to validate if a specific video's embeddings are loaded correctly
and can be retrieved from search.
"""

import pickle
import numpy as np
from pathlib import Path
import sys

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.core.search import get_search_engine
from src.config.settings import app_config


def validate_video_embeddings(video_name: str):
    """Validate embeddings for a specific video"""
    
    print(f"Validating embeddings for: {video_name}")
    print("=" * 70)
    
    # 1. Check raw embedding files
    print("\n1. Checking raw embedding files...")
    embeddings_dir = project_root / "data" / "embeddings"
    
    with open(embeddings_dir / "frame_paths.pkl", 'rb') as f:
        frame_paths = pickle.load(f)
    
    with open(embeddings_dir / "object_paths.pkl", 'rb') as f:
        object_paths = pickle.load(f)
    
    with open(embeddings_dir / "frame_embeddings.pkl", 'rb') as f:
        frame_embeddings = pickle.load(f)
        
    with open(embeddings_dir / "object_embeddings.pkl", 'rb') as f:
        object_embeddings = pickle.load(f)
    
    # Count items for this video
    video_frames = [p for p in frame_paths if video_name in p]
    video_objects = [p for p in object_paths if video_name in p]
    
    print(f"   ✓ Frame paths for {video_name}: {len(video_frames)}")
    print(f"   ✓ Object paths for {video_name}: {len(video_objects)}")
    
    if video_frames:
        print(f"   Sample frame path: {video_frames[0]}")
    if video_objects:
        print(f"   Sample object path: {video_objects[0]}")
    
    # 2. Check embeddings shape
    print(f"\n2. Checking embedding data...")
    print(f"   Frame embeddings type: {type(frame_embeddings)}")
    print(f"   Object embeddings type: {type(object_embeddings)}")
    
    # Convert to numpy if needed
    if isinstance(frame_embeddings, dict):
        print("   Converting frame embeddings dict to array...")
        frame_embeddings = np.array(frame_embeddings['embeddings'])
    if isinstance(object_embeddings, dict):
        print("   Converting object embeddings dict to array...")
        object_embeddings = np.array(object_embeddings['embeddings'])
    
    print(f"   Total frame embeddings shape: {frame_embeddings.shape}")
    print(f"   Total object embeddings shape: {object_embeddings.shape}")
    print(f"   Total frame paths: {len(frame_paths)}")
    print(f"   Total object paths: {len(object_paths)}")
    
    # Verify counts match
    assert len(frame_paths) == frame_embeddings.shape[0], "Frame paths and embeddings count mismatch!"
    assert len(object_paths) == object_embeddings.shape[0], "Object paths and embeddings count mismatch!"
    print("   ✓ Paths and embeddings counts match")
    
    # 3. Check if video embeddings are actually in the arrays
    print(f"\n3. Checking if {video_name} embeddings are in the arrays...")
    video_frame_indices = [i for i, p in enumerate(frame_paths) if video_name in p]
    video_object_indices = [i for i, p in enumerate(object_paths) if video_name in p]
    
    print(f"   Video frame indices: {len(video_frame_indices)} found")
    print(f"   Video object indices: {len(video_object_indices)} found")
    
    if video_frame_indices:
        print(f"   First frame index: {video_frame_indices[0]}")
        print(f"   Last frame index: {video_frame_indices[-1]}")
    
    if video_object_indices:
        print(f"   First object index: {video_object_indices[0]}")
        print(f"   Last object index: {video_object_indices[-1]}")
    
    # 4. Initialize search engine and check if it loads correctly
    print(f"\n4. Initializing search engine...")
    try:
        search_engine = get_search_engine()
        status = search_engine.get_status()
        print(f"   ✓ Search engine initialized")
        print(f"   Embeddings loaded: {status['embeddings_status']['loaded']}")
        print(f"   Frame count: {status['embeddings_status']['frame_count']}")
        print(f"   Object count: {status['embeddings_status']['object_count']}")
        
        # Verify the search engine sees the video
        engine_frame_paths = search_engine.embeddings_manager.frame_paths
        engine_object_paths = search_engine.embeddings_manager.object_paths
        
        engine_video_frames = [p for p in engine_frame_paths if video_name in p]
        engine_video_objects = [p for p in engine_object_paths if video_name in p]
        
        print(f"\n   Search engine sees:")
        print(f"   - {len(engine_video_frames)} frames from {video_name}")
        print(f"   - {len(engine_video_objects)} objects from {video_name}")
        
    except Exception as e:
        print(f"   ✗ Error initializing search engine: {e}")
        import traceback
        traceback.print_exc()
    
    # 5. Test actual search
    print(f"\n5. Testing search functionality...")
    print("   Note: This requires REPLICATE_API_TOKEN to be set")
    
    try:
        # Try a simple search that might match the video
        results = search_engine.search_by_text(
            "person",
            search_frames=True,
            search_objects=True,
            max_results=100
        )
        
        print(f"   Total results returned: {len(results)}")
        
        # Check if any results are from this video
        video_results = [r for r in results if video_name in r.path]
        print(f"   Results from {video_name}: {len(video_results)}")
        
        if video_results:
            print(f"\n   ✓ Video IS appearing in search results!")
            print(f"   Top result from this video:")
            top_result = video_results[0]
            print(f"   - Path: {top_result.path}")
            print(f"   - Similarity: {top_result.similarity:.4f}")
            print(f"   - Type: {top_result.result_type}")
        else:
            print(f"\n   ✗ Video NOT appearing in search results")
            print(f"   Top 5 overall results:")
            for i, r in enumerate(results[:5]):
                print(f"   {i+1}. {r.path} (similarity: {r.similarity:.4f})")
                
    except Exception as e:
        print(f"   ✗ Error during search: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 70)
    print("Validation complete!")


if __name__ == "__main__":
    video_name = "video_reconstrucción_jonathan"
    
    # Allow command line argument
    if len(sys.argv) > 1:
        video_name = sys.argv[1]
    
    validate_video_embeddings(video_name)

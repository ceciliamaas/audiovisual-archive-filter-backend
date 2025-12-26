#!/usr/bin/env python3
"""
Example demonstrating the new pipeline infrastructure.

This shows how to use PipelineState and NamingConvention for processing a video.
"""

from scripts.pipeline import PipelineState, VideoStatus, NamingConvention

def example_process_video(video_name: str, source_type: str, source_url: str):
    """Example of processing a video with state management.
    
    Args:
        video_name: Name for the video (will be sanitized)
        source_type: Type of source (youtube, drive, local)
        source_url: URL or path to source
    """
    # 1. Sanitize video name to be filesystem-safe
    video_name = NamingConvention.sanitize_video_name(video_name)
    print(f"Processing video: {video_name}")
    
    # 2. Load existing state or create new one
    state = PipelineState.load(video_name)
    if state:
        print(f"Resuming from status: {state.status.value}")
    else:
        state = PipelineState(
            video_name=video_name,
            source_type=source_type,
            source_url=source_url
        )
        print("Starting new processing")
    
    # 3. Process steps (example - actual implementation would do real work)
    
    # Step 1: Download
    if not state.is_step_completed("download"):
        print(f"\n→ Downloading from {source_type}...")
        state.update_status(VideoStatus.DOWNLOADING)
        state.save()
        
        # ... actual download logic here ...
        video_path = NamingConvention.video_local_path(video_name)
        print(f"  Saved to: {video_path}")
        
        state.update_status(VideoStatus.DOWNLOADED)
        state.mark_step_completed("download")
        state.save()
        print("  ✓ Download complete")
    else:
        print("\n✓ Download already completed")
    
    # Step 2: Extract Frames
    if not state.is_step_completed("extract_frames"):
        print("\n→ Extracting frames...")
        state.update_status(VideoStatus.EXTRACTING_FRAMES)
        state.save()
        
        # ... actual frame extraction logic here ...
        frames_dir = NamingConvention.frames_dir_local(video_name)
        print(f"  Saving frames to: {frames_dir}")
        
        # Example: 240 frames extracted
        frame_count = 240
        state.frame_count = frame_count
        state.update_status(VideoStatus.FRAMES_EXTRACTED)
        state.mark_step_completed("extract_frames")
        state.save()
        print(f"  ✓ Extracted {frame_count} frames")
    else:
        print(f"\n✓ Frame extraction already completed ({state.frame_count} frames)")
    
    # Step 3: Detect Objects
    if not state.is_step_completed("detect_objects"):
        print("\n→ Detecting objects with YOLO...")
        state.update_status(VideoStatus.DETECTING_OBJECTS)
        state.save()
        
        # ... actual object detection logic here ...
        objects_dir = NamingConvention.objects_dir_local(video_name)
        print(f"  Saving objects to: {objects_dir}")
        
        # Example: 1500 objects detected
        object_count = 1500
        state.object_count = object_count
        state.update_status(VideoStatus.OBJECTS_DETECTED)
        state.mark_step_completed("detect_objects")
        state.save()
        print(f"  ✓ Detected {object_count} objects")
    else:
        print(f"\n✓ Object detection already completed ({state.object_count} objects)")
    
    # Step 4: Compute Embeddings
    if not state.is_step_completed("compute_embeddings"):
        print("\n→ Computing CLIP embeddings...")
        state.update_status(VideoStatus.COMPUTING_EMBEDDINGS)
        state.save()
        
        # ... actual embedding computation logic here ...
        frame_emb_path = NamingConvention.frame_embeddings_local()
        object_emb_path = NamingConvention.object_embeddings_local()
        print(f"  Frame embeddings: {frame_emb_path}")
        print(f"  Object embeddings: {object_emb_path}")
        
        state.update_status(VideoStatus.EMBEDDINGS_COMPUTED)
        state.mark_step_completed("compute_embeddings")
        state.save()
        print("  ✓ Embeddings computed")
    else:
        print("\n✓ Embeddings already computed")
    
    # Step 5: Upload to S3
    if not state.is_step_completed("upload"):
        print("\n→ Uploading to S3...")
        state.update_status(VideoStatus.UPLOADING)
        state.save()
        
        # ... actual S3 upload logic here ...
        print(f"  Video: {NamingConvention.video_s3_key(video_name)}")
        print(f"  Frames: frames/{video_name}/*")
        print(f"  Objects: objects/{video_name}/*")
        print(f"  Embeddings: embeddings/*")
        
        state.update_status(VideoStatus.COMPLETED)
        state.mark_step_completed("upload")
        state.save()
        print("  ✓ Upload complete")
    else:
        print("\n✓ Upload already completed")
    
    # Final summary
    print(f"\n{'='*50}")
    print(f"✅ Processing complete for: {video_name}")
    print(f"   Status: {state.status.value}")
    print(f"   Frames: {state.frame_count}")
    print(f"   Objects: {state.object_count}")
    print(f"   Steps completed: {', '.join(state.steps_completed)}")
    print(f"{'='*50}\n")


def example_list_videos():
    """Example of listing all videos and their status."""
    print("All videos in pipeline:\n")
    
    all_states = PipelineState.list_all()
    if not all_states:
        print("No videos found.")
        return
    
    for state in all_states:
        status_emoji = "✅" if state.status == VideoStatus.COMPLETED else "⏳"
        print(f"{status_emoji} {state.video_name:30s} {state.status.value:20s} "
              f"frames={state.frame_count or 0:3d} objects={state.object_count or 0:4d}")


def example_naming_conventions():
    """Example showing naming convention usage."""
    video_name = "my_awesome_video"
    
    print("Naming Convention Examples:\n")
    print(f"Video name: {video_name}\n")
    
    print("Local paths:")
    print(f"  Video:  {NamingConvention.video_local_path(video_name)}")
    print(f"  Frame:  {NamingConvention.frame_local_path(video_name, 42)}")
    print(f"  Object: {NamingConvention.object_local_path(video_name, 42, 3)}")
    
    print("\nS3 keys:")
    print(f"  Video:  {NamingConvention.video_s3_key(video_name)}")
    print(f"  Frame:  {NamingConvention.frame_s3_key(video_name, 42)}")
    print(f"  Object: {NamingConvention.object_s3_key(video_name, 42, 3)}")
    
    print("\nName sanitization:")
    messy_name = "My Cool Video (2024) - Part 1!"
    clean_name = NamingConvention.sanitize_video_name(messy_name)
    print(f"  Original: {messy_name}")
    print(f"  Sanitized: {clean_name}")


if __name__ == "__main__":
    print("="*60)
    print("PIPELINE INFRASTRUCTURE EXAMPLES")
    print("="*60)
    
    # Example 1: Naming conventions
    print("\n1. NAMING CONVENTIONS")
    print("-" * 60)
    example_naming_conventions()
    
    # Example 2: Process a video
    print("\n\n2. PROCESSING A VIDEO")
    print("-" * 60)
    example_process_video(
        video_name="Example Video",
        source_type="youtube",
        source_url="https://youtube.com/watch?v=example"
    )
    
    # Example 3: List all videos
    print("\n3. LIST ALL VIDEOS")
    print("-" * 60)
    example_list_videos()

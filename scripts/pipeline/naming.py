"""
Naming convention utilities for consistent file and path handling.

This module standardizes all naming across the pipeline:
- Video files
- Frame images
- Object images
- Embedding files
- S3 paths
"""

from pathlib import Path
from typing import Optional


class NamingConvention:
    """Centralized naming convention for all pipeline artifacts."""
    
    @staticmethod
    def video_filename(video_name: str) -> str:
        """Get standardized video filename.
        
        Args:
            video_name: Name of the video (e.g., "my_video")
            
        Returns:
            Filename like "my_video.mp4"
        """
        return f"{video_name}.mp4"
    
    @staticmethod
    def video_local_path(video_name: str, base_dir: str = "data/videos") -> Path:
        """Get local path for video file.
        
        Args:
            video_name: Name of the video
            base_dir: Base directory for videos
            
        Returns:
            Path like "data/videos/my_video.mp4"
        """
        return Path(base_dir) / NamingConvention.video_filename(video_name)
    
    @staticmethod
    def video_s3_key(video_name: str) -> str:
        """Get S3 key for video file.
        
        Args:
            video_name: Name of the video
            
        Returns:
            S3 key like "videos/my_video.mp4"
        """
        return f"videos/{NamingConvention.video_filename(video_name)}"
    
    @staticmethod
    def frame_filename(frame_index: int) -> str:
        """Get standardized frame filename.
        
        Args:
            frame_index: Zero-based frame index
            
        Returns:
            Filename like "frame_00042.jpg"
        """
        return f"frame_{frame_index:05d}.jpg"
    
    @staticmethod
    def frame_local_path(video_name: str, frame_index: int, 
                         base_dir: str = "data/frames") -> Path:
        """Get local path for frame image.
        
        Args:
            video_name: Name of the video
            frame_index: Zero-based frame index
            base_dir: Base directory for frames
            
        Returns:
            Path like "data/frames/my_video/frame_00042.jpg"
        """
        return Path(base_dir) / video_name / NamingConvention.frame_filename(frame_index)
    
    @staticmethod
    def frame_s3_key(video_name: str, frame_index: int) -> str:
        """Get S3 key for frame image.
        
        Args:
            video_name: Name of the video
            frame_index: Zero-based frame index
            
        Returns:
            S3 key like "frames/my_video/frame_00042.jpg"
        """
        return f"frames/{video_name}/{NamingConvention.frame_filename(frame_index)}"
    
    @staticmethod
    def frames_dir_local(video_name: str, base_dir: str = "data/frames") -> Path:
        """Get local directory for all frames of a video.
        
        Args:
            video_name: Name of the video
            base_dir: Base directory for frames
            
        Returns:
            Path like "data/frames/my_video"
        """
        return Path(base_dir) / video_name
    
    @staticmethod
    def object_filename(frame_index: int, object_index: int) -> str:
        """Get standardized object filename.
        
        Args:
            frame_index: Zero-based frame index
            object_index: Zero-based object index within frame
            
        Returns:
            Filename like "frame_00042_obj_003.jpg"
        """
        return f"frame_{frame_index:05d}_obj_{object_index:03d}.jpg"
    
    @staticmethod
    def object_local_path(video_name: str, frame_index: int, object_index: int,
                          base_dir: str = "data/objects") -> Path:
        """Get local path for object image.
        
        Args:
            video_name: Name of the video
            frame_index: Zero-based frame index
            object_index: Zero-based object index
            base_dir: Base directory for objects
            
        Returns:
            Path like "data/objects/my_video/frame_00042_obj_003.jpg"
        """
        return Path(base_dir) / video_name / NamingConvention.object_filename(frame_index, object_index)
    
    @staticmethod
    def object_s3_key(video_name: str, frame_index: int, object_index: int) -> str:
        """Get S3 key for object image.
        
        Args:
            video_name: Name of the video
            frame_index: Zero-based frame index
            object_index: Zero-based object index
            
        Returns:
            S3 key like "objects/my_video/frame_00042_obj_003.jpg"
        """
        return f"objects/{video_name}/{NamingConvention.object_filename(frame_index, object_index)}"
    
    @staticmethod
    def objects_dir_local(video_name: str, base_dir: str = "data/objects") -> Path:
        """Get local directory for all objects of a video.
        
        Args:
            video_name: Name of the video
            base_dir: Base directory for objects
            
        Returns:
            Path like "data/objects/my_video"
        """
        return Path(base_dir) / video_name
    
    @staticmethod
    def frame_embeddings_local(base_dir: str = "data/embeddings") -> Path:
        """Get local path for frame embeddings file.
        
        Args:
            base_dir: Base directory for embeddings
            
        Returns:
            Path like "data/embeddings/frame_embeddings.pkl"
        """
        return Path(base_dir) / "frame_embeddings.pkl"
    
    @staticmethod
    def frame_paths_local(base_dir: str = "data/embeddings") -> Path:
        """Get local path for frame paths file.
        
        Args:
            base_dir: Base directory for embeddings
            
        Returns:
            Path like "data/embeddings/frame_paths.pkl"
        """
        return Path(base_dir) / "frame_paths.pkl"
    
    @staticmethod
    def object_embeddings_local(base_dir: str = "data/embeddings") -> Path:
        """Get local path for object embeddings file.
        
        Args:
            base_dir: Base directory for embeddings
            
        Returns:
            Path like "data/embeddings/object_embeddings.pkl"
        """
        return Path(base_dir) / "object_embeddings.pkl"
    
    @staticmethod
    def object_paths_local(base_dir: str = "data/embeddings") -> Path:
        """Get local path for object paths file.
        
        Args:
            base_dir: Base directory for embeddings
            
        Returns:
            Path like "data/embeddings/object_paths.pkl"
        """
        return Path(base_dir) / "object_paths.pkl"
    
    @staticmethod
    def frame_embeddings_s3_key() -> str:
        """Get S3 key for frame embeddings file.
        
        Returns:
            S3 key like "embeddings/frame_embeddings.pkl"
        """
        return "embeddings/frame_embeddings.pkl"
    
    @staticmethod
    def frame_paths_s3_key() -> str:
        """Get S3 key for frame paths file.
        
        Returns:
            S3 key like "embeddings/frame_paths.pkl"
        """
        return "embeddings/frame_paths.pkl"
    
    @staticmethod
    def object_embeddings_s3_key() -> str:
        """Get S3 key for object embeddings file.
        
        Returns:
            S3 key like "embeddings/object_embeddings.pkl"
        """
        return "embeddings/object_embeddings.pkl"
    
    @staticmethod
    def object_paths_s3_key() -> str:
        """Get S3 key for object paths file.
        
        Returns:
            S3 key like "embeddings/object_paths.pkl"
        """
        return "embeddings/object_paths.pkl"
    
    @staticmethod
    def sanitize_video_name(name: str) -> str:
        """Sanitize video name to be filesystem and S3 safe.
        
        Removes/replaces special characters, spaces, etc.
        
        Args:
            name: Original video name
            
        Returns:
            Sanitized name safe for use in paths
        """
        # Replace spaces and special chars with underscores
        safe_name = name.replace(" ", "_")
        safe_name = "".join(c for c in safe_name if c.isalnum() or c in "_-")
        # Remove leading/trailing underscores
        safe_name = safe_name.strip("_")
        # Convert to lowercase for consistency
        safe_name = safe_name.lower()
        return safe_name
    
    @staticmethod
    def parse_frame_index(filename: str) -> Optional[int]:
        """Parse frame index from filename.
        
        Args:
            filename: Frame filename like "frame_00042.jpg"
            
        Returns:
            Frame index (42) or None if not a valid frame filename
        """
        if not filename.startswith("frame_") or not filename.endswith(".jpg"):
            return None
        try:
            index_str = filename[6:-4]  # Remove "frame_" and ".jpg"
            return int(index_str)
        except ValueError:
            return None
    
    @staticmethod
    def parse_object_indices(filename: str) -> Optional[tuple[int, int]]:
        """Parse frame and object indices from object filename.
        
        Args:
            filename: Object filename like "frame_00042_obj_003.jpg"
            
        Returns:
            Tuple of (frame_index, object_index) or None if invalid
        """
        if not filename.startswith("frame_") or "_obj_" not in filename:
            return None
        try:
            # Extract: frame_00042_obj_003.jpg -> frame_index=42, obj_index=3
            parts = filename.replace(".jpg", "").split("_")
            frame_idx = int(parts[1])  # "00042"
            obj_idx = int(parts[3])     # "003"
            return (frame_idx, obj_idx)
        except (ValueError, IndexError):
            return None

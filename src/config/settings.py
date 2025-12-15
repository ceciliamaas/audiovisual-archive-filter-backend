"""
Configuration settings for the audiovisual archive filter application.
Centralizes all configuration management and environment variables.
"""

import os
from pathlib import Path
from dataclasses import dataclass
from typing import Optional


@dataclass
class StorageConfig:
    """Configuration for storage backends (S3, local, etc.)"""

    # Storj S3 Configuration
    storj_endpoint: str = "https://gateway.storjshare.io"
    access_key: Optional[str] = os.getenv("STORJ_ACCESS_KEY")
    secret_key: Optional[str] = os.getenv("STORJ_SECRET_KEY")
    bucket_name: str = os.getenv("STORJ_BUCKET_NAME", "audiovisual-archive")

    # Storage paths within bucket/local storage
    embeddings_path: str = "embeddings/"
    frames_path: str = "frames/"
    objects_path: str = "objects/"

    # Local fallback configuration
    local_data_dir: Path = Path("data")
    use_local_fallback: bool = (
        os.getenv("USE_LOCAL_FALLBACK", "false").lower() == "true"
    )
    storage_mode: str = os.getenv(
        "STORAGE_MODE", "auto"
    )  # auto, s3-only, local-only, hybrid

    def validate(self) -> bool:
        """Validate that required storage credentials are present"""
        if not self.access_key or not self.secret_key:
            if not self.use_local_fallback and self.storage_mode in ["s3-only", "auto"]:
                # Only raise error if explicitly set to s3-only mode
                if self.storage_mode == "s3-only":
                    raise ValueError(
                        "S3-only mode selected but storage credentials are missing"
                    )
                return False
            return False
        return True


@dataclass
class AppConfig:
    """Main application configuration"""

    # Application settings
    app_title: str = "Buscador de Archivo Audiovisual"
    app_icon: str = "🎥"
    layout: str = "wide"

    # Search settings
    max_search_results: int = 50
    similarity_threshold: float = 0.7

    # AI Model settings
    embedding_model: str = "openai/clip"
    yolo_model_path: str = "yolov8n.pt"

    # Data processing settings
    frame_extraction_fps: int = 1
    max_object_size: tuple = (224, 224)
    supported_video_formats: list = None

    def __post_init__(self):
        if self.supported_video_formats is None:
            self.supported_video_formats = [".mp4", ".avi", ".mov", ".mkv"]


@dataclass
class DevelopmentConfig:
    """Development and debugging configuration"""

    debug_mode: bool = os.getenv("DEBUG", "false").lower() == "true"
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    enable_profiling: bool = os.getenv("ENABLE_PROFILING", "false").lower() == "true"

    # Development data paths (smaller datasets for testing)
    dev_video_limit: int = 2
    dev_frame_limit: int = 100


# Global configuration instances
storage_config = StorageConfig()
app_config = AppConfig()
dev_config = DevelopmentConfig()


def get_data_dir() -> Path:
    """Get the appropriate data directory based on environment"""
    if dev_config.debug_mode:
        return Path("data_dev")
    return storage_config.local_data_dir


def is_storage_available() -> bool:
    """Check if cloud storage is properly configured"""
    return storage_config.validate()


def get_storage_paths() -> dict:
    """Get standardized storage paths for different data types"""
    return {
        "embeddings": storage_config.embeddings_path,
        "frames": storage_config.frames_path,
        "objects": storage_config.objects_path,
    }


def get_preferred_storage_mode() -> str:
    """Get the preferred storage mode based on configuration and availability"""
    mode = storage_config.storage_mode

    if mode == "auto":
        # Auto mode: prefer S3 if available, otherwise local
        if storage_config.validate():
            return "s3-primary"  # S3 primary with optional local fallback
        else:
            return "local-only"  # S3 not available, use local only

    return mode

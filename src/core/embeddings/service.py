"""
Embedding computation service.

Provides unified interface for computing CLIP embeddings from text and images.
"""

import time
import logging
import numpy as np
from pathlib import Path
from typing import Union, Optional, List

from .client import get_replicate_client
from ...config.settings import app_config

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Service for computing CLIP embeddings."""

    # Retry configuration for API calls
    RETRY_DELAYS = [1, 2, 4, 8]  # Exponential backoff

    def __init__(self, model_name: Optional[str] = None):
        """
        Initialize embedding service.

        Args:
            model_name: CLIP model to use (defaults to config setting)
        """
        self.model_name = model_name or app_config.embedding_model
        self._client = None

    @property
    def client(self):
        """Lazy-load Replicate client."""
        if self._client is None:
            self._client = get_replicate_client()
        return self._client

    def compute_text_embedding(
        self, text: str, normalize: bool = True
    ) -> Optional[np.ndarray]:
        """
        Compute CLIP embedding for text query.

        Args:
            text: Text to embed
            normalize: Whether to normalize the embedding vector

        Returns:
            Normalized embedding vector or None if failed
        """
        try:
            inputs = {"text": text}
            output = self.client.run(self.model_name, input=inputs)

            if output and "embedding" in output:
                embedding = np.array(output["embedding"], dtype=np.float32)

                if normalize:
                    embedding = embedding / np.linalg.norm(embedding)

                return embedding
            else:
                logger.error("Empty output from CLIP model for text")
                return None

        except Exception as e:
            logger.error(f"Error computing text embedding: {e}")
            return None

    def compute_image_embedding(
        self, image_path: Union[str, Path], normalize: bool = True, retry: bool = True
    ) -> Optional[np.ndarray]:
        """
        Compute CLIP embedding for image.

        Args:
            image_path: Path to image file
            normalize: Whether to normalize the embedding vector
            retry: Whether to retry on failure

        Returns:
            Normalized embedding vector or None if failed
        """
        image_path = Path(image_path)

        if not image_path.exists():
            logger.error(f"Image not found: {image_path}")
            return None

        delays = self.RETRY_DELAYS if retry else [0]

        for retry_count, delay in enumerate(delays):
            if delay > 0:
                time.sleep(delay)

            try:
                with open(image_path, "rb") as f:
                    output = self.client.run(self.model_name, input={"image": f})

                if output:
                    # Handle different output formats
                    if isinstance(output, list):
                        embedding = np.array(output, dtype=np.float32)
                    elif isinstance(output, dict) and "embedding" in output:
                        embedding = np.array(output["embedding"], dtype=np.float32)
                    else:
                        embedding = np.array(output, dtype=np.float32)

                    if normalize:
                        embedding = embedding / np.linalg.norm(embedding)

                    return embedding
                else:
                    logger.warning(f"Empty output from CLIP model for {image_path}")

            except Exception as e:
                if retry_count < len(delays) - 1:
                    logger.warning(
                        f"Error computing embedding for {image_path} "
                        f"(attempt {retry_count + 1}/{len(delays)}): {e}"
                    )
                else:
                    logger.error(
                        f"Failed to compute embedding for {image_path} after "
                        f"{len(delays)} attempts: {e}"
                    )

        return None

    def compute_batch_embeddings(
        self,
        image_paths: List[Union[str, Path]],
        normalize: bool = True,
        show_progress: bool = False,
    ) -> List[Optional[np.ndarray]]:
        """
        Compute embeddings for multiple images.

        Args:
            image_paths: List of image file paths
            normalize: Whether to normalize embedding vectors
            show_progress: Whether to show progress bar

        Returns:
            List of embedding vectors (None for failed images)
        """
        embeddings = []

        iterator = image_paths
        if show_progress:
            try:
                from tqdm import tqdm

                iterator = tqdm(image_paths, desc="Computing embeddings")
            except ImportError:
                pass

        for image_path in iterator:
            embedding = self.compute_image_embedding(
                image_path, normalize=normalize, retry=True
            )
            embeddings.append(embedding)

        return embeddings

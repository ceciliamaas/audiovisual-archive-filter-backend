"""
Replicate API client management.

Centralized Replicate client creation and configuration.
"""

import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Global client instance
_replicate_client = None


def get_replicate_client():
    """
    Get or create Replicate client instance.

    Returns:
        replicate.Client: Configured Replicate client

    Raises:
        RuntimeError: If REPLICATE_API_TOKEN is not set
        ImportError: If replicate package is not installed
    """
    global _replicate_client

    if _replicate_client is None:
        token = os.getenv("REPLICATE_API_TOKEN")

        if not token:
            raise RuntimeError(
                "Missing Replicate API token. Set REPLICATE_API_TOKEN in environment variables."
            )

        try:
            import replicate
        except ImportError:
            logger.error("replicate package not installed")
            raise ImportError(
                "replicate package required. Install with: pip install replicate"
            )

        _replicate_client = replicate.Client(api_token=token)
        logger.info("Initialized Replicate client")

    return _replicate_client


def reset_client():
    """Reset the global client instance (useful for testing)."""
    global _replicate_client
    _replicate_client = None

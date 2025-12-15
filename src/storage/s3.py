"""
S3 storage backend implementation for Storj.
Refactored version of the original s3_storage.py with improved architecture.
"""

import os
import boto3
from pathlib import Path
import tempfile
from typing import List, Optional, Union, Dict, Any
from botocore.exceptions import ClientError
import requests
import hashlib
import hmac
import base64
from datetime import datetime
import logging

from .base import StorageBackend
from ..config.settings import storage_config

logger = logging.getLogger(__name__)


class S3Storage(StorageBackend):
    """S3-compatible storage backend for Storj and other S3 services"""

    def __init__(self, **config):
        # Merge with global storage config
        self.endpoint_url = config.get("endpoint_url", storage_config.storj_endpoint)
        self.access_key = config.get("access_key", storage_config.access_key)
        self.secret_key = config.get("secret_key", storage_config.secret_key)
        self.bucket_name = config.get("bucket_name", storage_config.bucket_name)
        self.region = config.get("region", "us-east-1")

        super().__init__(**config)
        self._init_client()
        self._ensure_bucket_exists()

    def _validate_config(self) -> None:
        """Validate S3-specific configuration"""
        required = ["endpoint_url", "access_key", "secret_key", "bucket_name"]
        missing = []

        for field in required:
            if not getattr(self, field):
                missing.append(field)

        if missing:
            raise ValueError(f"Missing S3 configuration: {missing}")

    def _init_client(self) -> None:
        """Initialize S3 client"""
        # Configure client with timeouts
        config = boto3.session.Config(
            read_timeout=30, connect_timeout=10, retries={"max_attempts": 3}
        )

        self.s3_client = boto3.client(
            "s3",
            endpoint_url=self.endpoint_url,
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
            region_name=self.region,
            config=config,
        )
        logger.info(f"Initialized S3 client for {self.endpoint_url}")

    def _ensure_bucket_exists(self) -> None:
        """Create bucket if it doesn't exist"""
        try:
            self.s3_client.head_bucket(Bucket=self.bucket_name)
            logger.debug(f"Bucket {self.bucket_name} exists")
        except ClientError as e:
            error_code = int(e.response["Error"]["Code"])
            if error_code == 404:
                self.s3_client.create_bucket(Bucket=self.bucket_name)
                logger.info(f"Created bucket: {self.bucket_name}")
            else:
                logger.error(f"Error checking bucket: {e}")
                raise e

    def upload_file(self, local_path: Union[str, Path], remote_path: str) -> bool:
        """Upload a file using direct HTTP requests (better Storj compatibility)"""
        try:
            local_path = Path(local_path)
            if not local_path.exists():
                logger.error(f"File not found: {local_path}")
                return False

            with open(local_path, "rb") as f:
                file_content = f.read()

            # Create headers for direct HTTP upload
            date_string = datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S GMT")
            headers = {
                "Date": date_string,
                "Content-Type": "application/octet-stream",
                "Content-Length": str(len(file_content)),
            }

            # Create resource and signature
            resource = f"/{self.bucket_name}/{remote_path}"
            canonical_string = (
                f"PUT\n\napplication/octet-stream\n{date_string}\n{resource}"
            )
            signature = base64.b64encode(
                hmac.new(
                    self.secret_key.encode(), canonical_string.encode(), hashlib.sha1
                ).digest()
            ).decode()

            headers["Authorization"] = f"AWS {self.access_key}:{signature}"

            # Upload using requests
            url = f"{self.endpoint_url}/{self.bucket_name}/{remote_path}"
            response = requests.put(
                url, data=file_content, headers=headers, timeout=120
            )

            if response.status_code in [200, 201]:
                logger.info(f"Uploaded {local_path.name} to {remote_path}")
                return True
            else:
                logger.error(
                    f"HTTP upload failed: {response.status_code} - {response.text}"
                )
                return False

        except Exception as e:
            logger.error(f"Error uploading {local_path}: {e}")
            return False

    def download_file(self, remote_path: str, local_path: Union[str, Path]) -> bool:
        """Download a file from S3"""
        try:
            local_path = Path(local_path)
            local_path.parent.mkdir(parents=True, exist_ok=True)

            self.s3_client.download_file(self.bucket_name, remote_path, str(local_path))
            logger.info(f"Downloaded {remote_path} to {local_path}")
            return True
        except Exception as e:
            logger.error(f"Error downloading {remote_path}: {e}")
            return False

    def file_exists(self, remote_path: str) -> bool:
        """Check if a file exists in S3"""
        try:
            response = self.s3_client.head_object(
                Bucket=self.bucket_name, Key=remote_path
            )
            return True
        except ClientError as e:
            if int(e.response["Error"]["Code"]) == 404:
                return False
            logger.error(f"Error checking if file exists {remote_path}: {e}")
            raise e
        except Exception as e:
            logger.error(f"Timeout or connection error checking {remote_path}: {e}")
            raise e

    def list_files(self, prefix: str = "") -> List[str]:
        """List files in S3 with given prefix (handles pagination for large datasets)"""
        try:
            files = []
            continuation_token = None

            while True:
                # Prepare parameters for list_objects_v2
                list_params = {
                    "Bucket": self.bucket_name,
                    "Prefix": prefix,
                    "MaxKeys": 1000,  # S3 maximum
                }

                if continuation_token:
                    list_params["ContinuationToken"] = continuation_token

                response = self.s3_client.list_objects_v2(**list_params)

                # Add files from this batch
                if "Contents" in response:
                    files.extend([obj["Key"] for obj in response["Contents"]])

                # Check if there are more files to fetch
                if not response.get("IsTruncated", False):
                    break

                continuation_token = response.get("NextContinuationToken")
                if not continuation_token:
                    break

            logger.info(f"Listed {len(files)} files with prefix '{prefix}'")
            return files

        except Exception as e:
            logger.error(f"Error listing files with prefix {prefix}: {e}")
            return []

    def delete_file(self, remote_path: str) -> bool:
        """Delete a file from S3"""
        try:
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=remote_path)
            logger.info(f"Deleted {remote_path}")
            return True
        except Exception as e:
            logger.error(f"Error deleting {remote_path}: {e}")
            return False

    def get_file_url(self, remote_path: str, expiration: int = 3600) -> Optional[str]:
        """Generate a presigned URL for viewing files"""
        try:
            url = self.s3_client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket_name, "Key": remote_path},
                ExpiresIn=expiration,
            )
            return url
        except Exception as e:
            logger.error(f"Error generating presigned URL for {remote_path}: {e}")
            return None

    def get_info(self) -> Dict[str, Any]:
        """Get S3-specific information"""
        info = super().get_info()
        info.update(
            {
                "endpoint": self.endpoint_url,
                "bucket": self.bucket_name,
                "region": self.region,
                "has_credentials": bool(self.access_key and self.secret_key),
            }
        )
        return info

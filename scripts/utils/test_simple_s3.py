"""
Alternative S3 client using requests for better Storj compatibility
"""

import requests
import hashlib
import hmac
import base64
from datetime import datetime
from urllib.parse import quote
import xml.etree.ElementTree as ET


def create_simple_s3_client():
    """Create a simple S3 client using requests"""

    access_key = "jxfibkt7bkn6l5rfvl4rexkivfzq"
    secret_key = "j3cqwugqe2x7oa4ucgjb33krw2niqvnwojtpylsprszjhyyvnjnow"
    bucket_name = "videos"
    endpoint_url = "https://gateway.storjshare.io"

    return SimpleS3Client(access_key, secret_key, bucket_name, endpoint_url)


class SimpleS3Client:
    def __init__(self, access_key, secret_key, bucket_name, endpoint_url):
        self.access_key = access_key
        self.secret_key = secret_key
        self.bucket_name = bucket_name
        self.endpoint_url = endpoint_url.rstrip("/")

    def _create_signature(self, method, resource, headers, date_string):
        """Create AWS signature v2"""

        # Create canonical string
        content_md5 = headers.get("Content-MD5", "")
        content_type = headers.get("Content-Type", "")

        canonical_string = (
            f"{method}\n{content_md5}\n{content_type}\n{date_string}\n{resource}"
        )

        # Create signature
        signature = base64.b64encode(
            hmac.new(
                self.secret_key.encode(), canonical_string.encode(), hashlib.sha1
            ).digest()
        ).decode()

        return f"AWS {self.access_key}:{signature}"

    def upload_file_simple(self, file_path, s3_key):
        """Upload file using simple HTTP PUT"""

        try:
            with open(file_path, "rb") as f:
                file_content = f.read()

            # Create headers
            date_string = datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S GMT")
            headers = {
                "Date": date_string,
                "Content-Type": "application/octet-stream",
                "Content-Length": str(len(file_content)),
            }

            # Create resource
            resource = f"/{self.bucket_name}/{s3_key}"

            # Create authorization header
            headers["Authorization"] = self._create_signature(
                "PUT", resource, headers, date_string
            )

            # Make request
            url = f"{self.endpoint_url}/{self.bucket_name}/{s3_key}"

            print(f"Uploading to: {url}")
            print(f"Content-Length: {len(file_content)}")

            response = requests.put(url, data=file_content, headers=headers, timeout=60)

            if response.status_code in [200, 201]:
                print(f"✅ Upload successful!")
                return True
            else:
                print(f"❌ Upload failed: {response.status_code}")
                print(f"Response: {response.text}")
                return False

        except Exception as e:
            print(f"❌ Upload error: {e}")
            return False

    def list_files(self):
        """List files in bucket"""
        try:
            date_string = datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S GMT")
            headers = {"Date": date_string}

            resource = f"/{self.bucket_name}/"
            headers["Authorization"] = self._create_signature(
                "GET", resource, headers, date_string
            )

            url = f"{self.endpoint_url}/{self.bucket_name}/"
            response = requests.get(url, headers=headers, timeout=30)

            if response.status_code == 200:
                # Parse XML response
                root = ET.fromstring(response.content)
                files = []
                for content in root.findall(
                    ".//{http://s3.amazonaws.com/doc/2006-03-01/}Key"
                ):
                    files.append(content.text)
                return files
            else:
                print(f"❌ List failed: {response.status_code}")
                return []

        except Exception as e:
            print(f"❌ List error: {e}")
            return []


def test_simple_upload():
    """Test upload with simple S3 client"""

    from pathlib import Path

    client = create_simple_s3_client()

    # Test with smallest file first
    test_file = Path(__file__).parent / "app/embeddings/frame_paths.pkl"

    if not test_file.exists():
        print(f"Test file not found: {test_file}")
        return

    print(f"Testing upload of {test_file.name}")

    if client.upload_file_simple(test_file, "embeddings/frame_paths.pkl"):
        print("\n✅ Upload successful! Testing list...")
        files = client.list_files()
        print(f"Files in bucket: {files}")
    else:
        print("❌ Upload failed")


if __name__ == "__main__":
    test_simple_upload()

"""
Test upload using AWS CLI for better Storj compatibility
"""

import subprocess
import os
from pathlib import Path


def test_aws_cli_upload():
    """Test upload using AWS CLI"""

    # Set up environment variables for AWS CLI
    env = os.environ.copy()
    env["AWS_ACCESS_KEY_ID"] = "jxfibkt7bkn6l5rfvl4rexkivfzq"
    env["AWS_SECRET_ACCESS_KEY"] = (
        "j3cqwugqe2x7oa4ucgjb33krw2niqvnwojtpylsprszjhyyvnjnow"
    )
    env["AWS_ENDPOINT_URL"] = "https://gateway.storjshare.io"

    # Test with a small file first
    test_file = Path(__file__).parent / "app/embeddings/frame_paths.pkl"

    if not test_file.exists():
        print(f"Test file not found: {test_file}")
        return

    print(f"Testing upload of {test_file.name} ({test_file.stat().st_size} bytes)")

    # AWS CLI command
    cmd = [
        "aws",
        "s3",
        "cp",
        str(test_file),
        "s3://videos/embeddings/frame_paths.pkl",
        "--endpoint-url",
        "https://gateway.storjshare.io",
    ]

    try:
        result = subprocess.run(
            cmd, env=env, capture_output=True, text=True, timeout=60
        )

        if result.returncode == 0:
            print("✅ AWS CLI upload successful!")
            print(result.stdout)

            # Test list to verify
            list_cmd = [
                "aws",
                "s3",
                "ls",
                "s3://videos/embeddings/",
                "--endpoint-url",
                "https://gateway.storjshare.io",
            ]
            list_result = subprocess.run(
                list_cmd, env=env, capture_output=True, text=True, timeout=30
            )

            if list_result.returncode == 0:
                print("\nFiles in bucket:")
                print(list_result.stdout)
            else:
                print(f"List error: {list_result.stderr}")

        else:
            print("❌ AWS CLI upload failed!")
            print(f"Error: {result.stderr}")

    except subprocess.TimeoutExpired:
        print("❌ Upload timed out")
    except FileNotFoundError:
        print("❌ AWS CLI not found. Make sure it's installed correctly.")
    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    test_aws_cli_upload()

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

load_dotenv()

from src.storage import get_storage_manager

storage = get_storage_manager().get_storage()
files = list(storage.list_files("frames/video_1/"))[:20]
print(f"\nTotal files found: {len(files)}")
print("\nFrame paths in S3:")
for f in files:
    print(f"  {f}")

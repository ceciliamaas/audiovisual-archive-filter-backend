import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

load_dotenv()

from src.storage import get_storage_manager
import pickle
import tempfile

storage = get_storage_manager().get_storage()
print(f"Storage type: {type(storage)}")

with tempfile.NamedTemporaryFile(suffix=".pkl", delete=False) as tmp:
    tmp_path = tmp.name
    print(f"Downloading to: {tmp_path}")
    success = storage.download_file("embeddings/object_paths.pkl", tmp_path)
    print(f"Download success: {success}")

    if success:
        with open(tmp_path, "rb") as f:
            paths = pickle.load(f)

        print(f"Total: {len(paths)}")
        print("\nSample paths:")
        for p in paths[:10]:
            print(f"  {p}")
    else:
        # Try listing embeddings folder
        print("\nListing embeddings folder...")
        files = storage.list_files("embeddings/", max_results=10)
        for f in files:
            print(f"  {f}")
        print("Sample paths:")
        for p in paths[:10]:
            print(f"  {p}")

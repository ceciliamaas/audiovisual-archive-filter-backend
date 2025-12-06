import pickle
import numpy as np
from pathlib import Path
from collections import defaultdict
import os

import pickle

file_path = "clip_yolo_embeddings.pkl"

try:
    with open(file_path, "rb") as f:
        clip_embeddings = pickle.load(f)
    print(f"Loaded {len(clip_embeddings)} embeddings.")
except EOFError:
    print(f"Error: The file {file_path} is corrupted or incomplete.")
except Exception as e:
    print(f"Unexpected error: {e}")

# # Print the total number of embeddings
# print(f"Total embeddings in the file: {len(clip_embeddings)}")
# # Group embeddings by video folder
# frames_per_video = defaultdict(int)

# for path in clip_embeddings.keys():
#     # Extract the parent folder (e.g., "video_1")
#     folder = Path(path).parent.name
#     frames_per_video[folder] += 1

# # Print the number of frames per video
# print("\nNumber of frames per video:")
# for folder, count in frames_per_video.items():
#     print(f"{folder}: {count} frames")

import pickle
import numpy as np
from pathlib import Path

# Load the embeddings
with open("clip_only_embeddings.pkl", "rb") as f:
    clip_embeddings = pickle.load(f)

# Print the total number of embeddings
print(f"Total embeddings in the file: {len(clip_embeddings)}")

# Inspect the structure of the file
print("\nInspecting the structure of the embeddings file:\n")
for i, (path, embedding) in enumerate(clip_embeddings.items()):
    print(f"Path: {path}")  # Print the path (key)
    print(
        f"Embedding shape: {np.array(embedding).shape}"
    )  # Print the shape of the embedding
    print(
        f"Embedding (first 10 values): {np.array(embedding)[:10]}"
    )  # Print the first 10 values of the embedding
    print("-" * 50)

    # Limit the output to the first 10 entries for readability
    if i >= 9:
        print("\n... (only showing the first 10 entries)")
        break

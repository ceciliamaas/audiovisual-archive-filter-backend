#!/usr/bin/env python3
"""
Reindex existing videos to add bounding box data to Qdrant.

This script:
1. Re-runs YOLO detection to create bbox JSON metadata files
2. Updates Qdrant with the bbox data from those JSON files

Usage: python reindex_with_bbox.py <video_name>
"""

import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from scripts.pipeline.steps.compute_embeddings import ComputeEmbeddingsStep
from scripts.pipeline.state import PipelineState


def main():
    if len(sys.argv) < 2:
        print("Usage: python reindex_with_bbox.py <video_name>")
        print(
            "Example: python reindex_with_bbox.py manifestacion_jubilados_12_de_marzo"
        )
        sys.exit(1)

    video_name = sys.argv[1]

    print(f"🔄 Reindexing video with bbox data: {video_name}")
    print("=" * 60)

    # Load pipeline state
    state = PipelineState.load(video_name)

    # Recompute embeddings (which will also update Qdrant with bbox data)
    print("\n1️⃣ Recomputing embeddings and updating Qdrant with bbox data...")
    embed_step = ComputeEmbeddingsStep(state=state, config={})

    # Validate input
    valid, error_msg = embed_step.validate_input()
    if not valid:
        print(f"❌ Validation failed: {error_msg}")
        sys.exit(1)

    # Execute
    success = embed_step.execute()
    if not success:
        print("\n❌ Failed to compute embeddings")
        sys.exit(1)

    # Validate output
    valid, error_msg = embed_step.validate_output()
    if not valid:
        print(f"❌ Validation failed: {error_msg}")
        sys.exit(1)

    print("\n" + "=" * 60)
    print("✅ Successfully reindexed video with bbox data!")
    print("   The search API will now return bounding box coordinates.")
    print("   Try searching and you should see boxes drawn on images.")


if __name__ == "__main__":
    main()

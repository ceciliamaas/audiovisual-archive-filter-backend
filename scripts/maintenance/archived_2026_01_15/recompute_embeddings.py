#!/usr/bin/env python3
"""
Script to recompute embeddings for a specific video.
This bypasses the pipeline state and directly runs the compute_embeddings step.
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
        print("Usage: python recompute_embeddings.py <video_name>")
        print(
            "Example: python recompute_embeddings.py reconstruccion_jonathan_timestamps"
        )
        sys.exit(1)

    video_name = sys.argv[1]

    print(f"🔄 Recomputing embeddings for: {video_name}")
    print("=" * 60)

    # Load or create pipeline state
    state = PipelineState.load(video_name)

    # Create and run the embeddings step
    step = ComputeEmbeddingsStep(state=state, config={})

    # Validate input
    print("\n1️⃣ Validating input...")
    valid, error_msg = step.validate_input()
    if not valid:
        print(f"❌ Validation failed: {error_msg}")
        sys.exit(1)
    print("✅ Input validated")

    # Execute
    print("\n2️⃣ Computing embeddings...")
    success = step.execute()

    if not success:
        print("\n❌ Failed to compute embeddings")
        sys.exit(1)

    # Validate output
    print("\n3️⃣ Validating output...")
    valid, error_msg = step.validate_output()
    if not valid:
        print(f"❌ Validation failed: {error_msg}")
        sys.exit(1)

    print("\n" + "=" * 60)
    print("✅ Successfully recomputed embeddings!")
    print("   You can now use the search API again with unique results.")


if __name__ == "__main__":
    main()

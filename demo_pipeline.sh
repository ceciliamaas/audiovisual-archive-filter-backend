#!/bin/bash

# Demo: Complete Pipeline Usage
# This script demonstrates all pipeline capabilities

echo "=========================================="
echo "  INTEGRATED PIPELINE DEMONSTRATION"
echo "=========================================="
echo ""

# 1. Show help
echo "1. Pipeline Commands"
echo "-------------------"
python -m scripts.pipeline --help
echo ""

# 2. List current videos
echo ""
echo "2. Current Videos"
echo "-----------------"
python -m scripts.pipeline list
echo ""

# 3. Show example process command
echo ""
echo "3. Example: Process YouTube Video"
echo "----------------------------------"
echo "Command:"
echo '  python -m scripts.pipeline process "my_video" \'
echo '      --source youtube \'
echo '      --url "https://youtube.com/watch?v=..."'
echo ""

# 4. Show example with options
echo ""
echo "4. Example: Process with Custom Options"
echo "---------------------------------------"
echo "Command:"
echo '  python -m scripts.pipeline process "my_video" \'
echo '      --source youtube \'
echo '      --url "https://youtube.com/watch?v=..." \'
echo '      --fps 2 \'
echo '      --yolo-classes "person,gun,car,building"'
echo ""

# 5. Show resume example
echo ""
echo "5. Example: Resume Processing"
echo "-----------------------------"
echo "Command:"
echo '  python -m scripts.pipeline resume "my_video"'
echo ""

# 6. Show status example
echo ""
echo "6. Example: Check Status"
echo "------------------------"
echo "Command:"
echo '  python -m scripts.pipeline status "my_video"'
echo ""

# 7. Show validation example
echo ""
echo "7. Example: Validate Artifacts"
echo "------------------------------"
echo "Command:"
echo '  python -m scripts.pipeline validate "my_video"'
echo ""

# 8. Show what gets created
echo ""
echo "8. Files Created for a Video"
echo "----------------------------"
echo "Local:"
echo "  data/videos/my_video.mp4"
echo "  data/frames/my_video/frame_00000.jpg (... 240 frames)"
echo "  data/objects/my_video/frame_00000_obj_000.jpg (... 1500 objects)"
echo "  data/embeddings/frame_embeddings.pkl"
echo "  data/embeddings/frame_paths.pkl"
echo "  data/embeddings/object_embeddings.pkl"
echo "  data/embeddings/object_paths.pkl"
echo "  data/pipeline_state/my_video.json"
echo ""
echo "S3 (if configured):"
echo "  s3://bucket/videos/my_video.mp4"
echo "  s3://bucket/frames/my_video/frame_00000.jpg"
echo "  s3://bucket/objects/my_video/frame_00000_obj_000.jpg"
echo "  s3://bucket/embeddings/*.pkl"
echo ""

# 9. Show complete workflow
echo ""
echo "9. Complete Workflow Example"
echo "----------------------------"
echo "# Process a new protest video"
echo 'python -m scripts.pipeline process "protest_2024_jan" \'
echo '    --source youtube \'
echo '    --url "https://youtube.com/watch?v=abc123" \'
echo '    --fps 1 \'
echo '    --yolo-classes "person,gun,backpack,hat,building"'
echo ""
echo "# Check status"
echo 'python -m scripts.pipeline status "protest_2024_jan"'
echo ""
echo "# Validate results"
echo 'python -m scripts.pipeline validate "protest_2024_jan"'
echo ""
echo "# List all videos"
echo 'python -m scripts.pipeline list'
echo ""

# 10. Key features summary
echo ""
echo "10. Key Features"
echo "---------------"
echo "  ✅ Single command for complete pipeline"
echo "  ✅ Resume from any interruption"
echo "  ✅ Skip completed steps automatically"
echo "  ✅ Multiple source types (YouTube/Drive/local)"
echo "  ✅ Configurable FPS and YOLO settings"
echo "  ✅ Status tracking and validation"
echo "  ✅ Standardized naming conventions"
echo "  ✅ S3 upload support"
echo "  ✅ Progress tracking"
echo "  ✅ Error handling with clear messages"
echo ""

echo "=========================================="
echo "  For more details, see:"
echo "  - scripts/PIPELINE_GUIDE.md"
echo "  - PHASE2_COMPLETE.md"
echo "=========================================="

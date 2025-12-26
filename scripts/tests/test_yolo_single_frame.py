#!/usr/bin/env python3
"""Test YOLO on a single frame to debug output"""

import os
import sys
import json
from pathlib import Path
from dotenv import load_dotenv
import replicate

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

load_dotenv()

REPLICATE_API_TOKEN = os.getenv("REPLICATE_API_TOKEN")
client = replicate.Client(api_token=REPLICATE_API_TOKEN)

# Test frame
FRAMES_DIR = PROJECT_ROOT / "data" / "frames"
test_frame = FRAMES_DIR / "video_reconstrucción_jonathan" / "frame_00000.jpg"

print(f"Testing YOLO on: {test_frame}")
print(f"File exists: {test_frame.exists()}")

if test_frame.exists():
    # Test with adjusted parameters that might work better
    print(f"\n{'='*60}")
    print(f"Testing YOLO detection")
    print(f"{'='*60}")

    with open(test_frame, "rb") as f:
        output = client.run(
            "franz-biz/yolo-world-xl:fd1305d3fc19e81540542f51c2530cf8f393e28cc6ff4976337c3e2b75c7c292",
            input={
                "input_media": f,
                "classes": "person",
                "confidence_threshold": 0.01,
                "iou_threshold": 0.5,
                "return_json": True,  # Try explicitly requesting JSON
            },
        )

    print(f"Output type: {type(output)}")
    print(f"Output keys: {list(output.keys()) if isinstance(output, dict) else 'N/A'}")
    print(f"\nFull output structure:")
    print(
        json.dumps(
            {
                k: str(v)[:100] if not isinstance(v, (dict, list)) else v
                for k, v in output.items()
            },
            indent=2,
        )
    )

    if "json_str" in output:
        json_str = output["json_str"]
        print(f"\njson_str: {json_str}")

    if "media_path" in output:
        print(f"\nmedia_path: {output['media_path']}")

else:
    print("Test frame not found!")

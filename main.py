"""
Main entry point for the audiovisual archive search application.
This replaces the original app.py and provides a clean interface to the refactored application.
"""

import sys
from pathlib import Path

# Load environment variables early
from dotenv import load_dotenv

load_dotenv()

# Add src to Python path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

# Import and run the web application
from src.web.app import main

if __name__ == "__main__":
    main()

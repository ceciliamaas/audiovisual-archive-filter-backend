#!/bin/bash
cd /Users/Cecilia/Documents/Programación/archive-filter_backend
.venv/bin/python -m uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000

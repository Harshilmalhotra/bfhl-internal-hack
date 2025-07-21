"""
Vercel-compatible FastAPI application handler
"""
import sys
import os
from pathlib import Path

# Add parent directory to Python path
parent_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(parent_dir))

# Now import the FastAPI app
from app import app

# Export for Vercel
app = app
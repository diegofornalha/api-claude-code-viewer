#!/usr/bin/env python3
"""Start corrected server on port 8990."""

import uvicorn
import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from server import app

if __name__ == "__main__":
    print("🚀 Starting corrected Claude Chat API on port 8991...")
    print("✅ Includes: CORS fixes, SDK corrections, loguru dependency")
    print("🔧 Backend na porta 8991 (evitando conflitos)")
    
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=8991, 
        reload=False,
        log_level="info"
    )
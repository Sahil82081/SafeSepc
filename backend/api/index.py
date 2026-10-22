import sys
from pathlib import Path

# Add project root and backend to python path for Vercel serverless runtime
CURRENT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = CURRENT_DIR.parent
REPO_ROOT = BACKEND_DIR.parent

for p in (str(REPO_ROOT), str(BACKEND_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

from backend.app.main import app

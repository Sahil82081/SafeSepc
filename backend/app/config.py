"""SafeSpec Configuration.

Only this file defines the LLM model name.
API keys, paths, and retry limits are centrally configured here.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Directory Paths
BACKEND_DIR = Path(__file__).resolve().parent.parent
ROOT_DIR = BACKEND_DIR.parent
APP_DIR = BACKEND_DIR / "app"

DOCUMENTS_DIR = BACKEND_DIR / "documents"
EVALUATION_DIR = BACKEND_DIR / "evaluation"
REPORTS_DIR = APP_DIR / "reports"
ECU_VERSIONS_DIR = APP_DIR / "ecu" / "versions"

# Ensure runtime directories exist
DOCUMENTS_DIR.mkdir(parents=True, exist_ok=True)
EVALUATION_DIR.mkdir(parents=True, exist_ok=True)
REPORTS_DIR.mkdir(parents=True, exist_ok=True)
ECU_VERSIONS_DIR.mkdir(parents=True, exist_ok=True)

# Environment loading
ENV_PATH = ROOT_DIR / ".env"
BACKEND_ENV_PATH = BACKEND_DIR / ".env"

if BACKEND_ENV_PATH.exists():
    load_dotenv(dotenv_path=BACKEND_ENV_PATH)
elif ENV_PATH.exists():
    load_dotenv(dotenv_path=ENV_PATH)
else:
    load_dotenv()

# Rule 3: The Gemini key comes from .env (GEMINI_API_KEY).
GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")

# Rule 3: The model name lives ONLY in backend/app/config.py.
GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-flash-lite-latest")

# Database Configuration
DATABASE_PATH = (BACKEND_DIR / "safespec.db").resolve()
_env_db = os.getenv("DATABASE_URL", "")
if not _env_db or "sqlite:///." in _env_db:
    DATABASE_URL: str = f"sqlite:///{DATABASE_PATH.as_posix()}"
else:
    DATABASE_URL: str = _env_db

# Rule 7: Agent loop limits
MAX_FIX_ATTEMPTS: int = 3
MAX_TOOL_CALLS_PER_ATTEMPT: int = 8

# Automotive Safety Integrity Levels requiring human sign-off (Rule 9)
HIGH_RISK_ASIL_LEVELS: tuple[str, ...] = ("C", "D")

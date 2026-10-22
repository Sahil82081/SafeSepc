import sys
import types
from pathlib import Path

# Ensure both repo root and backend directory are in sys.path
_CURRENT_DIR = Path(__file__).resolve().parent  # app/
_BACKEND_DIR = _CURRENT_DIR.parent              # backend/
_REPO_ROOT = _BACKEND_DIR.parent                # repo root/

for _path in (str(_REPO_ROOT), str(_BACKEND_DIR)):
    if _path not in sys.path:
        sys.path.insert(0, _path)

# If running directly inside backend/ where 'backend' package is not recognized,
# register 'backend' in sys.modules pointing to _BACKEND_DIR so 'from backend.app...' works
if "backend" not in sys.modules:
    try:
        import backend  # noqa: F401
    except ModuleNotFoundError:
        _backend_pkg = types.ModuleType("backend")
        _backend_pkg.__path__ = [str(_BACKEND_DIR)]
        sys.modules["backend"] = _backend_pkg

from contextlib import asynccontextmanager
from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware

from backend.app.config import GEMINI_MODEL
from backend.app.db.session import init_db
from backend.app.api.routes import router as api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context manager initializing SQLite database."""
    init_db()
    yield


app = FastAPI(
    title="SafeSpec API",
    description="Automotive Requirements Verification, Formal Proof & ECU Simulation Platform",
    version="0.1.0",
    lifespan=lifespan,
)

# Enable CORS for frontend communication (specifically http://localhost:5173)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "*",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API routers
app.include_router(api_router)


@app.get("/", status_code=status.HTTP_200_OK, tags=["system"])
@app.head("/", status_code=status.HTTP_200_OK, tags=["system"])
async def root() -> dict:
    """Root service information and ping endpoint."""
    return {
        "status": "online",
        "service": "SafeSpec API",
        "version": "0.1.0",
    }


@app.get("/health", tags=["system"])
@app.head("/health", tags=["system"])
async def health_check() -> dict:
    """Service health and system status check."""
    return {
        "status": "healthy",
        "service": "SafeSpec",
        "version": "0.1.0",
        "model_configured": bool(GEMINI_MODEL),
    }


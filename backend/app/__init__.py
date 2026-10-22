"""SafeSpec Backend Application Package."""

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

if "backend" not in sys.modules:
    try:
        import backend  # noqa: F401
    except ModuleNotFoundError:
        _backend_pkg = types.ModuleType("backend")
        _backend_pkg.__path__ = [str(_BACKEND_DIR)]
        sys.modules["backend"] = _backend_pkg

__version__ = "0.1.0"


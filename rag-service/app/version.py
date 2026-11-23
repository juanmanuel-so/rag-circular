"""Service version. pyproject.toml is the source of truth; GIT_SHA comes from the Docker build."""
import os
import tomllib
from pathlib import Path

_PYPROJECT = Path(__file__).resolve().parent.parent / "pyproject.toml"

try:
    _project = tomllib.loads(_PYPROJECT.read_text())["project"]
except (OSError, KeyError, tomllib.TOMLDecodeError):
    _project = {}

NAME: str = _project.get("name", "rag-circular")
VERSION: str = _project.get("version", "0.0.0")
COMMIT: str | None = os.environ.get("GIT_SHA", "")[:12] or None

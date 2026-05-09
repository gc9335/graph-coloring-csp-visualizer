from __future__ import annotations

import os
from pathlib import Path
import sys
import tempfile


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _configure_workspace_temp() -> Path:
    root = PROJECT_ROOT / ".tmp"
    root.mkdir(parents=True, exist_ok=True)
    for env_name in ("TMPDIR", "TEMP", "TMP"):
        os.environ.setdefault(env_name, str(root))
    tempfile.tempdir = str(root)
    return root


_WORKSPACE_TEMP = _configure_workspace_temp()


def pytest_configure(config) -> None:
    basetemp = _WORKSPACE_TEMP / "pytest"
    basetemp.mkdir(parents=True, exist_ok=True)
    config.option.basetemp = str(basetemp)

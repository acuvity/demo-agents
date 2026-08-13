"""Filesystem roots for the agent package (CWD-independent)."""
from __future__ import annotations

import os
from pathlib import Path


def get_agent_root() -> Path:
    """Directory containing main.py, tools/, prompt-scenarios/, docs/.

    Override with env IBAC_AGENT_ROOT for non-standard layouts.
    """
    override = os.environ.get("IBAC_AGENT_ROOT", "").strip()
    if override:
        return Path(override).expanduser().resolve()
    return Path(__file__).resolve().parent.parent


def get_upload_dir() -> Path:
    """PDF upload directory; must match server.py and tools that read uploads."""
    raw = os.environ.get("IBAC_UPLOAD_DIR", "").strip()
    if raw:
        return Path(raw).expanduser().resolve()
    return (get_agent_root() / "uploads").resolve()

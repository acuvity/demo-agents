from __future__ import annotations

import logging
import os
import re
from pathlib import Path
from typing import Any

import yaml

_ENV_PATTERN = re.compile(r"\$\{([^}]+)\}")
logger = logging.getLogger("uvicorn.error")


def warn(msg: str) -> None:
    logger.warning(msg)


def info(msg: str) -> None:
    logger.info(msg)


def expand_env(value: Any) -> Any:
    """Recursively expand ${VAR} references in strings using os.environ."""
    if isinstance(value, str):
        def _replace(m: re.Match[str]) -> str:
            env_var = m.group(1)
            result = os.environ.get(env_var, "")
            if not result:
                warn(f"environment variable '{env_var}' is not set")
            return result

        return _ENV_PATTERN.sub(_replace, value)

    if isinstance(value, dict):
        return {k: expand_env(v) for k, v in value.items()}

    if isinstance(value, list):
        return [expand_env(i) for i in value]

    return value


def load_config(path: str) -> dict:
    raw = Path(path).read_text()
    data = yaml.safe_load(raw)
    return expand_env(data or {})
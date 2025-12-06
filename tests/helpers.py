"""Test helper functions for appimage-configs tests."""

import json
from pathlib import Path


def write_config(path: Path, config: dict | str) -> Path:
    """Write a config to a file, return the path."""
    if isinstance(config, str):
        path.write_text(config, encoding="utf-8")
    else:
        path.write_text(json.dumps(config, indent=2), encoding="utf-8")
    return path

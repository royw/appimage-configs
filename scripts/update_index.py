#!/usr/bin/env python3
"""Generate index.json from config files in the configs/ directory.

Creates a new_index.json file, then atomically swaps it with index.json.
"""

import hashlib
import json
import os
import sys
from pathlib import Path


def compute_sha256(file_path: Path) -> str:
    """Compute SHA256 hash of a file."""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256_hash.update(chunk)
    return f"sha256:{sha256_hash.hexdigest()}"


def extract_app_name(config_path: Path) -> str | None:
    """Extract the app name from a config file.
    
    Looks for name in:
    1. applications[0].name (appimage-updater format)
    2. Top-level 'name' field
    3. Falls back to filename stem (preserving case)
    """
    try:
        with open(config_path, encoding="utf-8") as f:
            config = json.load(f)
            
            # Check applications[0].name first (appimage-updater format)
            if "applications" in config and config["applications"]:
                app_name = config["applications"][0].get("name")
                if app_name:
                    return app_name
            
            # Check top-level name
            if config.get("name"):
                return config["name"]
            
            # Fallback to filename stem (preserving case)
            return config_path.stem
    except (json.JSONDecodeError, OSError) as e:
        print(f"Warning: Could not read {config_path}: {e}", file=sys.stderr)
        return None


def build_index(configs_dir: Path) -> dict[str, list[str]]:
    """Build index from all JSON files in configs directory.
    
    Returns:
        Dict mapping app name to [relative_path, hash]
    """
    index: dict[str, list[str]] = {}
    
    if not configs_dir.exists():
        print(f"Warning: configs directory not found: {configs_dir}", file=sys.stderr)
        return index
    
    for config_path in sorted(configs_dir.glob("*.json")):
        app_name = extract_app_name(config_path)
        if app_name is None:
            continue
            
        relative_path = f"configs/{config_path.name}"
        file_hash = compute_sha256(config_path)
        index[app_name] = [relative_path, file_hash]
        print(f"  {app_name}: {relative_path}")
    
    return index


def update_index(repo_root: Path) -> bool:
    """Generate new index and atomically swap with existing index.json.
    
    Returns:
        True if index was updated, False on error
    """
    configs_dir = repo_root / "configs"
    index_path = repo_root / "index.json"
    new_index_path = repo_root / "new_index.json"
    
    print(f"Scanning {configs_dir}...")
    index = build_index(configs_dir)
    
    if not index:
        print("Error: No valid config files found", file=sys.stderr)
        return False
    
    # Write new index
    print(f"\nWriting {new_index_path}...")
    with open(new_index_path, "w", encoding="utf-8") as f:
        json.dump(index, f, indent=2, sort_keys=True)
        f.write("\n")  # Trailing newline
    
    # Atomic swap (rename is atomic on POSIX systems)
    print(f"Swapping {new_index_path} -> {index_path}...")
    os.replace(new_index_path, index_path)
    
    print(f"\nUpdated index.json with {len(index)} apps")
    return True


def main() -> int:
    """Main entry point."""
    # Determine repo root (script is in scripts/)
    script_dir = Path(__file__).resolve().parent
    repo_root = script_dir.parent
    
    print(f"Repository root: {repo_root}")
    
    if not update_index(repo_root):
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

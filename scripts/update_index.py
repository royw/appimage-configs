#!/usr/bin/env python3
"""Generate index.json from config files in the configs/ directory.

Creates a new_index.json file, then atomically swaps it with index.json.

The index.json includes:
- repo_hash: SHA256 of all config hashes (for quick change detection)
- generated_at: ISO timestamp of generation
- Per-app entries: [config_path, sha256_hash]

Each config is validated before being added to the index.
The script fails with non-zero exit if any validation errors occur.
"""

import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# Import validator from sibling module
from validate_configs import ConfigValidator, load_schema


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


def compute_repo_hash(config_hashes: list[str]) -> str:
    """Compute a combined hash of all config hashes.
    
    This provides a quick way to check if any config has changed.
    """
    # Sort hashes for deterministic output
    combined = "\n".join(sorted(config_hashes))
    repo_hash = hashlib.sha256(combined.encode()).hexdigest()
    return f"sha256:{repo_hash}"


def build_index(configs_dir: Path, validator: ConfigValidator) -> dict | None:
    """Build index from all JSON files in configs directory.
    
    Args:
        configs_dir: Path to the configs directory
        validator: ConfigValidator instance for validation
    
    Returns:
        Dict with repo_hash, generated_at, and app entries, or None if validation failed
    """
    apps: dict[str, list[str]] = {}
    config_hashes: list[str] = []
    validation_failed = False
    
    if not configs_dir.exists():
        print(f"Warning: configs directory not found: {configs_dir}", file=sys.stderr)
        return None
    
    for config_path in sorted(configs_dir.glob("*.json")):
        # Validate config before adding
        if not validator.validate_file(config_path):
            print(f"  ✗ {config_path.name} - validation failed", file=sys.stderr)
            validation_failed = True
            continue
        
        app_name = extract_app_name(config_path)
        if app_name is None:
            continue
            
        relative_path = f"configs/{config_path.name}"
        file_hash = compute_sha256(config_path)
        apps[app_name] = [relative_path, file_hash]
        config_hashes.append(file_hash)
        print(f"  ✓ {app_name}: {relative_path}")
    
    # Fail if any validation errors
    if validation_failed:
        print("\n✗ Validation errors:", file=sys.stderr)
        for error in validator.errors:
            print(f"  - {error}", file=sys.stderr)
        return None
    
    if not apps:
        return None
    
    # Build final index with metadata
    index = {
        "repo_hash": compute_repo_hash(config_hashes),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        **apps,
    }
    
    return index


def update_index(repo_root: Path) -> bool:
    """Generate new index and atomically swap with existing index.json.
    
    Returns:
        True if index was updated, False on error
    """
    configs_dir = repo_root / "configs"
    index_path = repo_root / "index.json"
    new_index_path = repo_root / "new_index.json"
    
    # Load schema for validation
    schema = load_schema(repo_root)
    if schema:
        print("Using JSON Schema validation")
    validator = ConfigValidator(schema=schema)
    
    print(f"\nScanning and validating {configs_dir}...")
    index = build_index(configs_dir, validator)
    
    if index is None:
        print("Error: Validation failed or no valid config files found", file=sys.stderr)
        return False
    
    # Count apps (excluding metadata keys)
    app_count = len(index) - 2  # Subtract repo_hash and generated_at
    print(f"\nRepo hash: {index['repo_hash']}")
    
    # Write new index
    print(f"\nWriting {new_index_path}...")
    with open(new_index_path, "w", encoding="utf-8") as f:
        json.dump(index, f, indent=2, sort_keys=True)
        f.write("\n")  # Trailing newline
    
    # Atomic swap (rename is atomic on POSIX systems)
    print(f"Swapping {new_index_path} -> {index_path}...")
    os.replace(new_index_path, index_path)
    
    print(f"\nUpdated index.json with {app_count} apps")
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

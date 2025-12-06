#!/usr/bin/env python3
"""Validate app configuration files in the configs/ directory.

Validations performed:
- JSON Schema: Validates against schemas/app-config.schema.json (if jsonschema installed)
- JSON syntax: Valid JSON parsing
- Required fields: name, url, download_dir, pattern
- Field types: Correct types for all fields
- Relative paths: download_dir and symlink_path must not be absolute
- Valid source types: github, gitlab, sourceforge, direct, direct_download, dynamic_download
- Regex patterns: Valid regex syntax in pattern field
- URL format: Must start with http:// or https://
- Checksum config: Valid algorithm values (sha256, sha512, md5)
- Name matching: Warning if filename doesn't match app name

Usage:
    python scripts/validate_configs.py
    python scripts/validate_configs.py --no-schema  # Skip JSON Schema validation
"""

import argparse
import json
import re
import sys
from pathlib import Path

# Optional JSON Schema validation
try:
    import jsonschema
    HAS_JSONSCHEMA = True
except ImportError:
    HAS_JSONSCHEMA = False


class ValidationError:
    """A single validation error."""

    def __init__(self, file: str, message: str, field: str | None = None):
        self.file = file
        self.message = message
        self.field = field

    def __str__(self) -> str:
        if self.field:
            return f"{self.file}: [{self.field}] {self.message}"
        return f"{self.file}: {self.message}"


class ConfigValidator:
    """Validates appimage-updater config files."""

    # Required fields in the application config
    REQUIRED_APP_FIELDS = {"name", "url", "download_dir", "pattern"}

    def __init__(self, schema: dict | None = None):
        self.errors: list[ValidationError] = []
        self.warnings: list[ValidationError] = []
        self.schema = schema

    # Optional fields with their expected types
    OPTIONAL_APP_FIELDS = {
        "source_type": str,
        "version_pattern": (str, type(None)),
        "basename": (str, type(None)),
        "enabled": bool,
        "prerelease": bool,
        "rotation_enabled": bool,
        "symlink_path": (str, type(None)),
        "retain_count": int,
        "checksum": dict,
    }

    # Fields that contain paths (must be relative)
    PATH_FIELDS = {"download_dir", "symlink_path"}

    # Valid source types (from appimage-updater handlers)
    VALID_SOURCE_TYPES = {
        "github",
        "gitlab",
        "sourceforge",
        "direct",           # alias for direct_download
        "direct_download",
        "dynamic_download",
    }

    def validate_file(self, config_path: Path) -> bool:
        """Validate a single config file. Returns True if valid."""
        filename = config_path.name
        initial_error_count = len(self.errors)

        # Check JSON syntax
        try:
            with open(config_path, encoding="utf-8") as f:
                config = json.load(f)
        except json.JSONDecodeError as e:
            self.errors.append(ValidationError(filename, f"Invalid JSON: {e}"))
            return False
        except OSError as e:
            self.errors.append(ValidationError(filename, f"Cannot read file: {e}"))
            return False

        # Validate against JSON Schema if available
        if self.schema and HAS_JSONSCHEMA:
            try:
                jsonschema.validate(config, self.schema)
            except jsonschema.ValidationError as e:
                # Extract the most relevant error info
                path = ".".join(str(p) for p in e.absolute_path) if e.absolute_path else ""
                self.errors.append(
                    ValidationError(filename, e.message, path if path else None)
                )

        # Check top-level structure
        if "applications" not in config:
            self.errors.append(
                ValidationError(filename, "Missing 'applications' array", "applications")
            )
            return False

        if not isinstance(config["applications"], list):
            self.errors.append(
                ValidationError(filename, "'applications' must be an array", "applications")
            )
            return False

        if len(config["applications"]) == 0:
            self.errors.append(
                ValidationError(filename, "'applications' array is empty", "applications")
            )
            return False

        # Validate each application entry
        for i, app in enumerate(config["applications"]):
            self._validate_app(filename, app, i)

        # Check that app name matches filename (for first app)
        if config["applications"]:
            app_name = config["applications"][0].get("name", "")
            expected_filename = f"{app_name.lower()}.json"
            # Allow some flexibility - compare lowercase
            if config_path.name.lower() != expected_filename.lower():
                self.warnings.append(
                    ValidationError(
                        filename,
                        f"Filename '{config_path.name}' doesn't match app name '{app_name}'",
                        "name",
                    )
                )

        return len(self.errors) == initial_error_count

    def _validate_app(self, filename: str, app: dict, index: int) -> None:
        """Validate a single application entry."""
        prefix = f"applications[{index}]"

        if not isinstance(app, dict):
            self.errors.append(
                ValidationError(filename, f"{prefix} must be an object")
            )
            return

        # Check required fields
        for field in self.REQUIRED_APP_FIELDS:
            if field not in app:
                self.errors.append(
                    ValidationError(filename, "Missing required field", f"{prefix}.{field}")
                )
            elif app[field] is None or app[field] == "":
                self.errors.append(
                    ValidationError(filename, "Field cannot be empty", f"{prefix}.{field}")
                )

        # Validate field types and values
        self._validate_name(filename, app, prefix)
        self._validate_url(filename, app, prefix)
        self._validate_pattern(filename, app, prefix)
        self._validate_paths(filename, app, prefix)
        self._validate_source_type(filename, app, prefix)
        self._validate_checksum(filename, app, prefix)
        self._validate_optional_types(filename, app, prefix)

    def _validate_name(self, filename: str, app: dict, prefix: str) -> None:
        """Validate app name."""
        name = app.get("name")
        if name and not isinstance(name, str):
            self.errors.append(
                ValidationError(filename, "Must be a string", f"{prefix}.name")
            )
        elif name and not re.match(r"^[A-Za-z0-9_-]+$", name):
            self.warnings.append(
                ValidationError(
                    filename,
                    f"Name '{name}' contains special characters",
                    f"{prefix}.name",
                )
            )

    def _validate_url(self, filename: str, app: dict, prefix: str) -> None:
        """Validate repository URL."""
        url = app.get("url")
        if url and not isinstance(url, str):
            self.errors.append(
                ValidationError(filename, "Must be a string", f"{prefix}.url")
            )
        elif url and not url.startswith(("http://", "https://")):
            self.errors.append(
                ValidationError(filename, "URL must start with http:// or https://", f"{prefix}.url")
            )

    def _validate_pattern(self, filename: str, app: dict, prefix: str) -> None:
        """Validate regex pattern."""
        pattern = app.get("pattern")
        if pattern and not isinstance(pattern, str):
            self.errors.append(
                ValidationError(filename, "Must be a string", f"{prefix}.pattern")
            )
        elif pattern:
            try:
                re.compile(pattern)
            except re.error as e:
                self.errors.append(
                    ValidationError(filename, f"Invalid regex: {e}", f"{prefix}.pattern")
                )

    def _validate_paths(self, filename: str, app: dict, prefix: str) -> None:
        """Validate that all path fields are relative."""
        for field in self.PATH_FIELDS:
            value = app.get(field)
            if value is None:
                continue

            if not isinstance(value, str):
                self.errors.append(
                    ValidationError(filename, "Must be a string", f"{prefix}.{field}")
                )
                continue

            # Check for absolute paths
            if value.startswith("/"):
                self.errors.append(
                    ValidationError(
                        filename,
                        f"Path must be relative, not absolute: '{value}'",
                        f"{prefix}.{field}",
                    )
                )
            elif value.startswith("~"):
                self.errors.append(
                    ValidationError(
                        filename,
                        f"Path must be relative, not use ~: '{value}'",
                        f"{prefix}.{field}",
                    )
                )
            elif re.match(r"^[A-Za-z]:", value):  # Windows absolute path
                self.errors.append(
                    ValidationError(
                        filename,
                        f"Path must be relative, not absolute: '{value}'",
                        f"{prefix}.{field}",
                    )
                )

    def _validate_source_type(self, filename: str, app: dict, prefix: str) -> None:
        """Validate source type."""
        source_type = app.get("source_type")
        if source_type is None:
            return

        if not isinstance(source_type, str):
            self.errors.append(
                ValidationError(filename, "Must be a string", f"{prefix}.source_type")
            )
        elif source_type not in self.VALID_SOURCE_TYPES:
            self.errors.append(
                ValidationError(
                    filename,
                    f"Invalid source_type '{source_type}'. Valid: {self.VALID_SOURCE_TYPES}",
                    f"{prefix}.source_type",
                )
            )

    def _validate_checksum(self, filename: str, app: dict, prefix: str) -> None:
        """Validate checksum configuration."""
        checksum = app.get("checksum")
        if checksum is None:
            return

        if not isinstance(checksum, dict):
            self.errors.append(
                ValidationError(filename, "Must be an object", f"{prefix}.checksum")
            )
            return

        # Validate checksum fields
        if "enabled" in checksum and not isinstance(checksum["enabled"], bool):
            self.errors.append(
                ValidationError(filename, "Must be a boolean", f"{prefix}.checksum.enabled")
            )

        if "algorithm" in checksum:
            valid_algorithms = {"sha256", "sha512", "md5"}
            if checksum["algorithm"] not in valid_algorithms:
                self.errors.append(
                    ValidationError(
                        filename,
                        f"Invalid algorithm. Valid: {valid_algorithms}",
                        f"{prefix}.checksum.algorithm",
                    )
                )

    def _validate_optional_types(self, filename: str, app: dict, prefix: str) -> None:
        """Validate types of optional fields."""
        for field, expected_type in self.OPTIONAL_APP_FIELDS.items():
            if field not in app or field in {"checksum"}:  # checksum handled separately
                continue

            value = app[field]
            if not isinstance(value, expected_type):
                type_name = (
                    expected_type.__name__
                    if isinstance(expected_type, type)
                    else str(expected_type)
                )
                self.errors.append(
                    ValidationError(
                        filename, f"Expected type {type_name}, got {type(value).__name__}", f"{prefix}.{field}"
                    )
                )


def load_schema(repo_root: Path) -> dict | None:
    """Load the JSON schema if available."""
    schema_path = repo_root / "schemas" / "app-config.schema.json"
    if not schema_path.exists():
        return None
    try:
        with open(schema_path, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def validate_configs(
    configs_dir: Path, schema: dict | None = None
) -> tuple[list[ValidationError], list[ValidationError]]:
    """Validate all config files in directory.
    
    Returns:
        Tuple of (errors, warnings)
    """
    validator = ConfigValidator(schema=schema)

    if not configs_dir.exists():
        validator.errors.append(
            ValidationError(str(configs_dir), "Directory does not exist")
        )
        return validator.errors, validator.warnings

    config_files = sorted(configs_dir.glob("*.json"))
    if not config_files:
        validator.warnings.append(
            ValidationError(str(configs_dir), "No config files found")
        )
        return validator.errors, validator.warnings

    print(f"Validating {len(config_files)} config files in {configs_dir}...\n")

    valid_count = 0
    for config_path in config_files:
        if validator.validate_file(config_path):
            valid_count += 1
            print(f"  ✓ {config_path.name}")
        else:
            print(f"  ✗ {config_path.name}")

    return validator.errors, validator.warnings


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Validate app configuration files in the configs/ directory."
    )
    parser.add_argument(
        "--no-schema",
        action="store_true",
        help="Skip JSON Schema validation",
    )
    args = parser.parse_args()

    # Determine repo root (script is in scripts/)
    script_dir = Path(__file__).resolve().parent
    repo_root = script_dir.parent
    configs_dir = repo_root / "configs"

    print(f"Repository root: {repo_root}\n")

    # Load schema unless disabled
    schema = None
    if not args.no_schema:
        schema = load_schema(repo_root)
        if schema and HAS_JSONSCHEMA:
            print("Using JSON Schema validation\n")
        elif not HAS_JSONSCHEMA:
            print("Note: Install 'jsonschema' for schema validation\n")

    errors, warnings = validate_configs(configs_dir, schema=schema)

    # Print warnings
    if warnings:
        print(f"\n⚠ {len(warnings)} warning(s):")
        for warning in warnings:
            print(f"  - {warning}")

    # Print errors
    if errors:
        print(f"\n✗ {len(errors)} error(s):")
        for error in errors:
            print(f"  - {error}")
        return 1

    print("\n✓ All configs valid")
    return 0


if __name__ == "__main__":
    sys.exit(main())

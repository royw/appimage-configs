"""Pytest configuration and fixtures for appimage-configs tests."""

import sys
from pathlib import Path

import pytest

# Add scripts directory to path for imports
REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = REPO_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))


@pytest.fixture
def temp_repo(tmp_path):
    """Create a temporary repository structure."""
    configs_dir = tmp_path / "configs"
    configs_dir.mkdir()
    schemas_dir = tmp_path / "schemas"
    schemas_dir.mkdir()
    
    # Copy the real schema
    real_schema = REPO_ROOT / "schemas" / "app-config.schema.json"
    if real_schema.exists():
        (schemas_dir / "app-config.schema.json").write_text(
            real_schema.read_text(encoding="utf-8"), encoding="utf-8"
        )
    
    return tmp_path


@pytest.fixture
def valid_config():
    """Return a valid app configuration."""
    return {
        "applications": [
            {
                "name": "TestApp",
                "url": "https://github.com/test/repo",
                "download_dir": "TestApp",
                "pattern": r".*\.AppImage$",
            }
        ]
    }


@pytest.fixture
def valid_config_full():
    """Return a fully-specified valid app configuration."""
    return {
        "applications": [
            {
                "name": "TestApp",
                "url": "https://github.com/test/repo",
                "download_dir": "TestApp",
                "pattern": r"TestApp.*\.AppImage$",
                "source_type": "github",
                "symlink_path": "bin/testapp",
                "prerelease": False,
                "rotation_enabled": True,
                "retain_count": 3,
                "checksum": {
                    "enabled": True,
                    "algorithm": "sha256",
                    "required": False,
                },
            }
        ]
    }


@pytest.fixture
def invalid_config_missing_pattern():
    """Return a config missing required 'pattern' field."""
    return {
        "applications": [
            {
                "name": "TestApp",
                "url": "https://github.com/test/repo",
                "download_dir": "TestApp",
            }
        ]
    }


@pytest.fixture
def invalid_config_absolute_path():
    """Return a config with absolute path (not allowed)."""
    return {
        "applications": [
            {
                "name": "TestApp",
                "url": "https://github.com/test/repo",
                "download_dir": "/absolute/path",
                "pattern": r".*\.AppImage$",
            }
        ]
    }


@pytest.fixture
def invalid_config_bad_url():
    """Return a config with invalid URL."""
    return {
        "applications": [
            {
                "name": "TestApp",
                "url": "not-a-valid-url",
                "download_dir": "TestApp",
                "pattern": r".*\.AppImage$",
            }
        ]
    }


@pytest.fixture
def invalid_config_bad_regex():
    """Return a config with invalid regex pattern."""
    return {
        "applications": [
            {
                "name": "TestApp",
                "url": "https://github.com/test/repo",
                "download_dir": "TestApp",
                "pattern": r"[invalid(regex",
            }
        ]
    }


@pytest.fixture
def invalid_config_bad_source_type():
    """Return a config with invalid source type."""
    return {
        "applications": [
            {
                "name": "TestApp",
                "url": "https://github.com/test/repo",
                "download_dir": "TestApp",
                "pattern": r".*\.AppImage$",
                "source_type": "invalid_source",
            }
        ]
    }


@pytest.fixture
def invalid_json_syntax():
    """Return invalid JSON string."""
    return '{"applications": [{"name": "broken"'

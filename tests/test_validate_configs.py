"""Tests for validate_configs.py script."""

import pytest

from validate_configs import (
    ConfigValidator,
    ValidationError,
    load_schema,
    validate_configs,
)
from helpers import write_config


class TestValidationError:
    """Tests for ValidationError dataclass."""

    def test_str_with_field(self):
        """Test string representation with field."""
        error = ValidationError("test.json", "Missing field", "applications[0].name")
        assert str(error) == "test.json: [applications[0].name] Missing field"

    def test_str_without_field(self):
        """Test string representation without field."""
        error = ValidationError("test.json", "Invalid JSON")
        assert str(error) == "test.json: Invalid JSON"


class TestLoadSchema:
    """Tests for load_schema function."""

    def test_load_existing_schema(self, temp_repo):
        """Test loading an existing schema."""
        schema = load_schema(temp_repo)
        assert schema is not None
        assert "$schema" in schema

    def test_load_missing_schema(self, tmp_path):
        """Test loading from repo without schema."""
        schema = load_schema(tmp_path)
        assert schema is None

    def test_load_invalid_schema(self, tmp_path):
        """Test loading invalid JSON schema."""
        schemas_dir = tmp_path / "schemas"
        schemas_dir.mkdir()
        (schemas_dir / "app-config.schema.json").write_text(
            "not valid json", encoding="utf-8"
        )
        schema = load_schema(tmp_path)
        assert schema is None


class TestConfigValidator:
    """Tests for ConfigValidator class."""

    def test_validate_valid_config(self, temp_repo, valid_config):
        """Test validating a valid config."""
        config_path = write_config(temp_repo / "configs" / "test.json", valid_config)
        validator = ConfigValidator()
        
        result = validator.validate_file(config_path)
        
        assert result is True
        assert len(validator.errors) == 0

    def test_validate_valid_config_full(self, temp_repo, valid_config_full):
        """Test validating a fully-specified valid config."""
        config_path = write_config(
            temp_repo / "configs" / "test.json", valid_config_full
        )
        validator = ConfigValidator()
        
        result = validator.validate_file(config_path)
        
        assert result is True
        assert len(validator.errors) == 0

    def test_validate_with_schema(self, temp_repo, valid_config):
        """Test validating with JSON Schema."""
        config_path = write_config(temp_repo / "configs" / "test.json", valid_config)
        schema = load_schema(temp_repo)
        validator = ConfigValidator(schema=schema)
        
        result = validator.validate_file(config_path)
        
        assert result is True
        assert len(validator.errors) == 0

    def test_validate_missing_pattern(self, temp_repo, invalid_config_missing_pattern):
        """Test that missing pattern is detected."""
        config_path = write_config(
            temp_repo / "configs" / "test.json", invalid_config_missing_pattern
        )
        validator = ConfigValidator()
        
        result = validator.validate_file(config_path)
        
        assert result is False
        assert len(validator.errors) > 0
        assert any("pattern" in str(e).lower() for e in validator.errors)

    def test_validate_absolute_path(self, temp_repo, invalid_config_absolute_path):
        """Test that absolute paths are rejected."""
        config_path = write_config(
            temp_repo / "configs" / "test.json", invalid_config_absolute_path
        )
        validator = ConfigValidator()
        
        result = validator.validate_file(config_path)
        
        assert result is False
        assert any("absolute" in str(e).lower() for e in validator.errors)

    def test_validate_bad_url(self, temp_repo, invalid_config_bad_url):
        """Test that invalid URLs are rejected."""
        config_path = write_config(
            temp_repo / "configs" / "test.json", invalid_config_bad_url
        )
        validator = ConfigValidator()
        
        result = validator.validate_file(config_path)
        
        assert result is False
        assert any("url" in str(e).lower() for e in validator.errors)

    def test_validate_bad_regex(self, temp_repo, invalid_config_bad_regex):
        """Test that invalid regex patterns are rejected."""
        config_path = write_config(
            temp_repo / "configs" / "test.json", invalid_config_bad_regex
        )
        validator = ConfigValidator()
        
        result = validator.validate_file(config_path)
        
        assert result is False
        assert any("regex" in str(e).lower() or "pattern" in str(e).lower() 
                   for e in validator.errors)

    def test_validate_bad_source_type(self, temp_repo, invalid_config_bad_source_type):
        """Test that invalid source types are rejected."""
        config_path = write_config(
            temp_repo / "configs" / "test.json", invalid_config_bad_source_type
        )
        validator = ConfigValidator()
        
        result = validator.validate_file(config_path)
        
        assert result is False
        assert any("source" in str(e).lower() for e in validator.errors)

    def test_validate_invalid_json(self, temp_repo, invalid_json_syntax):
        """Test that invalid JSON is rejected."""
        config_path = temp_repo / "configs" / "test.json"
        config_path.write_text(invalid_json_syntax, encoding="utf-8")
        validator = ConfigValidator()
        
        result = validator.validate_file(config_path)
        
        assert result is False
        assert any("json" in str(e).lower() for e in validator.errors)

    def test_validate_missing_applications(self, temp_repo):
        """Test that missing applications array is rejected."""
        config_path = write_config(temp_repo / "configs" / "test.json", {"name": "test"})
        validator = ConfigValidator()
        
        result = validator.validate_file(config_path)
        
        assert result is False
        assert any("applications" in str(e).lower() for e in validator.errors)

    def test_validate_empty_applications(self, temp_repo):
        """Test that empty applications array is rejected."""
        config_path = write_config(
            temp_repo / "configs" / "test.json", {"applications": []}
        )
        validator = ConfigValidator()
        
        result = validator.validate_file(config_path)
        
        assert result is False

    def test_validate_missing_file(self, temp_repo):
        """Test that missing file is handled."""
        config_path = temp_repo / "configs" / "nonexistent.json"
        validator = ConfigValidator()
        
        result = validator.validate_file(config_path)
        
        assert result is False
        assert len(validator.errors) > 0

    def test_warnings_for_filename_mismatch(self, temp_repo, valid_config):
        """Test that filename/name mismatch generates warning."""
        # Config has name "TestApp" but filename is "different.json"
        config_path = write_config(
            temp_repo / "configs" / "different.json", valid_config
        )
        validator = ConfigValidator()
        
        validator.validate_file(config_path)
        
        # Should have a warning about filename mismatch
        assert any("filename" in str(w).lower() or "mismatch" in str(w).lower() 
                   for w in validator.warnings)


class TestValidateConfigs:
    """Tests for validate_configs function."""

    def test_validate_empty_directory(self, temp_repo):
        """Test validating empty configs directory."""
        errors, warnings = validate_configs(temp_repo / "configs")
        
        # Empty directory should produce a warning
        assert len(warnings) > 0

    def test_validate_multiple_valid_configs(self, temp_repo, valid_config):
        """Test validating multiple valid configs."""
        for name in ["app1", "app2", "app3"]:
            config = valid_config.copy()
            config["applications"] = [
                {**valid_config["applications"][0], "name": name}
            ]
            write_config(temp_repo / "configs" / f"{name}.json", config)
        
        errors, warnings = validate_configs(temp_repo / "configs")
        
        assert len(errors) == 0

    def test_validate_mixed_valid_invalid(self, temp_repo, valid_config, invalid_config_bad_url):
        """Test validating mix of valid and invalid configs."""
        write_config(temp_repo / "configs" / "valid.json", valid_config)
        write_config(temp_repo / "configs" / "invalid.json", invalid_config_bad_url)
        
        errors, warnings = validate_configs(temp_repo / "configs")
        
        assert len(errors) > 0

    def test_validate_nonexistent_directory(self, tmp_path):
        """Test validating nonexistent directory."""
        errors, warnings = validate_configs(tmp_path / "nonexistent")
        
        assert len(errors) > 0

    def test_validate_with_schema(self, temp_repo, valid_config):
        """Test validating with schema."""
        write_config(temp_repo / "configs" / "test.json", valid_config)
        schema = load_schema(temp_repo)
        
        errors, warnings = validate_configs(temp_repo / "configs", schema=schema)
        
        assert len(errors) == 0


class TestValidSourceTypes:
    """Tests for valid source types."""

    @pytest.mark.parametrize("source_type", [
        "github",
        "gitlab",
        "sourceforge",
        "direct",
        "direct_download",
        "dynamic_download",
    ])
    def test_valid_source_types(self, temp_repo, valid_config, source_type):
        """Test that all valid source types are accepted."""
        config = valid_config.copy()
        config["applications"] = [
            {**valid_config["applications"][0], "source_type": source_type}
        ]
        config_path = write_config(temp_repo / "configs" / "test.json", config)
        validator = ConfigValidator()
        
        result = validator.validate_file(config_path)
        
        # Should not have source type errors
        source_errors = [e for e in validator.errors if "source" in str(e).lower()]
        assert len(source_errors) == 0


class TestChecksumValidation:
    """Tests for checksum configuration validation."""

    def test_valid_checksum_config(self, temp_repo, valid_config):
        """Test valid checksum configuration."""
        config = valid_config.copy()
        config["applications"][0]["checksum"] = {
            "enabled": True,
            "algorithm": "sha256",
            "required": False,
        }
        config_path = write_config(temp_repo / "configs" / "test.json", config)
        validator = ConfigValidator()
        
        result = validator.validate_file(config_path)
        
        assert result is True

    def test_invalid_checksum_algorithm(self, temp_repo, valid_config):
        """Test invalid checksum algorithm."""
        config = valid_config.copy()
        config["applications"][0]["checksum"] = {
            "enabled": True,
            "algorithm": "invalid_algo",
        }
        config_path = write_config(temp_repo / "configs" / "test.json", config)
        validator = ConfigValidator()
        
        result = validator.validate_file(config_path)
        
        # Should have an error about algorithm
        assert any("algorithm" in str(e).lower() for e in validator.errors)

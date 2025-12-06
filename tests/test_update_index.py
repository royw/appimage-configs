"""Tests for update_index.py script."""

import json

from update_index import (
    compute_sha256,
    extract_app_name,
    compute_repo_hash,
    build_index,
    update_index,
)
from validate_configs import ConfigValidator, load_schema
from helpers import write_config


class TestComputeSha256:
    """Tests for compute_sha256 function."""

    def test_compute_hash(self, tmp_path):
        """Test computing SHA256 hash of a file."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("hello world", encoding="utf-8")
        
        result = compute_sha256(test_file)
        
        assert result.startswith("sha256:")
        assert len(result) == 71  # "sha256:" + 64 hex chars

    def test_same_content_same_hash(self, tmp_path):
        """Test that same content produces same hash."""
        file1 = tmp_path / "file1.txt"
        file2 = tmp_path / "file2.txt"
        file1.write_text("identical content", encoding="utf-8")
        file2.write_text("identical content", encoding="utf-8")
        
        assert compute_sha256(file1) == compute_sha256(file2)

    def test_different_content_different_hash(self, tmp_path):
        """Test that different content produces different hash."""
        file1 = tmp_path / "file1.txt"
        file2 = tmp_path / "file2.txt"
        file1.write_text("content A", encoding="utf-8")
        file2.write_text("content B", encoding="utf-8")
        
        assert compute_sha256(file1) != compute_sha256(file2)


class TestExtractAppName:
    """Tests for extract_app_name function."""

    def test_extract_from_applications_array(self, tmp_path, valid_config):
        """Test extracting name from applications[0].name."""
        config_path = write_config(tmp_path / "test.json", valid_config)
        
        result = extract_app_name(config_path)
        
        assert result == "TestApp"

    def test_extract_from_top_level_name(self, tmp_path):
        """Test extracting name from top-level 'name' field."""
        config = {"name": "TopLevelName", "other": "data"}
        config_path = write_config(tmp_path / "test.json", config)
        
        result = extract_app_name(config_path)
        
        assert result == "TopLevelName"

    def test_fallback_to_filename(self, tmp_path):
        """Test falling back to filename when no name field."""
        config = {"other": "data"}
        config_path = write_config(tmp_path / "MyApp.json", config)
        
        result = extract_app_name(config_path)
        
        assert result == "MyApp"

    def test_preserves_case(self, tmp_path, valid_config):
        """Test that case is preserved in extracted name."""
        valid_config["applications"][0]["name"] = "CamelCaseApp"
        config_path = write_config(tmp_path / "test.json", valid_config)
        
        result = extract_app_name(config_path)
        
        assert result == "CamelCaseApp"

    def test_invalid_json_returns_none(self, tmp_path):
        """Test that invalid JSON returns None."""
        config_path = tmp_path / "invalid.json"
        config_path.write_text("not valid json", encoding="utf-8")
        
        result = extract_app_name(config_path)
        
        assert result is None


class TestComputeRepoHash:
    """Tests for compute_repo_hash function."""

    def test_deterministic(self):
        """Test that repo hash is deterministic."""
        hashes = ["sha256:abc", "sha256:def", "sha256:ghi"]
        
        result1 = compute_repo_hash(hashes)
        result2 = compute_repo_hash(hashes)
        
        assert result1 == result2

    def test_order_independent(self):
        """Test that repo hash is order-independent (sorted internally)."""
        hashes1 = ["sha256:abc", "sha256:def", "sha256:ghi"]
        hashes2 = ["sha256:ghi", "sha256:abc", "sha256:def"]
        
        assert compute_repo_hash(hashes1) == compute_repo_hash(hashes2)

    def test_different_hashes_different_repo_hash(self):
        """Test that different config hashes produce different repo hash."""
        hashes1 = ["sha256:abc", "sha256:def"]
        hashes2 = ["sha256:abc", "sha256:xyz"]
        
        assert compute_repo_hash(hashes1) != compute_repo_hash(hashes2)

    def test_returns_sha256_format(self):
        """Test that result is in sha256: format."""
        result = compute_repo_hash(["sha256:test"])
        
        assert result.startswith("sha256:")


class TestBuildIndex:
    """Tests for build_index function."""

    def test_build_from_valid_configs(self, temp_repo, valid_config):
        """Test building index from valid configs."""
        for name in ["App1", "App2"]:
            config = valid_config.copy()
            config["applications"] = [
                {**valid_config["applications"][0], "name": name}
            ]
            write_config(temp_repo / "configs" / f"{name.lower()}.json", config)
        
        validator = ConfigValidator()
        index = build_index(temp_repo / "configs", validator)
        
        assert index is not None
        assert "App1" in index
        assert "App2" in index
        assert "repo_hash" in index
        assert "generated_at" in index

    def test_includes_file_path_and_hash(self, temp_repo, valid_config):
        """Test that index entries include path and hash."""
        write_config(temp_repo / "configs" / "test.json", valid_config)
        
        validator = ConfigValidator()
        index = build_index(temp_repo / "configs", validator)
        
        assert "TestApp" in index
        entry = index["TestApp"]
        assert len(entry) == 2
        assert entry[0] == "configs/test.json"
        assert entry[1].startswith("sha256:")

    def test_fails_on_invalid_config(self, temp_repo, invalid_config_bad_url):
        """Test that build fails when config is invalid."""
        write_config(temp_repo / "configs" / "invalid.json", invalid_config_bad_url)
        
        validator = ConfigValidator()
        index = build_index(temp_repo / "configs", validator)
        
        assert index is None

    def test_fails_on_any_invalid(self, temp_repo, valid_config, invalid_config_bad_url):
        """Test that one invalid config fails entire build."""
        write_config(temp_repo / "configs" / "valid.json", valid_config)
        write_config(temp_repo / "configs" / "invalid.json", invalid_config_bad_url)
        
        validator = ConfigValidator()
        index = build_index(temp_repo / "configs", validator)
        
        assert index is None

    def test_empty_directory_returns_none(self, temp_repo):
        """Test that empty directory returns None."""
        validator = ConfigValidator()
        index = build_index(temp_repo / "configs", validator)
        
        assert index is None

    def test_nonexistent_directory_returns_none(self, tmp_path):
        """Test that nonexistent directory returns None."""
        validator = ConfigValidator()
        index = build_index(tmp_path / "nonexistent", validator)
        
        assert index is None

    def test_with_schema_validation(self, temp_repo, valid_config):
        """Test building index with schema validation."""
        write_config(temp_repo / "configs" / "test.json", valid_config)
        schema = load_schema(temp_repo)
        validator = ConfigValidator(schema=schema)
        
        index = build_index(temp_repo / "configs", validator)
        
        assert index is not None
        assert "TestApp" in index


class TestUpdateIndex:
    """Tests for update_index function."""

    def test_creates_index_file(self, temp_repo, valid_config):
        """Test that index.json is created."""
        write_config(temp_repo / "configs" / "test.json", valid_config)
        
        result = update_index(temp_repo)
        
        assert result is True
        assert (temp_repo / "index.json").exists()

    def test_index_contains_apps(self, temp_repo, valid_config):
        """Test that created index contains apps."""
        write_config(temp_repo / "configs" / "test.json", valid_config)
        
        update_index(temp_repo)
        
        index = json.loads((temp_repo / "index.json").read_text(encoding="utf-8"))
        assert "TestApp" in index
        assert "repo_hash" in index
        assert "generated_at" in index

    def test_atomic_update(self, temp_repo, valid_config):
        """Test that index is updated atomically."""
        write_config(temp_repo / "configs" / "test.json", valid_config)
        
        # Create initial index
        update_index(temp_repo)
        initial_content = (temp_repo / "index.json").read_text(encoding="utf-8")
        
        # Update a config
        valid_config["applications"][0]["name"] = "UpdatedApp"
        write_config(temp_repo / "configs" / "test.json", valid_config)
        
        # Update index
        update_index(temp_repo)
        updated_content = (temp_repo / "index.json").read_text(encoding="utf-8")
        
        assert initial_content != updated_content
        assert "UpdatedApp" in updated_content

    def test_fails_on_invalid_config(self, temp_repo, invalid_config_bad_url):
        """Test that update fails when config is invalid."""
        write_config(temp_repo / "configs" / "invalid.json", invalid_config_bad_url)
        
        result = update_index(temp_repo)
        
        assert result is False

    def test_no_new_index_on_failure(self, temp_repo, invalid_config_bad_url):
        """Test that new_index.json is not left behind on failure."""
        write_config(temp_repo / "configs" / "invalid.json", invalid_config_bad_url)
        
        update_index(temp_repo)
        
        # new_index.json should not exist after failure
        assert not (temp_repo / "new_index.json").exists()

    def test_empty_configs_fails(self, temp_repo):
        """Test that empty configs directory fails."""
        result = update_index(temp_repo)
        
        assert result is False


class TestRepoHashConsistency:
    """Tests for repo hash consistency."""

    def test_unchanged_configs_same_hash(self, temp_repo, valid_config):
        """Test that unchanged configs produce same repo hash."""
        write_config(temp_repo / "configs" / "test.json", valid_config)
        
        update_index(temp_repo)
        index1 = json.loads((temp_repo / "index.json").read_text(encoding="utf-8"))
        hash1 = index1["repo_hash"]
        
        # Run again without changes
        update_index(temp_repo)
        index2 = json.loads((temp_repo / "index.json").read_text(encoding="utf-8"))
        hash2 = index2["repo_hash"]
        
        assert hash1 == hash2

    def test_changed_config_different_hash(self, temp_repo, valid_config):
        """Test that changed config produces different repo hash."""
        write_config(temp_repo / "configs" / "test.json", valid_config)
        
        update_index(temp_repo)
        index1 = json.loads((temp_repo / "index.json").read_text(encoding="utf-8"))
        hash1 = index1["repo_hash"]
        
        # Modify config
        valid_config["applications"][0]["pattern"] = ".*modified.*"
        write_config(temp_repo / "configs" / "test.json", valid_config)
        
        update_index(temp_repo)
        index2 = json.loads((temp_repo / "index.json").read_text(encoding="utf-8"))
        hash2 = index2["repo_hash"]
        
        assert hash1 != hash2

    def test_added_config_different_hash(self, temp_repo, valid_config):
        """Test that adding a config produces different repo hash."""
        write_config(temp_repo / "configs" / "app1.json", valid_config)
        
        update_index(temp_repo)
        index1 = json.loads((temp_repo / "index.json").read_text(encoding="utf-8"))
        hash1 = index1["repo_hash"]
        
        # Add another config
        valid_config["applications"][0]["name"] = "App2"
        write_config(temp_repo / "configs" / "app2.json", valid_config)
        
        update_index(temp_repo)
        index2 = json.loads((temp_repo / "index.json").read_text(encoding="utf-8"))
        hash2 = index2["repo_hash"]
        
        assert hash1 != hash2

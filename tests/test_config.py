"""Tests for configuration loading and validation."""

from pathlib import Path

import pytest
import yaml

from claude_memory.config import Config, load_config, AVAILABLE_MODULES, MODULE_DEPENDENCIES


class TestConfigParsing:
    """Tests for config file parsing."""

    def test_valid_config_parses(self, sample_config):
        """A well-formed Config should validate without errors."""
        errors = sample_config.validate()
        assert not errors, f"Unexpected validation errors: {errors}"

    def test_valid_config_from_yaml(self, fixtures_dir):
        """The sample_config.yaml fixture should parse as valid YAML."""
        config_path = fixtures_dir / "sample_config.yaml"
        assert config_path.exists(), "Fixture sample_config.yaml missing"

        with open(config_path) as f:
            config = yaml.safe_load(f)

        assert isinstance(config, dict)
        assert "user_name" in config

    def test_default_config(self):
        """Default Config() should have sensible defaults."""
        cfg = Config()
        assert isinstance(cfg.modules, list)
        assert "memory" in cfg.modules
        assert isinstance(cfg.module_config, dict)

    def test_load_config_missing_file(self, tmp_path):
        """Loading from a non-existent path should return defaults."""
        cfg = load_config(tmp_path / "nonexistent.yaml")
        assert isinstance(cfg, Config)
        assert cfg.modules == ["memory"]

    def test_load_config_from_yaml(self, tmp_path):
        """Loading from a valid YAML file should populate the Config."""
        config_path = tmp_path / "config.yaml"
        config_path.write_text(yaml.dump({
            "user_name": "Alice",
            "user_role": "engineer",
            "modules": ["memory", "tasks"],
        }))

        cfg = load_config(config_path)
        assert cfg.user_name == "Alice"
        assert cfg.user_role == "engineer"
        assert "tasks" in cfg.modules


class TestConfigValidation:
    """Tests for config validation logic."""

    def test_module_dependencies_enforced(self):
        """Enabling a module without its dependency should produce a validation error."""
        # tasks requires memory
        config = Config(
            user_name="Test",
            modules=["tasks"],  # missing "memory"
        )
        errors = config.validate()
        assert any("memory" in e for e in errors)

    def test_missing_user_name_errors(self):
        """Config without user_name should produce a validation error."""
        config = Config(user_name="", modules=["memory"])
        errors = config.validate()
        assert any("user_name" in e for e in errors)

    def test_unknown_module_errors(self):
        """An unrecognized module name should produce a validation error."""
        config = Config(
            user_name="Test",
            modules=["nonexistent_module_xyz"],
        )
        errors = config.validate()
        assert any("nonexistent_module_xyz" in e for e in errors)

    def test_valid_config_no_errors(self):
        """A properly configured Config should have no validation errors."""
        config = Config(
            user_name="Test User",
            user_role="developer",
            modules=["memory"],
        )
        errors = config.validate()
        assert errors == []

    def test_all_modules_are_known(self):
        """AVAILABLE_MODULES should be a non-empty list of strings."""
        assert len(AVAILABLE_MODULES) > 0
        for mod in AVAILABLE_MODULES:
            assert isinstance(mod, str)

    def test_dependency_targets_exist(self):
        """Every dependency target in MODULE_DEPENDENCIES should be in AVAILABLE_MODULES."""
        for mod, deps in MODULE_DEPENDENCIES.items():
            assert mod in AVAILABLE_MODULES, f"Module {mod} in dependencies but not in AVAILABLE_MODULES"
            for dep in deps:
                assert dep in AVAILABLE_MODULES, f"Dependency {dep} not in AVAILABLE_MODULES"

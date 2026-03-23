"""Tests for configuration loading."""

import os
import tempfile
from pathlib import Path

import pytest
import yaml

from config import (
    AppConfig,
    BedrockConfig,
    DatabaseConfig,
    Settings,
    _apply_env_overrides,
    _load_yaml_config,
    load_settings,
)


# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------

class TestDefaults:
    def test_bedrock_defaults(self):
        cfg = BedrockConfig()
        assert cfg.region == "us-east-1"
        assert cfg.model_id == "us.anthropic.claude-haiku-4-5-20251001-v1:0"
        assert cfg.max_tokens == 16384
        assert cfg.temperature == 0.2
        assert cfg.timeout_seconds == 120
        assert cfg.retry_attempts == 2
        assert cfg.retry_backoff_base == 1.0

    def test_database_defaults(self):
        cfg = DatabaseConfig()
        assert cfg.path == "data/sizing_tool.db"
        assert cfg.echo_sql is False

    def test_app_defaults(self):
        cfg = AppConfig()
        assert cfg.host == "0.0.0.0"
        assert cfg.port == 8000
        assert cfg.cors_origins == ["http://localhost:5173"]
        assert cfg.max_upload_size_mb == 20
        assert cfg.supported_image_formats == ["png", "jpg", "jpeg", "webp"]
        assert cfg.default_pricing_region == "us-east-1"

    def test_settings_defaults(self):
        s = Settings()
        assert s.bedrock.region == "us-east-1"
        assert s.database.path == "data/sizing_tool.db"
        assert s.app.default_pricing_region == "us-east-1"


# ---------------------------------------------------------------------------
# YAML loading
# ---------------------------------------------------------------------------

class TestYamlLoading:
    def test_load_existing_yaml(self, tmp_path):
        cfg_file = tmp_path / "config.yaml"
        cfg_file.write_text(yaml.dump({
            "bedrock": {"region": "eu-west-1", "max_tokens": 8192},
            "app": {"port": 9000},
        }))
        data = _load_yaml_config(cfg_file)
        assert data["bedrock"]["region"] == "eu-west-1"
        assert data["app"]["port"] == 9000

    def test_load_missing_yaml_returns_empty(self, tmp_path):
        data = _load_yaml_config(tmp_path / "nonexistent.yaml")
        assert data == {}

    def test_load_empty_yaml_returns_empty(self, tmp_path):
        cfg_file = tmp_path / "config.yaml"
        cfg_file.write_text("")
        data = _load_yaml_config(cfg_file)
        assert data == {}

    def test_load_settings_from_yaml(self, tmp_path):
        cfg_file = tmp_path / "config.yaml"
        cfg_file.write_text(yaml.dump({
            "bedrock": {"region": "ap-southeast-1"},
            "database": {"path": "/tmp/test.db", "echo_sql": True},
            "app": {"port": 3000, "default_pricing_region": "ap-southeast-1"},
        }))
        s = load_settings(cfg_file)
        assert s.bedrock.region == "ap-southeast-1"
        assert s.database.path == "/tmp/test.db"
        assert s.database.echo_sql is True
        assert s.app.port == 3000
        assert s.app.default_pricing_region == "ap-southeast-1"

    def test_load_settings_missing_yaml_uses_defaults(self, tmp_path):
        s = load_settings(tmp_path / "nope.yaml")
        assert s.bedrock.region == "us-east-1"
        assert s.app.default_pricing_region == "us-east-1"


# ---------------------------------------------------------------------------
# Environment variable overrides
# ---------------------------------------------------------------------------

class TestEnvOverrides:
    def test_aws_default_region(self, monkeypatch):
        monkeypatch.setenv("AWS_DEFAULT_REGION", "eu-central-1")
        data = _apply_env_overrides({})
        assert data["bedrock"]["region"] == "eu-central-1"

    def test_bedrock_model_id(self, monkeypatch):
        monkeypatch.setenv("BEDROCK_MODEL_ID", "my-model")
        data = _apply_env_overrides({})
        assert data["bedrock"]["model_id"] == "my-model"

    def test_bedrock_max_tokens(self, monkeypatch):
        monkeypatch.setenv("BEDROCK_MAX_TOKENS", "4096")
        data = _apply_env_overrides({})
        assert data["bedrock"]["max_tokens"] == "4096"

    def test_app_port(self, monkeypatch):
        monkeypatch.setenv("APP_PORT", "5000")
        data = _apply_env_overrides({})
        assert data["app"]["port"] == "5000"

    def test_cors_origins_comma_separated(self, monkeypatch):
        monkeypatch.setenv("APP_CORS_ORIGINS", "http://a.com, http://b.com")
        data = _apply_env_overrides({})
        assert data["app"]["cors_origins"] == ["http://a.com", "http://b.com"]

    def test_database_path(self, monkeypatch):
        monkeypatch.setenv("DATABASE_PATH", "/data/prod.db")
        data = _apply_env_overrides({})
        assert data["database"]["path"] == "/data/prod.db"

    def test_env_overrides_yaml_values(self, tmp_path, monkeypatch):
        """Env vars should override YAML values."""
        cfg_file = tmp_path / "config.yaml"
        cfg_file.write_text(yaml.dump({
            "bedrock": {"region": "us-west-2"},
            "app": {"port": 8000},
        }))
        monkeypatch.setenv("AWS_DEFAULT_REGION", "eu-west-1")
        monkeypatch.setenv("APP_PORT", "9999")

        s = load_settings(cfg_file)
        assert s.bedrock.region == "eu-west-1"
        assert s.app.port == 9999

    def test_unset_env_vars_dont_override(self, tmp_path):
        """When env vars are not set, YAML values are used."""
        cfg_file = tmp_path / "config.yaml"
        cfg_file.write_text(yaml.dump({
            "bedrock": {"region": "us-west-2"},
        }))
        s = load_settings(cfg_file)
        assert s.bedrock.region == "us-west-2"


# ---------------------------------------------------------------------------
# default_pricing_region requirement 4.6
# ---------------------------------------------------------------------------

class TestDefaultPricingRegion:
    def test_default_is_us_east_1(self):
        cfg = AppConfig()
        assert cfg.default_pricing_region == "us-east-1"

    def test_overridable_via_yaml(self, tmp_path):
        cfg_file = tmp_path / "config.yaml"
        cfg_file.write_text(yaml.dump({
            "app": {"default_pricing_region": "eu-west-1"},
        }))
        s = load_settings(cfg_file)
        assert s.app.default_pricing_region == "eu-west-1"

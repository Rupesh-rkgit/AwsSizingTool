"""Configuration loading for AWS Infrastructure Sizing Tool.

Layered config: defaults → config.yaml → environment variables (highest priority).
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from pydantic import Field
from pydantic_settings import BaseSettings


def _load_yaml_config(path: str | Path | None = None) -> dict[str, Any]:
    """Load configuration from a YAML file. Returns empty dict if file not found."""
    if path is None:
        # Default: config.yaml next to this file
        path = Path(__file__).parent / "config.yaml"
    path = Path(path)
    if not path.exists():
        return {}
    with open(path, "r") as f:
        data = yaml.safe_load(f)
    return data if isinstance(data, dict) else {}


class BedrockConfig(BaseSettings):
    """Amazon Bedrock API configuration."""

    model_config = {"env_prefix": "BEDROCK_INTERNAL_"}  # prevent auto env pickup

    region: str = "us-east-1"
    model_id: str = "us.anthropic.claude-sonnet-4-5-20250929-v1:0"
    max_tokens: int = 64000
    temperature: float = 0.2
    timeout_seconds: int = 180
    retry_attempts: int = 2
    retry_backoff_base: float = 1.0


class DatabaseConfig(BaseSettings):
    """SQLite database configuration."""

    model_config = {"env_prefix": "DB_INTERNAL_"}  # prevent auto env pickup

    path: str = "data/sizing_tool.db"
    echo_sql: bool = False


class AppConfig(BaseSettings):
    """Application server configuration."""

    model_config = {"env_prefix": "APPCONFIG_INTERNAL_"}  # prevent auto env pickup

    host: str = "0.0.0.0"
    port: int = 8000
    cors_origins: list[str] = Field(default=["http://localhost:5173"])
    max_upload_size_mb: int = 20
    supported_image_formats: list[str] = Field(
        default=["png", "jpg", "jpeg", "webp"]
    )
    default_pricing_region: str = "us-east-1"
    enable_enrichment: bool = True
    enrichment_timeout_seconds: int = 15
    enrichment_max_pricing_results: int = 10


class Settings(BaseSettings):
    """Root settings composing all config sections."""

    model_config = {"env_prefix": "SETTINGS_INTERNAL_"}  # prevent auto env pickup

    bedrock: BedrockConfig = Field(default_factory=BedrockConfig)
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    app: AppConfig = Field(default_factory=AppConfig)


# ---------------------------------------------------------------------------
# Environment variable → nested config mapping
# ---------------------------------------------------------------------------
_ENV_OVERRIDES: list[tuple[str, list[str]]] = [
    ("AWS_DEFAULT_REGION", ["bedrock", "region"]),
    ("BEDROCK_MODEL_ID", ["bedrock", "model_id"]),
    ("BEDROCK_MAX_TOKENS", ["bedrock", "max_tokens"]),
    ("APP_PORT", ["app", "port"]),
    ("APP_CORS_ORIGINS", ["app", "cors_origins"]),
    ("DATABASE_PATH", ["database", "path"]),
    ("LOG_LEVEL", ["logging", "level"]),
]


def _apply_env_overrides(data: dict[str, Any]) -> dict[str, Any]:
    """Apply environment variable overrides on top of the YAML dict.

    Env vars take highest priority. Only set keys whose env var is present.
    """
    for env_var, key_path in _ENV_OVERRIDES:
        value = os.environ.get(env_var)
        if value is None:
            continue

        # Navigate / create nested dicts
        target = data
        for key in key_path[:-1]:
            target = target.setdefault(key, {})

        final_key = key_path[-1]

        # Special handling for comma-separated list values
        if final_key == "cors_origins":
            target[final_key] = [v.strip() for v in value.split(",")]
        else:
            target[final_key] = value

    return data


def load_settings(yaml_path: str | Path | None = None) -> Settings:
    """Load settings from YAML file with environment variable overrides.

    Priority (highest → lowest):
      1. Environment variables
      2. config.yaml values
      3. Pydantic field defaults
    """
    raw = _load_yaml_config(yaml_path)
    raw = _apply_env_overrides(raw)

    # Build each sub-config from the merged dict, then compose into Settings
    bedrock_data = raw.get("bedrock", {})
    database_data = raw.get("database", {})
    app_data = raw.get("app", {})

    return Settings(
        bedrock=BedrockConfig(**bedrock_data),
        database=DatabaseConfig(**database_data),
        app=AppConfig(**app_data),
    )

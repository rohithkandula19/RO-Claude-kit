"""Config file management for csk.

Config lives at ``./.csk/config.toml`` (project-local, takes priority) or
``~/.config/csk/config.toml`` (user-global). Demo mode skips all real creds.
"""
from __future__ import annotations

import os
import tomllib
from pathlib import Path
from typing import Any

import tomli_w
from pydantic import BaseModel, Field


CONFIG_FILENAME = "config.toml"
PROJECT_DIR = Path(".csk")
USER_DIR = Path.home() / ".config" / "csk"


class CSKConfig(BaseModel):
    """csk configuration. Each service is optional — only configured ones get tools registered."""

    demo_mode: bool = False
    anthropic_api_key: str | None = None
    model: str = "claude-sonnet-4-6"

    stripe_api_key: str | None = None
    linear_api_key: str | None = None
    slack_bot_token: str | None = None
    slack_user_token: str | None = None
    notion_token: str | None = None
    database_url: str | None = None

    extra: dict[str, Any] = Field(default_factory=dict)

    def configured_services(self) -> list[str]:
        """Names of services that have credentials set (or are available in demo mode)."""
        if self.demo_mode:
            return ["stripe", "linear", "slack", "notion", "postgres"]
        services: list[str] = []
        if self.stripe_api_key:
            services.append("stripe")
        if self.linear_api_key:
            services.append("linear")
        if self.slack_bot_token:
            services.append("slack")
        if self.notion_token:
            services.append("notion")
        if self.database_url:
            services.append("postgres")
        return services

    def has_anthropic_auth(self) -> bool:
        return self.demo_mode or bool(self.anthropic_api_key or os.environ.get("ANTHROPIC_API_KEY"))


def find_config_path() -> Path | None:
    """Return the first existing config path: project, then user. None if neither exists."""
    project = PROJECT_DIR / CONFIG_FILENAME
    if project.exists():
        return project
    user = USER_DIR / CONFIG_FILENAME
    if user.exists():
        return user
    return None


def load_config() -> CSKConfig:
    """Load config from disk. Returns an empty config if no file exists.

    Env vars override file values for keys that aren't None in env:
    ``ANTHROPIC_API_KEY``, ``STRIPE_API_KEY``, ``LINEAR_API_KEY``,
    ``SLACK_BOT_TOKEN``, ``NOTION_TOKEN``, ``DATABASE_URL``.
    """
    path = find_config_path()
    raw: dict[str, Any] = {}
    if path is not None:
        with path.open("rb") as fh:
            raw = tomllib.load(fh)

    # env override
    env_overrides = {
        "anthropic_api_key": os.environ.get("ANTHROPIC_API_KEY"),
        "stripe_api_key": os.environ.get("STRIPE_API_KEY"),
        "linear_api_key": os.environ.get("LINEAR_API_KEY"),
        "slack_bot_token": os.environ.get("SLACK_BOT_TOKEN"),
        "slack_user_token": os.environ.get("SLACK_USER_TOKEN"),
        "notion_token": os.environ.get("NOTION_TOKEN"),
        "database_url": os.environ.get("DATABASE_URL"),
    }
    for key, value in env_overrides.items():
        if value:
            raw[key] = value

    return CSKConfig(**raw)


def save_config(config: CSKConfig, *, scope: str = "project") -> Path:
    """Write config to disk. ``scope`` is ``"project"`` or ``"user"``."""
    target_dir = PROJECT_DIR if scope == "project" else USER_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    path = target_dir / CONFIG_FILENAME

    payload = config.model_dump(exclude_none=False)
    payload = {k: v for k, v in payload.items() if v not in (None, {}, "")}
    with path.open("wb") as fh:
        tomli_w.dump(payload, fh)
    return path

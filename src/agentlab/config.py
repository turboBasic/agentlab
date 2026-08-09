from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="AGENTLAB_", extra="ignore")

    provider: Literal["openrouter", "anthropic"] = "openrouter"
    model: str = "deepseek/deepseek-v4-flash-0731"
    max_tokens: int = 4096
    temperature: float = 0.2

    openrouter_api_key: SecretStr | None = Field(default=None, alias="OPENROUTER_API_KEY")
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    anthropic_api_key: SecretStr | None = Field(default=None, alias="ANTHROPIC_API_KEY")

    workdir: Path = Field(default_factory=Path.cwd)
    db_path: Path = Path(".agentlab/agentlab.db")

    auto_approve: bool = False

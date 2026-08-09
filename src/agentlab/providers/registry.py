from __future__ import annotations

from agentlab.config import Settings
from agentlab.providers.anthropic_direct import AnthropicProvider
from agentlab.providers.base import Provider
from agentlab.providers.openrouter import OpenRouterProvider


def build_provider(settings: Settings) -> Provider:
    if settings.provider == "openrouter":
        if settings.openrouter_api_key is None:
            raise RuntimeError("OPENROUTER_API_KEY is not set")
        return OpenRouterProvider(
            api_key=settings.openrouter_api_key.get_secret_value(),
            base_url=settings.openrouter_base_url,
        )
    if settings.provider == "anthropic":
        if settings.anthropic_api_key is None:
            raise RuntimeError("ANTHROPIC_API_KEY is not set")
        return AnthropicProvider(api_key=settings.anthropic_api_key.get_secret_value())
    raise ValueError(f"unknown provider: {settings.provider!r}")

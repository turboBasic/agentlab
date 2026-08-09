from __future__ import annotations

import os

import pytest

from agentlab.config import Settings
from agentlab.providers.registry import build_provider
from agentlab.types import TextDelta, UserMessage

pytestmark = pytest.mark.live


async def test_openrouter_smoke() -> None:
    if not os.environ.get("OPENROUTER_API_KEY"):
        pytest.skip("OPENROUTER_API_KEY not set")

    settings = Settings()
    provider = build_provider(settings)

    text = ""
    async for event in provider.stream(
        messages=[UserMessage(content="Say 'ok' and nothing else.")],
        tools=[],
        model=settings.model,
        max_tokens=16,
        temperature=0.0,
    ):
        if isinstance(event, TextDelta):
            text += event.text

    assert text

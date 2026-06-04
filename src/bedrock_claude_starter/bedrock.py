"""Bedrock client wrapper with retries, thinking mode, and tool support.

Uses the Bedrock Converse API which is model-agnostic.
"""

from __future__ import annotations

from typing import Any

import boto3
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from .models import ToolDefinition

DEFAULT_MAX_TOKENS = 4096
DEFAULT_TEMPERATURE = 0.7


class BedrockClient:
    """Thin wrapper over boto3 bedrock-runtime with retry semantics."""

    def __init__(
        self,
        model_id: str,
        *,
        region: str = "us-east-1",
        profile: str | None = None,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        temperature: float = DEFAULT_TEMPERATURE,
    ) -> None:
        self.model_id = model_id
        self.max_tokens = max_tokens
        self.temperature = temperature
        session = boto3.Session(profile_name=profile, region_name=region)
        self._client = session.client("bedrock-runtime")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=15),
        retry=retry_if_exception_type(Exception),
        reraise=True,
    )
    def converse(
        self,
        messages: list[dict[str, Any]],
        *,
        system_prompt: str = "",
        tools: list[ToolDefinition] | None = None,
        thinking: bool = False,
    ) -> dict[str, Any]:
        """Send a Converse API request and return the parsed response.

        `messages` follow the Bedrock Converse format directly:
            [{"role": "user", "content": [{"text": "Hello"}]}, ...]
        """
        kwargs: dict[str, Any] = {
            "modelId": self.model_id,
            "messages": messages,
            "inferenceConfig": {
                "maxTokens": self.max_tokens,
                "temperature": self.temperature,
            },
        }

        if system_prompt:
            kwargs["system"] = [{"text": system_prompt}]

        if tools:
            kwargs["toolConfig"] = {
                "tools": [
                    {
                        "toolSpec": {
                            "name": t.name,
                            "description": t.description,
                            "inputSchema": {"json": t.input_schema},
                        }
                    }
                    for t in tools
                ],
            }

        if thinking:
            kwargs["additionalModelRequestFields"] = {
                "reasoning_config": {"type": "enabled", "budget_tokens": 2000},
            }

        response: dict[str, Any] = self._client.converse(**kwargs)
        return response

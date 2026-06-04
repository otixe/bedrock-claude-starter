"""Tests for the Agent loop with mocked Bedrock client."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from bedrock_claude_starter import tool
from bedrock_claude_starter.agent import Agent
from bedrock_claude_starter.bedrock import BedrockClient


def _bedrock_response_text(text: str) -> dict[str, Any]:
    return {
        "stopReason": "end_turn",
        "output": {
            "message": {
                "role": "assistant",
                "content": [{"text": text}],
            }
        },
    }


def _bedrock_response_tool_use(
    tool_name: str, tool_input: dict[str, Any], tool_use_id: str = "tu_1"
) -> dict[str, Any]:
    return {
        "stopReason": "tool_use",
        "output": {
            "message": {
                "role": "assistant",
                "content": [
                    {
                        "toolUse": {
                            "toolUseId": tool_use_id,
                            "name": tool_name,
                            "input": tool_input,
                        }
                    }
                ],
            }
        },
    }


@pytest.fixture
def mock_client() -> MagicMock:
    return MagicMock(spec=BedrockClient)


def test_agent_returns_text_response(mock_client: MagicMock) -> None:
    mock_client.converse.return_value = _bedrock_response_text("Hello there.")

    agent = Agent(bedrock_client=mock_client)
    response = agent.run("Hi")

    assert response.text == "Hello there."
    assert response.iterations == 1
    assert response.tool_calls == []
    assert mock_client.converse.call_count == 1


def test_agent_executes_tool_then_returns(mock_client: MagicMock) -> None:
    @tool(description="Square a number.")
    def square(n: int) -> int:
        return n * n

    mock_client.converse.side_effect = [
        _bedrock_response_tool_use("square", {"n": 4}),
        _bedrock_response_text("The square of 4 is 16."),
    ]

    agent = Agent(tools=[square], bedrock_client=mock_client)
    response = agent.run("What is 4 squared?")

    assert response.text == "The square of 4 is 16."
    assert response.iterations == 2
    assert len(response.tool_calls) == 1
    assert response.tool_calls[0].name == "square"
    assert response.tool_calls[0].input == {"n": 4}


def test_agent_respects_max_iterations(mock_client: MagicMock) -> None:
    @tool(description="Always loops.")
    def loop(x: int) -> int:
        return x

    # Always returns tool_use → forces hitting iteration limit
    mock_client.converse.return_value = _bedrock_response_tool_use("loop", {"x": 1})

    agent = Agent(tools=[loop], bedrock_client=mock_client, max_iterations=3)
    response = agent.run("loop forever")

    assert response.iterations == 3
    assert response.stop_reason == "max_iterations"
    assert mock_client.converse.call_count == 3


def test_agent_handles_unknown_tool_gracefully(mock_client: MagicMock) -> None:
    mock_client.converse.side_effect = [
        _bedrock_response_tool_use("nonexistent", {}),
        _bedrock_response_text("Sorry, that tool doesn't exist."),
    ]

    agent = Agent(bedrock_client=mock_client)
    response = agent.run("trigger unknown tool")

    assert "Sorry" in response.text
    assert response.iterations == 2


def test_agent_handles_tool_exception(mock_client: MagicMock) -> None:
    @tool(description="Always errors.")
    def broken(x: int) -> int:
        raise ValueError("nope")

    mock_client.converse.side_effect = [
        _bedrock_response_tool_use("broken", {"x": 1}),
        _bedrock_response_text("Tool returned an error."),
    ]

    agent = Agent(tools=[broken], bedrock_client=mock_client)
    response = agent.run("call broken")

    assert response.iterations == 2
    # Tool result message gets appended after the tool_use response.
    # Find the user message that contains a toolResult (it's the second-to-last
    # in the messages list since the final assistant text response is appended last)
    second_call_messages = mock_client.converse.call_args_list[1].kwargs["messages"]
    tool_result_message = next(
        m
        for m in second_call_messages
        if m["role"] == "user" and any("toolResult" in c for c in m["content"])
    )
    tool_result = tool_result_message["content"][0]["toolResult"]
    assert tool_result["status"] == "error"

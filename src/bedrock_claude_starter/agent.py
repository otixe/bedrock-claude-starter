"""Agent: bedrock client + tool-use loop + optional memory.

The main entrypoint. Holds conversation state, runs the iterative
tool-use loop until Claude finishes the task or limits are hit.
"""

from __future__ import annotations

from typing import Any

from .bedrock import BedrockClient
from .memory import Memory
from .models import AgentResponse, ToolUseBlock
from .tools import Tool

DEFAULT_MAX_ITERATIONS = 10
DEFAULT_MODEL = "us.anthropic.claude-sonnet-4-5-20250929-v1:0"


class Agent:
    """Single-conversation Claude agent with tools and optional memory."""

    def __init__(
        self,
        system_prompt: str = "You are a helpful AI assistant.",
        *,
        tools: list[Tool] | None = None,
        memory: Memory | None = None,
        memory_top_k: int = 5,
        model: str = DEFAULT_MODEL,
        max_iterations: int = DEFAULT_MAX_ITERATIONS,
        thinking: bool = False,
        bedrock_client: BedrockClient | None = None,
        aws_region: str = "us-east-1",
        aws_profile: str | None = None,
    ) -> None:
        self.system_prompt = system_prompt
        self.tools = tools or []
        self._tools_by_name = {t.name: t for t in self.tools}
        self.memory = memory
        self.memory_top_k = memory_top_k
        self.max_iterations = max_iterations
        self.thinking = thinking
        self.client = bedrock_client or BedrockClient(
            model_id=model, region=aws_region, profile=aws_profile
        )

    def run(self, user_message: str) -> AgentResponse:
        """Run a single user→agent turn (with internal tool-use iterations)."""
        system_prompt = self._compose_system_prompt(user_message)
        messages: list[dict[str, Any]] = [{"role": "user", "content": [{"text": user_message}]}]
        tool_calls: list[ToolUseBlock] = []
        stop_reason = ""

        for iteration in range(1, self.max_iterations + 1):
            response = self.client.converse(
                messages=messages,
                system_prompt=system_prompt,
                tools=[t.definition for t in self.tools] if self.tools else None,
                thinking=self.thinking,
            )

            stop_reason = response.get("stopReason", "")
            output_message = response["output"]["message"]
            messages.append(output_message)

            tool_uses = [block for block in output_message.get("content", []) if "toolUse" in block]

            if not tool_uses or stop_reason != "tool_use":
                # Final assistant message
                text = self._extract_text(output_message)
                if self.memory and text:
                    self.memory.remember(f"User asked: {user_message}\nAssistant answered: {text}")
                return AgentResponse(
                    text=text,
                    iterations=iteration,
                    tool_calls=tool_calls,
                    stop_reason=stop_reason,
                )

            # Execute each tool and append results
            tool_results: list[dict[str, Any]] = []
            for block in tool_uses:
                tu = block["toolUse"]
                tool_calls.append(
                    ToolUseBlock(
                        tool_use_id=tu["toolUseId"],
                        name=tu["name"],
                        input=tu.get("input", {}),
                    )
                )
                result_content, is_error = self._invoke_tool(tu["name"], tu.get("input", {}))
                tool_results.append(
                    {
                        "toolResult": {
                            "toolUseId": tu["toolUseId"],
                            "content": [{"text": result_content}],
                            "status": "error" if is_error else "success",
                        }
                    }
                )

            messages.append({"role": "user", "content": tool_results})

        # Reached iteration limit
        return AgentResponse(
            text="[max iterations reached without final response]",
            iterations=self.max_iterations,
            tool_calls=tool_calls,
            stop_reason="max_iterations",
        )

    def _compose_system_prompt(self, user_message: str) -> str:
        prompt = self.system_prompt
        if self.memory:
            recalled = self.memory.recall(user_message, limit=self.memory_top_k)
            if recalled:
                memory_block = "\n".join(f"- {entry.text}" for entry in recalled)
                prompt = f"{prompt}\n\n## Relevant memory\n{memory_block}"
        return prompt

    def _invoke_tool(self, name: str, input_data: dict[str, Any]) -> tuple[str, bool]:
        """Invoke a registered tool by name. Returns (result_text, is_error)."""
        tool = self._tools_by_name.get(name)
        if tool is None:
            return f"Tool '{name}' not registered.", True
        try:
            return tool.invoke(input_data), False
        except (TypeError, ValueError) as e:
            return f"Tool '{name}' failed: {e}", True
        except Exception as e:
            return f"Tool '{name}' unexpected error: {type(e).__name__}: {e}", True

    @staticmethod
    def _extract_text(message: dict[str, Any]) -> str:
        parts: list[str] = []
        for block in message.get("content", []):
            if "text" in block:
                parts.append(block["text"])
        return "\n".join(parts).strip()

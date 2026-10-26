"""Offline demo of the tool-use loop: no AWS account, no network.

A scripted stand-in for BedrockClient returns a `toolUse` turn and then a final
answer, so you can watch the Agent call your Python function and feed the result
back. Run: python examples/offline_tool_loop.py
"""

from typing import Any

from bedrock_claude_starter import Agent, tool


@tool(description="Look up an order by its ID.")
def get_order(order_id: str) -> dict:
    return {"order_id": order_id, "status": "shipped", "eta_days": 2}


class ScriptedBedrock:
    """Mimics BedrockClient.converse() for the Converse API response shape."""

    def __init__(self) -> None:
        self.calls = 0

    def converse(self, messages: list[dict[str, Any]], **_: Any) -> dict[str, Any]:
        self.calls += 1
        if self.calls == 1:
            return {
                "stopReason": "tool_use",
                "output": {
                    "message": {
                        "role": "assistant",
                        "content": [
                            {
                                "toolUse": {
                                    "toolUseId": "t1",
                                    "name": "get_order",
                                    "input": {"order_id": "A-1001"},
                                }
                            }
                        ],
                    }
                },
            }
        result = messages[-1]["content"][0]["toolResult"]["content"][0]["text"]
        return {
            "stopReason": "end_turn",
            "output": {
                "message": {
                    "role": "assistant",
                    "content": [{"text": f"Order A-1001 is on its way. Tool said: {result}"}],
                }
            },
        }


agent = Agent(
    system_prompt="You are a support assistant. Use tools when needed.",
    tools=[get_order],
    bedrock_client=ScriptedBedrock(),  # type: ignore[arg-type]
)
response = agent.run("Where is my order A-1001?")

print("tool schema :", get_order.definition.input_schema)
print("tool calls  :", [(c.name, c.input) for c in response.tool_calls])
print("iterations  :", response.iterations, "| stop_reason:", response.stop_reason)
print("answer      :", response.text)

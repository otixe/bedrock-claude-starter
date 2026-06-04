"""Tool registration and schema generation.

Use the `@tool` decorator to expose any Python function to the agent.
Type hints are converted to JSON Schema automatically.
"""

from __future__ import annotations

import inspect
from collections.abc import Callable
from typing import Any

from pydantic import BaseModel

from .models import ToolDefinition

_PRIMITIVE_TYPE_MAP: dict[type, str] = {
    str: "string",
    int: "integer",
    float: "number",
    bool: "boolean",
}


class Tool:
    """Wraps a Python function with its Claude-facing schema."""

    def __init__(
        self,
        fn: Callable[..., Any],
        description: str,
        name: str | None = None,
    ) -> None:
        self.fn = fn
        self.name = name or fn.__name__
        self.description = description
        self.definition = self._build_definition()

    def _build_definition(self) -> ToolDefinition:
        sig = inspect.signature(self.fn)
        # Resolve string annotations (PEP 563 / future annotations) to actual types
        try:
            resolved = inspect.get_annotations(self.fn, eval_str=True)
        except (NameError, AttributeError):
            resolved = {}

        properties: dict[str, dict[str, Any]] = {}
        required: list[str] = []

        for param_name, param in sig.parameters.items():
            if param_name in {"self", "cls"}:
                continue
            param_type: Any = resolved.get(param_name, param.annotation)
            if param_type is inspect.Parameter.empty:
                param_type = str

            if isinstance(param_type, type) and issubclass(param_type, BaseModel):
                schema = param_type.model_json_schema()
                properties[param_name] = schema
            elif param_type in _PRIMITIVE_TYPE_MAP:
                properties[param_name] = {"type": _PRIMITIVE_TYPE_MAP[param_type]}
            else:
                properties[param_name] = {"type": "string"}

            if param.default is inspect.Parameter.empty:
                required.append(param_name)

        return ToolDefinition(
            name=self.name,
            description=self.description,
            input_schema={
                "type": "object",
                "properties": properties,
                "required": required,
            },
        )

    def invoke(self, input_data: dict[str, Any]) -> str:
        """Call the underlying function with input data, return string result."""
        result = self.fn(**input_data)
        if isinstance(result, str):
            return result
        if isinstance(result, BaseModel):
            return result.model_dump_json()
        return str(result)


def tool(description: str, *, name: str | None = None) -> Callable[[Callable[..., Any]], Tool]:
    """Decorator: register a Python function as an agent tool.

    Example:
        @tool(description="Get current weather.")
        def get_weather(city: str) -> str:
            return f"Sunny in {city}"
    """

    def wrapper(fn: Callable[..., Any]) -> Tool:
        return Tool(fn=fn, description=description, name=name)

    return wrapper

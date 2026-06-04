"""Tests for tool registration and schema generation."""

import pytest
from pydantic import BaseModel

from bedrock_claude_starter import tool
from bedrock_claude_starter.tools import Tool


def test_basic_tool_registration() -> None:
    @tool(description="Greet a person.")
    def greet(name: str) -> str:
        return f"Hello, {name}!"

    assert isinstance(greet, Tool)
    assert greet.name == "greet"
    assert greet.description == "Greet a person."


def test_tool_invocation_returns_string() -> None:
    @tool(description="Echo.")
    def echo(text: str) -> str:
        return text

    assert echo.invoke({"text": "hi"}) == "hi"


def test_tool_with_int_arg() -> None:
    @tool(description="Add 1 to n.")
    def add_one(n: int) -> int:
        return n + 1

    schema = add_one.definition.input_schema
    assert schema["properties"]["n"]["type"] == "integer"
    assert add_one.invoke({"n": 5}) == "6"


def test_tool_with_optional_arg_not_required() -> None:
    @tool(description="Greet with optional politeness.")
    def greet(name: str, polite: bool = True) -> str:
        return f"{'Hello' if polite else 'Hey'}, {name}"

    schema = greet.definition.input_schema
    assert "name" in schema["required"]
    assert "polite" not in schema["required"]


def test_tool_with_pydantic_model() -> None:
    class Item(BaseModel):
        sku: str
        qty: int

    @tool(description="Order an item.")
    def order(item: Item) -> str:
        return f"ordered {item.qty} of {item.sku}"

    schema = order.definition.input_schema
    # Pydantic schema embedded as the parameter's spec
    assert "properties" in schema["properties"]["item"]
    assert order.invoke({"item": Item(sku="ABC", qty=3)}) == "ordered 3 of ABC"


def test_custom_tool_name() -> None:
    @tool(description="Custom-named tool.", name="my_special_tool")
    def some_function() -> str:
        return "ok"

    assert some_function.name == "my_special_tool"


def test_tool_returning_pydantic_serialized_to_json() -> None:
    class Result(BaseModel):
        ok: bool
        message: str

    @tool(description="Returns structured result.")
    def do_thing() -> Result:
        return Result(ok=True, message="done")

    out = do_thing.invoke({})
    assert "true" in out.lower()
    assert "done" in out


def test_tool_invocation_propagates_errors() -> None:
    @tool(description="Always fails.")
    def broken(x: int) -> int:
        raise ValueError(f"bad x: {x}")

    with pytest.raises(ValueError, match="bad x"):
        broken.invoke({"x": 7})

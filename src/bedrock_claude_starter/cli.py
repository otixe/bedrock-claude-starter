"""Demo CLI."""

from __future__ import annotations

from typing import Annotated

import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.prompt import Prompt

from . import __version__
from .agent import DEFAULT_MODEL, Agent
from .tools import tool

app = typer.Typer(
    name="agent",
    help="🧠 Demo CLI for bedrock-claude-starter",
    no_args_is_help=True,
)
console = Console()


@tool(description="Get the current weather for a city. Returns a short string.")
def get_weather(city: str) -> str:
    """Demo tool — replace with a real weather API in production."""
    return f"It's 22°C and sunny in {city}."


@tool(description="Echo back a string (useful for testing tool plumbing).")
def echo(text: str) -> str:
    return text


def _version_callback(value: bool) -> None:
    if value:
        console.print(f"bedrock-claude-starter {__version__}")
        raise typer.Exit


@app.callback()
def main(
    version: Annotated[
        bool, typer.Option("--version", "-V", callback=_version_callback, is_eager=True)
    ] = False,
) -> None:
    """Global options."""


@app.command()
def chat(
    model: Annotated[str, typer.Option(help="Bedrock model ID")] = DEFAULT_MODEL,
    region: Annotated[str, typer.Option(help="AWS region")] = "us-east-1",
    profile: Annotated[str | None, typer.Option(help="AWS profile name")] = None,
    thinking: Annotated[bool, typer.Option(help="Enable extended thinking")] = False,
) -> None:
    """Interactive chat with the demo agent."""
    agent = Agent(
        system_prompt=(
            "You are a friendly demo assistant. "
            "You have tools for weather lookup and echo. "
            "Use them when relevant; otherwise just answer concisely."
        ),
        tools=[get_weather, echo],
        model=model,
        thinking=thinking,
        aws_region=region,
        aws_profile=profile,
    )

    console.print(
        f"[bold cyan]bedrock-claude-starter[/bold cyan] · model={model} · region={region}\n"
        "Type your message. Ctrl+C to exit.\n"
    )

    while True:
        try:
            message = Prompt.ask("[green]you[/green]")
        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]bye[/dim]")
            return

        if not message.strip():
            continue

        with console.status("[dim]thinking…[/dim]"):
            response = agent.run(message)

        console.print()
        console.print("[bold magenta]assistant[/bold magenta]")
        console.print(Markdown(response.text))
        if response.tool_calls:
            console.print(
                f"[dim](used {len(response.tool_calls)} tool call"
                f"{'s' if len(response.tool_calls) != 1 else ''}, "
                f"{response.iterations} iteration"
                f"{'s' if response.iterations != 1 else ''})[/dim]"
            )
        console.print()


if __name__ == "__main__":
    app()

"""Smoke tests for the CLI."""

from __future__ import annotations

from typer.testing import CliRunner

from bedrock_claude_starter.cli import app

runner = CliRunner()


def test_version() -> None:
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "bedrock-claude-starter" in result.stdout


def test_help_lists_commands() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "chat" in result.stdout

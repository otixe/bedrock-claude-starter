# Contributing

Thanks for considering a contribution.

## Local setup

```bash
git clone https://github.com/otixe/bedrock-claude-starter.git
cd bedrock-claude-starter
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pre-commit install
```

## Testing

Tests do **not** call AWS. The Bedrock client is fully mocked. Run them locally:

```bash
pytest -v
```

If you want to test end-to-end against real Bedrock:

```bash
export AWS_PROFILE=my-bedrock-profile
agent chat
```

## Workflow

1. Branch from `main`: `git checkout -b feat/your-feature`
2. Make changes, add tests
3. Quality gates:
   ```bash
   ruff check src/ tests/
   ruff format src/ tests/
   mypy src/
   pytest
   ```
4. Commit using [Conventional Commits](https://www.conventionalcommits.org/)
5. Open a PR. CI must pass.

## Scope

This is intentionally a **starter**, not a framework. Keep it small.

- ✅ Better tool-use ergonomics, retry logic, memory abstractions
- ✅ Bedrock-specific features (thinking mode, prompt caching, model-agnostic Converse)
- ❌ Multi-agent orchestration (use a real framework)
- ❌ Web UI / HTTP API (out of scope)
- ❌ Non-Bedrock LLM backends (use a different starter)

## Reporting bugs

Include:
- Python version
- AWS region and Bedrock model used
- Reproduction with mocked Bedrock if possible
- Expected vs actual behavior

# bedrock-claude-starter

<div align="center">

🧠 **Production-ready boilerplate for Claude agents on AWS Bedrock**

*Tool-use loop · semantic memory · structured I/O · ready to clone*

[![CI](https://github.com/otixe/bedrock-claude-starter/actions/workflows/ci.yml/badge.svg)](https://github.com/otixe/bedrock-claude-starter/actions/workflows/ci.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)

</div>

---

## Why?

Most "Claude agent" tutorials are toy chat loops with no production concerns:
no retries, no memory, no observability, no real tool plumbing.

This is a **deliberately small** starter that ships with the four things every
real agent eventually needs:

1. **Robust Bedrock client** — retries, exponential backoff, `thinking` mode toggle
2. **Tool-use loop** — register Python functions, get them called by Claude with structured args
3. **Semantic memory** — persist exchanges in Qdrant, retrieve by embedding similarity
4. **Structured I/O** — Pydantic-typed messages and results (no dict-stringly-typed hellscapes)

Clone it, replace the example tools and system prompt, and you have a working agent
in 30 minutes.

---

## Features

- 🤖 **Bedrock-native** — uses `bedrock-runtime` Converse API (the modern, model-agnostic one)
- 🔁 **Tool loop** — auto-iterates between Claude and your Python functions until task complete
- 🧠 **Semantic memory** — Qdrant + Titan v2 embeddings (1024 dims), in-memory or remote
- 💬 **Conversation history** — sliding window with semantic retrieval of older context
- 🎯 **Typed messages** — Pydantic models for messages, tool defs, memory entries
- 🛡️ **Safety nets** — max iterations, timeout, IAM-scoped tools
- 🧪 **Test suite** — full mocked Bedrock + Qdrant for fast offline tests
- 🪶 **Lightweight** — no LangChain, no LlamaIndex, no framework lock-in

---

## Quickstart

```bash
pip install bedrock-claude-starter

# Configure AWS credentials (SSO recommended)
export AWS_PROFILE=my-bedrock-profile
export AWS_REGION=us-east-1

# Spin up local Qdrant in Docker
docker run -d -p 6333:6333 --name qdrant qdrant/qdrant

# Run the demo agent
agent chat
```

```python
from bedrock_claude_starter import Agent, tool


@tool(description="Get the current weather for a city.")
def get_weather(city: str) -> str:
    """In real life, call your weather API. Here, a stub."""
    return f"It's 22°C and sunny in {city}."


agent = Agent(
    system_prompt="You are a helpful assistant. Use tools when needed.",
    tools=[get_weather],
    model="us.anthropic.claude-sonnet-4-5-20250929-v1:0",
)

response = agent.run("What's the weather in Santiago?")
print(response.text)
```

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         Agent                               │
│                                                             │
│  ┌─────────────┐   ┌─────────────────┐   ┌──────────────┐   │
│  │ Bedrock     │◄─►│  Tool-use Loop  │◄─►│  Memory      │   │
│  │ Client      │   │  (Converse API) │   │  (Qdrant)    │   │
│  │ (boto3)     │   │                 │   │              │   │
│  └──────┬──────┘   └────────┬────────┘   └──────┬───────┘   │
│         │                   │                   │           │
└─────────┼───────────────────┼───────────────────┼───────────┘
          │                   │                   │
          ▼                   ▼                   ▼
   ┌─────────────┐    ┌─────────────┐     ┌──────────────┐
   │  Bedrock    │    │  Your Python│     │   Qdrant     │
   │  (Claude    │    │  functions  │     │   (vector    │
   │  models)    │    │  as @tool   │     │   DB)        │
   └─────────────┘    └─────────────┘     └──────────────┘
```

The agent runs a loop:

1. Send messages + tool definitions to Bedrock
2. Receive response — either text or tool-use blocks
3. If tool-use: invoke the registered Python function, append result to messages
4. If text: return it (or store in memory and return)
5. Repeat until terminal response or `max_iterations` reached

Memory is queried before each turn — relevant past exchanges are injected
as context.

---

## Tools API

Define tools with the `@tool` decorator. Type hints generate the schema:

```python
from bedrock_claude_starter import tool

@tool(description="Look up a customer by ID.")
def get_customer(customer_id: str) -> dict:
    return db.fetch(customer_id)

@tool(description="Create a support ticket.")
def create_ticket(title: str, body: str, priority: str = "medium") -> str:
    """Returns the new ticket ID."""
    return tickets.create(title, body, priority).id
```

Pydantic models also work for richer schemas:

```python
from pydantic import BaseModel

class TicketSpec(BaseModel):
    title: str
    body: str
    priority: Literal["low", "medium", "high"]

@tool(description="Create a support ticket from a structured spec.")
def create_ticket(spec: TicketSpec) -> str:
    return tickets.create(**spec.model_dump()).id
```

---

## Semantic memory

```python
from bedrock_claude_starter import Memory

memory = Memory(
    collection_name="customer-support",
    qdrant_url="http://localhost:6333",
    embedding_model="amazon.titan-embed-text-v2:0",
)

memory.remember("Customer X prefers email over phone.")
memory.remember("Refund threshold for tier-2 customers is $500.")

# Retrieve by similarity
results = memory.recall("How should I contact customer X?", limit=3)
```

Pass it to the agent:

```python
agent = Agent(
    system_prompt="You are a support agent.",
    tools=[get_customer, create_ticket],
    memory=memory,
    memory_top_k=5,
)
```

The agent auto-injects the top-K relevant memory entries into the system context
before each turn.

---

## What this starter is NOT

- ❌ A full agent framework (use LangChain or LlamaIndex if you want a kitchen sink)
- ❌ A multi-agent orchestrator (single-agent, single-conversation only)
- ❌ A web app (no UI, no HTTP server — bring your own)
- ❌ Locked to one Claude version (works with any Bedrock-hosted Claude)

The goal is to be **boilerplate** — clone it, hack it, ship it. Read the source.

---

## Examples

- [`examples/customer-support-agent.md`](examples/customer-support-agent.md) — multi-tool agent with memory
- [`examples/research-agent.md`](examples/research-agent.md) — long-running research with web tools
- [`examples/structured-output.md`](examples/structured-output.md) — get JSON-typed results out of Claude

---

## License

MIT — see [LICENSE](LICENSE).

Built by [@otixe](https://github.com/otixe) — DevOps & Agentic Systems Engineer · 🇨🇱

# Customer support agent example

A multi-tool agent with persistent memory, demonstrating the typical
production pattern.

## Setup

```python
from bedrock_claude_starter import Agent, Memory, tool

# Sample stub stores — replace with your real backends
CUSTOMERS = {
    "C001": {"name": "Alice", "tier": "premium", "email": "alice@example.com"},
    "C002": {"name": "Bob", "tier": "standard", "email": "bob@example.com"},
}
TICKETS: dict[str, dict] = {}


@tool(description="Look up a customer by ID. Returns name, tier, email.")
def get_customer(customer_id: str) -> dict:
    return CUSTOMERS.get(customer_id, {"error": "not found"})


@tool(description="Create a support ticket. Returns the ticket ID.")
def create_ticket(customer_id: str, title: str, body: str, priority: str = "medium") -> str:
    ticket_id = f"T{len(TICKETS) + 1:04d}"
    TICKETS[ticket_id] = {
        "customer_id": customer_id,
        "title": title,
        "body": body,
        "priority": priority,
        "status": "open",
    }
    return ticket_id


@tool(description="Look up an existing ticket.")
def get_ticket(ticket_id: str) -> dict:
    return TICKETS.get(ticket_id, {"error": "not found"})


# Persistent memory across runs
memory = Memory(
    collection_name="customer-support",
    qdrant_url="http://localhost:6333",  # in-memory for demo: omit
)

# Pre-load policy memory
memory.remember("Premium customers get refunds up to $500 without manager approval.")
memory.remember("Standard customers must wait 14 days before refund eligibility.")
memory.remember("All escalations require manager review when amount > $1000.")

agent = Agent(
    system_prompt=(
        "You are a customer support agent. "
        "Use tools to look up customers and tickets. "
        "Cite policies from memory when making decisions."
    ),
    tools=[get_customer, create_ticket, get_ticket],
    memory=memory,
    memory_top_k=3,
)
```

## Sample interaction

```python
response = agent.run(
    "Customer C001 wants a $400 refund. Can I approve it? "
    "If yes, create a ticket about it."
)

print(response.text)
# → "Customer Alice is a premium tier customer. Per policy, premium
#    customers can receive refunds up to $500 without manager approval.
#    The $400 refund is approved. I've created ticket T0001 to track it."

print(response.tool_calls)
# → [
#     ToolUseBlock(name="get_customer", input={"customer_id": "C001"}),
#     ToolUseBlock(name="create_ticket", input={...}),
#   ]

print(response.iterations)
# → 3   (1 lookup + 1 create + 1 final summary)
```

## Why this pattern works

1. **Memory** carries policy/context that's expensive to re-prompt every turn
2. **Tools** let Claude take real actions, not just answer questions
3. **Pydantic-typed inputs** make the agent's reasoning auditable
4. **Iteration cap** prevents runaway loops on ambiguous queries

In production, swap the dict stores for your real data layer, add proper
error handling per-tool, and wire CloudWatch logging on the agent loop.

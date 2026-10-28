# Mem0 SDK Guide

Complete SDK reference for Python and TypeScript. All methods use `MemoryClient` (Platform API).

> **For language-specific deep references (including OSS):** See [client/python.md](../client/python.md) and [client/node.md](../client/node.md). For Python vs TypeScript differences: [client/differences.md](../client/differences.md).

## Initialization

**Python:**
```python
from mem0 import MemoryClient
client = MemoryClient(api_key="m0-your-api-key")
```

**Python (Async):**
```python
from mem0 import AsyncMemoryClient
client = AsyncMemoryClient(api_key="m0-your-api-key")
```

**TypeScript:**
```typescript
import MemoryClient from 'mem0ai';
const client = new MemoryClient({ apiKey: 'm0-your-api-key' });
```

Constructor accepts `apiKey` (required) and `host` (optional, default: `https://api.mem0.ai`).

---

## add() -- Store Memories

**Python:**
```python
messages = [
    {"role": "user", "content": "I'm a vegetarian and allergic to nuts."},
    {"role": "assistant", "content": "Got it! I'll remember that."}
]
client.add(messages)

# With metadata
client.add(messages, metadata={"source": "onboarding"})
```

**TypeScript:**
```typescript
await client.add(messages);
await client.add(messages, { metadata: { source: "onboarding" } });
```

### Parameters

| Name | Type | Description |
|------|------|-------------|
| `messages` | array | `[{"role": "user", "content": "..."}]` |
| `agent_id` | string | Agent identifier |
| `run_id` | string | Session identifier |
| `metadata` | object | Custom key-value pairs |
| `infer` | boolean | If `false`, store raw text without inference (default: `true`) |

### Advanced Add Options

```python
# Agent + session scoping
client.add(messages, agent_id="nutrition-agent", run_id="session-456")

# Raw text -- skip LLM inference
client.add(
    [{"role": "user", "content": "User prefers dark mode."}],
    infer=False,
)
```

---

## search() -- Find Memories

**Python:**
```python
results = client.search("dietary preferences?")

# With filters and reranking
results = client.search(
    query="work experience",
    filters={"categories": {"contains": "professional_details"}},
    top_k=5,
    rerank=True,
    threshold=0.5
)
```

**TypeScript:**
```typescript
const results = await client.search("dietary preferences");
const results = await client.search("work experience", {
    filters: { categories: { contains: "professional_details" } },
    topK: 5,
    rerank: true,
});
```

### Parameters

| Name | Type | Description                                              |
|------|------|----------------------------------------------------------|
| `query` | string | Natural language search query                            |
| `filters` | object | Filter object (AND/OR operators).                        |
| `top_k` | number | Number of results (default: 10 for Platform)             |
| `rerank` | boolean | Enable reranking for better relevance (default: `false`) |
| `threshold` | number | Minimum similarity score (default: 0.1)                  |

### Common Filter Patterns

**Python:**
```python
# Match a set of agents
filters={"agent_id": {"in": ["travel-agent", "sports-agent"]}}

# Category filtering (partial match)
filters={"categories": {"contains": "finance"}}

# Category filtering (exact match)
filters={"categories": {"in": ["personal_information"]}}

# Wildcard (match any non-null run)
filters={"run_id": "*"}

# Date range
filters={"AND": [
    {"created_at": {"gte": "2024-01-01T00:00:00Z"}},
    {"created_at": {"lt": "2024-02-01T00:00:00Z"}}
]}

# Exclude categories with NOT
filters={"NOT": {"categories": {"in": ["spam", "test"]}}}

# Multi-dimensional query
filters={"AND": [
    {"keywords": {"icontains": "invoice"}},
    {"categories": {"in": ["finance"]}},
    {"created_at": {"gte": "2024-01-01T00:00:00Z"}}
]}
```

**TypeScript:**
```typescript
// Match a set of agents
filters: { agent_id: { in: ["travel-agent", "sports-agent"] } }

// Category filtering (partial match)
filters: { categories: { contains: "finance" } }

// Category filtering (exact match)
filters: { categories: { in: ["personal_information"] } }
```

---

## get() / getAll() -- Retrieve Memories

**Python:**
```python
# Single memory by ID
memory = client.get(memory_id="ea925981-...")

# Every memory visible to the API key
memories = client.get_all()

# With date range
memories = client.get_all(
    filters={"created_at": {"gte": "2024-07-01", "lte": "2024-07-31"}}
)
```

**TypeScript:**
```typescript
const memory = await client.get("ea925981-...");
const memories = await client.getAll();
```

**Note:** filters are optional -- ownership comes from the API key. Add `agent_id`, `app_id`, or `run_id` to narrow the result.

---

## update() -- Modify Memories

**Python:**
```python
client.update(memory_id="ea925981-...", text="Updated: vegan since 2024")
client.update(memory_id="ea925981-...", text="Updated", metadata={"verified": True})
```

**TypeScript:**
```typescript
await client.update("ea925981-...", { text: "Updated: vegan since 2024" });
```

---

## delete() / deleteAll() -- Remove Memories

**Python:**
```python
client.delete(memory_id="ea925981-...")
client.delete_all()  # Irreversible: every memory visible to the API key
client.delete_all(run_id="session-456")  # Narrower: only that session, still irreversible
```

**TypeScript:**
```typescript
await client.delete("ea925981-...");
await client.deleteAll();
```

---

## history() -- Track Changes

**Python:**
```python
history = client.history(memory_id="ea925981-...")
# Returns: [{previous_value, new_value, action, timestamps}]
```

**TypeScript:**
```typescript
const history = await client.history("ea925981-...");
```

---

## Batch Operations (TypeScript)

```typescript
// Batch update
await client.batchUpdate([
    { memoryId: "uuid-1", text: "Updated text" },
    { memoryId: "uuid-2", text: "Another updated text" },
]);

// Batch delete
await client.batchDelete(["uuid-1", "uuid-2", "uuid-3"]);
```

---

## Additional Methods

```python
# List all users/agents/sessions with memories
users = client.users()

# Submit feedback on a memory
client.feedback(memory_id="...", feedback="POSITIVE", feedback_reason="Accurate extraction")
```

---

## Common Pitfalls

1. **`user_id` and `env` are not filter dimensions** -- ownership comes from the API key: `env` is always refused, and `user_id` is refused unless it names the key's own user.
2. **SQL operators rejected** -- use `gte`, `lt`, etc. Not `>=`, `<`.
3. **Metadata filtering is limited** -- only top-level keys with `eq`, `contains`, `ne`.
4. **Wildcard `*` excludes null** -- only matches non-null values.
5. **Default threshold is 0.1** -- increase for stricter matching.
6. **Async processing** -- memories process asynchronously. Wait 2-3s after `add()` before searching.

## Naming Conventions

Python uses `snake_case` everywhere (`memory_id`, `get_all`). TypeScript uses `camelCase` for methods (`getAll`, `deleteAll`, `batchUpdate`) and top-level parameters (`topK`, `pageSize`), but filter keys use `snake_case` (`agent_id`).

---

## v2 to v3 Migration

### Breaking Changes in v3

**1. Entity IDs in search() and getAll()**

v3 requires entity IDs (`agent_id`, `run_id`) inside `filters` instead of as top-level parameters.

**2. TypeScript Parameter Naming**

v3 TypeScript uses camelCase for all parameters:

| v2 | v3 |
|----|-----|
| `agent_id` | `agentId` |
| `run_id` | `runId` |
| `top_k` | `topK` |
| `page_size` | `pageSize` |

**3. Default Values Changed**

| Parameter | v2 Default | v3 Default |
|-----------|------------|------------|
| `threshold` | 0.3 | 0.1 |
| `rerank` | (not specified) | `false` |

**4. Removed Parameters**

The following parameters are no longer supported:

| Parameter | Status |
|-----------|--------|
| `enable_graph` | Removed from add/search/getAll |
| `keyword_search` | Removed from search |
| `filter_memories` | Removed |
| `immutable` | Removed from add |
| `expiration_date` | Removed from add |
| `includes` | Removed from add |
| `excludes` | Removed from add |
| `async_mode` | Removed from add |

---
name: list-projects
description: Lists all projects with stored memories, showing memory counts and last activity dates. Use when checking which projects have memories, comparing memory distribution across repos, or finding a specific project scope.
---

# Mem0 List Projects

Show all known project scopes.

## Execution

### Step 1: Fetch memories to discover app_ids

There is no dedicated "list projects" API endpoint. Discover projects by fetching
memories across all scopes.

Run two queries and merge:

1. **Current scope:** `get_memories` with `page_size=200` and no filters
   — the hook scopes it to the current project
2. **App-scoped:** `get_memories` with `filters={"AND": [{"app_id": {"exists": true}}]}`, `page_size=200`
   — catches memories with any `app_id`

Run both calls in parallel. Merge results, deduplicate by memory `id`.

If either response indicates more pages, paginate (up to 1000 total).

### Step 2: Extract distinct projects

For each memory, determine project by:
1. Top-level `app_id` field (preferred)
2. `metadata.project_id` (legacy memories)
3. `metadata.project` (oldest format)
4. `"(unscoped)"` if none found

Group by resolved project name. For each project, count:
- Total memories
- Most recent `created_at` date
- Top 3 `metadata.type` values by frequency

### Step 3: Display

```
## mem0 projects

  <app_id_1>  <count> memories  (last: <date>) ← current
  <app_id_2>  <count> memories  (last: <date>)

<N> projects, <M> total memories
```

Mark current project with `← current`. Sort by memory count descending.

### Step 4: Empty state

If zero memories found:
```
No projects found. Run /mem0:onboard to get started.
```

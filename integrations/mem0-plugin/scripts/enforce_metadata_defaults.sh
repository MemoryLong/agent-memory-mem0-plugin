#!/usr/bin/env bash
# PreToolUse hook for mem0 MCP tools.
# Injects app_id and metadata defaults when the agent omits them. Uses the
# hookSpecificOutput.updatedInput contract to modify tool call parameters
# before execution. user_id is never injected: the backend derives it from the
# X-API-Key.
#
# Handles:
#   add_memory         — top-level app_id, metadata defaults
#   search_memories    — app_id into filters.AND[]
#   get_memories       — app_id into filters.AND[]
#   delete_all_memories — top-level app_id
#
# Hook contract:
#   exit 0 = allow. If stdout contains {"hookSpecificOutput": {"updatedInput": ...}},
#            the updatedInput replaces the tool's input parameters.
#   exit 2 = block (stderr shown as rejection reason).

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/_identity.sh" 2>/dev/null || true

INPUT=$(cat)

TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name // ""' 2>/dev/null)

# Determine which handler to use based on tool name
HANDLER=""
case "$TOOL_NAME" in
  mcp__mem0__add_memory|mcp__plugin_mem0_mem0__add_memory)
    HANDLER="add_memory" ;;
  mcp__mem0__search_memories|mcp__plugin_mem0_mem0__search_memories)
    HANDLER="search_memories" ;;
  mcp__mem0__get_memories|mcp__plugin_mem0_mem0__get_memories)
    HANDLER="get_memories" ;;
  mcp__mem0__delete_all_memories|mcp__plugin_mem0_mem0__delete_all_memories)
    HANDLER="delete_all" ;;
  *) exit 0 ;;
esac

TOOL_INPUT=$(echo "$INPUT" | jq -r '.tool_input // "{}"' 2>/dev/null)

_PATCH_OUT="/tmp/mem0_enforce_$$"
trap 'rm -f "$_PATCH_OUT"' EXIT
_MEM0_TOOL_INPUT="$TOOL_INPUT" \
_MEM0_APP_ID="${MEM0_PROJECT_ID:-}" \
_MEM0_GLOBAL_SEARCH="${MEM0_GLOBAL_SEARCH:-false}" \
_MEM0_HANDLER="$HANDLER" \
python3 <<'PYEOF' > "$_PATCH_OUT" 2>/dev/null || true
import json, os, sys

raw = os.environ.get("_MEM0_TOOL_INPUT", "{}")
try:
    inp = json.loads(raw)
except Exception:
    sys.exit(0)

handler = os.environ.get("_MEM0_HANDLER", "")
resolved_aid = os.environ.get("_MEM0_APP_ID", "")
global_search = os.environ.get("_MEM0_GLOBAL_SEARCH", "false") == "true"
changed = False


def is_empty_group(value):
    return isinstance(value, (dict, list)) and not value


def drop_user_id(node):
    """Remove user_id at any depth.

    The account calling the LLM is a dedicated agent-memory account, not the
    end user whose memories are stored, so the model must never narrow by
    user_id — the backend resolves the owner from the X-API-Key. A group that
    held nothing but user_id becomes an empty AND/OR clause, so it is dropped
    as well. Mirrors stripUserId() in .opencode-plugin/opencode-mem0.ts.
    """
    if isinstance(node, dict):
        clean = {}
        for key, value in node.items():
            if key == "user_id":
                continue
            stripped = drop_user_id(value)
            if is_empty_group(stripped) and not is_empty_group(value):
                continue
            clean[key] = stripped
        return clean
    if isinstance(node, list):
        items = []
        for item in node:
            stripped = drop_user_id(item)
            if is_empty_group(stripped) and not is_empty_group(item):
                continue
            items.append(stripped)
        return items
    return node


clean_input = drop_user_id(inp)
user_id_dropped = clean_input != inp
inp = clean_input


def inject_top_level_identity(inp, aid):
    """Inject app_id as a top-level param (for add_memory, delete_all)."""
    changed = False
    if aid and not inp.get("app_id"):
        inp["app_id"] = aid
        changed = True
    return changed


def inject_filter_identity(inp, aid):
    """Inject app_id into filters.AND[] (for search/get_memories)."""
    changed = False
    if not aid:
        return False

    filters = inp.get("filters")

    if filters is None:
        # No filters at all — create from scratch
        and_clauses = []
        if aid:
            and_clauses.append({"app_id": aid})
        inp["filters"] = {"AND": and_clauses}
        return True

    if not isinstance(filters, dict):
        return False

    # Check if filters already contain app_id
    and_clauses = filters.get("AND")
    if and_clauses is None:
        # Filters exist but no AND — could be flat like {"app_id": "x"}
        has_aid = "app_id" in filters
        if has_aid:
            return False
        # Convert flat filters to AND format and add the project label
        existing = []
        for k, v in list(filters.items()):
            existing.append({k: v})
        if aid and not has_aid:
            existing.append({"app_id": aid})
            changed = True
        if changed:
            inp["filters"] = {"AND": existing}
        return changed

    if not isinstance(and_clauses, list):
        return False

    # AND array exists — check for existing app_id
    has_aid = any("app_id" in c for c in and_clauses if isinstance(c, dict))

    if aid and not has_aid:
        and_clauses.append({"app_id": aid})
        changed = True

    return changed


if handler == "add_memory":
    changed = inject_top_level_identity(inp, resolved_aid)

    meta = inp.get("metadata") or {}

    if "confidence" not in meta:
        meta["confidence"] = 0.7
        changed = True
    if "files" not in meta:
        meta["files"] = ["*"]
        changed = True
    if "source" not in meta:
        meta["source"] = "auto_capture"
        changed = True
    if "type" not in meta:
        meta["type"] = "task_learning"
        changed = True

    if meta.get("confidence", 0) >= 1.0 and "infer" not in inp:
        inp["infer"] = False
        changed = True

    # Track session in metadata instead of run_id.
    # run_id creates a separate entity partition in the v3 API,
    # making memories invisible to search/get_memories calls
    # that don't include a run_id filter.
    if "session_id" not in meta:
        sid = os.environ.get("MEM0_SESSION_ID", "")
        if not sid:
            session_file = "/tmp/mem0_session_id_" + os.environ.get("USER", "default")
            if os.path.isfile(session_file):
                try:
                    with open(session_file) as f:
                        sid = f.read().strip()
                except OSError:
                    pass
        if sid:
            meta["session_id"] = sid
            changed = True

    if changed:
        inp["metadata"] = meta

elif handler in ("search_memories", "get_memories"):
    # A global search reads across projects, so it gets no app_id narrowing.
    if not global_search:
        changed = inject_filter_identity(inp, resolved_aid)

elif handler == "delete_all":
    changed = inject_top_level_identity(inp, resolved_aid)

if changed or user_id_dropped:
    print(json.dumps(inp))
PYEOF
PATCHED=$(cat "$_PATCH_OUT" 2>/dev/null)
rm -f "$_PATCH_OUT"

if [ -n "$PATCHED" ] && echo "$PATCHED" | jq empty 2>/dev/null; then
  jq -n --argjson updated "$PATCHED" '{
    "hookSpecificOutput": {
      "hookEventName": "PreToolUse",
      "permissionDecision": "allow",
      "updatedInput": $updated
    }
  }' 2>/dev/null || true
fi

# Track session stats here because PostToolUse hooks don't fire for plugin MCP tools.
case "$HANDLER" in
  add_memory)
    _CAT=$(echo "$TOOL_INPUT" | jq -r '.metadata.type // .metadata.category // ""' 2>/dev/null || echo "")
    python3 "$SCRIPT_DIR/session_stats.py" add "$_CAT" 2>/dev/null &
    ;;
  search_memories|get_memories)
    python3 "$SCRIPT_DIR/session_stats.py" search 2>/dev/null &
    ;;
esac

exit 0

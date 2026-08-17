"""Shared mem0 search API helper.

Wraps POST /v1/agent/memory/search into a single function call.
All pre-fetch hooks use this instead of duplicating urllib boilerplate.
"""

from __future__ import annotations

import json
import os
import urllib.request

from _identity import resolve_api_url

API_BASE = resolve_api_url()
SEARCH_URL = f"{API_BASE}/v1/agent/memory/search"
SEARCH_TIMEOUT = 5


def should_rerank() -> bool:
    """Whether auto-injection searches should request reranking.

    The REST search endpoint does not rerank when ``rerank`` is omitted, so
    auto-injected context is ordered by raw vector similarity and the single
    most relevant memory can fall outside the injected top_k window. We default
    reranking ON for the hook-driven injection path (the extra ~150-200ms is
    well within the hook's curl budget) and let users opt out via MEM0_RERANK.

    MEM0_RERANK is read case-insensitively; ``0``, ``false``, ``no``, and
    ``off`` disable reranking. Anything else (including unset) enables it.
    """
    raw = os.environ.get("MEM0_RERANK")
    if raw is None:
        return True
    return raw.strip().lower() not in ("0", "false", "no", "off", "")


def _do_search(api_key: str, payload: dict) -> list[dict]:
    body = json.dumps(payload).encode()
    req = urllib.request.Request(
        SEARCH_URL,
        data=body,
        headers={"X-API-Key": api_key, "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=SEARCH_TIMEOUT) as r:
        data = json.loads(r.read())
        return data if isinstance(data, list) else data.get("results", [])


def search_memories(
    api_key: str,
    query: str,
    metadata_type: str | None = None,
    metadata_filters: dict | None = None,
    top_k: int = 3,
    min_score: float = 0.0,
    rerank: bool = False,
    threshold: float = 0.3,
    global_search: bool = False,
) -> list[dict]:
    if not api_key:
        return []

    # Local backend uses flat metadata filters (no AND/OR). Identity
    # (user_id/app_id) is resolved from X-API-Key; scope maps global vs project.
    filters: dict = {}
    if not global_search:
        if metadata_type:
            filters["type"] = metadata_type
        if metadata_filters:
            filters.update(metadata_filters)

    base_payload: dict = {
        "query": query,
        "top_k": top_k,
        "threshold": threshold,
        "filters": filters,
        "scope": "global" if global_search else "project",
    }
    if rerank:
        base_payload["rerank"] = True

    try:
        results = _do_search(api_key, base_payload)[:top_k]

        if min_score > 0:
            results = [m for m in results if m.get("score", 0) >= min_score]
        return results
    except Exception:
        return []


def format_results_for_context(
    memories: list[dict],
    heading: str = "Relevant memories",
) -> str:
    if not memories:
        return ""
    lines = [f"### {heading}", ""]
    for m in memories:
        mid = m.get("id", "?")[:8]
        text = (m.get("content") or m.get("memory", ""))[:200]
        cat = (m.get("metadata") or {}).get("type", "unknown")
        lines.append(f"- [{cat}] {text} [mem0:{mid}]")
    lines.append("")
    return "\n".join(lines)

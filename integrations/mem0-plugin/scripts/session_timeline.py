#!/usr/bin/env python3
"""Fetch recent memories and format a compact timeline for SessionStart.

Fetches the most recent memories from the local backend and formats them
as a compact activity timeline injected below the SessionStart banner.

Input:  env vars (MEM0_API_KEY, MEM0_BASE_URL)
Output: Compact timeline text to stdout (empty if nothing found)
"""

from __future__ import annotations

import json
import os
import sys
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _formatting import TYPE_ICONS, format_age
from _identity import resolve_api_key, resolve_api_url

API_URL = resolve_api_url()
MAX_RECENT = 10
FETCH_TIMEOUT = 5


def fetch_recent_memories(api_key: str) -> list[dict]:
    """Fetch the most recent memories via the local list endpoint.
    Identity (user/app) is resolved from X-API-Key; no filters needed."""
    req = urllib.request.Request(
        f"{API_URL}/v1/agent/memory?page=1&page_size={MAX_RECENT}",
        headers={"X-API-Key": api_key},
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=FETCH_TIMEOUT) as r:
            result = json.loads(r.read())
            if isinstance(result, dict) and "results" in result:
                return result["results"][:MAX_RECENT]
            if isinstance(result, list):
                return result[:MAX_RECENT]
            return []
    except Exception:
        return []


def format_timeline(memories: list[dict]) -> str:
    """Format memories into a compact recent activity timeline."""
    if not memories:
        return ""

    lines = ["### Recent Activity", ""]

    for m in memories:
        mid = m.get("id", "?")[:8]
        text = (m.get("content") or m.get("memory", "") or "")[:120].replace("\n", " ").strip()
        meta = m.get("metadata") or {}
        cat = meta.get("type", "unknown")
        icon = TYPE_ICONS.get(cat, "❓")
        age = format_age(m)
        age_str = f" ({age})" if age else ""
        lines.append(f"- {icon} [{cat}]{age_str} {text} [mem0:{mid}]")

    lines.append("")
    lines.append("Search mem0 for details on any of these, or for past decisions and task learnings relevant to the current task.")

    return "\n".join(lines)


def main():
    api_key = resolve_api_key()
    if not api_key:
        return

    memories = fetch_recent_memories(api_key)
    if not memories:
        return

    timeline = format_timeline(memories)
    if timeline:
        print(timeline, end="")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
    sys.exit(0)

"""Tests for write-path identity handling and API key resolution.

Verifies that all scripts writing to the Mem0 API:
1. Do NOT send user_id or app_id in the body (identity is resolved from the API key)
2. Do NOT include project_id in metadata
3. Include branch in metadata when available
4. Use resolve_api_key() for key resolution with userConfig fallback
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch


def test_auto_import_post_memory_omits_identity():
    """auto_import.post_memory does not send user_id/app_id (resolved from API key)."""
    from auto_import import post_memory

    captured = {}

    def mock_urlopen(req, timeout=None):
        body = json.loads(req.data.decode("utf-8"))
        captured.update(body)
        resp = MagicMock()
        resp.status = 200
        resp.__enter__ = lambda s: s
        resp.__exit__ = MagicMock(return_value=False)
        return resp

    with patch("urllib.request.urlopen", side_effect=mock_urlopen):
        result = post_memory(
            api_key="test-key",
            content="test content",
            filename="CLAUDE.md",
            project_id="my-project",
            branch="main",
        )

    assert result is True
    assert "user_id" not in captured
    assert "app_id" not in captured
    assert "project_id" not in captured.get("metadata", {})
    assert captured["metadata"]["type"] == "project_profile"
    assert captured["metadata"]["branch"] == "main"
    assert captured["infer"] is False


def test_auto_import_post_memory_omits_empty_branch():
    """auto_import.post_memory skips branch in metadata when empty."""
    from auto_import import post_memory

    captured = {}

    def mock_urlopen(req, timeout=None):
        body = json.loads(req.data.decode("utf-8"))
        captured.update(body)
        resp = MagicMock()
        resp.status = 200
        resp.__enter__ = lambda s: s
        resp.__exit__ = MagicMock(return_value=False)
        return resp

    with patch("urllib.request.urlopen", side_effect=mock_urlopen):
        post_memory("key", "content", "FILE.md", "proj", branch="")

    assert "branch" not in captured.get("metadata", {})


def test_on_pre_compact_store_memory_omits_identity():
    """on_pre_compact.store_memory does not send user_id/app_id."""
    from on_pre_compact import store_memory

    captured = {}

    def mock_urlopen(req, timeout=None):
        body = json.loads(req.data.decode("utf-8"))
        captured.update(body)
        resp = MagicMock()
        resp.status = 200
        resp.__enter__ = lambda s: s
        resp.__exit__ = MagicMock(return_value=False)
        return resp

    with patch("urllib.request.urlopen", side_effect=mock_urlopen):
        result = store_memory(
            api_key="test-key",
            content="session state content",
            source="pre-compaction",
            session_id="sess-123",
            branch="feat/auth",
        )

    assert result is True
    assert "user_id" not in captured
    assert "app_id" not in captured
    assert "project_id" not in captured.get("metadata", {})
    assert captured["metadata"]["type"] == "session_state"
    assert captured["metadata"]["source"] == "pre-compaction"
    assert captured["metadata"]["branch"] == "feat/auth"
    assert "expiration_date" in captured


def test_capture_compact_summary_store_omits_identity():
    """capture_compact_summary.store_summary does not send user_id/app_id."""
    from capture_compact_summary import store_summary

    captured = {}

    def mock_urlopen(req, timeout=None):
        body = json.loads(req.data.decode("utf-8"))
        captured.update(body)
        resp = MagicMock()
        resp.status = 200
        resp.__enter__ = lambda s: s
        resp.__exit__ = MagicMock(return_value=False)
        return resp

    with patch("urllib.request.urlopen", side_effect=mock_urlopen):
        result = store_summary(
            api_key="test-key",
            summary="compact summary text",
            session_id="sess-456",
            branch="main",
        )

    assert result is True
    assert "user_id" not in captured
    assert "app_id" not in captured
    assert "project_id" not in captured.get("metadata", {})
    assert captured["metadata"]["type"] == "compact_summary"
    assert captured["metadata"]["branch"] == "main"
    assert captured["infer"] is True
    assert "expiration_date" in captured


def test_no_identity_or_project_id_anywhere():
    """Ensure none of the write functions send user_id/app_id or metadata.project_id."""
    from auto_import import post_memory
    from capture_compact_summary import store_summary
    from on_pre_compact import store_memory

    bodies = []

    def mock_urlopen(req, timeout=None):
        body = json.loads(req.data.decode("utf-8"))
        bodies.append(body)
        resp = MagicMock()
        resp.status = 200
        resp.__enter__ = lambda s: s
        resp.__exit__ = MagicMock(return_value=False)
        return resp

    with patch("urllib.request.urlopen", side_effect=mock_urlopen):
        post_memory("k", "c", "f", "proj", "br")
        store_memory("k", "c", "src", "sid", "br")
        store_summary("k", "s", "sid", "br")

    for i, body in enumerate(bodies):
        metadata = body.get("metadata", {})
        assert "project_id" not in metadata, f"Write function #{i} still has metadata.project_id"
        assert "user_id" not in body, f"Write function #{i} still sends user_id"
        assert "app_id" not in body, f"Write function #{i} still sends app_id"


def test_resolve_api_key_prefers_env_var(monkeypatch):
    """resolve_api_key returns MEM0_API_KEY when both are set."""
    from _identity import resolve_api_key

    monkeypatch.setenv("MEM0_API_KEY", "direct-key")
    monkeypatch.setenv("CLAUDE_PLUGIN_OPTION_MEM0_API_KEY", "fallback-key")
    assert resolve_api_key() == "direct-key"


def test_resolve_api_key_falls_back_to_plugin_option(monkeypatch):
    """resolve_api_key falls back to CLAUDE_PLUGIN_OPTION_MEM0_API_KEY."""
    from _identity import resolve_api_key

    monkeypatch.delenv("MEM0_API_KEY", raising=False)
    monkeypatch.setenv("CLAUDE_PLUGIN_OPTION_MEM0_API_KEY", "fallback-key")
    assert resolve_api_key() == "fallback-key"


def test_resolve_api_key_returns_empty_when_neither_set(monkeypatch):
    """resolve_api_key returns empty string when no key is available."""
    from _identity import resolve_api_key

    monkeypatch.delenv("MEM0_API_KEY", raising=False)
    monkeypatch.delenv("CLAUDE_PLUGIN_OPTION_API_KEY", raising=False)
    monkeypatch.delenv("CLAUDE_PLUGIN_OPTION_MEM0_API_KEY", raising=False)
    monkeypatch.setattr("_identity._extract_key_from_shell_profiles", lambda: "")
    assert resolve_api_key() == ""


def test_resolve_api_key_falls_back_to_shell_profile(monkeypatch):
    """resolve_api_key extracts key from shell profile when env vars are empty."""
    from _identity import resolve_api_key

    monkeypatch.delenv("MEM0_API_KEY", raising=False)
    monkeypatch.delenv("CLAUDE_PLUGIN_OPTION_API_KEY", raising=False)
    monkeypatch.delenv("CLAUDE_PLUGIN_OPTION_MEM0_API_KEY", raising=False)
    monkeypatch.setattr("_identity._extract_key_from_shell_profiles", lambda: "m0-from-profile")
    assert resolve_api_key() == "m0-from-profile"
/**
 * Memory scope resolution — ported from the pi-agent plugin's scoping model.
 *
 * Identity (user_id) is owned by the backend: it is resolved from the X-API-Key
 * on every request, so a client never sends it. Scope only decides which
 * *labels* a call is narrowed to:
 *   - "project" (default): this repo only        -> { app_id }
 *   - "session": this run only                   -> { app_id, run_id }
 *   - "global": across ALL of the key's projects -> { app_id: "*" }
 *
 * Mirrors pi-agent/src/memory/scoping.ts (resolveSearchFilters / resolveAddParams)
 * so the OpenCode plugin exposes scope the same way: as a per-call tool parameter,
 * not a stateful "switch project" command.
 */

export type Scope = "project" | "session" | "global";

/** Filters for `search` / `get_memories` at the given scope. */
export function scopeSearchFilters(
  scope: Scope,
  appId: string,
  runId: string,
): Record<string, string> {
  switch (scope) {
    case "session":
      return { app_id: appId, run_id: runId };
    case "global":
      return { app_id: "*" };
    case "project":
    default:
      return { app_id: appId };
  }
}

/** Label params for `add` / `delete_all` at the given scope. */
export function scopeWriteParams(
  scope: Scope,
  appId: string,
  runId: string,
): { app_id?: string; run_id?: string } {
  switch (scope) {
    case "session":
      return { app_id: appId, run_id: runId };
    case "global":
      return {};
    case "project":
    default:
      return { app_id: appId };
  }
}

/** Normalize an arbitrary value to a valid Scope (defaults to "project"). */
export function asScope(value: unknown): Scope {
  return value === "session" || value === "global" ? value : "project";
}

/**
 * Resolve the persisted default scope from a parsed `~/.mem0/settings.json`
 * object. This is the user-changeable default applied to memory operations when
 * no explicit `scope` is passed (set via the `mem0-scope` skill). Falls back to
 * "project" when unset or invalid.
 */
export function resolveDefaultScope(
  settings: Record<string, unknown> | null | undefined,
): Scope {
  return asScope(settings?.default_scope);
}

/** Guidance injected so the agent uses `global` only when explicitly asked. */
export const SCOPE_GUIDANCE =
  'Memory tools accept an optional `scope`: omit it (or "project") for normal queries; use "session" to limit to the current run; use "global" ONLY when the user explicitly asks to search across all their projects in this workspace.';

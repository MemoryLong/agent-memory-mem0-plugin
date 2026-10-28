import { describe, expect, test } from "bun:test";
import { scopeSearchFilters, scopeWriteParams, asScope, resolveDefaultScope } from "./scope";

describe("memory scope (pi-agent parity)", () => {
  test("project scope = this repo", () => {
    expect(scopeSearchFilters("project", "app", "run")).toEqual({
      app_id: "app",
    });
    expect(scopeWriteParams("project", "app", "run")).toEqual({
      app_id: "app",
    });
  });

  test("session scope adds run_id", () => {
    expect(scopeSearchFilters("session", "app", "run")).toEqual({
      app_id: "app",
      run_id: "run",
    });
    expect(scopeWriteParams("session", "app", "run")).toEqual({
      app_id: "app",
      run_id: "run",
    });
  });

  test("global scope spans all the key's projects", () => {
    // No user_id anywhere: the backend derives it from the key.
    expect(scopeSearchFilters("global", "app", "run")).toEqual({ app_id: "*" });
    // global writes drop app_id so the memory is user-wide, not project-bound
    expect(scopeWriteParams("global", "app", "run")).toEqual({});
  });

  test("default scope is project when settings are absent", () => {
    expect(resolveDefaultScope(null)).toBe("project");
    expect(resolveDefaultScope(undefined)).toBe("project");
    expect(resolveDefaultScope({})).toBe("project");
  });

  test("default scope reads default_scope from settings", () => {
    expect(resolveDefaultScope({ default_scope: "session" })).toBe("session");
    expect(resolveDefaultScope({ default_scope: "global" })).toBe("global");
    expect(resolveDefaultScope({ default_scope: "project" })).toBe("project");
  });

  test("default scope normalizes an invalid default_scope to project", () => {
    expect(resolveDefaultScope({ default_scope: "nonsense" })).toBe("project");
    expect(resolveDefaultScope({ default_scope: 42 })).toBe("project");
  });

  test("asScope normalizes unknown values to project", () => {
    expect(asScope("global")).toBe("global");
    expect(asScope("session")).toBe("session");
    expect(asScope("project")).toBe("project");
    expect(asScope("nonsense")).toBe("project");
    expect(asScope(undefined)).toBe("project");
  });
});

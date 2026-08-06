# MCP 2026-07-28 / Python SDK v2 — Fleet Migration Plan

**Status: hold on `mcp` 1.x. No fleet server is broken, and nothing needs to move today.**
Filed 2026-08-06, covering all 17 repos in the KG fleet.

---

## Verdict

Two things landed on 2026-07-28: the `2026-07-28` MCP **specification** (the stateless
rewrite) and the **`mcp` 2.0.0 Python SDK**. They are usually discussed together, but for
this fleet they are not the same event:

- **The spec rewrite is a non-event here.** Every KG server we ship is a plain stdio tool
  server. Sessions, `Mcp-Session-Id`, the `initialize` handshake, SSE resumability, and
  horizontal scale-out — the things the revision changes — are HTTP-transport concerns
  that stdio never had. No server in the fleet uses Sampling, Roots, Logging
  notifications, elicitation, resource subscriptions, or `Context` injection, which is
  the entire set of newly-deprecated features.
- **The SDK 2.0 rename is the real work**, and for 15 of 17 repos it is a two-line diff.

Every repo already pins `mcp>=1.0.0,<2`, so `pip install` still resolves to the v1 line
(1.29.0, released the same day as 2.0.0 and still maintained). Nothing installs 2.0 by
accident. **The pins are the plan** until one of the triggers below fires.

---

## What actually changed

### The specification (`2026-07-28`)

| Change | Effect on this fleet |
|---|---|
| `initialize` / `notifications/initialized` handshake removed; protocol version + client capabilities travel in `_meta` per request | None — SDK-internal |
| Protocol-level sessions and `Mcp-Session-Id` removed from Streamable HTTP | None — stdio only |
| New `server/discover` RPC (servers **MUST** implement) | None — SDK provides it |
| `resources/subscribe` + HTTP GET → `subscriptions/listen` | None — no server subscribes |
| `ping`, `logging/setLevel`, `notifications/roots/list_changed` removed | None — unused |
| Server-initiated requests → Multi Round-Trip Requests (`InputRequiredResult`) | None — unused |
| All results carry a required `resultType` | Handled by the SDK's types |
| `ttlMs` + `cacheScope` required on list results | Opportunity, not a break — see Phase 3 |
| **Roots, Sampling, Logging deprecated** (≥12-month window) | None — unused |
| **HTTP+SSE transport deprecated** | **Applies.** Five CLIs still offer `--transport sse` |
| OAuth Dynamic Client Registration deprecated in favour of Client ID Metadata Documents | None — no auth surface |

### The Python SDK (`mcp` 2.0.0)

Verified by unpacking the published wheel, not from release notes:

- **`mcp.server.fastmcp` is gone.** `FastMCP` → **`MCPServer`**, living at
  `mcp.server.mcpserver` and re-exported from `mcp.server`. The decorator API
  (`@mcp.tool()`) carries over unchanged.
- **The low-level `Server` survives, but its decorators do not.**
  `@server.list_tools()` / `@server.call_tool()` are replaced by constructor kwargs:
  ```python
  on_list_tools: (ServerRequestContext, PaginatedRequestParams | None) -> ListToolsResult
  on_call_tool:  (ServerRequestContext, CallToolRequestParams) -> CallToolResult | InputRequiredResult
  ```
  `create_initialization_options()`, `stdio_server()`, and `server.run(r, w, opts)` are
  all unchanged.
- `host`/`port` moved from the constructor to `run()` — `MCPServer("x", port=9000)` now
  raises `TypeError`. Irrelevant to us: every constructor in the fleet passes only `name`
  and `instructions`.
- Python attributes are snake_case (`result.is_error`, `tool.input_schema`); the wire
  stays camelCase.
- Wire types split into a standalone **`mcp-types`** distribution. `mcp.types` mirrors it
  exactly, so `from mcp.types import TextContent` still works.
- Synchronous tool functions now run on worker threads instead of blocking the loop.
- **New dependency surface:** `httpx2`, `pydantic>=2.12`, `opentelemetry-api`,
  `jsonschema`. This — not the code — is the resolution risk. `mcp` 1.x depends on
  `httpx<1.0` and `pydantic>=2.11`.
- A v2 server speaks **both protocol eras** on one endpoint (`serve_dual_era_loop`); there
  is no flag to set and no second deployment.

---

## Fleet inventory

Measured 2026-08-06 across all 17 repos.

| Group | Repos | What they import | Cost |
|---|---|---|---|
| **A — bundled FastMCP** | `doc_kg` (4 tools), `memory_kg` (4), `diary_kg` (3), `metabo_kg` (factory), `pycode_kg` (19), `tscode_kg` (19) | `from mcp.server.fastmcp import FastMCP` | Mechanical — 1 import + 1 symbol per repo |
| **B — low-level `Server`** | `KGRAG` (22 tools), `agent_kg` (10) | `from mcp.server import Server` + decorators | Real work — handler registration rewrite |
| **C — standalone FastMCP** | `gutenberg_kg` (2 tools) | `from fastmcp import FastMCP` (`>=3,<4`) | Blocked on FastMCP 4 going stable |
| **D — no MCP surface** | `ftree_kg`, `KG_utils`, `waverider`, `quiltwright`, `pdb2pov`, `proteusPy`, `bridge.js`, `POV` | — | None |

`ftree_kg` and `KG_utils` carry MCP *client* configuration docs only; nothing to migrate.

---

## Phased plan

### Phase 0 — now, on `mcp` 1.x (no v2 dependency)

1. **Keep the `<2` upper bounds.** They are working as designed. Bump the *floor* to
   `mcp>=1.29,<2` only after reading 1.29.0's release notes — do not bump blind.
2. **Retire `--transport sse`.** `doc_kg`, `memory_kg`, `diary_kg`, `pycode_kg` and
   `tscode_kg` all declare `choices=["stdio", "sse"]`. HTTP+SSE is now formally
   Deprecated, and `streamable-http` has been supported on `mcp` 1.x for many releases.
   Add it as the choice, keep `sse` as a hidden alias that warns. **This is the only
   time-sensitive item in the whole plan**, and it needs no v2.
3. **Add a canary CI job** per MCP-bearing repo: install `mcp==2.0.*` and run
   `tests/test_mcp_server.py`. It fails today by design — mark it non-blocking. It is the
   tripwire that reports when the rename is the only thing standing between us and v2.

### Phase 1 — pilot one Group A repo

Use `doc_kg` or `memory_kg` (4 tools each, ~190 lines):

```diff
- from mcp.server.fastmcp import FastMCP
+ from mcp.server import MCPServer

- mcp = FastMCP(
+ mcp = MCPServer(
      "dockg",
      instructions=(...),
  )
```

`@mcp.tool()` and `mcp.run(transport="stdio")` are untouched. Then update the test helper
(each `tests/test_mcp_server.py` names `FastMCP` in its docstring and reaches for
`list_tools()`), and — the actual point of the pilot — **resolve the lockfile against
`httpx2` and `pydantic>=2.12`**. If that resolution is clean, the rest of Group A is
bookkeeping.

### Phase 2 — roll Group A

`diary_kg`, `metabo_kg` (its `FastMCP` is built inside a factory at `mcp_tools.py:636`),
then `pycode_kg` and `tscode_kg` last. The two 19-tool servers are still a two-line diff;
they go last only because they have the most surface to smoke-test.

Per the MCP-instruction-sync rule in `pycode_kg` and `tscode_kg`, any change to the tool
API must update the `MCPServer(..., instructions=...)` block in the same commit. A pure
rename does not change the tool API, so the instructions text stays as-is.

### Phase 3 — Group B (`KGRAG`, `agent_kg`)

The only genuine engineering, and it is contained. `KGRAG`'s `_make_server()` already
funnels everything through a single name-dispatch `call_tool`, so the port is a signature
change plus a result wrapper — the 22 tool bodies do not move.

```diff
- def _make_server(registry_path: Path | None = None) -> Server:
-     server = Server("kgrag")
-     reg_path = registry_path or default_registry_path()
-
-     @server.list_tools()
-     async def list_tools() -> list[Tool]:
-         return [Tool(name="kgrag_stats", ...), ...]
-
-     @server.call_tool()
-     async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
-         if name == "kgrag_stats":
-             ...
-             return [TextContent(type="text", text=json.dumps(result, indent=2))]
-
-     return server
+ def _make_server(registry_path: Path | None = None) -> Server:
+     reg_path = registry_path or default_registry_path()
+
+     async def list_tools(ctx, params) -> types.ListToolsResult:
+         return types.ListToolsResult(tools=[Tool(name="kgrag_stats", ...), ...])
+
+     async def call_tool(ctx, params) -> types.CallToolResult:
+         name, arguments = params.name, params.arguments or {}
+         if name == "kgrag_stats":
+             ...
+             return types.CallToolResult(
+                 content=[TextContent(type="text", text=json.dumps(result, indent=2))]
+             )
+
+     return Server("kgrag", on_list_tools=list_tools, on_call_tool=call_tool)
```

Notes that save time:

- `result_type` defaults to `"complete"` on the SDK's superset types, so handlers do not
  set it.
- `ListToolsResult` inherits `ttl_ms=0` / `cache_scope="private"` — valid on the wire
  without action. The registry tool list is stable between builds, so a non-zero `ttl_ms`
  here is a cheap client-side caching win once the port lands.
- Error returns keep working, but `is_error=True` on `CallToolResult` is now the right
  spelling for the `{"error": ...}` payloads the dispatcher returns today.
- `main()` and the `stdio_server()` block are unchanged.
- `tests/test_mcp_server.py` asserts on the low-level `Server` shape and imports
  `ListToolsRequest` directly; it will need the same treatment.

### Phase 4 — `gutenberg_kg`

Wait for FastMCP 4 to go stable (4.0.0b1 shipped 2026-07-28; 3.4.6 is the current stable
and is what the `>=3,<4` pin resolves to). FastMCP 4 adds 2026-07-28 support with the same
dual-era negotiation, keeping the decorator API. Then relax to `fastmcp>=4,<5`.

---

## Triggers — what should pull this forward

None of these have fired as of 2026-08-06:

- `mcp` 1.x stops receiving security fixes.
- A Claude client (Code, Desktop, connectors) starts requiring the 2026-07-28 era. The
  rollout is announced but undated, and the spec requires clients to fall back for
  earlier-era stdio servers.
- We want the Tasks extension, Multi Round-Trip Requests, or MCP Apps.
- We want to serve a KG over horizontally-scaled Streamable HTTP — the actual payoff of
  statelessness, and irrelevant while everything is stdio.

Absent a trigger, migrating nine servers buys nothing but risk.

---

## How these facts were established

Release notes for a rewrite this size are not a reliable source, so the SDK claims above
were checked against the artifact:

- `mcp` 2.0.0 and `mcp-types` 2.0.0 wheels downloaded from PyPI and unpacked; module
  layout, `MCPServer.__init__`, `Server.__init__`, `run()` overloads, and the
  `CallToolResult` / `ListToolsResult` / `CacheableResult` field defaults read directly
  from source.
- Version and dependency metadata read from the PyPI JSON API (`mcp` 1.29.0 and 2.0.0 both
  published 2026-07-28; `fastmcp` 3.4.6 stable, 4.0.0b1 pre-release).
- Fleet usage inventoried by grep across all 17 working copies.

## Sources

- [2026-07-28 specification changelog](https://modelcontextprotocol.io/specification/2026-07-28/changelog)
- [Specification announcement](https://blog.modelcontextprotocol.io/posts/2026-07-28/)
- [Feature lifecycle and deprecation policy](https://modelcontextprotocol.io/community/feature-lifecycle)
- [Pydantic — MCP Python SDK v2](https://pydantic.dev/articles/mcp-python-sdk-v2-beta)
- [FastMCP releases](https://gofastmcp.com/development/releases)
- [Real Python — MCP Gets Its Biggest Rewrite, August 2026](https://realpython.com/python-news-august-2026/)

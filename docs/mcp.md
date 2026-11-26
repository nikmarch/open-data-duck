# Open Data Duck with MCP clients

Open Data Duck can be used from Claude, Hermes, Cursor, VS Code, and other MCP-compatible clients in two complementary ways:

1. **DuckDB query execution through an existing DuckDB MCP server.** Use this when the agent should run real SQL against ODD table facades.
2. **ODD registry discovery through `open-data-duck-mcp`.** Use this when the agent needs source metadata, table references, validation SQL, and cached schema hints without opening a DuckDB query surface.

The first path is the recommended spike for real open-data questions. The second path is ODD-specific context for better source selection.

## Query execution with MotherDuck's DuckDB MCP server

The most practical generic DuckDB MCP server today is MotherDuck's local server, published as `mcp-server-motherduck`. It supports local DuckDB, stdio and HTTP transports, result caps, query timeout, and startup SQL.

Compatibility note: the ODD pre-community repository currently publishes DuckDB `v2.0.0` extension artifacts. A query MCP server must run a DuckDB runtime that can load those artifacts, or ODD must publish artifacts for that server's DuckDB version. In the current smoke test, `mcp-server-motherduck==1.1.1` used DuckDB `v1.5.6` and failed to install ODD from the custom repository because no `v1.5.6` ODD artifact exists. The same SQL succeeds in DuckDB `v2.0.0`, so the remaining gap is MCP server/runtime packaging, not the ODD facade SQL.

Use startup SQL to install/load ODD and attach the ODD catalog once the MCP server's DuckDB runtime matches an ODD artifact version:

```bash
uvx mcp-server-motherduck \
  --db-path :memory: \
  --read-write \
  --max-rows 100 \
  --max-chars 50000 \
  --query-timeout 30 \
  --init-sql "
    FORCE INSTALL open_data_duck FROM 'https://nikmarch.github.io/open-data-duck/extensions';
    LOAD open_data_duck;
    SET s3_region='us-west-2';
    ATTACH ':memory:' AS odd (TYPE open_data_duck);
  "
```

This gives the client a DuckDB SQL tool. The agent can query `odd.index`, inspect `odd.tables`, and read table facades such as `odd.overturemaps.latest.building`.

### Claude Code

```bash
claude mcp add --scope user odd-duckdb --transport stdio -- \
  uvx mcp-server-motherduck \
    --db-path :memory: \
    --read-write \
    --max-rows 100 \
    --max-chars 50000 \
    --query-timeout 30 \
    --init-sql "FORCE INSTALL open_data_duck FROM 'https://nikmarch.github.io/open-data-duck/extensions'; LOAD open_data_duck; SET s3_region='us-west-2'; ATTACH ':memory:' AS odd (TYPE open_data_duck);"
```

### Hermes

Add an MCP server entry to the active Hermes profile config:

```yaml
mcp_servers:
  odd_duckdb:
    command: uvx
    args:
      - mcp-server-motherduck
      - --db-path
      - :memory:
      - --read-write
      - --max-rows
      - "100"
      - --max-chars
      - "50000"
      - --query-timeout
      - "30"
      - --init-sql
      - >-
        FORCE INSTALL open_data_duck FROM 'https://nikmarch.github.io/open-data-duck/extensions';
        LOAD open_data_duck;
        SET s3_region='us-west-2';
        ATTACH ':memory:' AS odd (TYPE open_data_duck);
```

Restart the MCP-capable client after changing its config.

## Real question example

Question:

> What Overture Maps building records are available near Wasilla, Alaska? Return only a tiny bounded sample and show the SQL.

A safe first discovery query is:

```sql
SELECT table_reference, source_id, reader, path
FROM odd.tables
WHERE table_reference = 'odd.overturemaps.latest.building'
LIMIT 1;
```

Then run a tight bounded sample. Overture tables are large, so keep bbox filters narrow and keep `LIMIT` small:

```sql
SELECT id, bbox
FROM odd.overturemaps.latest.building
WHERE bbox.xmin <= -149.40
  AND bbox.xmax >= -149.42
  AND bbox.ymin <= 61.59
  AND bbox.ymax >= 61.58
LIMIT 5;
```

The agent response should include the SQL it used and the small returned result, or the exact runtime blocker if the local DuckDB/MCP environment cannot fetch the remote source.

## ODD registry MCP server

ODD also ships a small MCP server for source discovery:

```bash
uv sync --extra mcp
uv run open-data-duck-mcp
```

Its tools are metadata-oriented:

- `search_sources_tool` — search ODD registry sources.
- `get_source` — return one source with AI-friendly table metadata and optional SQL.
- `get_source_sql` — return ODD facade SQL or direct-vs-ODD validation SQL.
- `get_source_schema` — return cached DuckDB-discovered schema manifest data.

Use this next to a DuckDB query MCP server when the client supports multiple MCP servers. The registry server helps the agent choose the right ODD table; the DuckDB MCP server executes real SQL.

Hermes config for the registry server from a local checkout:

```yaml
mcp_servers:
  open_data_duck_registry:
    command: uv
    args:
      - run
      - --project
      - /absolute/path/to/open-data-duck
      - --extra
      - mcp
      - open-data-duck-mcp
```

## Guardrails

- Keep `--max-rows`, `--max-chars`, and `--query-timeout` set for agent use.
- Use tight filters before querying large Overture, Census, or NOAA-backed facades.
- Ask agents to inspect `odd.tables` and copy `table_reference` exactly before querying.
- Self-hosted DuckDB MCP `read-only` mode is not enough for untrusted third-party access by itself. In plain words: read-only mode is not enough. DuckDB can still expose local filesystem, settings, and extension behavior unless the host is locked down with DuckDB security settings and process isolation.
- Do not expose a local unrestricted DuckDB MCP server to public clients.

## Future ODD-native query MCP

A generic DuckDB MCP server is enough for the first usable path. If agent UX needs to become more ODD-native, add a separate thin query server with tools such as:

- `odd_search`
- `odd_table_info`
- `odd_sample`
- `odd_query`

That server should enforce read-only ODD facade queries, bounded results, timeouts, and provenance-first responses instead of exposing arbitrary DuckDB SQL.

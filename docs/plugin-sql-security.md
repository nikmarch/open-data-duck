# Source SQL security boundary

Open Data Duck treats registry-provided SQL as untrusted input.

Today that untrusted SQL is limited to the release-discovery and table-discovery snippets embedded in `registry/sources.yml`:

- `release.latest.resolve_sql`
- `duckdb.tables.discover_sql`

User-facing SQL returned by `open_data_sql()` and `open_data_validation_sql()` is only rendered for the caller to inspect or run. Open Data Duck does not execute those recipes on the caller's behalf.

## Threat model

A malicious or compromised source definition must not be able to read or reuse secrets from the caller's live DuckDB session. This includes:

- temp tables or views in the caller's session;
- attached databases or schemas that may contain private data;
- DuckDB user variables or settings that may contain tokens;
- DuckDB secrets/credentials;
- arbitrary local database files attached by untrusted SQL.

## Enforced boundary

When Open Data Duck needs to run source-controlled discovery SQL, it now runs it in a fresh in-memory DuckDB database instead of the caller's `DatabaseInstance`.

That isolated database has no access to the caller's:

- attached databases;
- temp objects;
- user variables;
- session settings;
- registered secrets.

Before execution, discovery SQL is also constrained to a single `SELECT`/`WITH` query. The guard rejects statement chaining and blocks session- or filesystem-mutating tokens such as `ATTACH`, `LOAD`, `INSTALL`, `CREATE`, `COPY`, `SET`, `RESET`, and `PRAGMA`. It also blocks explicit session/secret inspection through `getvariable`, `current_setting`, `duckdb_settings`, and `duckdb_secrets`.

## Allowed work

Discovery SQL may read public source metadata needed to resolve releases or list tables, for example public HTTPS/S3 catalogs through DuckDB reader functions.

The table facade itself still binds approved discovered table paths to DuckDB readers such as `read_parquet`, `read_csv`, `read_json`, and `st_read`. Those are data-access paths, not source-controlled control statements.

## Limitations

This boundary is intentionally conservative, not a complete SQL sandbox for arbitrary plugins. If future sources need more powerful plugin code, they should get a separate reviewed capability model instead of widening discovery SQL privileges.

# Security Policy

Open Data Duck is a pre-community DuckDB extension and source-registry project. Security reports are welcome.

## Supported versions

Until the project reaches a stable community-extension release, security support applies to the current `main` branch and the most recent published pre-community build.

Older experimental builds may not receive fixes.

## Report a vulnerability

Do not open a public issue for vulnerabilities, secrets, exploit details, or private data.

Use GitHub private vulnerability reporting if it is available for this repository. If it is not available, contact the maintainer through the repository with a minimal public note asking for a private security contact, without exploit details.

Include, if safe:

- affected version, commit, or release tag;
- operating system and DuckDB version;
- steps to reproduce;
- expected and actual behavior;
- impact and whether secrets, local files, or private databases can be exposed.

## Source SQL boundary

Open Data Duck treats source-controlled discovery SQL as untrusted. Discovery SQL should run in a separate DuckDB connection and must not read caller session secrets, attached databases, local private files, or user data.

See [docs/plugin-sql-security.md](docs/plugin-sql-security.md) for the current boundary.

Report any way for registry metadata, source SQL, table discovery, replacement scans, package installation, or extension loading to bypass that boundary.

## Public issues and pull requests

Do not include secrets, tokens, credentials, private data, proprietary data, or exploit payloads in public issues, pull requests, examples, tests, or CI logs.

If sensitive information is exposed, remove it where possible and rotate affected credentials. Git history and third-party caches may retain copies.

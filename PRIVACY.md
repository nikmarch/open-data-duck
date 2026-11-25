# Privacy Policy

Last updated: 2026-11-25

Open Data Duck is an open-source DuckDB extension, Python CLI, documentation set, and source registry. It does not operate user accounts for the project and does not intentionally collect application analytics through the repository tools.

This is a project privacy notice, not legal advice.

## Local use

When you run Open Data Duck locally, DuckDB queries and CLI commands run in your own environment.

Open Data Duck does not intentionally send your local tables, attached databases, DuckDB secrets, credentials, query history, or files to the project maintainers.

Some commands query public network resources because that is the purpose of the tool. For example, Open Data Duck may request metadata or data from GitHub Pages, GitHub releases, public S3 buckets, public HTTPS URLs, or upstream dataset providers.

## Third-party logs

Network requests may create logs with third parties, including:

- GitHub and GitHub Pages;
- PyPI or package mirrors;
- DuckDB extension distribution infrastructure;
- upstream dataset publishers;
- cloud providers hosting public datasets;
- your own network, proxy, VPN, DNS, or cloud environment.

Those providers control their own logs and privacy policies. Open Data Duck does not control them.

## Public project spaces

GitHub issues, pull requests, discussions, comments, commit metadata, CI logs, and similar project spaces are public by default.

Do not post secrets, credentials, private datasets, personal data, access tokens, proprietary query results, or security vulnerabilities in public issues or pull requests.

If you accidentally publish sensitive information, remove it if possible and rotate any affected credentials. Git history and third-party caches may still retain copies.

## Source registry metadata

Open Data Duck registry entries describe public data sources, licenses, attribution, table warnings, and query examples. They should not include personal data except where the upstream public dataset itself lawfully publishes public records and the source is appropriate for inclusion under the [data source policy](docs/legal/data-source-policy.md).

## Security reports

Report vulnerabilities privately using [SECURITY.md](SECURITY.md). Do not open public issues for vulnerability details or secrets.

## Changes

This notice may change as the project distribution model changes.

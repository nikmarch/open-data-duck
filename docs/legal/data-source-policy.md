# Data source policy

Open Data Duck is a DuckDB-native facade over authoritative public datasets. It is not a data broker, scraper collection, or mirror of upstream datasets.

This policy defines what can be added to the source registry.

## Inclusion rules

A source may be promoted only when it has:

- an authoritative publisher or maintainer;
- a public homepage, catalog record, or authority URL;
- a clear license or terms URL;
- attribution text or a documented statement that attribution is not required;
- public anonymous access or another access pattern that is explicitly allowed for Open Data Duck users;
- a bounded DuckDB-readable path or a clearly labeled connector blocker;
- table-level metadata explaining what one row means;
- warnings for scan size, rate limits, costs, geography/time limits, data quality, or compliance issues where relevant.

Queryable sources should also include validation SQL that compares the Open Data Duck facade with the direct upstream reader path.

## Sources that do not belong

Do not add sources that require or encourage:

- private accounts, credentials, API keys, paid access, or non-public permissions;
- bypassing access controls, export controls, rate limits, robots rules, or terms of service;
- scraping where the source terms do not allow it;
- use of leaked, gray-area, unofficial, or unauthorized mirrors;
- copying large upstream datasets into this repository;
- inventing license or attribution language when the publisher is unclear.

If a source is valuable but the license or terms are unclear, mark it for license review and keep it blocked until a maintainer resolves it.

## Upstream terms control

Open Data Duck records license URLs, attribution, and warnings to help users comply with source requirements. That metadata is not a legal opinion.

The upstream publisher's license, terms, attribution rules, and access policies control use of the data. If Open Data Duck metadata is wrong or stale, fix or remove the registry entry.

## Attribution

Every source should capture the attribution expected by the publisher. When attribution is unknown, the source should not be treated as ready.

Attribution metadata should be specific enough for users to copy into notebooks, applications, reports, or downstream documentation.

## Removal and correction

A source should be corrected, blocked, deprecated, or removed when:

- the license or terms no longer allow the documented use;
- attribution is missing or wrong;
- access becomes private, paid, key-gated, or unstable;
- the source publisher asks for removal or correction;
- validation fails and the issue is not temporary;
- the registry entry points to an unofficial mirror when an authoritative path exists.

Open a GitHub issue or pull request for corrections. Use [SECURITY.md](../../SECURITY.md) for private vulnerability reports.

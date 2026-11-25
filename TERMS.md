# Terms of Use

Last updated: 2026-11-25

These terms describe how the Open Data Duck project, documentation, examples, registry metadata, command-line tools, and pre-community DuckDB extension builds may be used. They are plain project terms, not legal advice.

## Software license

Open Data Duck source code is licensed under the MIT License. See [LICENSE](LICENSE).

The MIT License controls your rights to copy, modify, distribute, and use the software. These terms do not replace the MIT License.

## What Open Data Duck does

Open Data Duck helps users find and query authoritative public datasets from DuckDB. It maps friendly table names to upstream public data sources and query recipes.

Open Data Duck does not sell, mirror, or republish the upstream datasets. Most data remains hosted by third-party publishers such as government agencies, public-data portals, or other data providers.

## Pre-community extension builds

Open Data Duck is currently distributed as a pre-community DuckDB extension build. These builds may be unsigned and may change before community-extension acceptance.

You are responsible for deciding whether a pre-community build is appropriate for your environment. Use production systems carefully.

## Third-party data and upstream terms

Each upstream dataset remains governed by its publisher's license, terms, attribution requirements, privacy notices, and access rules.

Open Data Duck may record source metadata such as license URLs, attribution text, warnings, and validation queries. That metadata is a convenience, not a legal determination. If the upstream publisher's terms conflict with Open Data Duck metadata, the upstream publisher's terms control.

You are responsible for:

- reviewing upstream dataset licenses and terms before using data;
- providing required attribution;
- complying with rate limits, API policies, cloud-provider rules, requester-pays costs, export limits, and local law;
- verifying whether a dataset is suitable for your intended use.

## Acceptable use

Do not use Open Data Duck to:

- access private, paid, key-gated, credential-gated, or unauthorized data;
- bypass access controls, rate limits, robots rules, or publisher restrictions;
- scrape or automate against sources where the source terms do not allow it;
- submit registry sources with unclear or misleading license/attribution information;
- run unlawful, abusive, or harmful queries or workloads;
- publish secrets, credentials, personal data, or non-public data in issues, examples, registry entries, or pull requests.

## No professional advice

Open Data Duck exposes public data for analysis. It does not provide legal, financial, medical, safety, navigation, emergency, or other professional advice.

Do not rely on Open Data Duck output as the sole basis for decisions where errors could cause harm. Verify against the authoritative source.

## No warranty

Open Data Duck is provided as-is. Data may be incomplete, stale, unavailable, incorrectly labeled, or changed by the upstream publisher without notice.

To the fullest extent allowed by law, the project maintainers are not responsible for damages, losses, costs, outages, incorrect analysis, missed attribution, license violations, third-party provider charges, or other problems arising from your use of Open Data Duck or upstream datasets.

## Source removal and corrections

If you believe Open Data Duck points to a source incorrectly, omits required attribution, misstates a license, violates source terms, or should remove a source, open a GitHub issue or contact the maintainers through the repository.

For security issues, follow [SECURITY.md](SECURITY.md) instead of opening a public issue.

## Changes

These terms may change as the project moves toward DuckDB community-extension distribution and broader public use.

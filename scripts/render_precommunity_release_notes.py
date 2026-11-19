#!/usr/bin/env python3
"""Render GitHub release notes for unsigned pre-community extension builds."""

from __future__ import annotations

import argparse
import re
import textwrap


EXTENSION_NAME = "open_data_duck"
DUCKDB_VERSION = "v2.0.0"
REPO = "nikmarch/open-data-duck"
SUPPORTED_PLATFORMS = (
    ("Linux x64", "linux_amd64", f"{EXTENSION_NAME}-{DUCKDB_VERSION}-linux_amd64.duckdb_extension"),
    ("macOS Apple Silicon", "osx_arm64", f"{EXTENSION_NAME}-{DUCKDB_VERSION}-osx_arm64.duckdb_extension"),
)


def validate_release_tag(tag: str) -> str:
    if not re.fullmatch(r"v\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?", tag):
        raise ValueError(f"release tag must look like v0.1.0 or v0.1.0-pre.1, got {tag!r}")
    return tag


def render_release_notes(release_tag: str) -> str:
    release_tag = validate_release_tag(release_tag)
    compatibility_rows = "\n".join(
        f"| {DUCKDB_VERSION} | {label} (`{platform}`) | `{asset}` |"
        for label, platform, asset in SUPPORTED_PLATFORMS
    )
    compatibility_rows = textwrap.indent(compatibility_rows, "        ").lstrip()

    return textwrap.dedent(
        fr"""
        # Open Data Duck {release_tag} pre-community extension

        This is an unsigned pre-community DuckDB extension build for DuckDB {DUCKDB_VERSION}.

        Use this release if you want to test Open Data Duck before it is accepted into DuckDB community extensions. It is not the community build yet, so `INSTALL open_data_duck FROM community;` is not expected to work.

        ## Install and smoke test

        Copy-paste this whole block from the release you want to install:

        ```
        bash <<BASH
        set -euo pipefail

        release_tag={release_tag}
        case \$(uname -s)-\$(uname -m) in
          Darwin-arm64) platform=osx_arm64 ;;
          Linux-x86_64) platform=linux_amd64 ;;
          *) echo unsupported platform: \$(uname -s)-\$(uname -m) >&2; exit 1 ;;
        esac

        curl --fail --location --show-error \\
          --output open_data_duck.duckdb_extension \\
          \$(printf %s h ttps://git hub .com/{REPO}/releases/download/\${{release_tag}}/open_data_duck-{DUCKDB_VERSION}-\${{platform}}.duckdb_extension)

        xattr -dr com.apple.quarantine open_data_duck.duckdb_extension 2>/dev/null || true
        codesign --force --deep --sign - open_data_duck.duckdb_extension 2>/dev/null || true

        duckdb -unsigned :memory: <<SQL
        LOAD './open_data_duck.duckdb_extension';
        SELECT open_data_duck_ping();
        SELECT count(*) > 0 FROM open_data_sources();
        SQL
        BASH
        ```

        Expected output includes:

        ```
        open_data_duck: pong
        true
        ```

        The downloaded file is saved as `open_data_duck.duckdb_extension` on purpose. DuckDB derives the extension entrypoint name from the local filename; loading the versioned asset filename directly can fail.

        ## What is in this release

        | DuckDB version | OS/arch | Release asset |
        | --- | --- | --- |
        {compatibility_rows}

        `SHA256SUMS.txt` is attached for checksum verification.

        ## Tags and prereleases

        Each public prerelease should have a matching Git tag with the same name as this release: `{release_tag}`. Newer prereleases replace older ones as the recommended test build; older prereleases remain only for comparison or rollback.

        These are temporary unsigned binaries while the native extension is in active development. Install commands, release asset names, and supported platforms may change before community extension acceptance.
        """
    ).strip() + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("release_tag", help="release tag, for example v0.1.0-pre.1")
    args = parser.parse_args()
    print(render_release_notes(args.release_tag), end="")


if __name__ == "__main__":
    main()

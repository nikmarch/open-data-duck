from __future__ import annotations

import struct
from pathlib import Path


LOGO = Path("assets/brand/open-data-duck-facing-camera-logo.png")


def test_primary_logo_asset_is_checked_in_png() -> None:
    data = LOGO.read_bytes()

    assert data.startswith(b"\x89PNG\r\n\x1a\n")
    assert struct.unpack(">II", data[16:24]) == (1440, 1520)


def test_primary_logo_asset_is_linked_from_repo_and_docs() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")
    brand_page = Path("docs/brand-assets.md").read_text(encoding="utf-8")

    assert "assets/brand/open-data-duck-facing-camera-logo.png" in readme
    assert "assets/brand/open-data-duck-facing-camera-logo.png" in brand_page

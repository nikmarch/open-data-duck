from __future__ import annotations

import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SITE_SOURCE = ROOT / "site"
BRAND_SOURCE = ROOT / "docs" / "assets" / "brand"


def build_site(output_dir: Path = ROOT / "_site") -> Path:
    if output_dir.exists():
        shutil.rmtree(output_dir)

    shutil.copytree(SITE_SOURCE, output_dir)
    shutil.copytree(BRAND_SOURCE, output_dir / "assets" / "brand")
    (output_dir / ".nojekyll").write_text("", encoding="utf-8")
    return output_dir


if __name__ == "__main__":
    build_site()

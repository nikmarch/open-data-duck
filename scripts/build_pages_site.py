from __future__ import annotations

import shutil
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from odd.registry import load_sources, render_site_index_html
SITE_SOURCE = ROOT / "site"
BRAND_SOURCE = ROOT / "docs" / "assets" / "brand"
REGISTRY = ROOT / "registry" / "sources.yml"


def build_site(output_dir: Path = ROOT / "_site") -> Path:
    if output_dir.exists():
        shutil.rmtree(output_dir)

    shutil.copytree(SITE_SOURCE, output_dir)
    index_html = render_site_index_html(load_sources(REGISTRY))
    (output_dir / "index.html").write_text(index_html, encoding="utf-8")
    shutil.copytree(BRAND_SOURCE, output_dir / "assets" / "brand")
    (output_dir / ".nojekyll").write_text("", encoding="utf-8")
    return output_dir


if __name__ == "__main__":
    build_site()

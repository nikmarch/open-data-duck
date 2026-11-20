#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.11"
# ///
"""Render five Samarkand Overture geometry sample maps.

This is a thin convenience wrapper around scripts/render_spatial_map.py. It keeps
Valiko's Samarkand sample points in one runnable place while the generic renderer
stays reusable for any lat/lon/radius.

Example:
    scripts/render_samarkand_spatial_samples.py \
      --release-tag v0.1.1-pre.2 \
      --output-dir /tmp/odd-samarkand \
      --limit 500
"""

from __future__ import annotations

import argparse
import json
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Spot:
    slug: str
    label: str
    lat: float
    lon: float


SPOTS = [
    Spot("registan", "Registan", 39.6548, 66.9750),
    Spot("bibi-khanym", "Bibi-Khanym", 39.6606, 66.9789),
    Spot("shah-i-zinda", "Shah-i-Zinda", 39.6611, 66.9878),
    Spot("gur-e-amir", "Gur-e-Amir", 39.6486, 66.9696),
    Spot("siab-bazaar", "Siab Bazaar", 39.6625, 66.9805),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render the Samarkand ODD/Overture spatial sample maps.")
    parser.add_argument("--release-tag", default=None, help="GitHub release tag for open_data_duck. Defaults to latest visible release.")
    parser.add_argument("--radius-m", type=float, default=300.0, help="Radius around each sample point in meters.")
    parser.add_argument("--limit", type=int, default=500, help="Maximum features per layer to query/draw for each spot.")
    parser.add_argument("--output-dir", type=Path, default=Path("samarkand-spatial-results"), help="Directory for PNGs, reports, and per-spot caches.")
    parser.add_argument(
        "--spot",
        choices=[spot.slug for spot in SPOTS],
        action="append",
        help="Render only this spot. Can be passed multiple times. Defaults to all five.",
    )
    parser.add_argument("--include-full-addresses", action="store_true", help="Pass through to render_spatial_map.py reports. Map labels stay redacted.")
    return parser.parse_args()


def selected_spots(slugs: list[str] | None) -> list[Spot]:
    if not slugs:
        return SPOTS
    wanted = set(slugs)
    return [spot for spot in SPOTS if spot.slug in wanted]


def main() -> int:
    args = parse_args()
    if args.radius_m <= 0:
        raise SystemExit("--radius-m must be positive")
    if args.limit <= 0:
        raise SystemExit("--limit must be positive")

    script = Path(__file__).with_name("render_spatial_map.py")
    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    rendered = []
    for spot in selected_spots(args.spot):
        output = output_dir / f"{spot.slug}.png"
        report = output_dir / f"{spot.slug}.md"
        workdir = output_dir / f"cache-{spot.slug}"
        command = [
            str(script),
            "--lat",
            str(spot.lat),
            "--lon",
            str(spot.lon),
            "--radius-m",
            str(args.radius_m),
            "--limit",
            str(args.limit),
            "--output",
            str(output),
            "--report",
            str(report),
            "--workdir",
            str(workdir),
        ]
        if args.release_tag:
            command.extend(["--release-tag", args.release_tag])
        if args.include_full_addresses:
            command.append("--include-full-addresses")

        subprocess.run(command, check=True)
        rendered.append({"spot": spot.label, "map": str(output), "report": str(report), "workdir": str(workdir)})

    print(json.dumps({"rendered": rendered}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

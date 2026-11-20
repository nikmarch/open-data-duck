#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.11"
# dependencies = ["pillow>=11.0"]
# ///
"""Render an Open Data Duck spatial-query result map.

Example:
    scripts/render_spatial_map.py \
      --lat 61.60757040082204 \
      --lon -149.38067090928263 \
      --radius-m 100 \
      --release-tag v0.1.0-pre.N \
      --output /tmp/odd-spatial-map.png
"""

from __future__ import annotations

import argparse
import csv
import gzip
import io
import json
import math
import os
import platform
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import textwrap
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from zipfile import ZipFile

from PIL import Image, ImageDraw, ImageFont

REPO = "nikmarch/open-data-duck"
DUCKDB_VERSION = "v2.0.0"
EXTENSION_NAME = "open_data_duck"
TILE_SIZE = 256
USER_AGENT = "OpenDataDuckSpatialMap/1.0 (+https://github.com/nikmarch/open-data-duck)"


@dataclass(frozen=True)
class RuntimePaths:
    workdir: Path
    duckdb: Path
    extension_file: Path
    extension_repo: Path


def run(cmd: list[str], *, input_text: str | None = None, cwd: Path | None = None) -> str:
    proc = subprocess.run(
        cmd,
        input=input_text,
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"command failed ({proc.returncode}): {' '.join(cmd)}\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}"
        )
    return proc.stdout


def request_url(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=60) as response:
        return response.read()


def host_platform() -> tuple[str, str, str]:
    system = platform.system()
    machine = platform.machine()
    if system == "Linux" and machine == "x86_64":
        return "linux_amd64", "duckdb-cli-linux-amd64.tar.gz", "tar.gz"
    if system == "Darwin" and machine == "arm64":
        return "osx_arm64", "duckdb_cli-osx-universal.zip", "zip"
    raise SystemExit(f"unsupported platform for this helper: {system}-{machine}")


def download_duckdb_cli(workdir: Path) -> Path:
    _, asset_name, archive_kind = host_platform()
    duckdb_path = workdir / "duckdb"
    if duckdb_path.exists():
        return duckdb_path

    archive_path = workdir / asset_name
    url = f"https://github.com/duckdb/duckdb/releases/download/{DUCKDB_VERSION}/{asset_name}"
    archive_path.write_bytes(request_url(url))

    if archive_kind == "tar.gz":
        with tarfile.open(archive_path) as tar:
            try:
                tar.extractall(workdir, filter="data")
            except TypeError:
                tar.extractall(workdir)
    else:
        with ZipFile(archive_path) as zip_file:
            zip_file.extractall(workdir)

    if not duckdb_path.exists():
        matches = list(workdir.glob("**/duckdb"))
        if not matches:
            raise RuntimeError(f"DuckDB CLI was not found after extracting {archive_path}")
        shutil.copy(matches[0], duckdb_path)
    duckdb_path.chmod(0o755)
    return duckdb_path


def latest_release_tag() -> str:
    gh = shutil.which("gh")
    if gh:
        out = run([gh, "release", "list", "--repo", REPO, "--limit", "1", "--json", "tagName", "--jq", ".[0].tagName"])
        tag = out.strip()
        if tag:
            return tag
    raise SystemExit("--release-tag is required when GitHub CLI is unavailable or no release is visible")


def download_release_asset(release_tag: str, workdir: Path) -> Path:
    platform_id, _, _ = host_platform()
    asset_name = f"{EXTENSION_NAME}-{DUCKDB_VERSION}-{platform_id}.duckdb_extension"
    downloaded = workdir / asset_name

    gh = shutil.which("gh")
    if gh:
        try:
            run(
                [
                    gh,
                    "release",
                    "download",
                    release_tag,
                    "--repo",
                    REPO,
                    "--pattern",
                    asset_name,
                    "--clobber",
                    "--dir",
                    str(workdir),
                ]
            )
            if downloaded.exists():
                return downloaded
        except RuntimeError:
            # Public releases can still be fetched without gh auth below.
            pass

    url = f"https://github.com/{REPO}/releases/download/{release_tag}/{asset_name}"
    try:
        downloaded.write_bytes(request_url(url))
    except urllib.error.HTTPError as exc:
        raise RuntimeError(
            f"could not download {asset_name} for {release_tag}. "
            "If this is a draft release, authenticate gh and retry."
        ) from exc
    return downloaded


def prepare_runtime(release_tag: str, base_workdir: Path | None) -> RuntimePaths:
    workdir = base_workdir or Path(tempfile.mkdtemp(prefix="odd-spatial-map-"))
    workdir.mkdir(parents=True, exist_ok=True)
    duckdb = download_duckdb_cli(workdir)
    release_asset = download_release_asset(release_tag, workdir)

    canonical_extension = workdir / "open_data_duck.duckdb_extension"
    shutil.copyfile(release_asset, canonical_extension)

    platform_id, _, _ = host_platform()
    extension_repo = workdir / "custom-extension-repository"
    repo_dir = extension_repo / DUCKDB_VERSION / platform_id
    repo_dir.mkdir(parents=True, exist_ok=True)
    with canonical_extension.open("rb") as source, gzip.open(repo_dir / "open_data_duck.duckdb_extension.gz", "wb") as target:
        shutil.copyfileobj(source, target)

    return RuntimePaths(workdir=workdir, duckdb=duckdb, extension_file=canonical_extension, extension_repo=extension_repo)


def duckdb_csv(paths: RuntimePaths, sql: str) -> list[dict[str, str]]:
    out = run([str(paths.duckdb), "-unsigned", "-csv", ":memory:"], input_text=sql, cwd=paths.workdir)
    return list(csv.DictReader(io.StringIO(out)))


def query_overture_release(paths: RuntimePaths) -> str:
    sql = f"""
FORCE INSTALL open_data_duck FROM '{paths.extension_repo.as_posix()}';
LOAD open_data_duck;
SELECT open_data_release('overture.maps.release') AS release;
"""
    rows = duckdb_csv(paths, sql)
    if not rows or not rows[0].get("release"):
        raise RuntimeError("ODD did not resolve the Overture release")
    return rows[0]["release"]


def utm_epsg(lat: float, lon: float) -> str:
    zone = int((lon + 180) // 6) + 1
    prefix = 326 if lat >= 0 else 327
    return f"EPSG:{prefix}{zone:02d}"


def query_spatial_results(paths: RuntimePaths, lat: float, lon: float, radius_m: float, limit: int) -> dict[str, list[dict[str, str]]]:
    lat_delta = (radius_m / 111_320.0) * 1.5
    lon_delta = (radius_m / (111_320.0 * max(math.cos(math.radians(lat)), 0.01))) * 1.5
    epsg = utm_epsg(lat, lon)

    sql = f"""
FORCE INSTALL open_data_duck FROM '{paths.extension_repo.as_posix()}';
LOAD open_data_duck;
ATTACH ':memory:' AS odd (TYPE open_data_duck);
INSTALL httpfs;
INSTALL spatial;
LOAD httpfs;
LOAD spatial;
SET s3_region='us-west-2';
SET geometry_always_xy = true;
COPY (
  WITH params AS (
    SELECT {lat:.15f}::DOUBLE AS lat, {lon:.15f}::DOUBLE AS lon
  ), ranked AS (
    SELECT id,
           concat_ws(' ', number, street, unit) AS address,
           postal_city,
           country,
           ST_Y(geometry) AS lat,
           ST_X(geometry) AS lon,
           ST_Distance_Sphere(geometry, ST_Point((SELECT lon FROM params), (SELECT lat FROM params))) AS distance_m
    FROM odd.overturemaps.latest.address, params
    WHERE bbox.xmin <= lon + {lon_delta:.15f}
      AND bbox.xmax >= lon - {lon_delta:.15f}
      AND bbox.ymin <= lat + {lat_delta:.15f}
      AND bbox.ymax >= lat - {lat_delta:.15f}
  )
  SELECT id, address, postal_city, country, distance_m, lat, lon
  FROM ranked
  WHERE distance_m <= {radius_m:.6f}
  ORDER BY distance_m
  LIMIT {limit}
) TO 'addresses.csv' (HEADER, DELIMITER ',');

COPY (
  WITH params AS (
    SELECT {lat:.15f}::DOUBLE AS lat, {lon:.15f}::DOUBLE AS lon,
           ST_Transform(ST_Point({lon:.15f}, {lat:.15f}), 'EPSG:4326', '{epsg}', true) AS pt_utm
  ), candidates AS (
    SELECT id, names."primary" AS name, subtype, class, subclass, geometry, bbox
    FROM odd.overturemaps.latest.segment, params
    WHERE bbox.xmin <= lon + {lon_delta:.15f}
      AND bbox.xmax >= lon - {lon_delta:.15f}
      AND bbox.ymin <= lat + {lat_delta:.15f}
      AND bbox.ymax >= lat - {lat_delta:.15f}
  ), ranked AS (
    SELECT id, coalesce(name, '(unnamed)') AS name, subtype, class, coalesce(subclass, '') AS subclass,
           ST_Distance(ST_Transform(geometry, 'EPSG:4326', '{epsg}', true), (SELECT pt_utm FROM params)) AS distance_m,
           ST_AsText(geometry) AS wkt
    FROM candidates
  )
  SELECT id, name, subtype, class, subclass, distance_m, wkt
  FROM ranked
  WHERE distance_m <= {radius_m:.6f}
  ORDER BY distance_m
  LIMIT {limit}
) TO 'roads.csv' (HEADER, DELIMITER ',');

COPY (
  WITH params AS (
    SELECT {lat:.15f}::DOUBLE AS lat, {lon:.15f}::DOUBLE AS lon
  ), ranked AS (
    SELECT id, names."primary" AS name, basic_category, taxonomy."primary" AS category,
           ST_Y(geometry) AS lat,
           ST_X(geometry) AS lon,
           ST_Distance_Sphere(geometry, ST_Point((SELECT lon FROM params), (SELECT lat FROM params))) AS distance_m
    FROM odd.overturemaps.latest.place, params
    WHERE bbox.xmin <= lon + {lon_delta:.15f}
      AND bbox.xmax >= lon - {lon_delta:.15f}
      AND bbox.ymin <= lat + {lat_delta:.15f}
      AND bbox.ymax >= lat - {lat_delta:.15f}
  )
  SELECT id, coalesce(name, '') AS name, basic_category, category, distance_m, lat, lon
  FROM ranked
  WHERE distance_m <= {radius_m:.6f}
  ORDER BY distance_m
  LIMIT {limit}
) TO 'places.csv' (HEADER, DELIMITER ',');

COPY (
  WITH params AS (
    SELECT {lat:.15f}::DOUBLE AS lat, {lon:.15f}::DOUBLE AS lon,
           ST_Transform(ST_Point({lon:.15f}, {lat:.15f}), 'EPSG:4326', '{epsg}', true) AS pt_utm
  ), candidates AS (
    SELECT id, coalesce(names."primary", '') AS name, subtype, class, geometry, bbox
    FROM odd.overturemaps.latest.building, params
    WHERE bbox.xmin <= lon + {lon_delta:.15f}
      AND bbox.xmax >= lon - {lon_delta:.15f}
      AND bbox.ymin <= lat + {lat_delta:.15f}
      AND bbox.ymax >= lat - {lat_delta:.15f}
  ), ranked AS (
    SELECT id, name, coalesce(subtype, '') AS subtype, coalesce(class, '') AS class,
           ST_Distance(ST_Transform(geometry, 'EPSG:4326', '{epsg}', true), (SELECT pt_utm FROM params)) AS distance_m,
           ST_AsText(ST_PointOnSurface(geometry)) AS sample_point_wkt
    FROM candidates
  )
  SELECT id, name, subtype, class, distance_m, sample_point_wkt
  FROM ranked
  WHERE distance_m <= {radius_m:.6f}
  ORDER BY distance_m
  LIMIT {limit}
) TO 'buildings.csv' (HEADER, DELIMITER ',');
"""
    run([str(paths.duckdb), "-unsigned", ":memory:"], input_text=sql, cwd=paths.workdir)

    out: dict[str, list[dict[str, str]]] = {}
    for name in ["addresses", "roads", "places", "buildings"]:
        with (paths.workdir / f"{name}.csv").open(newline="") as handle:
            out[name] = list(csv.DictReader(handle))
    return out


def lonlat_to_global_px(lon: float, lat: float, zoom: int) -> tuple[float, float]:
    lat_rad = math.radians(lat)
    n = 2**zoom
    x = (lon + 180.0) / 360.0 * n * TILE_SIZE
    y = (1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n * TILE_SIZE
    return x, y


def meters_per_px(lat: float, zoom: int) -> float:
    return 156543.03392 * math.cos(math.radians(lat)) / (2**zoom)


def choose_zoom(lat: float, radius_m: float, size_px: int) -> int:
    target_m_per_px = max(radius_m * 2.8 / size_px, 0.05)
    zoom = math.log2(156543.03392 * math.cos(math.radians(lat)) / target_m_per_px)
    return max(2, min(19, int(math.floor(zoom))))


def to_screen_factory(center_lat: float, center_lon: float, zoom: int, width: int, height: int):
    center_px = lonlat_to_global_px(center_lon, center_lat, zoom)
    top_left = (center_px[0] - width / 2, center_px[1] - height / 2)

    def to_screen(lon: float, lat: float) -> tuple[float, float]:
        x, y = lonlat_to_global_px(lon, lat, zoom)
        return x - top_left[0], y - top_left[1]

    return to_screen, top_left


def load_font(size: int, bold: bool = False):
    names = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Arial.ttf",
    ]
    for name in names:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def download_tile(z: int, x: int, y: int) -> Image.Image | None:
    if x < 0 or y < 0 or x >= 2**z or y >= 2**z:
        return None
    url = f"https://tile.openstreetmap.org/{z}/{x}/{y}.png"
    try:
        return Image.open(io.BytesIO(request_url(url))).convert("RGB")
    except Exception:
        return None


def parse_linestring(wkt: str) -> list[tuple[float, float]]:
    match = re.match(r"LINESTRING \((.*)\)", wkt or "")
    if not match:
        return []
    points: list[tuple[float, float]] = []
    for pair in match.group(1).split(","):
        lon, lat = map(float, pair.strip().split()[:2])
        points.append((lon, lat))
    return points


def parse_point_wkt(wkt: str) -> tuple[float, float] | None:
    match = re.match(r"POINT \(([-0-9.]+) ([-0-9.]+)\)", wkt or "")
    if not match:
        return None
    return float(match.group(1)), float(match.group(2))


def render_map(
    results: dict[str, list[dict[str, str]]],
    *,
    lat: float,
    lon: float,
    radius_m: float,
    release_tag: str,
    overture_release: str,
    output: Path,
    width: int = 1000,
    height: int = 1000,
) -> None:
    zoom = choose_zoom(lat, radius_m, min(width, height))
    to_screen, top_left = to_screen_factory(lat, lon, zoom, width, height)

    image = Image.new("RGB", (width, height), (240, 239, 233))
    draw = ImageDraw.Draw(image)
    min_tx = math.floor(top_left[0] / TILE_SIZE)
    max_tx = math.floor((top_left[0] + width) / TILE_SIZE)
    min_ty = math.floor(top_left[1] / TILE_SIZE)
    max_ty = math.floor((top_left[1] + height) / TILE_SIZE)
    for tx in range(min_tx, max_tx + 1):
        for ty in range(min_ty, max_ty + 1):
            tile = download_tile(zoom, tx, ty)
            x = int(tx * TILE_SIZE - top_left[0])
            y = int(ty * TILE_SIZE - top_left[1])
            if tile:
                image.paste(tile, (x, y))
            else:
                draw.rectangle([x, y, x + TILE_SIZE, y + TILE_SIZE], outline=(210, 210, 210), fill=(245, 245, 245))

    image = Image.alpha_composite(image.convert("RGBA"), Image.new("RGBA", image.size, (255, 255, 255, 35)))
    draw = ImageDraw.Draw(image)
    font = load_font(16)
    font_b = load_font(18, bold=True)
    font_s = load_font(13)

    cx, cy = to_screen(lon, lat)
    r_px = radius_m / meters_per_px(lat, zoom)
    draw.ellipse([cx - r_px, cy - r_px, cx + r_px, cy + r_px], outline=(20, 110, 255, 230), width=4, fill=(20, 110, 255, 30))
    draw.ellipse([cx - 9, cy - 9, cx + 9, cy + 9], fill=(20, 70, 220, 255), outline="white", width=3)
    draw.text((cx + 12, cy - 26), "query point", fill=(10, 40, 130), font=font_b, stroke_width=3, stroke_fill="white")

    for road in results["roads"]:
        points = [to_screen(point_lon, point_lat) for point_lon, point_lat in parse_linestring(road.get("wkt", ""))]
        if len(points) < 2:
            continue
        draw.line(points, fill=(210, 90, 0, 230), width=7, joint="curve")
        draw.line(points, fill=(255, 200, 0, 245), width=3, joint="curve")
        mx, my = points[len(points) // 2]
        draw.text(
            (mx + 8, my + 8),
            f"road: {road['name']} ({float(road['distance_m']):.1f}m)",
            fill=(120, 45, 0),
            font=font_s,
            stroke_width=3,
            stroke_fill="white",
        )

    for i, address in enumerate(results["addresses"], 1):
        x, y = to_screen(float(address["lon"]), float(address["lat"]))
        draw.ellipse([x - 8, y - 8, x + 8, y + 8], fill=(220, 30, 60, 255), outline="white", width=3)
        draw.text((x + 10, y - 18), f"A{i}: {float(address['distance_m']):.1f}m", fill=(150, 0, 25), font=font_b, stroke_width=3, stroke_fill="white")

    for i, place in enumerate(results["places"], 1):
        if not place.get("lat") or not place.get("lon"):
            continue
        x, y = to_screen(float(place["lon"]), float(place["lat"]))
        draw.rectangle([x - 7, y - 7, x + 7, y + 7], fill=(0, 145, 80, 255), outline="white", width=3)
        name = place.get("name") or "place"
        draw.text((x + 10, y - 18), f"P{i}: {name}", fill=(0, 90, 55), font=font_s, stroke_width=3, stroke_fill="white")

    for i, building in enumerate(results["buildings"], 1):
        point = parse_point_wkt(building.get("sample_point_wkt", ""))
        if not point:
            continue
        x, y = to_screen(*point)
        draw.polygon([(x, y - 9), (x + 8, y + 6), (x - 8, y + 6)], fill=(120, 70, 180, 255), outline="white")
        draw.text((x + 10, y - 18), f"B{i}: {float(building['distance_m']):.1f}m", fill=(80, 45, 130), font=font_s, stroke_width=3, stroke_fill="white")

    panel_width = min(width - 36, 580)
    panel = [18, 18, 18 + panel_width, 176]
    draw.rounded_rectangle(panel, radius=14, fill=(255, 255, 255, 235), outline=(180, 180, 180, 255), width=1)
    draw.text((34, 32), "Open Data Duck spatial query", fill=(0, 0, 0), font=font_b)
    draw.text((34, 60), f"Center: {lat:.7f}, {lon:.7f}   Radius: {radius_m:g}m", fill=(30, 30, 30), font=font_s)
    draw.text((34, 84), f"Release: {release_tag} / Overture {overture_release}", fill=(30, 30, 30), font=font_s)
    draw.ellipse([36, 113, 50, 127], fill=(220, 30, 60), outline="white")
    draw.text((60, 110), f"Address hits: {len(results['addresses'])} shown, labels redacted", fill=(30, 30, 30), font=font_s)
    draw.line([(38, 146), (52, 146)], fill=(255, 200, 0), width=4)
    draw.text((60, 137), f"Road hits: {len(results['roads'])} shown", fill=(30, 30, 30), font=font_s)

    scale_m = nice_scale(radius_m)
    scale_px = scale_m / meters_per_px(lat, zoom)
    x0, y0 = width - scale_px - 70, height - 70
    draw.line([(x0, y0), (x0 + scale_px, y0)], fill=(0, 0, 0), width=5)
    draw.line([(x0, y0 - 8), (x0, y0 + 8)], fill=(0, 0, 0), width=3)
    draw.line([(x0 + scale_px, y0 - 8), (x0 + scale_px, y0 + 8)], fill=(0, 0, 0), width=3)
    draw.text((x0, y0 + 12), f"{scale_m:g} m", fill=(0, 0, 0), font=font_s, stroke_width=3, stroke_fill="white")
    draw.text((18, height - 28), "Tiles © OpenStreetMap contributors | ODD query screenshot", fill=(60, 60, 60), font=font_s, stroke_width=2, stroke_fill="white")

    output.parent.mkdir(parents=True, exist_ok=True)
    image.convert("RGB").save(output, quality=95)


def nice_scale(radius_m: float) -> int:
    candidates = [10, 20, 50, 100, 200, 500, 1000, 2000, 5000]
    target = radius_m / 2
    return min(candidates, key=lambda value: abs(value - target))


def redact_address(address: str) -> str:
    return re.sub(r"^\d+", "40xx", address or "")


def markdown_table(headers: list[str], rows: list[list[str]]) -> str:
    if not rows:
        return "No rows.\n"
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    lines.extend("| " + " | ".join(row) + " |" for row in rows)
    return "\n".join(lines) + "\n"


def write_report(results: dict[str, list[dict[str, str]]], output: Path, *, lat: float, lon: float, radius_m: float, release_tag: str, overture_release: str, include_full_addresses: bool) -> None:
    address_rows = []
    for row in results["addresses"]:
        address = row["address"] if include_full_addresses else redact_address(row["address"])
        address_rows.append([address, row["postal_city"], row["country"], f"{float(row['distance_m']):.1f}", f"{float(row['lat']):.7f}", f"{float(row['lon']):.7f}"])

    road_rows = [[row["name"], row["subtype"], row["class"], row.get("subclass", ""), f"{float(row['distance_m']):.1f}"] for row in results["roads"]]
    place_rows = [[row["name"], row["basic_category"], row["category"], f"{float(row['distance_m']):.1f}"] for row in results["places"]]
    building_rows = [[row["name"], row["subtype"], row["class"], f"{float(row['distance_m']):.1f}"] for row in results["buildings"]]

    content = f"""# Open Data Duck spatial query

- Center: `{lat}, {lon}`
- Radius: `{radius_m:g}` meters
- Release tag: `{release_tag}`
- Overture release: `{overture_release}`

## Addresses

{markdown_table(['address', 'city', 'country', 'meters', 'lat', 'lon'], address_rows)}
## Road segments

{markdown_table(['name', 'subtype', 'class', 'subclass', 'meters'], road_rows)}
## Places

{markdown_table(['name', 'basic_category', 'category', 'meters'], place_rows)}
## Buildings

{markdown_table(['name', 'subtype', 'class', 'meters'], building_rows)}
"""
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(content, encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render an ODD/Overture spatial-query map from lat/lon/radius.")
    parser.add_argument("--lat", type=float, required=True)
    parser.add_argument("--lon", type=float, required=True)
    parser.add_argument("--radius-m", type=float, required=True)
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--release-tag", default=None, help="GitHub release tag to install. Defaults to latest visible gh release.")
    parser.add_argument("--output", type=Path, default=Path("spatial-results-map.png"))
    parser.add_argument("--report", type=Path, default=None, help="Markdown report path. Defaults to OUTPUT with .md suffix.")
    parser.add_argument("--workdir", type=Path, default=None, help="Cache/work directory for DuckDB CLI, extension, and intermediate CSVs.")
    parser.add_argument("--include-full-addresses", action="store_true", help="Include full address numbers in the Markdown report. Map labels stay redacted.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.radius_m <= 0:
        raise SystemExit("--radius-m must be positive")
    if args.limit <= 0:
        raise SystemExit("--limit must be positive")

    release_tag = args.release_tag or latest_release_tag()
    runtime = prepare_runtime(release_tag, args.workdir)
    overture_release = query_overture_release(runtime)
    results = query_spatial_results(runtime, args.lat, args.lon, args.radius_m, args.limit)

    render_map(
        results,
        lat=args.lat,
        lon=args.lon,
        radius_m=args.radius_m,
        release_tag=release_tag,
        overture_release=overture_release,
        output=args.output,
    )
    report = args.report or args.output.with_suffix(".md")
    write_report(
        results,
        report,
        lat=args.lat,
        lon=args.lon,
        radius_m=args.radius_m,
        release_tag=release_tag,
        overture_release=overture_release,
        include_full_addresses=args.include_full_addresses,
    )

    print(json.dumps({"map": str(args.output), "report": str(report), "workdir": str(runtime.workdir), "release_tag": release_tag, "overture_release": overture_release}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

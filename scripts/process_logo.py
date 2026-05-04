#!/usr/bin/env python3
"""
process_logo.py — logo transparency fix, size variants, and SVG export.

Pipeline
--------
1. Remove baked-in checkerboard background → real RGBA alpha channel
2. Save compressed master PNG (overwrites input)
3. Generate logo variants:  32 / 64 / 128 / 256 / 512 px squares
4. Generate badge variants:  20 / 40 / 80 / 200 px squares
5. Export full-size SVG:
   - If `vtracer` is installed: true vector output  (pip install vtracer)
   - Otherwise: SVG wrapper embedding the base64 PNG  (always works, fully scalable)

Usage
-----
    python scripts/process_logo.py assets/gutenberg_logo.png
    python scripts/process_logo.py assets/gutenberg_logo.png --out assets/logos
    python scripts/process_logo.py assets/gutenberg_logo.png --feather 6 --bg-thresh 210
"""

import argparse
import base64
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

# ── CLI ────────────────────────────────────────────────────────────────────────


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    p.add_argument("src", help="Source PNG (RGB or RGBA)")
    p.add_argument("--out", default=None, help="Output directory (default: same dir as src)")
    p.add_argument(
        "--feather", type=int, default=5, help="Edge feather radius in pixels (default: 5)"
    )
    p.add_argument(
        "--bg-thresh",
        type=int,
        default=220,
        help="Brightness threshold for background detection (default: 220)",
    )
    p.add_argument(
        "--no-compress", action="store_true", help="Skip zlib-9 compression on output PNGs"
    )
    return p.parse_args()


# ── Transparency fix ───────────────────────────────────────────────────────────


def remove_background(arr: np.ndarray, bg_thresh: int, feather: int) -> np.ndarray:
    """Return RGBA uint8 array with checkerboard background replaced by real alpha."""
    h, w = arr.shape[:2]
    gray = arr[:, :, :3].mean(axis=2)

    # Connected-component flood fill from image corners
    bright = gray > bg_thresh
    labeled, _ = ndimage.label(bright)
    corner_labels = {
        labeled[0, 0],
        labeled[0, w - 1],
        labeled[h - 1, 0],
        labeled[h - 1, w - 1],
    } - {0}
    bg_mask = np.isin(labeled, list(corner_labels))

    dist_into_fg = ndimage.distance_transform_edt(~bg_mask)

    # Alpha: 0 inside BG, 255 inside FG, feathered at boundary
    alpha = np.full((h, w), 255, dtype=np.float32)
    deep_bg = bg_mask & (dist_into_fg >= feather)
    edge_bg = bg_mask & (dist_into_fg < feather)
    alpha[deep_bg] = 0.0
    alpha[edge_bg] = (dist_into_fg[edge_bg] / feather * 255).clip(0, 255)

    rgba = np.dstack([arr[:, :, :3], alpha.clip(0, 255).astype(np.uint8)])
    return rgba


# ── SVG export ─────────────────────────────────────────────────────────────────


def _svg_embedded(png_path: Path) -> str:
    """SVG wrapping the PNG as a base64 data URI — always available, fully scalable."""
    data = base64.b64encode(png_path.read_bytes()).decode()
    img = Image.open(png_path)
    iw, ih = img.size
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'xmlns:xlink="http://www.w3.org/1999/xlink" '
        f'width="{iw}" height="{ih}" viewBox="0 0 {iw} {ih}">\n'
        f'  <image href="data:image/png;base64,{data}" '
        f'width="{iw}" height="{ih}"/>\n'
        f"</svg>\n"
    )


def export_svg(png_path: Path, svg_path: Path) -> str:
    """Try vtracer for true vector output; fall back to embedded-PNG SVG."""
    try:
        import vtracer  # pip install vtracer

        vtracer.convert_image_to_svg_py(
            str(png_path),
            str(svg_path),
            colormode="color",
            hierarchical="stacked",
            mode="spline",
            filter_speckle=4,
            color_precision=6,
            layer_difference=16,
            corner_threshold=60,
            length_threshold=4.0,
            max_iterations=10,
            splice_threshold=45,
            path_precision=3,
        )
        return "vector (vtracer)"
    except ImportError:
        svg_path.write_text(_svg_embedded(png_path))
        return "embedded PNG (install vtracer for true vector)"


# ── Main ───────────────────────────────────────────────────────────────────────

LOGO_SIZES = [512, 256, 128, 64, 32]
BADGE_SIZES = [200, 80, 40, 20]


def main() -> None:
    args = parse_args()
    src = Path(args.src)
    if not src.exists():
        sys.exit(f"File not found: {src}")

    out_dir = Path(args.out) if args.out else src.parent
    logos_dir = out_dir / "logos"
    badges_dir = out_dir / "badges"
    logos_dir.mkdir(parents=True, exist_ok=True)
    badges_dir.mkdir(parents=True, exist_ok=True)

    compress = 9 if not args.no_compress else 1
    save_kw = dict(format="PNG", optimize=True, compress_level=compress)

    # ── Load & fix transparency ──────────────────────────────────────────────
    print(f"Loading {src} …")
    img = Image.open(src).convert("RGB")
    arr = np.array(img, dtype=np.uint8)

    print(f"  Removing background  (thresh={args.bg_thresh}, feather={args.feather}px) …")
    rgba = remove_background(arr, args.bg_thresh, args.feather)
    master = Image.fromarray(rgba, "RGBA")

    master.save(src, **save_kw)
    print(f"  Master saved → {src}  ({src.stat().st_size // 1024} KB)")

    # ── Logo variants ────────────────────────────────────────────────────────
    print("\nLogo variants:")
    for px in LOGO_SIZES:
        thumb = master.resize((px, px), Image.LANCZOS)
        dest = logos_dir / f"logo_{px}.png"
        thumb.save(dest, **save_kw)
        kb = dest.stat().st_size // 1024 or f"{dest.stat().st_size} B"
        print(f"  {dest}  ({kb} KB)" if isinstance(kb, int) else f"  {dest}  ({kb})")

    # ── Badge variants ───────────────────────────────────────────────────────
    print("\nBadge variants:")
    for px in BADGE_SIZES:
        thumb = master.resize((px, px), Image.LANCZOS)
        dest = badges_dir / f"badge_{px}.png"
        thumb.save(dest, **save_kw)
        b = dest.stat().st_size
        size_str = f"{b // 1024} KB" if b >= 1024 else f"{b} B"
        print(f"  {dest}  ({size_str})")

    # ── SVG export ───────────────────────────────────────────────────────────
    print("\nSVG export:")
    svg_path = out_dir / (src.stem + ".svg")
    method = export_svg(src, svg_path)
    print(f"  {svg_path}  ({svg_path.stat().st_size // 1024} KB)  [{method}]")

    print("\nDone.")


if __name__ == "__main__":
    main()

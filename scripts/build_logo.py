#!/usr/bin/env python3
"""Draw the KGRAG logo in Art Techno and write every size the repo uses.

The mark is the federation fan. Five member graphs, each a small chip, feed
short thin traces into the pins of one large chip, and three heavy spokes fan
the answer out to pads: many KGs, one query, one grounded answer. The palette,
drawing helpers and outlined lettering come from the Art Techno brand build,
so the SVGs render the same everywhere.

Usage::

    python scripts/build_logo.py

Needs ``fonttools`` and Pillow, Google Chrome for the PNG renders, and a clone
of https://github.com/Flux-Frontiers/art_techno beside this repo. Set ``CHROME``
to the browser binary if it is not at the default macOS path.

Writes, under ``assets/``:

- ``kgrag_logo_1024x1024.svg`` and ``.png``: the square mark
- ``logos/kgrag_icon.svg``: the mark reduced for 64 px and below
- ``logos/kgrag_banner.svg`` and ``logos/kgrag_banner.png``
- ``logos/logo_{512,256,128}.png`` from the mark and ``logos/logo_{64,32}.png``
  from the icon
- ``badges/badge_200.png`` from the mark and ``badges/badge_{80,40,20}.png``
  from the icon
"""

import importlib.util
import subprocess
import tempfile
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
AT_BUILD = ROOT.parent / "art_techno" / "docs" / "brand" / "build.py"

_spec = importlib.util.spec_from_file_location("at_build", AT_BUILD)
at = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(at)

f, line, pad, diamond, clipped_rect = at.f, at.line, at.pad, at.diamond, at.clipped_rect
OBSIDIAN, PANEL, COPPER, GOLD, GREEN, MINT, SILK = (
    at.OBSIDIAN,
    at.PANEL,
    at.COPPER,
    at.GOLD,
    at.GREEN,
    at.MINT,
    at.SILK,
)

NAME = "KGRAG"
PART = "ONE QUERY, MANY GRAPHS"


def rect(
    x: float, y: float, w: float, h: float, fill: str, stroke: str = "", width: float = 0
) -> str:
    s = f' stroke="{stroke}" stroke-width="{f(width)}"' if stroke else ""
    return f'<rect x="{f(x)}" y="{f(y)}" width="{f(w)}" height="{f(h)}" fill="{fill}"{s}/>'


def package(x: float, y: float, r: float, c: float, width: float) -> str:
    """A chip package: a dark square with 45-degree corners in a gold line.

    :param x: Center x.
    :param y: Center y.
    :param r: Half the side length.
    :param c: Corner cut.
    :param width: Stroke width.
    """
    return (
        f'<path d="{clipped_rect(x - r, y - r, 2 * r, 2 * r, c)}" fill="{PANEL}" '
        f'stroke="{GOLD}" stroke-width="{f(width)}"/>'
    )


def fan() -> str:
    """The federation fan on a 512 field, the chip centered on x = 256."""
    out = []
    cx, cy, h, c = 256, 212, 66, 20
    # The fan: three heavy spokes from the package to pads.
    k = h - c / 2
    ends = [
        ((cx + k, cy - k), (cx + k + 66, cy - k - 66)),
        ((cx + h, cy), (cx + h + 84, cy)),
        ((cx + k, cy + k), (cx + k + 66, cy + k + 66)),
    ]
    for a, b in ends:
        out.append(line([a, b], GOLD, 6))
    for _, (x, y) in ends:
        out.append(pad(x, y, 15, GOLD) + pad(x, y, 6.5, GREEN))
    # The federation: five member graphs, each on a thin trace to its own pin.
    mx, bend = 96, cx - h - 26
    for i, y in enumerate((124, 168, 212, 256, 300)):
        col = COPPER if i % 2 else GOLD
        yt = cy + 22 * (i - 2)
        run = abs(yt - y)
        pin = cx - h - 10
        pts = [(mx, y), (bend - run, y), (bend, yt), (pin, yt)] if run else [(mx, y), (pin, y)]
        out.append(line(pts, col, 3.5))
        out.append(rect(cx - h - 12, yt - 5, 12, 10, GOLD))
        out.append(package(mx, y, 14, 5, 3) + rect(mx - 5, y - 5, 10, 10, col))
    # Pin rows above and below.
    for dx in (-33, -11, 11, 33):
        out.append(rect(cx + dx - 5, cy - h - 12, 10, 12, GOLD))
        out.append(rect(cx + dx - 5, cy + h, 10, 12, GOLD))
    # The chip: package, hairline, die and core.
    out.append(package(cx, cy, h, c, 6))
    out.append(
        f'<path d="{clipped_rect(cx - h + 11, cy - h + 11, 2 * h - 22, 2 * h - 22, c - 6)}" '
        f'fill="none" stroke="{GOLD}" stroke-width="1.5" stroke-opacity=".6"/>'
    )
    out.append(
        rect(cx - 36, cy - 36, 72, 72, GREEN, GOLD, 4) + rect(cx - 12, cy - 12, 24, 24, SILK)
    )
    return "".join(out)


def fan_small() -> str:
    """The fan reduced for 64 px and below: three members, the chip, three spokes."""
    out = []
    ends = [((43, 21), (50, 14)), ((45, 32), (53, 32)), ((43, 43), (50, 50))]
    for a, b in ends:
        out.append(line([a, b], GOLD, 3))
    for _, (x, y) in ends:
        out.append(pad(x, y, 4.2, GOLD))
    for pts, col in (
        ([(10, 16), (13, 16), (20, 23)], COPPER),
        ([(10, 32), (20, 32)], GOLD),
        ([(10, 48), (13, 48), (20, 41)], COPPER),
    ):
        out.append(line(pts, col, 2))
        out.append(rect(pts[0][0] - 3, pts[0][1] - 3, 6, 6, col))
    out.append(package(32, 32, 13, 5, 2.6))
    out.append(rect(25, 25, 14, 14, GREEN) + rect(29.5, 29.5, 5, 5, SILK))
    return "".join(out)


def frame(w: float, h: float, inset: float, c: float, heavy: float) -> str:
    """Double frame with 45-degree corners and a green diamond at each corner.

    :param w: Canvas width.
    :param h: Canvas height.
    :param inset: Distance of the heavy line from the canvas edge.
    :param c: Corner cut of the heavy line.
    :param heavy: Stroke width of the heavy line.
    """
    out = [
        f'<path d="{clipped_rect(inset, inset, w - 2 * inset, h - 2 * inset, c)}" fill="none" stroke="{GOLD}" stroke-width="{f(heavy)}"/>',
        f'<path d="{clipped_rect(inset * 1.9, inset * 1.9, w - 3.8 * inset, h - 3.8 * inset, c * 0.75)}" fill="none" stroke="{GOLD}" stroke-width="{f(heavy * 0.4)}" stroke-opacity=".6"/>',
    ]
    d = inset * 1.45 + c * 0.4375
    for cx, cy in ((d, d), (w - d, d), (d, h - d), (w - d, h - d)):
        out.append(diamond(cx, cy, inset * 0.5, GREEN))
    return "".join(out)


def svg(w: int, h: int, title: str, body: str) -> str:
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">'
        f"<title>{title}</title>"
        f'<rect width="{w}" height="{h}" fill="{OBSIDIAN}"/>{body}</svg>\n'
    )


def mark(display, mono) -> str:
    """512 square mark: the fan, the name and the part line beneath."""
    body = frame(512, 512, 10, 26, 5) + fan()
    body += display.path(NAME, 256, 430, 40, 0.2, "middle", GOLD)
    body += mono.path(PART, 256, 462, 13.5, 0.3, "middle", MINT)
    return svg(512, 512, "KGRAG mark, Art Techno", body)


def icon() -> str:
    """64 icon: the reduced fan in one heavy frame, no lettering."""
    body = f'<path d="{clipped_rect(2.5, 2.5, 59, 59, 7.5)}" fill="none" stroke="{GOLD}" stroke-width="3"/>'
    return svg(64, 64, "KGRAG icon, Art Techno", body + fan_small())


def banner(display, mono) -> str:
    """1280 x 320 banner: the fan left, the name and part line right.

    The name is set as large as the room right of the fan allows, and the
    pair is centered on the banner's height.
    """
    s = 0.78
    body = frame(1280, 320, 10, 18, 3)
    body += (
        f'<g transform="translate({f(230 - 256 * s)} {f(160 - 212 * s)}) scale({s})">{fan()}</g>'
    )
    cx, room, gap = 820, 760, 34
    size = min(120, 120 * room / display.width(NAME, 120, 0.2))
    part = min(26, 26 * room / mono.width(PART, 26, 0.3))
    cap = display.cap * size / display.upm
    pcap = mono.cap * part / mono.upm
    base = (320 - (cap + gap + pcap)) / 2 + cap
    body += display.path(NAME, cx, base, size, 0.2, "middle", GOLD)
    body += mono.path(PART, cx, base + gap + pcap, part, 0.3, "middle", MINT)
    return svg(1280, 320, "KGRAG banner, Art Techno", body)


def render(src: Path, out: Path, w: int, h: int) -> None:
    """Render the SVG ``src`` to ``out`` at ``w`` x ``h`` px with headless Chrome.

    :param src: SVG file; its ``width`` attribute sets the CSS width.
    :param out: PNG to write.
    :param w: Output width in px.
    :param h: Output height in px.
    """
    svg_w = int(src.read_text().split('width="', 1)[1].split('"', 1)[0])
    subprocess.run(
        [
            at.CHROME,
            "--headless",
            "--disable-gpu",
            "--hide-scrollbars",
            f"--window-size={svg_w},{svg_w * h // w}",
            f"--force-device-scale-factor={w / svg_w}",
            f"--screenshot={out}",
            src.as_uri(),
        ],
        check=True,
        capture_output=True,
    )


def resized(master: Path, dest: Path, px: int) -> None:
    Image.open(master).convert("RGB").resize((px, px), Image.LANCZOS).save(dest, optimize=True)


def main() -> None:
    at.fetch_fonts()
    display = at.Face(at.CACHE / "JosefinSans.ttf", weight=600)
    mono = at.Face(at.CACHE / "IBMPlexMono-Medium.ttf")

    assets = ROOT / "assets"
    logos = assets / "logos"
    badges = assets / "badges"

    mark_svg = assets / "kgrag_logo_1024x1024.svg"
    icon_svg = logos / "kgrag_icon.svg"
    banner_svg = logos / "kgrag_banner.svg"
    mark_svg.write_text(mark(display, mono))
    icon_svg.write_text(icon())
    banner_svg.write_text(banner(display, mono))

    mark_png = mark_svg.with_suffix(".png")
    render(mark_svg, mark_png, 1024, 1024)
    render(banner_svg, banner_svg.with_suffix(".png"), 2560, 640)
    with tempfile.TemporaryDirectory() as tmp:
        icon_png = Path(tmp) / "icon.png"
        render(icon_svg, icon_png, 1024, 1024)
        for px in (512, 256, 128):
            resized(mark_png, logos / f"logo_{px}.png", px)
        for px in (64, 32):
            resized(icon_png, logos / f"logo_{px}.png", px)
        resized(mark_png, badges / "badge_200.png", 200)
        for px in (80, 40, 20):
            resized(icon_png, badges / f"badge_{px}.png", px)


if __name__ == "__main__":
    main()

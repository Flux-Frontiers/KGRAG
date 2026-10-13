"""
owl.py — the KGRAG owl, the system's voice.

The owl disc (Art Techno motif 23) drawn as an avatar in a chip-package frame.
It sits beside whatever KGRAG says and shows what the pipeline is doing, in the
colours of the Art Techno knowledge layer:

    idle        mint rays, dark eyes          latent, waiting
    retrieving  copper rays, green die eyes   walking relations in the KGs
    answering   gold rays, eyes lit           streaming a grounded answer

While it works, its rays light in sequence round each eye, like a radar sweep;
that is the only motion it has, and it stops for ``prefers-reduced-motion``.

Pure Python with no dependencies, so the Streamlit app, a web page or a CLI
export can all draw it::

    from kg_rag.owl import owl_html
    st.markdown(owl_html("retrieving", label="Retrieving", detail="4 KGs"),
                unsafe_allow_html=True)
"""

from __future__ import annotations

import math
from html import escape
from typing import Literal

OwlState = Literal["idle", "retrieving", "answering"]

# Art Techno palette (docs/STYLE.md in Flux-Frontiers/art_techno)
GOLD = "#D4AF5A"
COPPER = "#C77C48"
SOLDER_GREEN = "#2F8F74"
MINT = "#7FBFA8"
SILKSCREEN = "#EDE6D3"
OBSIDIAN = "#0B100E"
PANEL = "#121A17"

STATES: tuple[OwlState, ...] = ("idle", "retrieving", "answering")

# state -> (ray colour, ray weight, eye fill, eye stroke, die fill or None, lit core or None)
_STYLE: dict[str, tuple[str, float, str, str, str | None, str | None]] = {
    "idle": (MINT, 1.2, PANEL, MINT, None, None),
    "retrieving": (COPPER, 1.6, SOLDER_GREEN, GOLD, GOLD, None),
    "answering": (GOLD, 1.6, SOLDER_GREEN, GOLD, GOLD, SILKSCREEN),
}

# One status colour per state, for the label beside the owl.
STATE_COLOR: dict[str, str] = {"idle": MINT, "retrieving": COPPER, "answering": GOLD}

_LEFT_EYE = (22.0, 30.0)
_RIGHT_EYE = (42.0, 30.0)
# Rays fan round the outer side of each eye, mirrored. SVG angles: 0 = right, 90 = down.
_LEFT_RAYS = (120, 150, 180, 210, 240, 270, 300)
_RIGHT_RAYS = (60, 30, 0, -30, -60, -90, -120)
_SWEEP_SECONDS = 1.4

_CSS = f"""<style>
.kgowl {{ display: flex; align-items: center; gap: 14px; margin: 4px 0 12px; }}
.kgowl svg {{ flex: none; }}
.kgowl-label {{ display: flex; align-items: center; gap: 8px;
  font-family: ui-monospace, 'IBM Plex Mono', monospace; font-size: 0.8rem;
  letter-spacing: 0.16em; text-transform: uppercase; }}
.kgowl-pip {{ width: 7px; height: 7px; transform: rotate(45deg); flex: none; }}
.kgowl-detail {{ font-size: 0.85rem; opacity: 0.8; margin-top: 2px; }}
.kgowl-sweep .kgowl-ray {{ animation: kgowl-sweep {_SWEEP_SECONDS}s linear infinite; opacity: 0.35; }}
@keyframes kgowl-sweep {{ 0% {{ opacity: 1; }} 35% {{ opacity: 0.35; }} 100% {{ opacity: 0.35; }} }}
@media (prefers-reduced-motion: reduce) {{
  .kgowl-sweep .kgowl-ray {{ animation: none; opacity: 1; }}
}}
</style>"""


def _n(x: float) -> str:
    """Format a coordinate compactly."""
    return f"{x:.2f}".rstrip("0").rstrip(".")


def _ray(
    cx: float,
    cy: float,
    angle: float,
    length: float,
    colour: str,
    weight: float,
    delay: float | None,
) -> str:
    """One boot-sun ray: a line from the eye's rim ending in a round pad (rules 1 and 3)."""
    pad = 1.2
    t = math.radians(angle)
    x0, y0 = cx + 8.5 * math.cos(t), cy + 8.5 * math.sin(t)
    x1, y1 = cx + (length - pad) * math.cos(t), cy + (length - pad) * math.sin(t)
    xp, yp = cx + length * math.cos(t), cy + length * math.sin(t)
    style = f' style="animation-delay:{delay:.3f}s"' if delay is not None else ""
    return (
        f'<g class="kgowl-ray"{style}>'
        f'<line x1="{_n(x0)}" y1="{_n(y0)}" x2="{_n(x1)}" y2="{_n(y1)}" '
        f'stroke="{colour}" stroke-width="{weight}"/>'
        f'<circle cx="{_n(xp)}" cy="{_n(yp)}" r="{pad}" fill="{colour}"/></g>'
    )


def _octagon(cx: float, cy: float, r: float) -> str:
    """Points of an octagon with flat top and sides: the die eye's package."""
    pts = []
    for k in range(8):
        t = math.radians(22.5 + 45 * k)
        pts.append(f"{_n(cx + r * math.cos(t))},{_n(cy + r * math.sin(t))}")
    return " ".join(pts)


def owl_svg(
    state: OwlState = "idle", size: int = 64, working: bool = False, title: str | None = None
) -> str:
    """
    Return the owl avatar as an SVG string.

    :param state: ``"idle"``, ``"retrieving"`` or ``"answering"``.
    :param size: rendered width and height in pixels (the drawing is on a 64 grid).
    :param working: when True the rays light in sequence (needs the CSS from :func:`owl_css`).
    :param title: accessible name; defaults to "KGRAG owl, <state>".
    """
    if state not in _STYLE:
        raise ValueError(f"unknown owl state {state!r}; expected one of {STATES}")
    ray_c, ray_w, eye_fill, eye_stroke, die_fill, core = _STYLE[state]
    label = title or f"KGRAG owl, {state}"
    step = _SWEEP_SECONDS / len(_LEFT_RAYS)
    sweep = ' class="kgowl-sweep"' if working else ""

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" width="{size}" '
        f'height="{size}" role="img" aria-label="{escape(label)}"{sweep}>',
        f"<title>{escape(label)}</title>",
        # chip-package frame: a square with 45-degree clipped corners
        f'<polygon points="6,1 58,1 63,6 63,58 58,63 6,63 1,58 1,6" fill="{PANEL}" '
        f'stroke="{GOLD}" stroke-width="1.5"/>',
    ]
    # Both suns sweep outward from the top of the head, in step.
    for i, angle in enumerate(_LEFT_RAYS):
        delay = (len(_LEFT_RAYS) - 1 - i) * step if working else None
        parts.append(_ray(*_LEFT_EYE, angle, 14 if i % 2 == 0 else 12, ray_c, ray_w, delay))
    for i, angle in enumerate(_RIGHT_RAYS):
        delay = (len(_RIGHT_RAYS) - 1 - i) * step if working else None
        parts.append(_ray(*_RIGHT_EYE, angle, 14 if i % 2 == 0 else 12, ray_c, ray_w, delay))
    # ear tufts: stepped fins
    for x, h in ((9.0, 10.0), (12.5, 7.5)):
        parts.append(
            f'<rect x="{_n(x)}" y="{_n(18 - h)}" width="2" height="{_n(h)}" fill="{GOLD}"/>'
        )
        parts.append(
            f'<rect x="{_n(64 - x - 2)}" y="{_n(18 - h)}" width="2" height="{_n(h)}" fill="{GOLD}"/>'
        )
    # die eyes
    for cx, cy in (_LEFT_EYE, _RIGHT_EYE):
        parts.append(
            f'<polygon points="{_octagon(cx, cy, 7)}" fill="{eye_fill}" stroke="{eye_stroke}" '
            f'stroke-width="1.5"/>'
        )
        if die_fill:
            parts.append(
                f'<rect x="{_n(cx - 3)}" y="{_n(cy - 3)}" width="6" height="6" fill="{die_fill}"/>'
            )
        else:
            parts.append(
                f'<rect x="{_n(cx - 3)}" y="{_n(cy - 3)}" width="6" height="6" fill="none" '
                f'stroke="{MINT}" stroke-width="1"/>'
            )
        if core:
            parts.append(f'<circle cx="{_n(cx)}" cy="{_n(cy)}" r="1.4" fill="{core}"/>')
    # lozenge beak and a heat-sink breast stepped like an inverted ziggurat
    parts.append(f'<polygon points="32,38 35,41 32,44 29,41" fill="{GOLD}"/>')
    for i, (x, w) in enumerate(((20, 24), (23, 18), (26, 12))):
        parts.append(f'<rect x="{x}" y="{48 + i * 4}" width="{w}" height="2.5" fill="{COPPER}"/>')
    parts.append("</svg>")
    return "".join(parts)


def owl_css() -> str:
    """The ``<style>`` block the avatar's layout and sweep animation need."""
    return _CSS


def owl_html(
    state: OwlState = "idle",
    label: str | None = None,
    detail: str | None = None,
    size: int = 56,
    working: bool | None = None,
) -> str:
    """
    Return the owl with a status label beside it, ready for ``st.markdown(..., unsafe_allow_html=True)``.

    :param state: owl state.
    :param label: short status, shown in wide-tracked capitals; defaults to the state name.
    :param detail: optional second line (for example "4 KGs · top 4 each").
    :param size: avatar size in pixels.
    :param working: animate the sweep; defaults to True while retrieving.
    """
    if working is None:
        working = state == "retrieving"
    text = escape(label or state)
    detail_html = f'<div class="kgowl-detail">{escape(detail)}</div>' if detail else ""
    return (
        f"{_CSS}"
        f'<div class="kgowl">{owl_svg(state, size=size, working=working)}'
        # The label keeps the theme's text colour for contrast on light and dark
        # themes; the state colour rides on a diamond terminal beside it.
        f'<div><div class="kgowl-label"><span class="kgowl-pip" '
        f'style="background:{STATE_COLOR[state]}"></span>{text}</div>'
        f"{detail_html}</div></div>"
    )

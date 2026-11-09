"""
test_owl.py

Unit tests for kg_rag.owl — the owl avatar SVG and its status HTML.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET

import pytest

from kg_rag.owl import GOLD, MINT, STATES, owl_css, owl_html, owl_svg

SVG = "{http://www.w3.org/2000/svg}"


@pytest.mark.parametrize("state", STATES)
def test_svg_is_well_formed(state):
    root = ET.fromstring(owl_svg(state))
    assert root.tag == f"{SVG}svg"
    assert root.get("viewBox") == "0 0 64 64"
    assert root.get("role") == "img"
    assert state in root.get("aria-label")
    # fourteen rays, each a line ending in a pad (Art Techno rule 3)
    rays = root.findall(f"{SVG}g[@class='kgowl-ray']")
    assert len(rays) == 14
    for ray in rays:
        assert ray.find(f"{SVG}line") is not None
        assert ray.find(f"{SVG}circle") is not None


def test_state_colours():
    assert f'stroke="{MINT}"' in owl_svg("idle")
    assert f'stroke="{GOLD}" stroke-width="1.6"' in owl_svg("answering")


def test_only_answering_eyes_are_lit():
    from kg_rag.owl import SILKSCREEN

    assert SILKSCREEN not in owl_svg("idle")
    assert SILKSCREEN not in owl_svg("retrieving")
    assert owl_svg("answering").count(f'fill="{SILKSCREEN}"') == 2


def test_working_adds_sweep():
    still = owl_svg("retrieving", working=False)
    moving = owl_svg("retrieving", working=True)
    assert "kgowl-sweep" not in still and "animation-delay" not in still
    assert 'class="kgowl-sweep"' in moving
    assert moving.count("animation-delay") == 14


def test_size_and_title():
    root = ET.fromstring(owl_svg("idle", size=40, title="KGRAG"))
    assert root.get("width") == "40" and root.get("height") == "40"
    assert root.find(f"{SVG}title").text == "KGRAG"


def test_unknown_state_raises():
    with pytest.raises(ValueError):
        owl_svg("sleeping")  # type: ignore[arg-type]


def test_html_escapes_text_and_defaults_working():
    html = owl_html("retrieving", label="<b>x</b>", detail="a & b")
    assert "&lt;b&gt;x&lt;/b&gt;" in html
    assert "a &amp; b" in html
    assert 'class="kgowl-sweep"' in html  # retrieving sweeps by default
    assert 'class="kgowl-sweep"' not in owl_html("answering")
    assert owl_css() in html
    assert "prefers-reduced-motion" in owl_css()

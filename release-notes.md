# Release Notes -- v0.18.1

> Released: 2026-11-02

A security release. The `filetree` extra installs ftree-kg, which reads
image EXIF through Pillow, and a fresh install could resolve an ftree-kg
whose range still allowed Pillow 12.3.0 and its 41 advisories. kg-rag now
floors ftree-kg at 0.18.1, which floors Pillow at 13.0.0. The lock moves to
the fleet releases cut the same day. Federation, the registry and every
command are unchanged.

## What changed

**ftree-kg 0.18.1 is the floor in `filetree` and `all`.** That is the one
fleet floor kg-rag needed to raise. The other KG packages released alongside
it changed only their 3-D extras, which kg-rag does not install, so their
floors stay where they were.

**The lock follows the fleet.** kgmodule-utils 0.29.2, pycode-kg 0.29.3,
connectome-kg 0.10.1, ftree-kg 0.18.1 and vault-kg 0.6.1, plus genealogy-kg,
swift-kg and tscode-kg in the dev group. An earlier refresh moved Pillow,
Streamlit, certifi, filelock, msgpack, setuptools and virtualenv to patched
releases.

## Upgrading

`pip install -U "kg-rag[all]"` (or the extras you use). No registry or index
changes.

---

_Full changelog: [CHANGELOG.md](CHANGELOG.md)_

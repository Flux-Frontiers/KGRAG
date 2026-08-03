#!/usr/bin/env python3
"""Fleet version state — generate or verify FLEET_VERSIONS.md.

The KG fleet declares the same sibling versions in many places: each repo's
pyproject, the container requirements*.txt files, and Dockerfile ARG pins. They
drift silently, and the drift is only ever noticed when something breaks at
runtime. This collects the actual state into one table.

  python scripts/fleet_versions.py            # print the table
  python scripts/fleet_versions.py --write    # regenerate FLEET_VERSIONS.md
  python scripts/fleet_versions.py --check    # exit 1 on internal drift (CI)

--check reports two kinds of disagreement, both real bugs:
  * a container requirement or Dockerfile ARG that contradicts its own repo's
    pyproject (e.g. corpus_pepys pinning kgmodule-utils==0.4.3 while its
    pyproject requires >=0.6.2)
  * a declared floor above the version actually published on PyPI

Author: Eric G. Suchanek, PhD
License: Elastic 2.0
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import tomllib
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

# repo dir -> distribution name
FLEET = {
    "KG_utils": "kgmodule-utils",
    "doc_kg": "doc-kg",
    "pycode_kg": "pycode-kg",
    "tscode_kg": "tscode-kg",
    "diary_kg": "diary-kg",
    "gutenberg_kg": "gutenberg-kg",
    "agent_kg": "agent-kg",
    "memory_kg": "memory-kg",
    "ftree_kg": "ftree-kg",
    "Metabo_kg": "metabo-kg",
    "ia_kg": "ia-kg",
    "kgrag": "kg-rag",
    "kg_snapshot": "kg-snapshot",
    "corpus_pepys": "corpus-pepys",
}
DISTS = set(FLEET.values())


def vkey(v: str) -> tuple[int, ...]:
    """Sortable key for a dotted version, ignoring any suffix.

    :param v: Version string such as ``0.21.1`` or ``1.12.0rc1``.
    :return: Tuple of the leading numeric components, zero-padded to three.
    """
    parts = [int(x) for x in re.findall(r"\d+", v)[:3]]
    return tuple(parts + [0] * (3 - len(parts)))


def norm(s: str) -> str:
    """Return the distribution name from a requirement string."""
    return re.split(r"[\[<>=!~; ]", s.strip().lstrip("("), maxsplit=1)[0].lower().replace("_", "-")


def constraint(s: str) -> str:
    s = re.sub(r"[()]", "", s.strip())
    m = re.match(r"[A-Za-z0-9_.\-]+(\[[^\]]*\])?(.*)", s)
    return re.sub(r"\s+", "", m.group(2)) if m else ""


def local_version(repo: Path) -> str:
    pj = repo / "pyproject.toml"
    if not pj.exists():
        return "-"
    d = tomllib.load(open(pj, "rb"))
    p = d.get("project") or d.get("tool", {}).get("poetry", {})
    return p.get("version", "-")


def pypi_version(dist: str, offline: bool = False) -> str:
    if offline:
        return "?"
    try:
        with urllib.request.urlopen(f"https://pypi.org/pypi/{dist}/json", timeout=15) as r:
            return json.load(r)["info"]["version"]
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, ValueError):
        return "not-published"


def declared(repo: Path) -> dict[str, list[tuple[str, str]]]:
    """Fleet-sibling constraints this repo declares, by source location."""
    out: dict[str, list[tuple[str, str]]] = {}
    pj = repo / "pyproject.toml"
    if pj.exists():
        d = tomllib.load(open(pj, "rb"))
        p = d.get("project", {})
        poetry = d.get("tool", {}).get("poetry", {})
        for s in p.get("dependencies", []):
            if norm(s) in DISTS:
                out.setdefault(norm(s), []).append(("pyproject core", constraint(s)))
        for k, v in (p.get("optional-dependencies") or {}).items():
            for s in v:
                if norm(s) in DISTS:
                    out.setdefault(norm(s), []).append((f"pyproject [{k}]", constraint(s)))
        for k, v in (poetry.get("dependencies") or {}).items():
            if norm(k) in DISTS:
                c = (
                    v
                    if isinstance(v, str)
                    else (v.get("version", "") if isinstance(v, dict) else "")
                )
                out.setdefault(norm(k), []).append(("pyproject [poetry]", re.sub(r"\s+", "", c)))

    for f in sorted(repo.glob("**/requirements*.txt")):
        if ".venv" in str(f) or "site-packages" in str(f):
            continue
        for ln in f.read_text().splitlines():
            ln = ln.strip()
            if not ln or ln.startswith(("#", "-")):
                continue
            if norm(ln) in DISTS:
                out.setdefault(norm(ln), []).append((str(f.relative_to(repo)), constraint(ln)))

    for df in sorted(repo.glob("**/Dockerfile*")):
        if ".venv" in str(df):
            continue
        for name, ver in re.findall(
            r"^ARG\s+([A-Z0-9_]+)_VERSION=([0-9][^\s]*)", df.read_text(), re.M
        ):
            dist = name.lower().replace("_", "-")
            if dist in DISTS:
                out.setdefault(dist, []).append((f"{df.relative_to(repo)} ARG", f"=={ver}"))
    return out


def build(offline: bool = False):
    rows, problems = [], []
    for repo, dist in FLEET.items():
        rp = ROOT / repo
        if not rp.exists():
            continue
        loc, pub = local_version(rp), pypi_version(dist, offline)
        rows.append((repo, dist, loc, pub))
    versions = {d: p for _, d, _, p in rows}

    details = {}
    for repo, _dist, _, _ in rows:
        dec = declared(ROOT / repo)
        details[repo] = dec
        for sib, entries in dec.items():
            # An exact `==V` pin (Dockerfile ARG, frozen container) is consistent
            # with a floor `>=F` as long as V satisfies F — pinning the exact
            # floor version is the correct thing for a reproducible image, not
            # drift. Compare floors against floors, and check each `==` against
            # the highest floor declared anywhere in the repo.
            floors, exacts = set(), set()
            for _, c in entries:
                if not c:
                    continue
                m = re.match(r"^>=([0-9][^,]*)", c)
                e = re.match(r"^==([0-9].*)", c)
                if m:
                    floors.add(m.group(1))
                elif e:
                    exacts.add(e.group(1))
            if len(floors) > 1:
                problems.append(
                    f"{repo}: floors disagree on {sib} -> "
                    + "; ".join(f"{w} {c}" for w, c in entries if c)
                )
            if floors and exacts:
                hi = max(floors, key=vkey)
                for e in exacts:
                    if vkey(e) < vkey(hi):
                        problems.append(
                            f"{repo}: pins {sib}=={e} but its own pyproject requires >={hi}"
                        )
            pubv = versions.get(sib, "?")
            for where, c in entries:
                m = re.match(r"^>=([0-9][^,]*)", c or "")
                if m and pubv not in ("?", "not-published"):
                    if tuple(int(x) for x in re.findall(r"\d+", m.group(1))[:3]) > tuple(
                        int(x) for x in re.findall(r"\d+", pubv)[:3]
                    ):
                        problems.append(f"{repo}: {where} requires {sib}{c} but PyPI has {pubv}")
    return rows, details, problems


def render(rows, details, problems) -> str:
    out = [
        "# Fleet Version State",
        "",
        "Generated by `scripts/fleet_versions.py` — **do not hand-edit**; re-run",
        "`python scripts/fleet_versions.py --write` after any release or floor bump.",
        "",
        "`--check` runs the same comparison and exits non-zero, for CI.",
        "",
        "## Published versions",
        "",
        "| Repo | Distribution | Local | PyPI |",
        "|---|---|---|---|",
    ]
    for repo, dist, loc, pub in rows:
        flag = "" if loc == pub or pub in ("?", "not-published") else "  ⚠️ unreleased"
        out.append(f"| `{repo}` | `{dist}` | {loc} | {pub}{flag} |")

    out += [
        "",
        "## Declared sibling constraints",
        "",
        "Every place each repo pins another fleet package — pyproject, container",
        "requirements, and Dockerfile ARGs. These must agree within a repo.",
        "",
    ]
    for repo, dec in details.items():
        if not dec:
            continue
        out += [f"### `{repo}`", "", "| Sibling | Where | Constraint |", "|---|---|---|"]
        for sib in sorted(dec):
            for where, c in dec[sib]:
                out.append(f"| `{sib}` | {where} | `{c or '(any)'}` |")
        out.append("")

    out += ["## Drift", ""]
    out += [f"- ❌ {p}" for p in problems] if problems else ["No internal disagreement detected."]
    out.append("")
    return "\n".join(out)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--offline", action="store_true", help="skip PyPI lookups")
    a = ap.parse_args()

    rows, details, problems = build(a.offline)
    text = render(rows, details, problems)

    if a.write:
        (ROOT / "kgrag" / "FLEET_VERSIONS.md").write_text(text)
        print(f"wrote FLEET_VERSIONS.md ({len(rows)} repos, {len(problems)} problems)")
    else:
        print(text)

    if a.check and problems:
        print(f"\n{len(problems)} drift problem(s)", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

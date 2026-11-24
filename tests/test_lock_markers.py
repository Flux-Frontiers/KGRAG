"""poetry.lock must install at most one version of each package per platform.

Poetry 2.5.0 and 2.5.1 write a lock that drops part of an environment marker:
with torch 2.13 the second nvidia-cublas and nvidia-cuda-nvrtc entries were
marked ``platform_system == "Linux"`` instead of "Linux, but not x86_64 or
aarch64". On a Linux x86_64 runner both versions then installed over each
other and importing torch crashed with a segmentation fault. Poetry 2.4.3
writes the full marker. This test catches such a lock before CI installs it.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

import pytest
from packaging.markers import Marker

LOCK = Path(__file__).resolve().parent.parent / "poetry.lock"

# The platforms the fleet installs on, as PEP 508 marker environments.
_BASE = {
    "implementation_name": "cpython",
    "platform_python_implementation": "CPython",
    "python_version": "3.12",
    "python_full_version": "3.12.8",
    "platform_release": "",
    "platform_version": "",
    "extra": "",
}
PLATFORMS = {
    "linux-x86_64": {
        **_BASE,
        "sys_platform": "linux",
        "platform_system": "Linux",
        "platform_machine": "x86_64",
        "os_name": "posix",
    },
    "macos-arm64": {
        **_BASE,
        "sys_platform": "darwin",
        "platform_system": "Darwin",
        "platform_machine": "arm64",
        "os_name": "posix",
    },
    "windows-amd64": {
        **_BASE,
        "sys_platform": "win32",
        "platform_system": "Windows",
        "platform_machine": "AMD64",
        "os_name": "nt",
    },
}


def _locked_packages() -> list[tuple[str, str, str | dict | None]]:
    """Return ``(name, version, markers)`` for every ``[[package]]`` in the lock.

    ``markers`` is a string, or a table of one marker per dependency group.
    """
    lock = tomllib.loads(LOCK.read_text(encoding="utf-8"))
    return [(p["name"], p["version"], p.get("markers")) for p in lock["package"]]


def _satisfied(marker: str, env: dict) -> bool:
    if marker == "<empty>":  # Poetry's spelling of a marker nothing satisfies
        return False
    return Marker(marker).evaluate(env)


def _installs(markers: str | dict | None, env: dict) -> bool:
    if markers is None:
        return True
    if isinstance(markers, dict):  # installed if any group's marker holds
        return any(_satisfied(m, env) for m in markers.values())
    return _satisfied(markers, env)


@pytest.mark.parametrize("platform", sorted(PLATFORMS))
def test_one_version_per_package(platform: str) -> None:
    env = PLATFORMS[platform]
    chosen: dict[str, list[str]] = {}
    for name, version, markers in _locked_packages():
        if _installs(markers, env):
            chosen.setdefault(name, []).append(version)
    doubled = {name: vs for name, vs in chosen.items() if len(vs) > 1}
    assert not doubled, (
        f"poetry.lock installs two versions on {platform}: {doubled}. "
        "Relock with Poetry 2.4.3 (Poetry 2.5.x drops part of the marker)."
    )

"""
config.py

Config loader for KGRAG — reads [tool.kgrag] section from pyproject.toml.
"""
from __future__ import annotations

from pathlib import Path


def load_kgrag_config(project_root: Path | str | None = None) -> dict:
    """Read [tool.kgrag] from pyproject.toml, if present.

    :param project_root: Root directory to search for pyproject.toml.
        Defaults to current working directory.
    :return: Dict with kgrag config (may be empty if no section found).
    """
    root = Path(project_root).resolve() if project_root else Path.cwd()
    pyproject = root / "pyproject.toml"
    if not pyproject.exists():
        return {}
    try:
        import tomllib  # Python 3.11+
    except ImportError:
        try:
            import tomli as tomllib  # type: ignore[no-redef]
        except ImportError:
            return {}
    with pyproject.open("rb") as f:
        data = tomllib.load(f)
    return data.get("tool", {}).get("kgrag", {})

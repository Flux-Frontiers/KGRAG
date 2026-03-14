"""
config.py

Config loader for KGRAG — reads [tool.kgrag] section from pyproject.toml.
"""

from __future__ import annotations

from pathlib import Path


def _load_toml(pyproject: Path) -> dict:
    """Parse a pyproject.toml file and return its contents as a dict.

    :param pyproject: Path to the pyproject.toml file.
    :return: Parsed dict, or empty dict if tomllib/tomli is unavailable.
    """
    try:
        import tomllib  # Python 3.11+
    except ImportError:
        try:
            import tomli as tomllib  # type: ignore[no-redef]
        except ImportError:
            return {}
    with pyproject.open("rb") as f:
        return tomllib.load(f)


def read_pyproject_version(repo_path: Path | str | None = None) -> str:
    """Read the project version from pyproject.toml, if present.

    Checks ``[project] version`` (PEP 517/518) first, then
    ``[tool.poetry] version`` as a fallback.

    :param repo_path: Root directory containing pyproject.toml.
        Defaults to current working directory.
    :return: Version string, or ``"unknown"`` if not found.
    """
    root = Path(repo_path).resolve() if repo_path else Path.cwd()
    pyproject = root / "pyproject.toml"
    if not pyproject.exists():
        return "unknown"
    data = _load_toml(pyproject)
    if not data:
        return "unknown"
    return (
        data.get("project", {}).get("version")
        or data.get("tool", {}).get("poetry", {}).get("version")
        or "unknown"
    )


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
    data = _load_toml(pyproject)
    return data.get("tool", {}).get("kgrag", {})

#!/usr/bin/env python3
"""
Generate GitHub Wiki pages for the code_kg repository.

This script creates wiki pages by processing markdown files from docs/,
article/, and README.md, structuring them appropriately for the GitHub wiki.
All content is sourced from living markdown files — no hardcoded content strings.

Usage:
    python scripts/generate_wiki.py
    python scripts/generate_wiki.py --dry-run
    python scripts/generate_wiki.py --repo Flux-Frontiers/code_kg

Author: Eric G. Suchanek, PhD
Last Revision: 2026-03-02 14:03:04
"""

import argparse
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def extract_section(
    content: str,
    heading: str,
    stop_at_next_h2: bool = True,
) -> str | None:
    """
    Extract a section from markdown content by its heading text.

    Matches headings with or without emoji prefixes (e.g. ``## Installation``
    and ``## 🚀 Installation`` both match ``heading="Installation"``).
    The search is case-insensitive.

    :param content: Full markdown document string.
    :param heading: Heading text to search for (without ``#`` markers).
    :param stop_at_next_h2: When ``True``, stop extraction at the next ``##``
        heading.  When ``False``, return from the match to the end of the
        document.
    :return: Extracted section text including the heading line, or ``None``
        if the heading is not found.
    """
    # Build a pattern that tolerates optional emoji / decoration before the
    # heading text and is case-insensitive.
    pattern = re.compile(
        r"^##\s+.*?" + re.escape(heading) + r".*?$",
        re.IGNORECASE | re.MULTILINE,
    )
    match = pattern.search(content)
    if match is None:
        return None

    start = match.start()

    if stop_at_next_h2:
        # Find the next ## heading after the matched one.
        next_h2 = re.search(r"^\s*##\s+", content[match.end() :], re.MULTILINE)
        end = match.end() + next_h2.start() if next_h2 else len(content)
    else:
        end = len(content)

    return content[start:end]


def strip_image_refs(content: str) -> str:
    """
    Remove image references from markdown content.

    Handles both Markdown syntax (``![alt](url)``) and HTML ``<img>`` tags so
    that wiki pages, which cannot resolve local repository image paths, render
    cleanly without broken image placeholders.

    :param content: Markdown string that may contain image references.
    :return: Content with all image references removed.
    """
    # Remove HTML <img ...> tags (single-line; wiki pages rarely have
    # multi-line img tags, and the centered <p><img/></p> wrappers should also
    # go away).
    content = re.sub(r"<img\s[^>]*/?>", "", content, flags=re.IGNORECASE)

    # Remove Markdown image syntax: ![alt text](url)
    content = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", content)

    # Clean up <p align="center"> wrappers that become empty after stripping
    # the img tag.  Match optional whitespace between tags.
    content = re.sub(
        r"<p[^>]*>\s*</p>",
        "",
        content,
        flags=re.IGNORECASE,
    )

    return content


# ---------------------------------------------------------------------------
# Page generators — each returns a complete wiki page string
# ---------------------------------------------------------------------------


def generate_home_page(readme_path: Path, logo_path: Path | None = None) -> str:
    """
    Generate Home.md from README.md with optional logo.

    Strips local image references and prepends a wiki navigation header with logo.

    :param readme_path: Path to README.md.
    :param logo_path: Optional path to logo image file.
    :return: Wiki-formatted home page content.
    """
    with open(readme_path, encoding="utf-8") as f:
        content = f.read()

    content = strip_image_refs(content)

    logo_section = ""
    if logo_path and logo_path.exists():
        logo_section = f"![CodeKG Logo]({logo_path.name})\n\n"

    wiki_header = f"""{logo_section}# CodeKG Wiki

**Quick Navigation:**
- [Installation](Installation) — pip, Poetry, and quick-start installer
- [CLI Reference](CLI-Reference) — all subcommands and flags
- [Architecture](Architecture) — design principles and class API
- [MCP Integration](MCP-Integration) — configure AI agents
- [Python API](Python-API) — programmatic usage
- [Deployment](Deployment) — PyPI, Streamlit Cloud, Fly.io, GitHub Releases

---

"""
    return wiki_header + content


def generate_installation_page(readme_path: Path) -> str:
    """
    Extract and return the Installation section from README.md.

    :param readme_path: Path to README.md.
    :return: Installation guide wiki page content.
    """
    with open(readme_path, encoding="utf-8") as f:
        content = f.read()

    section = extract_section(content, "Installation")
    if section is None:
        return (
            "# Installation\n\n"
            "See [README.md](https://github.com/Flux-Frontiers/code_kg/blob/main/README.md) "
            "for installation instructions."
        )

    # Promote the ## heading to a top-level # heading for the wiki page.
    page = re.sub(
        r"^##\s+.*?Installation.*?$",
        "# Installation Guide",
        section,
        count=1,
        flags=re.MULTILINE | re.IGNORECASE,
    )

    return page


def generate_cli_reference_page(readme_path: Path) -> str:
    """
    Extract and return the CLI Usage section from README.md as a standalone
    CLI Reference wiki page.

    :param readme_path: Path to README.md.
    :return: CLI Reference wiki page content.
    """
    with open(readme_path, encoding="utf-8") as f:
        content = f.read()

    section = extract_section(content, "CLI Usage")
    if section is None:
        return (
            "# CLI Reference\n\n"
            "See [README.md](https://github.com/Flux-Frontiers/code_kg/blob/main/README.md) "
            "for CLI documentation."
        )

    page = re.sub(
        r"^##\s+.*?CLI Usage.*?$",
        "# CLI Reference",
        section,
        count=1,
        flags=re.MULTILINE | re.IGNORECASE,
    )
    return page


def generate_architecture_page(docs_dir: Path) -> str:
    """
    Return the full Architecture.md document as the Architecture wiki page.

    :param docs_dir: Path to the docs/ directory.
    :return: Architecture wiki page content.
    """
    arch_path = docs_dir / "Architecture.md"
    if not arch_path.exists():
        return (
            "# Architecture\n\n"
            "See `docs/Architecture.md` in the repository for architecture details."
        )

    with open(arch_path, encoding="utf-8") as f:
        content = f.read()

    return content


def generate_mcp_integration_page(docs_dir: Path) -> str:
    """
    Return the full MCP.md document as the MCP Integration wiki page.

    :param docs_dir: Path to the docs/ directory.
    :return: MCP Integration wiki page content.
    """
    mcp_path = docs_dir / "MCP.md"
    if not mcp_path.exists():
        return (
            "# MCP Integration\n\nSee `docs/MCP.md` in the repository for MCP integration details."
        )

    with open(mcp_path, encoding="utf-8") as f:
        content = f.read()

    return content


def generate_python_api_page(docs_dir: Path) -> str:
    """
    Compose the Python API wiki page from the Architecture.md class-API
    sections (layers, orchestrator, result types).

    :param docs_dir: Path to the docs/ directory.
    :return: Python API wiki page content.
    """
    arch_path = docs_dir / "Architecture.md"
    if not arch_path.exists():
        return (
            "# Python API\n\n"
            "See `docs/Architecture.md` in the repository for the Python API reference."
        )

    with open(arch_path, encoding="utf-8") as f:
        content = f.read()

    header = """# Python API Reference

This page documents the public Python API for the `code_kg` package.
For architectural context see the [Architecture](Architecture) page.

"""

    sections = []
    for heading in (
        "Layered Class Architecture",
        "Orchestrator",
        "Result Types",
        "Dependencies",
    ):
        section = extract_section(content, heading)
        if section:
            sections.append(section)

    if not sections:
        return (
            "# Python API Reference\n\n"
            "See `docs/Architecture.md` for the full Python API reference."
        )

    return header + "\n\n---\n\n".join(sections)


def generate_deployment_page(docs_dir: Path) -> str:
    """
    Return the full deployment.md document as the Deployment wiki page.

    :param docs_dir: Path to the docs/ directory.
    :return: Deployment wiki page content.
    """
    deploy_path = docs_dir / "deployment.md"
    if not deploy_path.exists():
        return (
            "# Deployment\n\n"
            "See `docs/deployment.md` in the repository for deployment instructions."
        )

    with open(deploy_path, encoding="utf-8") as f:
        content = f.read()

    return content


def generate_sidebar_page() -> str:
    """
    Generate the GitHub wiki sidebar with navigation.

    :return: Sidebar page content.
    """
    sidebar = """## Documentation

- [Home](Home)
- [Installation](Installation)
- [CLI Reference](CLI-Reference)
- [Architecture](Architecture)
- [MCP Integration](MCP-Integration)
- [Python API](Python-API)
- [Deployment](Deployment)

## Resources

- [GitHub Repository](https://github.com/Flux-Frontiers/code_kg)
- [Medium Article](https://medium.com/@coder/code-kg)
"""
    return sidebar


# ---------------------------------------------------------------------------
# Wiki I/O helpers
# ---------------------------------------------------------------------------


def clone_wiki(repo_url: str, temp_dir: str) -> None:
    """
    Clone the wiki repository into a temporary directory.

    Authenticates via the ``gh`` CLI when available, falling back to
    ``GITHUB_TOKEN`` / ``GITHUB_PERSONAL_ACCESS_TOKEN`` environment variables,
    and finally to an unauthenticated HTTPS clone.

    :param repo_url: GitHub repository slug (e.g. ``'Flux-Frontiers/code_kg'``).
    :param temp_dir: Destination directory for the wiki clone.
    """
    github_token: str | None = None

    # Prefer the gh CLI — it always has the right scopes.
    try:
        result = subprocess.run(
            ["gh", "auth", "token"],
            capture_output=True,
            text=True,
            check=True,
        )
        github_token = result.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        github_token = os.environ.get("GITHUB_TOKEN") or os.environ.get(
            "GITHUB_PERSONAL_ACCESS_TOKEN"
        )

    if github_token:
        wiki_url = f"https://x-access-token:{github_token}@github.com/{repo_url}.wiki.git"
    else:
        wiki_url = f"https://github.com/{repo_url}.wiki.git"

    print(f"Cloning wiki from https://github.com/{repo_url}.wiki.git...")
    subprocess.run(["git", "clone", wiki_url, temp_dir], check=True)


def write_wiki_pages(wiki_dir: Path, pages: dict[str, str], logo_path: Path | None = None) -> None:
    """
    Write generated wiki pages to the cloned wiki directory.

    :param wiki_dir: Path to the local wiki clone.
    :param pages: Mapping of ``{page_name: content}`` where ``page_name`` is
        the filename without the ``.md`` extension (e.g. ``"Home"``).
    :param logo_path: Optional path to a logo file to copy to the wiki directory.
    """
    for filename, content in pages.items():
        if not filename.endswith(".md"):
            filename += ".md"

        filepath = wiki_dir / filename
        print(f"Writing {filepath}...")

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)

    if logo_path and logo_path.exists():
        dest_path = wiki_dir / logo_path.name
        print(f"Copying logo to {dest_path}...")
        shutil.copy2(logo_path, dest_path)


def commit_and_push(wiki_dir: Path) -> None:
    """
    Stage, commit, and push any changes in the wiki directory.

    Pushes to ``origin master`` (GitHub wiki default branch).
    If there are no staged changes the function prints a notice and returns
    without error.

    :param wiki_dir: Path to the local wiki clone (must be a git repository).
    """
    os.chdir(wiki_dir)

    subprocess.run(["git", "add", "."], check=True)

    result = subprocess.run(
        ["git", "diff", "--staged", "--quiet"],
        capture_output=True,
        check=False,
    )

    if result.returncode != 0:
        print("Committing changes...")
        subprocess.run(
            ["git", "commit", "-m", "Auto-generated wiki update from docs/"],
            check=True,
        )
        print("Pushing to remote...")
        subprocess.run(["git", "push", "origin", "master"], check=True)
        print("Wiki updated successfully.")
    else:
        print("No changes to commit.")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """Main execution function."""
    parser = argparse.ArgumentParser(
        description="Generate GitHub wiki pages from docs/ and README.md"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be generated without cloning or committing",
    )
    parser.add_argument(
        "--repo",
        default="Flux-Frontiers/kgrag",
        help="GitHub repository slug (default: Flux-Frontiers/code_kg)",
    )

    args = parser.parse_args()

    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    readme_path = project_root / "README.md"
    docs_dir = project_root / "docs"
    assets_dir = project_root / "assets"
    logo_path = assets_dir / "logo-md-256x256.png"

    print("Generating wiki pages...")

    pages: dict[str, str] = {
        "Home": generate_home_page(readme_path, logo_path),
        "Installation": generate_installation_page(readme_path),
        "CLI-Reference": generate_cli_reference_page(readme_path),
        "Architecture": generate_architecture_page(docs_dir),
        "MCP-Integration": generate_mcp_integration_page(docs_dir),
        "Python-API": generate_python_api_page(docs_dir),
        "Deployment": generate_deployment_page(docs_dir),
        "_Sidebar": generate_sidebar_page(),
    }

    if args.dry_run:
        print("\nDry run - would generate the following pages:")
        for name, content in pages.items():
            print(f"  - {name}.md  ({len(content)} chars)")
        print("\nPreview of Home.md (first 500 chars):")
        print(pages["Home"][:500] + "...\n")
        return

    with tempfile.TemporaryDirectory() as temp_dir:
        wiki_path = Path(temp_dir)

        try:
            clone_wiki(args.repo, str(wiki_path))
        except subprocess.CalledProcessError as e:
            print(f"Error cloning wiki: {e}")
            print(
                "\nNote: the wiki must be initialised first by creating at least one "
                "page manually through the GitHub UI."
            )
            return

        write_wiki_pages(wiki_path, pages, logo_path)

        try:
            commit_and_push(wiki_path)
        except subprocess.CalledProcessError as e:
            print(f"Error committing/pushing: {e}")
            return


if __name__ == "__main__":
    main()

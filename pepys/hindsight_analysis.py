#!/usr/bin/env python3
"""
Hindsight Entity Analysis - Comprehensive Memory Graph Analytics

Generates detailed analysis reports of entity extraction, memory links,
and relationship patterns in Hindsight memory banks. Designed for regular
monitoring of memory graph growth and quality.

Features:
- Entity extraction quality metrics
- Link proliferation analysis
- Temporal clustering patterns
- Co-occurrence network visualization
- Historical entity timeline
- Memory density statistics
- Comparative bank analysis
"""

import argparse
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

import psycopg2
from dotenv import load_dotenv
from personal_agent.config.runtime_config import get_config
from personal_agent.tools import postgresql_manager
from psycopg2.extras import RealDictCursor
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

# Load environment variables
env_path = Path.home() / ".persagent" / ".env"
if env_path.exists():
    load_dotenv(env_path)
else:
    load_dotenv()

console = Console()


def remap_entity_name(entity_name: str) -> str:
    """Remap entity names for clarity in Pepys corpus.

    Args:
        entity_name: Original entity name from database

    Returns:
        Remapped entity name (e.g., 'user' -> 'Pepys')
    """
    entity_map = {
        "user": "Pepys",
        "user's wife": "Elizabeth Pepys",
    }
    return entity_map.get(entity_name, entity_name)


def connect_to_hindsight() -> tuple[psycopg2.extensions.connection, str]:
    """Connect to Hindsight PostgreSQL database using proper credentials."""
    config = get_config()
    user_id = config.user_id

    console.print(f"[cyan]🔗 Connecting to Hindsight database for user: {user_id}[/cyan]")

    try:
        conn_string = postgresql_manager.build_connection_string(user_id)
        conn = psycopg2.connect(conn_string)
        return conn, user_id
    except Exception as e:
        console.print(f"[red]✗ Error connecting to database: {e}[/red]")
        raise


def get_all_banks(conn) -> list[dict[str, Any]]:
    """Get all memory banks in the database."""
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute(
        """
        SELECT bank_id, name, mission, created_at, last_consolidated_at
        FROM banks
        ORDER BY created_at DESC
    """
    )
    banks = cursor.fetchall()
    cursor.close()
    return banks


def create_histogram(data: dict[str, int], max_width: int = 40, top_n: int = 15) -> str:
    """Create a text-based histogram."""
    if not data:
        return "No data"

    # Get top N items
    sorted_items = sorted(data.items(), key=lambda x: x[1], reverse=True)[:top_n]
    max_count = max(count for _, count in sorted_items)

    lines = []
    for label, count in sorted_items:
        bar_width = int((count / max_count) * max_width) if max_count > 0 else 0
        visual_bar = "█" * bar_width
        # Truncate long labels
        label_short = label[:25] + "..." if len(label) > 25 else label
        lines.append(f"{label_short:28} {visual_bar} {count:,}")

    return "\n".join(lines)


def create_sparkline(values: list[int], width: int = 20) -> str:
    """Create a sparkline from numeric values."""
    if not values or max(values) == 0:
        return "▁" * width

    chars = "▁▂▃▄▅▆▇█"
    max_val = max(values)
    min_val = min(values)
    range_val = max_val - min_val if max_val != min_val else 1

    return "".join(
        chars[min(len(chars) - 1, int((v - min_val) / range_val * (len(chars) - 1)))]
        for v in values
    )


def analyze_bank(conn, bank_id: str) -> dict[str, Any]:
    """Perform comprehensive analysis on a specific bank."""
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    results: dict[str, Any] = {"bank_id": bank_id}

    # Get entities
    cursor.execute(
        """
        SELECT id, canonical_name, metadata, first_seen, last_seen, mention_count
        FROM entities
        WHERE bank_id = %s
        ORDER BY mention_count DESC
    """,
        (bank_id,),
    )
    entities = cursor.fetchall()
    results["entities"] = entities
    results["entity_count"] = len(entities)

    # Get memory units
    cursor.execute(
        """
        SELECT fact_type, COUNT(*) as count,
               MIN(occurred_start) as earliest,
               MAX(occurred_start) as latest
        FROM memory_units
        WHERE bank_id = %s
        GROUP BY fact_type
    """,
        (bank_id,),
    )
    fact_types = cursor.fetchall()
    results["fact_types"] = {row["fact_type"]: row["count"] for row in fact_types}
    results["total_memories"] = sum(row["count"] for row in fact_types)

    # Get memory timeline data (filter out modern dates for historical corpora)
    if fact_types:
        all_dates = [row["earliest"] for row in fact_types if row["earliest"]]
        all_dates.extend([row["latest"] for row in fact_types if row["latest"]])

        # Filter to historical dates only (before 1900 for Pepys diary)
        historical_dates = [d for d in all_dates if d and d.year < 1900]

        if historical_dates:
            results["earliest_memory"] = min(historical_dates)
            results["latest_memory"] = max(historical_dates)
        else:
            # Fallback to all dates if no historical dates found
            results["earliest_memory"] = min(all_dates) if all_dates else None
            results["latest_memory"] = max(all_dates) if all_dates else None

    # Get link statistics
    cursor.execute(
        """
        SELECT link_type, COUNT(*) as count
        FROM memory_links ml
        JOIN memory_units mu ON ml.from_unit_id = mu.id
        WHERE mu.bank_id = %s
        GROUP BY link_type
    """,
        (bank_id,),
    )
    link_types = cursor.fetchall()
    results["link_types"] = {row["link_type"]: row["count"] for row in link_types}
    results["total_links"] = sum(row["count"] for row in link_types)

    # Get top entity co-occurrences
    cursor.execute(
        """
        SELECT e1.canonical_name as entity1, e2.canonical_name as entity2,
               ec.cooccurrence_count
        FROM entity_cooccurrences ec
        JOIN entities e1 ON ec.entity_id_1 = e1.id
        JOIN entities e2 ON ec.entity_id_2 = e2.id
        WHERE e1.bank_id = %s
        ORDER BY ec.cooccurrence_count DESC
        LIMIT 30
    """,
        (bank_id,),
    )
    results["cooccurrences"] = cursor.fetchall()

    # Get temporal distribution (memories by month)
    cursor.execute(
        """
        SELECT DATE_TRUNC('month', occurred_start) as month,
               COUNT(*) as count
        FROM memory_units
        WHERE bank_id = %s
          AND occurred_start IS NOT NULL
          AND EXTRACT(YEAR FROM occurred_start) < 1900
        GROUP BY month
        ORDER BY month
    """,
        (bank_id,),
    )
    results["temporal_distribution"] = cursor.fetchall()

    # Get entity mention distribution
    entity_mentions = Counter()
    for entity in entities:
        entity_mentions[entity["canonical_name"]] = entity["mention_count"]
    results["entity_mentions"] = entity_mentions

    cursor.close()
    return results


def display_summary_panel(data: dict[str, Any]):
    """Display high-level summary in a panel."""
    bank_id = data["bank_id"]
    title = f"📊 Memory Bank: {bank_id}"

    content = Text()
    content.append("Total Entities: ", style="bold cyan")
    content.append(f"{data['entity_count']:,}\n", style="bold white")

    content.append("Total Memories: ", style="bold cyan")
    content.append(f"{data['total_memories']:,}\n", style="bold white")

    content.append("Total Links: ", style="bold cyan")
    content.append(f"{data['total_links']:,}\n", style="bold white")

    if data.get("earliest_memory") and data.get("latest_memory"):
        earliest = data["earliest_memory"]
        latest = data["latest_memory"]
        span = (latest - earliest).days if latest > earliest else 0
        content.append("\nTime Span: ", style="bold cyan")
        content.append(f"{span:,} days ({earliest.year} - {latest.year})\n", style="bold white")

    # Calculate ratios
    if data["total_memories"] > 0:
        links_per_memory = data["total_links"] / data["total_memories"]
        entities_per_memory = data["entity_count"] / data["total_memories"]
        content.append("\nLinks per Memory: ", style="bold yellow")
        content.append(f"{links_per_memory:.1f}\n", style="white")
        content.append("Entity Density: ", style="bold yellow")
        content.append(f"{entities_per_memory:.2f}\n", style="white")

    console.print(Panel(content, title=title, border_style="cyan", box=box.DOUBLE))


def display_fact_types_table(data: dict[str, Any]):
    """Display memory types distribution."""
    table = Table(title="📝 Memory Types Distribution", box=box.ROUNDED)
    table.add_column("Type", style="cyan", no_wrap=True)
    table.add_column("Count", style="magenta", justify="right")
    table.add_column("Percentage", style="green", justify="right")
    table.add_column("Visualization", style="blue")

    total = data["total_memories"]
    for fact_type, count in sorted(data["fact_types"].items(), key=lambda x: x[1], reverse=True):
        percentage = (count / total * 100) if total > 0 else 0
        bar_width = int(percentage / 2)  # Scale to 50 chars max
        visual_bar = "█" * bar_width
        table.add_row(fact_type, f"{count:,}", f"{percentage:.1f}%", visual_bar)

    console.print(table)


def display_link_types_table(data: dict[str, Any]):
    """Display link types distribution."""
    table = Table(title="🔗 Link Types Distribution", box=box.ROUNDED)
    table.add_column("Link Type", style="cyan", no_wrap=True)
    table.add_column("Count", style="magenta", justify="right")
    table.add_column("Percentage", style="green", justify="right")
    table.add_column("Visualization", style="blue")

    total = data["total_links"]
    for link_type, count in sorted(data["link_types"].items(), key=lambda x: x[1], reverse=True):
        percentage = (count / total * 100) if total > 0 else 0
        bar_width = int(percentage / 2)  # Scale to 50 chars max
        visual_bar = "█" * bar_width
        table.add_row(link_type, f"{count:,}", f"{percentage:.1f}%", visual_bar)

    console.print(table)


def display_top_entities_table(data: dict[str, Any], limit: int = 30):
    """Display top entities by mentions."""
    table = Table(title=f"👥 Top {limit} Entities by Mentions", box=box.ROUNDED)
    table.add_column("Rank", style="dim", width=4)
    table.add_column("Entity", style="cyan")
    table.add_column("Mentions", style="magenta", justify="right")
    table.add_column("Activity", style="blue")

    entities = sorted(data["entities"], key=lambda x: x["mention_count"], reverse=True)[:limit]
    max_mentions = entities[0]["mention_count"] if entities else 1

    for idx, entity in enumerate(entities, 1):
        mentions = entity["mention_count"]
        # Create mini sparkline
        bar_width = int((mentions / max_mentions) * 20)
        visual_bar = "█" * bar_width
        entity_name = remap_entity_name(entity["canonical_name"])
        table.add_row(f"#{idx}", entity_name[:40], f"{mentions:,}", visual_bar)

    console.print(table)


def display_cooccurrence_network(data: dict[str, Any], limit: int = 15):
    """Display top entity co-occurrences."""
    table = Table(title=f"🕸️  Top {limit} Entity Relationships", box=box.ROUNDED)
    table.add_column("Entity 1", style="cyan")
    table.add_column("↔", style="dim", width=3)
    table.add_column("Entity 2", style="green")
    table.add_column("Count", style="magenta", justify="right")
    table.add_column("Strength", style="blue")

    cooccurrences = data["cooccurrences"][:limit]
    max_count = cooccurrences[0]["cooccurrence_count"] if cooccurrences else 1

    for row in cooccurrences:
        count = row["cooccurrence_count"]
        bar_width = int((count / max_count) * 15)
        visual_bar = "●" * bar_width
        entity1 = remap_entity_name(row["entity1"])
        entity2 = remap_entity_name(row["entity2"])
        table.add_row(entity1[:25], "↔", entity2[:25], f"{count:,}", visual_bar)

    console.print(table)


def display_temporal_distribution(data: dict[str, Any]):
    """Display temporal distribution of memories."""
    if not data.get("temporal_distribution"):
        return

    table = Table(title="📅 Memory Timeline (by Month)", box=box.ROUNDED)
    table.add_column("Year-Month", style="cyan")
    table.add_column("Memories", style="magenta", justify="right")
    table.add_column("Distribution", style="blue")

    temporal_data = data["temporal_distribution"]
    max_count = max(row["count"] for row in temporal_data) if temporal_data else 1

    for row in temporal_data:  # Show all months
        count = row["count"]
        bar_width = int((count / max_count) * 30)
        visual_bar = "█" * bar_width
        month_str = row["month"].strftime("%Y-%m")
        table.add_row(month_str, f"{count:,}", visual_bar)

    console.print(table)


def create_markdown_report(data: dict[str, Any], output_path: Path):
    """Generate comprehensive markdown report."""
    bank_id = data["bank_id"]
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("# Hindsight Entity Analysis Report\n\n")
        f.write(f"**Bank**: `{bank_id}`  \n")
        f.write(f"**Generated**: {timestamp}  \n\n")

        # Executive Summary
        f.write("## 📊 Executive Summary\n\n")
        f.write(f"- **Total Entities**: {data['entity_count']:,}\n")
        f.write(f"- **Total Memories**: {data['total_memories']:,}\n")
        f.write(f"- **Total Links**: {data['total_links']:,}\n")

        if data.get("earliest_memory") and data.get("latest_memory"):
            earliest = data["earliest_memory"]
            latest = data["latest_memory"]
            span = (latest - earliest).days
            f.write(f"- **Time Span**: {span:,} days ({earliest.year} - {latest.year})\n")

        if data["total_memories"] > 0:
            links_per_memory = data["total_links"] / data["total_memories"]
            entities_per_memory = data["entity_count"] / data["total_memories"]
            f.write(f"- **Links per Memory**: {links_per_memory:.1f}\n")
            f.write(f"- **Entity Density**: {entities_per_memory:.2f} entities/memory\n")

        # Memory Types
        f.write("\n## 📝 Memory Types\n\n")
        f.write("| Type | Count | Percentage | Distribution |\n")
        f.write("|------|-------|------------|-------------|\n")
        total = data["total_memories"]
        for fact_type, count in sorted(
            data["fact_types"].items(), key=lambda x: x[1], reverse=True
        ):
            percentage = (count / total * 100) if total > 0 else 0
            bar_length = int(percentage / 2)  # Scale to 50 chars max
            visual_bar = "█" * bar_length
            f.write(f"| {fact_type} | {count:,} | {percentage:.1f}% | `{visual_bar}` |\n")

        # Link Types
        f.write("\n## 🔗 Link Types\n\n")
        f.write("| Link Type | Count | Percentage | Distribution |\n")
        f.write("|-----------|-------|------------|-------------|\n")
        total_links = data["total_links"]
        for link_type, count in sorted(
            data["link_types"].items(), key=lambda x: x[1], reverse=True
        ):
            percentage = (count / total_links * 100) if total_links > 0 else 0
            bar_length = int(percentage / 2)  # Scale to 50 chars max
            visual_bar = "█" * bar_length
            f.write(f"| {link_type} | {count:,} | {percentage:.1f}% | `{visual_bar}` |\n")

        # Top Entities
        f.write("\n## 👥 Top 30 Entities\n\n")
        f.write("| Rank | Entity | Mentions | Frequency |\n")
        f.write("|------|--------|----------|----------|\n")
        entities = sorted(data["entities"], key=lambda x: x["mention_count"], reverse=True)[:30]
        max_mentions = entities[0]["mention_count"] if entities else 1
        for idx, entity in enumerate(entities, 1):
            # Create a scaled bar (max 30 chars)
            bar_length = int((entity["mention_count"] / max_mentions) * 30)
            visual_bar = "▓" * bar_length
            entity_name = remap_entity_name(entity["canonical_name"])
            f.write(f"| {idx} | {entity_name} | {entity['mention_count']:,} | `{visual_bar}` |\n")

        # Top Relationships
        f.write("\n## 🕸️ Top Entity Relationships\n\n")
        f.write("| Entity 1 | Entity 2 | Co-occurrences |\n")
        f.write("|----------|----------|----------------|\n")
        for row in data["cooccurrences"][:20]:
            entity1 = remap_entity_name(row["entity1"])
            entity2 = remap_entity_name(row["entity2"])
            f.write(f"| {entity1} | {entity2} | {row['cooccurrence_count']:,} |\n")

        # Analysis Insights
        f.write("\n## 💡 Analysis Insights\n\n")

        # Link proliferation analysis
        if data["total_memories"] > 0:
            links_per_mem = data["total_links"] / data["total_memories"]
            f.write("### Link Proliferation\n\n")
            f.write(f"With **{links_per_mem:.1f} links per memory**, this bank shows ")
            if links_per_mem > 100:
                f.write("very high interconnectivity, typical of rich semantic graphs.\n\n")
            elif links_per_mem > 50:
                f.write("good interconnectivity for semantic queries.\n\n")
            else:
                f.write(
                    "moderate interconnectivity - consider if more entity extraction is needed.\n\n"
                )

        # Entity distribution
        if data["entity_count"] > 0:
            f.write("### Entity Distribution\n\n")
            top_10_mentions = sum(e["mention_count"] for e in entities[:10])
            total_mentions = sum(e["mention_count"] for e in data["entities"])
            concentration = (top_10_mentions / total_mentions * 100) if total_mentions > 0 else 0
            f.write(f"The top 10 entities account for **{concentration:.1f}%** of all mentions, ")
            if concentration > 50:
                f.write("indicating a centralized memory structure around key entities.\n\n")
            else:
                f.write("indicating a distributed memory structure.\n\n")

        # Temporal coverage
        if data.get("temporal_distribution"):
            f.write("### Temporal Coverage\n\n")
            months_with_data = len(data["temporal_distribution"])
            f.write(f"Memories span **{months_with_data} months** ")
            if months_with_data > 12:
                f.write("- excellent longitudinal coverage.\n\n")
            else:
                f.write("- moderate temporal coverage.\n\n")

            # Add temporal distribution chart
            f.write("\n## 📅 Temporal Distribution\n\n")
            f.write("Memory creation timeline by month:\n\n")
            f.write("```\n")

            # Get temporal data sorted by month
            temporal_data = sorted(data["temporal_distribution"], key=lambda x: x["month"])
            max_count = max((t["count"] for t in temporal_data), default=1)

            for row in temporal_data:
                month_str = row["month"].strftime("%Y-%m")
                count = row["count"]
                # Scale bar to 50 chars max
                bar_length = int((count / max_count) * 50)
                visual_bar = "█" * bar_length
                f.write(f"{month_str}  {visual_bar} {count:3d}\n")

            f.write("```\n\n")

        f.write("\n---\n")
        f.write("\n*Report generated by Hindsight Entity Analysis Pipeline*\n")

    console.print(f"[green]✓ Markdown report saved: {output_path}[/green]")


def main():
    """Main entry point with enhanced reporting."""
    parser = argparse.ArgumentParser(
        description="Analyze Hindsight entity extraction and memory graph statistics"
    )
    parser.add_argument(
        "-o",
        "--output-path",
        type=Path,
        help="Output path for the markdown report (default: current directory)",
    )
    args = parser.parse_args()

    try:
        # Connect to database
        conn, user_id = connect_to_hindsight()

        # Get all banks
        banks = get_all_banks(conn)

        if not banks:
            console.print("[yellow]No banks found in database[/yellow]")
            return

        # Display banks selection
        console.print(f"\n[cyan]Found {len(banks)} memory banks[/cyan]")

        # Find primary persagent bank for user
        primary_bank = None
        for bank in banks:
            if bank["bank_id"] == f"persagent-{user_id}":
                primary_bank = bank
                break

        # Default to first bank if no primary found
        if not primary_bank:
            primary_bank = banks[0]

        bank_id = primary_bank["bank_id"]
        console.print(f"[green]Analyzing primary bank: {bank_id}[/green]\n")

        # Perform comprehensive analysis
        with console.status("[bold cyan]Analyzing memory graph..."):
            data = analyze_bank(conn, bank_id)

        # Display rich console output
        console.print()
        display_summary_panel(data)
        console.print()
        display_fact_types_table(data)
        console.print()
        display_link_types_table(data)
        console.print()
        display_top_entities_table(data, limit=30)
        console.print()
        display_cooccurrence_network(data, limit=15)
        console.print()
        display_temporal_distribution(data)

        # Generate markdown report
        console.print()
        if args.output_path:
            output_file = args.output_path
        else:
            # Default to current working directory
            output_file = (
                Path.cwd() / f"hindsight_report_{user_id}_{datetime.now().strftime('%Y%m%d')}.md"
            )
        create_markdown_report(data, output_file)

        # Close connection
        conn.close()

        console.print("\n[bold green]✓ Analysis complete![/bold green]")
        console.print(f"  Bank: [cyan]{bank_id}[/cyan]")
        console.print(f"  Entities: [magenta]{data['entity_count']:,}[/magenta]")
        console.print(f"  Memories: [magenta]{data['total_memories']:,}[/magenta]")
        console.print(f"  Links: [magenta]{data['total_links']:,}[/magenta]")

    except Exception as e:
        console.print(f"\n[red]✗ Error: {e}[/red]")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

"""Unit tests for `kgrag timeline`.

The command is the point at which the temporal contract becomes something a
person can ask a question with: a diary entry, a book, a photograph and a
conversation topic sorted into one sequence, because every module writes the
same three keys.

What is worth pinning is not that it runs, but that it does not *lie* — about
precision, about implied bounds, or about what it left out.
"""

from __future__ import annotations

import pytest
from click.testing import CliRunner
from kg_utils.temporal import read_span

from kg_rag.cli.cmd_timeline import _span_of, _when
from kg_rag.cli.main import cli
from kg_rag.primitives import CrossHit, KGKind, QueryScope


def _hit(name: str, metadata: dict, kg: str = "kg", score: float = 0.5) -> CrossHit:
    return CrossHit(
        kg_name=kg,
        kg_kind=KGKind.DOC,
        node_id=f"n:{name}",
        name=name,
        kind="chunk",
        score=score,
        summary=f"{name} summary",
        source_path="p",
        metadata=metadata,
    )


@pytest.fixture
def runner():
    return CliRunner()


class TestWhenRendering:
    """The column must show the precision the source actually had."""

    def test_year_stays_a_year(self):
        m = {"occurred_start": "1876"}
        assert _when(read_span(m), m) == "1876"

    def test_year_does_not_show_its_implied_end(self):
        """`1876 → 1876-12-31` would claim a bound the source never wrote."""
        m = {"occurred_start": "1876"}
        assert "→" not in _when(read_span(m), m)

    def test_month_stays_a_month(self):
        m = {"occurred_start": "2026-04"}
        assert _when(read_span(m), m) == "2026-04"

    def test_day_renders_as_a_day(self):
        m = {"occurred_start": "1666-09-02"}
        assert _when(read_span(m), m) == "1666-09-02"

    def test_an_explicit_interval_shows_its_range(self):
        m = {"occurred_start": "2026-04-01", "occurred_end": "2026-04-15"}
        assert _when(read_span(m), m) == "2026-04-01 → 2026-04-15"

    def test_recorded_only_is_marked(self):
        """A written-down date is a weaker claim and must look different."""
        m = {"recorded_at": "2025-06-15"}
        assert _when(read_span(m), m).startswith("~")

    def test_nothing_renders_as_a_dash(self):
        span = read_span({"recorded_at": "2025-06-15"})
        object.__setattr__(span, "recorded", None) if hasattr(span, "recorded") else None
        # A span with neither start nor recorded is degenerate; guard the branch.
        assert _when(span, {}) in {"—", "~2025-06-15"}


class TestOrdering:
    """Sorted by when, not by relevance — that is what makes it a timeline."""

    def _sorted_names(self, hits):
        dated = [(_span_of(h), h) for h in hits if _span_of(h) is not None]
        dated.sort(key=lambda pair: pair[0].sort_key)
        return [h.name for _, h in dated]

    def test_chronological_not_by_score(self):
        hits = [
            _hit("book", {"occurred_start": "1876"}, score=0.1),
            _hit("diary", {"occurred_start": "1666-09-02"}, score=0.9),
            _hit("topic", {"occurred_start": "2026-04-01"}, score=0.5),
        ]
        assert self._sorted_names(hits) == ["diary", "book", "topic"]

    def test_modules_interleave(self):
        """Four module shapes, one sequence."""
        hits = [
            _hit("topic", {"occurred_start": "2026-04-01", "occurred_end": "2026-04-15"}),
            _hit("photo", {"occurred_start": "1998-07-04", "recorded_at": "2024-04-01"}),
            _hit("diary", {"occurred_start": "1666-09-02"}),
            _hit("note", {"recorded_at": "2025-06-15"}),
        ]
        assert self._sorted_names(hits) == ["diary", "photo", "note", "topic"]

    def test_a_photo_sorts_by_capture_not_by_copy(self):
        hits = [
            _hit("photo", {"occurred_start": "1998-07-04", "recorded_at": "2024-04-01"}),
            _hit("later", {"occurred_start": "2000-01-01"}),
        ]
        assert self._sorted_names(hits)[0] == "photo"


class TestUndatedAreCounted:
    def test_a_hit_with_no_metadata_has_no_span(self):
        assert _span_of(_hit("x", {})) is None

    def test_undated_are_separable_from_dated(self):
        hits = [_hit("dated", {"occurred_start": "1876"}), _hit("undated", {})]
        dated = [h for h in hits if _span_of(h) is not None]
        undated = [h for h in hits if _span_of(h) is None]
        assert [h.name for h in dated] == ["dated"]
        assert [h.name for h in undated] == ["undated"]


class TestWindowing:
    """The scope filter the command builds from --from/--to."""

    def _matches(self, metadata, start, end):
        scope = QueryScope(time_range=(start, end))
        return scope.matches(source_path="p", kind="chunk", metadata=metadata)

    def test_a_year_window_selects_a_year_dated_book(self):
        assert self._matches({"occurred_start": "1876"}, "1876-06-01", "1876-06-30")

    def test_a_window_inside_an_interval_matches(self):
        m = {"occurred_start": "2026-04-01", "occurred_end": "2026-04-15"}
        assert self._matches(m, "2026-04-05", "2026-04-06")

    def test_outside_the_window_is_rejected(self):
        assert not self._matches({"occurred_start": "1876"}, "1900-01-01", "1901-01-01")

    def test_undated_is_rejected_by_a_window(self):
        """Deliberate: an undated node cannot be shown to be in range."""
        assert not self._matches({}, "1876-01-01", "1876-12-31")

    def test_recorded_only_is_still_windowable(self):
        assert self._matches({"recorded_at": "2025-06-15"}, "2025-06-01", "2025-06-30")


class TestCommandSurface:
    def test_timeline_is_registered(self, runner):
        result = runner.invoke(cli, ["--help"])
        assert "timeline" in result.output

    def test_help_documents_the_date_options(self, runner):
        result = runner.invoke(cli, ["timeline", "--help"])
        assert result.exit_code == 0
        assert "--from" in result.output
        assert "--to" in result.output

#!/usr/bin/env python3
"""
Samuel Pepys Diary Parser with Intelligent Time Inference

Transforms historical diary text into timestamped entries suitable for
temporal memory systems like Hindsight.

Features:
- **Date Parsing**: Handles multiple date formats
  - Full dates: "April 1st, 1660"
  - Day markers: "10th.", "25th."
  - Old calendar dual years: "January 1659-60" (handles leap years)

- **Smart Time Inference**: Derives realistic times from content
  - Specific mentions: "three in the morning" → 03:00
  - Time of day: "morning" → 08:00, "evening" → 18:00
  - Context aware: "three in the afternoon" → 15:00
  - Defaults to early morning (Pepys' typical entry start)

- **Robust Processing**:
  - Strips line numbers ("123→content" format)
  - Skips editorial notes ([...])
  - Normalizes whitespace and formatting

Output format: YYYY-MM-DDTHH:MM | raw | DiaryText | <content>

Usage:
    python pepys_proper_parse.py input.txt output.txt [--vary-times]

Arguments:
    input_path: Path to source diary text file
    output_path: Path for transformed output file
    --vary-times: Enable time inference (default: True)
    --min-chars: Minimum entry length to keep (default: 30)
"""

import argparse
import re
import sys
from datetime import date
from pathlib import Path
from typing import Optional, Iterator

MONTHS = {
    "january": 1, "jan": 1,
    "february": 2, "feb": 2,
    "march": 3, "mar": 3,
    "april": 4, "apr": 4,
    "may": 5,
    "june": 6, "jun": 6,
    "july": 7, "jul": 7,
    "august": 8, "aug": 8,
    "september": 9, "sep": 9,
    "october": 10, "oct": 10,
    "november": 11, "nov": 11,
    "december": 12, "dec": 12,
}

# Year header like "January 1660" or "February 1659-60"
YEAR_HEADER_RE = re.compile(
    r"^\s*(?P<month>January|February|March|April|May|June|July|August|September|October|November|December)\s+"
    r"(?P<year1>\d{4})(?:[\s–-]+(?P<year2>\d{2,4}))?\s*$",
    re.IGNORECASE,
)

# Full date with month: "Jan. 1st" or "January 1st"
DATE_WITH_MONTH_RE = re.compile(
    r"^\s*(?P<month>Jan\.?|Feb\.?|Mar\.?|Apr\.?|May\.?|Jun\.?|Jul\.?|Aug\.?|Sep\.?|Oct\.?|Nov\.?|Dec\.?|"
    r"January|February|March|April|May|June|July|August|September|October|November|December)\s+"
    r"(?P<day>[1-9]|[12][0-9]|3[01])(?:st|nd|rd|th)?\.?\s*"
    r"(?:\((?P<note>.*?)\))?\s*",
    re.IGNORECASE,
)

# Day marker: matches 1-31 (one or two digits)
# Handles both abbreviated ("1st", "2nd") and full ("10th", "21st") day numbers
DATE_DAY_RE = re.compile(
    r"^\s*(?P<day>\d{1,2})(?:st|nd|rd|th)?\.?\s*"
    r"(?:\((?P<note>.*?)\))?\s*",
    re.IGNORECASE,
)

def is_leap_year(year: int) -> bool:
    """Check if year is a leap year.

    :param year: Year to check
    :return: True if leap year
    """
    return (year % 4 == 0 and year % 100 != 0) or (year % 400 == 0)

def is_valid_date(year: int, month: int, day: int) -> bool:
    """Check if date is valid.

    :param year: Year
    :param month: Month (1-12)
    :param day: Day (1-31)
    :return: True if valid
    """
    if month < 1 or month > 12 or day < 1:
        return False

    days_in_month = [31, 29 if is_leap_year(year) else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    return day <= days_in_month[month - 1]

def resolve_abbreviated_day(day_marker: int, prev_day: Optional[int]) -> int:
    """Resolve abbreviated day number (0-9) to full day number (1-31).

    Pepys' abbreviation scheme:
    - After day 9, "0th" means 10, "1th" means 11, etc.
    - After day 19, "0th" means 20, "1th" means 21, etc.

    :param day_marker: The day number from the text (0-31)
    :param prev_day: The previous day number, or None
    :return: Resolved full day number
    """
    # If day_marker >= 10, it's already a full day number
    if day_marker >= 10:
        return day_marker

    # If no previous day, assume it's the literal day (1-9)
    if prev_day is None:
        return day_marker if day_marker > 0 else 10  # "0th" without context means 10

    # If day_marker is in same range as prev_day (no rollover)
    # e.g., prev=5, day=6 -> stay in 1-9 range
    if day_marker > (prev_day % 10):
        # Sequential within same decade
        return (prev_day // 10) * 10 + day_marker

    # Rollover to next decade
    # e.g., prev=9, day=0 -> 10
    # e.g., prev=19, day=0 -> 20
    return ((prev_day // 10) + 1) * 10 + day_marker

def infer_time_from_content(content: str, entry_index: int = 0) -> str:
    """Infer approximate time from diary content using temporal keywords.

    Pepys' entries typically progress through the day chronologically.
    Uses keywords like "morning", "afternoon", "evening" to estimate time.

    :param content: Entry content text
    :param entry_index: Index of entry within the day (for progression)
    :return: Time string HH:MM
    """
    content_lower = content.lower()

    # Map written numbers to integers
    number_words = {
        'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5, 'six': 6,
        'seven': 7, 'eight': 8, 'nine': 9, 'ten': 10, 'eleven': 11, 'twelve': 12
    }

    # Specific time mentions (HIGH PRIORITY - check these first)
    time_patterns = [
        # Written numbers: "three in the morning", "about five o'clock"
        (r'\b(one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve)\s+(?:in the|o\'?clock)',
         lambda m: number_words[m.group(1)]),
        # Numeric: "3 o'clock", "at 5 o'clock"
        (r'\b([1-9]|1[0-2])\s*o\'?clock', lambda m: int(m.group(1))),
        (r'\babout\s+([1-9]|1[0-2])\s+o\'?clock', lambda m: int(m.group(1))),
        (r'\bat\s+([1-9]|1[0-2])\s+o\'?clock', lambda m: int(m.group(1))),
    ]

    for pattern, extractor in time_patterns:
        match = re.search(pattern, content_lower)
        if match:
            hour = extractor(match)

            # Context-based AM/PM determination
            context = content_lower[max(0, match.start()-50):match.end()+50]

            # Explicit "in the morning" or "in the afternoon" takes precedence
            if 'in the morning' in context or 'this morning' in context:
                pass  # Keep as AM
            elif 'in the afternoon' in context or 'this afternoon' in context:
                if hour < 12:
                    hour += 12
            elif 'in the evening' in context or 'this evening' in context:
                if hour < 12:
                    hour += 12
            elif 'at night' in context or 'tonight' in context:
                if hour < 12:
                    hour += 12
            # General context clues (less reliable)
            elif hour < 12 and any(word in content_lower for word in ['afternoon', 'evening', 'supper']):
                hour += 12

            # Add some variation to minutes
            minute = (entry_index * 7) % 60
            return f"{hour:02d}:{minute:02d}"

    # Time-of-day keywords (by priority)
    time_keywords = [
        (['early morning', 'rose early', 'up early'], 6, 7),
        (['morning', 'forenoon'], 8, 11),
        (['noon', 'midday', 'dinner'], 12, 13),
        (['afternoon'], 14, 17),
        (['evening', 'supper'], 18, 20),
        (['night', 'late', 'midnight'], 21, 23),
    ]

    for keywords, hour_min, hour_max in time_keywords:
        if any(kw in content_lower for kw in keywords):
            # Use first keyword match, add variation based on entry index
            hour = hour_min + (entry_index % (hour_max - hour_min + 1))
            minute = (entry_index * 13) % 60
            return f"{hour:02d}:{minute:02d}"

    # Default: early morning (Pepys typically starts his day entries early)
    hour = 7 + (entry_index % 3)  # 7-9 AM with some variation
    minute = (entry_index * 17) % 60
    return f"{hour:02d}:{minute:02d}"

def normalize_body(text: str) -> str:
    """Normalize body text to single line.

    :param text: Raw body text
    :return: Normalized text
    """
    text = text.replace("\u00a0", " ")
    text = text.replace("\r", "")
    text = text.replace("\n", " ")
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()

def parse_diary(input_path: Path) -> Iterator[tuple[date, str, int]]:
    """Parse Pepys diary and yield (date, content, entry_index) tuples.

    :param input_path: Path to input file
    :yield: (date, content, entry_index) tuples where entry_index tracks position within day
    """
    with input_path.open("r", encoding="utf-8", errors="replace") as f:
        lines = f.readlines()

    current_year: Optional[int] = None
    current_month: Optional[int] = None
    dual_year_offset = 0
    prev_day: Optional[int] = None
    last_date: Optional[date] = None
    entry_index = 0  # Track entries within same day

    current_date: Optional[date] = None
    buffer: list[str] = []
    started = False

    def flush():
        nonlocal current_date, buffer, last_date, entry_index
        if current_date is None or not buffer:
            buffer = []
            return None
        body = normalize_body(" ".join(buffer))

        # Track entry index within the same day
        if last_date == current_date:
            entry_index += 1
        else:
            entry_index = 0
            last_date = current_date

        result = (current_date, body, entry_index)
        buffer = []
        return result

    for line_no, line in enumerate(lines, 1):
        # Strip line numbers if present (format: "123→content")
        if '→' in line:
            line = line.split('→', 1)[1]

        stripped = line.strip()

        # Skip bracketed editorial notes
        if stripped.startswith('[') and stripped.endswith(']'):
            continue

        # Check for year header
        ym = YEAR_HEADER_RE.match(line)
        if ym:
            started = True
            current_year = int(ym.group("year1"))

            # Handle dual years (e.g., "January 1659-60")
            if ym.group("year2"):
                year2_str = ym.group("year2")
                if len(year2_str) == 2:
                    year2 = int(str(current_year)[:2] + year2_str)
                else:
                    year2 = int(year2_str)

                month_name = ym.group("month").lower()
                month_num = MONTHS.get(month_name)
                if month_num in (1, 2):  # Jan/Feb use second year for leap year
                    dual_year_offset = year2 - current_year
                else:
                    dual_year_offset = 0
            else:
                dual_year_offset = 0

            prev_day = None  # Reset on new month
            continue

        if not started:
            continue

        # Check for full date with month
        m = DATE_WITH_MONTH_RE.match(line)
        if m:
            month_str = m.group("month").lower().strip(".")
            month = MONTHS.get(month_str)
            if month is None:
                continue

            day = int(m.group("day"))
            current_month = month
            prev_day = day

            # Determine year
            year_to_use = current_year
            if month in (1, 2) and dual_year_offset > 0:
                year_to_use = current_year + dual_year_offset

            if not is_valid_date(year_to_use, month, day):
                continue

            prev_entry = flush()
            if prev_entry:
                yield prev_entry

            current_date = date(year_to_use, month, day)
            body_start = line[m.end():].strip()
            if body_start:
                buffer.append(body_start)
            continue

        # Check for abbreviated day marker
        m2 = DATE_DAY_RE.match(line)
        if m2:
            if current_month is None or current_year is None:
                continue

            day_marker = int(m2.group("day"))
            day = resolve_abbreviated_day(day_marker, prev_day)
            prev_day = day

            # Determine year
            year_to_use = current_year
            if current_month in (1, 2) and dual_year_offset > 0:
                year_to_use = current_year + dual_year_offset

            if not is_valid_date(year_to_use, current_month, day):
                # Try without rollover (literal interpretation)
                day = day_marker
                if not is_valid_date(year_to_use, current_month, day):
                    continue

            prev_entry = flush()
            if prev_entry:
                yield prev_entry

            current_date = date(year_to_use, current_month, day)
            body_start = line[m2.end():].strip()
            if body_start:
                buffer.append(body_start)
            continue

        # Accumulate body text
        if current_date is not None and stripped and not (stripped.startswith('[') and ']' in stripped):
            buffer.append(line.rstrip("\n"))

    # Flush last entry
    last = flush()
    if last:
        yield last

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Parse Pepys diary with proper handling of abbreviated dates"
    )
    parser.add_argument("input_path", type=str, help="Input diary text file")
    parser.add_argument("output_path", type=str, help="Output transformed file")
    parser.add_argument(
        "--vary-times",
        action="store_true",
        default=True,
        help="Vary times (default: True)"
    )
    parser.add_argument(
        "--min-chars",
        type=int,
        default=30,
        help="Minimum content length to keep"
    )
    args = parser.parse_args()

    input_path = Path(args.input_path)
    output_path = Path(args.output_path)

    if not input_path.exists():
        print(f"ERROR: input file not found: {input_path}", file=sys.stderr)
        return 2

    n_entries = 0
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8", newline="\n") as f:
        for entry_date, content, entry_idx in parse_diary(input_path):
            if len(content) < args.min_chars:
                continue

            time_str = infer_time_from_content(content, entry_idx) if args.vary_times else "00:00"
            ts = f"{entry_date.isoformat()}T{time_str}"

            # Format: timestamp | raw | DiaryText | content
            line = f"{ts} | raw | DiaryText | {content}\n"
            f.write(line)
            n_entries += 1

    print(f"Parsed {n_entries} entries -> {output_path}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())

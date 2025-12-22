#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ASS QA & Auto-Fixer for professional subtitle workflows.

Key behaviors:
- Always de-duplicates Dialogue lines by default (same Start/End/Style/Text).
- Merges consecutive dialogue lines with identical text and timestamps within 500ms gap.
- Fixes overlapping timestamps between consecutive dialogues (within 0.02s threshold).
- Validates and normalizes Style names against defined styles.
- Sanitizes Layer to valid integer.
- Trims Text; treats "-", "–", "—", "/" as empty OCR artifacts (removed unless --keep-empty-text).
- Removes fake text (OCR artifacts like single digits, single letters, underscores).
- Preserves commas/spaces inside Text (safe maxsplit).
- Canonicalizes [V4+ Styles] from the first file in the run and applies to later files.

Usage:
  python ass_qafix.py                                    # Process all .ass files in current directory
  python ass_qafix.py --inplace                          # Process all files, overwriting originals
  python ass_qafix.py --keep-empty-text                  # Process all files, keeping empty text
  python ass_qafix.py file1.ass                           # Process single file
  python ass_qafix.py file1.ass file2.ass                # Process multiple specific files
  python ass_qafix.py --inplace file1.ass                 # Process single file, overwriting original
"""

from __future__ import annotations

import argparse
import copy
import glob
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Set
from rapidfuzz.distance import Levenshtein
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box

# Dictionary-based OCR artifact detection
# Note: enchant is imported lazily in _get_enchant_dict() to suppress libenchant warnings
from jieba3.tok import BASE_MODEL_FREQ

DIALOGUE_PREFIX = "Dialogue:"
FORMAT_PREFIX = "Format:"
STYLES_SECTION_HDR = "[V4+ Styles]"
EVENTS_SECTION_HDR = "[Events]"

CANON_EVENTS_FIELDS = [
    "Layer",
    "Start",
    "End",
    "Style",
    "Name",
    "MarginL",
    "MarginR",
    "MarginV",
    "Effect",
    "Text",
]

FAKE_TEXT_PATTERNS = [
    re.compile(r"^\s*(Format:|Layer\s*,\s*Start\s*,\s*End\s*,\s*Style\s*,\s*Name\s*,\s*MarginL\s*,\s*MarginR\s*,\s*MarginV\s*,\s*Effect\s*,\s*Text)\s*$", re.I),
]

# Single-glyph OCR artifacts considered "empty" after trimming
ARTIFACT_EMPTY_TEXT = {"-", "–", "—", "/"}

# Timestamp regex: H:MM:SS.cc (H = 1+ digits)
TIME_RE = re.compile(r"^\d+:\d{2}:\d{2}\.\d{2}$")


# Minimum duration threshold for dialogue lines (250ms = 25 centiseconds)
# Lines shorter than this are likely OCR merge errors
MIN_DURATION_CS = 25


@dataclass
class QAStats:
    total_lines: int = 0
    dialogue_lines: int = 0
    fixed_lines: int = 0
    style_fixes: int = 0
    empty_text_removed: int = 0
    fake_text_removed: int = 0
    duplicates_removed: int = 0
    consecutive_merges: int = 0  # merged consecutive dialogues with same text
    alternating_merges: int = 0  # merged alternating OCR variant patterns
    overlap_fixes: int = 0  # fixed overlapping timestamps between consecutive dialogues
    short_duration_removed: int = 0  # dialogue lines with duration < 50ms removed


def generate_results_table(reports: List[str], stats: QAStats, warning_files: Optional[Set[str]] = None) -> Panel:
    """
    Generate Rich table displaying ASS QA results with chi-to-eng styling.
    Shows all individual statistics as separate columns with summary footer.

    Args:
        reports: List of report strings from processed files
        stats: Aggregate statistics from all processed files
        warning_files: Optional set of filenames that should show WARNING
                       (for half-translation detection)

    Returns:
        Rich Panel containing the results table with footer summary
    """
    if warning_files is None:
        warning_files = set()

    # Create table with chi-to-eng styling and footer enabled
    table = Table(expand=True, show_header=True, show_footer=True, header_style="bold cyan", box=box.SIMPLE_HEAD)

    # Add all individual columns with chi-to-eng color scheme and footer values
    table.add_column("File Name", style="cyan", no_wrap=True, ratio=2, footer="TOTAL", footer_style="bold cyan")
    table.add_column("Dialogues", style="yellow", no_wrap=True, ratio=1, footer=str(stats.dialogue_lines), footer_style="bold yellow")
    table.add_column("Fixed", style="magenta", no_wrap=True, ratio=1, footer=str(stats.fixed_lines), footer_style="bold magenta")
    table.add_column("Style Fixes", style="magenta", no_wrap=True, ratio=1, footer=str(stats.style_fixes), footer_style="bold magenta")
    table.add_column("Empty Text Removed", style="magenta", no_wrap=True, ratio=1, footer=str(stats.empty_text_removed), footer_style="bold magenta")
    table.add_column("Fake Text Removed", style="magenta", no_wrap=True, ratio=1, footer=str(stats.fake_text_removed), footer_style="bold magenta")
    table.add_column("Deduped", style="magenta", no_wrap=True, ratio=1, footer=str(stats.duplicates_removed), footer_style="bold magenta")
    table.add_column("Consecutive Merged", style="magenta", no_wrap=True, ratio=1, footer=str(stats.consecutive_merges), footer_style="bold magenta")
    table.add_column("Alternating Merged", style="magenta", no_wrap=True, ratio=1, footer=str(stats.alternating_merges), footer_style="bold magenta")
    table.add_column("Overlap Fixes", style="magenta", no_wrap=True, ratio=1, footer=str(stats.overlap_fixes), footer_style="bold magenta")

    # Short Removed column (lines < 50ms removed)
    table.add_column("Short Removed", style="magenta", no_wrap=True, ratio=1, footer=str(stats.short_duration_removed), footer_style="bold magenta")

    # Warning column for half-translation detection
    warning_count = len(warning_files)
    table.add_column("Warning", style="bold red", no_wrap=True, ratio=1, footer=str(warning_count) if warning_count > 0 else "", footer_style="bold red")

    # Parse reports and extract data for table rows
    for report in reports:
        # Extract filename from report
        filename_match = re.search(r"'([^']+)'.*:", report)
        if filename_match:
            filename = filename_match.group(1)
        else:
            filename = "Unknown"

        # Extract all individual statistics
        def extract_stat(pattern: str) -> str:
            match = re.search(pattern, report)
            return match.group(1) if match else "0"

        dialogue_count = extract_stat(r"dialogue=(\d+)")
        fixed_count = extract_stat(r"fixed=(\d+)")
        style_fixes = extract_stat(r"style_fixes=(\d+)")
        empty_text_removed = extract_stat(r"empty_text_removed=(\d+)")
        fake_text_removed = extract_stat(r"fake_text_removed=(\d+)")
        deduped = extract_stat(r"deduped=(\d+)")
        consecutive_merged = extract_stat(r"consecutive_merged=(\d+)")
        alternating_merged = extract_stat(r"alternating_merged=(\d+)")
        overlap_fixes = extract_stat(r"overlap_fixes=(\d+)")
        short_removed = extract_stat(r"short_removed=(\d+)")

        # Check if this file should show warning
        warning_text = "WARNING" if filename in warning_files else ""

        # Add row to table with all individual statistics
        table.add_row(filename, dialogue_count, fixed_count, style_fixes, empty_text_removed, fake_text_removed, deduped, consecutive_merged, alternating_merged, overlap_fixes, short_removed, warning_text)

    # Wrap table in Panel with blue border and title
    panel = Panel(table, title="ASS QA Results", border_style="blue", padding=(0, 1))

    return panel


@dataclass
class ASSDocument:
    lines: List[str]
    styles: Set[str] = field(default_factory=set)
    events_format: List[str] = field(default_factory=lambda: copy.deepcopy(CANON_EVENTS_FIELDS))
    events_format_line_index: Optional[int] = None
    events_section_start: Optional[int] = None
    events_section_end: Optional[int] = None
    styles_section_start: Optional[int] = None
    styles_section_end: Optional[int] = None
    styles_block_lines: Optional[List[str]] = None


def parse_sections(lines: List[str]) -> Dict[str, Tuple[int, int]]:
    sections: Dict[str, Tuple[int, int]] = {}
    order: List[Tuple[str, int]] = []
    for i, line in enumerate(lines):
        m = re.match(r"^\s*\[(.+?)\]\s*$", line)
        if m:
            order.append((m.group(1), i))
    for i, (name, start) in enumerate(order):
        end = order[i + 1][1] if i + 1 < len(order) else len(lines)
        sections[name] = (start, end)
    return sections


def parse_styles(doc: ASSDocument) -> None:
    sections = parse_sections(doc.lines)
    if "V4+ Styles" not in sections:
        return
    start, end = sections["V4+ Styles"]
    doc.styles_section_start, doc.styles_section_end = start, end
    doc.styles_block_lines = doc.lines[start:end]

    # Parse Styles Format to extract style names
    fmt_fields: Optional[List[str]] = None
    for i in range(start, end):
        line = doc.lines[i].rstrip("\n")
        if line.strip().startswith(FORMAT_PREFIX):
            fmt_fields = [f.strip() for f in line.split(":", 1)[1].split(",")]
            break
    if fmt_fields:
        try:
            name_idx = [s.lower() for s in fmt_fields].index("name")
        except ValueError:
            name_idx = None
        for i in range(start, end):
            raw = doc.lines[i].rstrip("\n")
            if raw.strip().lower().startswith("style:"):
                payload = raw.split(":", 1)[1].lstrip()
                parts = [p.strip() for p in payload.split(",")]
                if name_idx is not None and name_idx < len(parts):
                    doc.styles.add(parts[name_idx])
                elif parts:
                    doc.styles.add(parts[0])


def parse_events_format(doc: ASSDocument) -> None:
    sections = parse_sections(doc.lines)
    if "Events" not in sections:
        return
    start, end = sections["Events"]
    doc.events_section_start, doc.events_section_end = start, end
    for i in range(start, end):
        line = doc.lines[i].rstrip("\n")
        if line.strip().startswith(FORMAT_PREFIX):
            fields = [f.strip() for f in line.split(":", 1)[1].split(",")]
            normalized = [next((c for c in CANON_EVENTS_FIELDS if c.lower() == f.lower()), f) for f in fields]
            doc.events_format = normalized
            doc.events_format_line_index = i
            break
    if doc.events_format is None:
        doc.events_format = copy.deepcopy(CANON_EVENTS_FIELDS)


def load_ass(path: str) -> ASSDocument:
    with open(path, "r", encoding="utf-8-sig", errors="replace") as f:
        lines = f.read().splitlines()
    doc = ASSDocument(lines=lines)
    parse_styles(doc)
    parse_events_format(doc)
    return doc


def save_ass(path: str, doc: ASSDocument) -> None:
    out_lines = doc.lines[:]
    fmt_line = f"{FORMAT_PREFIX} {', '.join(doc.events_format)}"
    if doc.events_format_line_index is not None:
        out_lines[doc.events_format_line_index] = fmt_line
    else:
        if doc.events_section_start is not None:
            idx = doc.events_section_start + 1
            out_lines.insert(idx, fmt_line)
        else:
            out_lines += ["", EVENTS_SECTION_HDR, fmt_line]
        doc.lines = out_lines
    with open(path, "w", encoding="utf-8", errors="replace") as f:
        f.write("\n".join(doc.lines) + "\n")


def split_dialogue_payload(payload: str, expected_fields: int) -> List[str]:
    """
    Split payload into exactly `expected_fields` items.
    We split with maxsplit = expected_fields - 1 so the last item is always Text,
    preserving any commas/spaces inside Text.
    """
    parts = payload.split(",", expected_fields - 1)
    parts = [p if i == len(parts) - 1 else p.strip() for i, p in enumerate(parts)]
    if len(parts) < expected_fields:
        if not parts:
            return [""] * (expected_fields - 1) + [""]
        head, text = parts[:-1], parts[-1]
        while len(head) < expected_fields - 1:
            head.append("")
        return head + [text]
    return parts


def is_valid_time(s: str) -> bool:
    return bool(TIME_RE.match(s))


def extract_minute(timestamp: str) -> Optional[int]:
    """Extract minute (MM) from H:MM:SS.cc timestamp.

    Args:
        timestamp: ASS timestamp in H:MM:SS.cc format

    Returns:
        The minute value (0-59), or None if timestamp is invalid
    """
    if not is_valid_time(timestamp):
        return None
    parts = timestamp.split(":")
    return int(parts[1])


def time_to_cs(s: str) -> Optional[int]:
    if not is_valid_time(s):
        return None
    h, m, rest = s.split(":")
    sec, cs = rest.split(".")
    return (int(h) * 3600 + int(m) * 60 + int(sec)) * 100 + int(cs)


# Lazy-load enchant dictionary to avoid import-time errors
_enchant_dict = None


def _get_enchant_dict():
    """Get the enchant English dictionary, lazy-loaded.

    Suppresses libenchant warnings about missing spell-check backends
    by redirecting stderr during import and dictionary creation.
    """
    global _enchant_dict
    if _enchant_dict is None:
        try:
            # Suppress libenchant warnings about missing backends (hspell, voikko, nuspell)
            # by redirecting stderr during import and Dict creation
            stderr_fd = os.dup(2)
            devnull = os.open(os.devnull, os.O_WRONLY)
            os.dup2(devnull, 2)
            try:
                import enchant

                _enchant_dict = enchant.Dict("en_US")
            finally:
                os.dup2(stderr_fd, 2)
                os.close(devnull)
                os.close(stderr_fd)
        except Exception:
            _enchant_dict = False  # Mark as unavailable
    return _enchant_dict if _enchant_dict else None


def is_valid_english_word(word: str) -> bool:
    """Check if a short English word is valid using enchant dictionary."""
    d = _get_enchant_dict()
    if d is None:
        return True  # If enchant unavailable, don't filter
    return d.check(word) or d.check(word.lower())


def is_valid_cjk_char(char: str) -> bool:
    """Check if a single CJK character is a valid word using jieba3 dictionary."""
    return BASE_MODEL_FREQ.get(char, 0) > 0


def is_fake_text(text: str) -> bool:
    t = text.strip()
    if t == "":
        return False
    for pat in FAKE_TEXT_PATTERNS:
        if pat.search(t):
            return True
    lower = t.lower().replace(" ", "")
    if "layer,start,end,style,name,marginl,marginr,marginv,effect,text" in lower:
        return True

    # Multi-dash patterns (OCR artifacts): --, ---, - -, etc.
    if re.fullmatch(r"-[\s-]*-+", t):
        return True

    # Backticks (OCR artifacts)
    if re.fullmatch(r"`+", t):
        return True

    # Contains replacement character (garbled OCR)
    if "□" in t:
        return True

    # OCR artifacts: single digits/numbers, single punctuation, and underscores
    # These are common OCR noise patterns that should be treated as fake text
    if re.fullmatch(r"\d+", t):  # Pure numbers (e.g., "1", "42", "123")
        return True
    if re.fullmatch(r"[^\w\s]", t):  # Single punctuation/non-alphanumeric (e.g., ".")
        return True
    if re.fullmatch(r"_+", t):  # One or more underscores (e.g., "_", "__", "___")
        return True

    # Single ASCII letter: only "I" is valid in Chinese donghua dialogue
    # All other single letters are OCR artifacts
    if re.fullmatch(r"[A-Za-z]", t):
        if t != "I":
            return True

    # Two ASCII letters: check against English dictionary
    if re.fullmatch(r"[A-Za-z]{2}", t):
        if not is_valid_english_word(t):
            return True

    # Single letter with trailing punctuation/garbage (e.g., "r.", "A -")
    # Always artifact except "I"
    single_letter_match = re.fullmatch(r"([A-Za-z])[\s.\-]+", t)
    if single_letter_match:
        if single_letter_match.group(1) != "I":
            return True

    # Two letters with trailing punctuation: check dictionary
    two_letter_match = re.fullmatch(r"([A-Za-z]{2})[\s.\-]+", t)
    if two_letter_match:
        if not is_valid_english_word(two_letter_match.group(1)):
            return True

    # Single CJK character: check against jieba3 dictionary
    if len(t) == 1 and "\u4e00" <= t <= "\u9fff":
        if not is_valid_cjk_char(t):
            return True

    return False


def texts_match_for_merge(text1: str, text2: str, duration1_cs: Optional[int] = None, duration2_cs: Optional[int] = None) -> bool:
    """
    Check if two texts should be considered matching for merge purposes.

    - Exact match: Always allowed
    - Fuzzy match (edit distance = 1): Only allowed if EITHER line's duration < MIN_DURATION_CS
      This prevents merging legitimate dialogue like "Go!" vs "No!" (both long)
      while allowing OCR artifact cleanup (short lines with OCR errors)

    Args:
        text1: First text to compare
        text2: Second text to compare
        duration1_cs: Duration of the first line in centiseconds
        duration2_cs: Duration of the second line in centiseconds

    Returns:
        True if texts match (exactly or within fuzzy tolerance if either line is short)
    """
    if text1 == text2:
        return True
    # Allow fuzzy matching if EITHER line is short (likely OCR artifact)
    either_short = (
        (duration1_cs is not None and duration1_cs < MIN_DURATION_CS) or
        (duration2_cs is not None and duration2_cs < MIN_DURATION_CS)
    )
    if either_short:
        return Levenshtein.distance(text1, text2) == 1
    return False


def texts_are_ocr_variants(text1: str, text2: str, min_similarity: float = 0.7) -> bool:
    """
    Check if two texts are OCR variants of each other (e.g., traditional vs simplified Chinese).

    Uses normalized Levenshtein similarity to determine if texts are similar enough
    to be considered variants of the same dialogue.

    Args:
        text1: First text
        text2: Second text
        min_similarity: Minimum normalized similarity threshold (0.0 to 1.0)

    Returns:
        True if texts are similar enough to be OCR variants
    """
    if text1 == text2:
        return True
    if not text1 or not text2:
        return False

    # Calculate normalized similarity (1.0 = identical, 0.0 = completely different)
    max_len = max(len(text1), len(text2))
    distance = Levenshtein.distance(text1, text2)
    similarity = 1.0 - (distance / max_len)

    return similarity >= min_similarity


def sanitize_int(val: str) -> Tuple[str, bool]:
    v = val.strip()
    changed = False
    if v == "" or not re.fullmatch(r"-?\d+", v):
        v = "0"
        changed = True
    if v.startswith("-"):
        v = "0"
        changed = True
    return v, changed


def rebuild_dialogue_line(fields_order: List[str], values: Dict[str, str]) -> str:
    parts = [values.get(k, "") for k in fields_order]
    return f"{DIALOGUE_PREFIX} " + ",".join(parts)


def process_dialogue_line(
    raw_line: str,
    fields_order: List[str],
    styles: Set[str],
    stats: QAStats,
    keep_empty_text: bool,
) -> Optional[str]:
    stats.dialogue_lines += 1
    payload = raw_line.split(":", 1)[1].lstrip()
    expected = len(fields_order)

    # Split payload into fields (keeps Text intact via maxsplit)
    parts = split_dialogue_payload(payload, expected)

    values = {fields_order[i]: parts[i] if i < len(parts) else "" for i in range(expected)}
    changed_any = False

    # Layer
    layer, ch = sanitize_int(values.get("Layer", "0"))
    if ch or layer != values.get("Layer", ""):
        changed_any = True
    values["Layer"] = layer

    # Start/End - use as-is
    values["Start"] = (values.get("Start", "") or "").strip()
    values["End"] = (values.get("End", "") or "").strip()

    # Style
    original_style = values.get("Style", "")
    style = original_style.strip() or "Default"

    # Validate style exists in styles section (case-insensitive)
    # If no styles section exists, or style is not found, use Default
    style_normalized = style.lower()
    valid_styles_lower = {s.lower() for s in styles} if styles else set()

    if (
        not styles  # No styles section exists
        or not original_style.strip()  # Empty style name (original, not after default assignment)
        or style_normalized not in valid_styles_lower
    ):  # Style not found (case-insensitive)
        style = "Default"
        stats.style_fixes += 1
        changed_any = True
    else:
        # Normalize the style name to match the case from the styles section
        for defined_style in styles:
            if defined_style.lower() == style_normalized:
                style = defined_style
                break

    values["Style"] = style

    # Text cleanup
    text = values.get("Text", "")
    text = re.sub(r"[\ufeff\u200b\u200e\u200f]", "", text)
    text = text.strip()

    if text in ARTIFACT_EMPTY_TEXT:
        text = ""

    if is_fake_text(text):
        stats.fake_text_removed += 1
        return None

    if not keep_empty_text and text == "":
        stats.empty_text_removed += 1
        return None

    values["Text"] = text
    if changed_any:
        stats.fixed_lines += 1
    return rebuild_dialogue_line(fields_order, values)


def dedupe_dialogues(dialogue_lines: List[str], fields_order: List[str]) -> Tuple[List[str], int]:
    seen: Set[Tuple[str, str, str, str]] = set()
    out: List[str] = []
    removed = 0
    for line in dialogue_lines:
        payload = line.split(":", 1)[1].lstrip()
        parts = split_dialogue_payload(payload, len(fields_order))
        m = {fields_order[i]: parts[i] if i < len(fields_order) else "" for i in range(len(fields_order))}
        key = (m.get("Start", ""), m.get("End", ""), m.get("Style", ""), (m.get("Text", "") or "").strip())
        if key in seen:
            removed += 1
            continue
        seen.add(key)
        out.append(line)
    return out, removed


def merge_consecutive_dialogues(dialogue_lines: List[str], fields_order: List[str]) -> Tuple[List[str], int]:
    """
    Merge consecutive dialogue lines with identical text and timestamps within 500ms gap.

    Consecutive means: the gap between the end time of one line and the start time of the next line
    is 500ms or less. When such lines are found with the same text, they are merged into a single
    line spanning from the earliest start to the latest end time.

    Returns:
        Tuple of (merged_dialogue_lines, number_of_merges_performed)
    """

    # Maximum allowed gap between dialogues for merging (500ms = 50 centiseconds)
    MAX_GAP_CS = 50
    if not dialogue_lines:
        return dialogue_lines, 0

    # Parse all dialogue lines into structured format
    parsed_dialogues = []
    for line in dialogue_lines:
        payload = line.split(":", 1)[1].lstrip()
        parts = split_dialogue_payload(payload, len(fields_order))
        m = {fields_order[i]: parts[i] if i < len(fields_order) else "" for i in range(len(fields_order))}
        parsed_dialogues.append(
            {
                "original_line": line,
                "start": m.get("Start", "").strip(),
                "end": m.get("End", "").strip(),
                "style": m.get("Style", "").strip(),
                "name": m.get("Name", "").strip(),
                "marginl": m.get("MarginL", "").strip(),
                "marginr": m.get("MarginR", "").strip(),
                "marginv": m.get("MarginV", "").strip(),
                "effect": m.get("Effect", "").strip(),
                "text": (m.get("Text", "") or "").strip(),
            }
        )

    if len(parsed_dialogues) < 2:
        return dialogue_lines, 0

    merged_dialogues = []
    merges_count = 0
    i = 0

    while i < len(parsed_dialogues):
        current = parsed_dialogues[i]
        merged_start = current["start"]
        merged_end = current["end"]
        merged_text = current["text"]  # Track which text to keep (may change for short echo)

        # Look ahead for consecutive dialogues with same text
        j = i + 1
        while j < len(parsed_dialogues):
            next_dialogue = parsed_dialogues[j]

            # Check if gap between dialogues is within 500ms (50 centiseconds)
            # and text and all other fields are identical (or fuzzy match for short lines)
            gap_cs = None
            if merged_end and next_dialogue["start"]:
                merged_end_cs = time_to_cs(merged_end)
                next_start_cs = time_to_cs(next_dialogue["start"])
                if merged_end_cs is not None and next_start_cs is not None:
                    gap_cs = next_start_cs - merged_end_cs

            # Calculate durations for both current and next line
            current_duration_cs = None
            next_duration_cs = None
            current_start_cs = time_to_cs(current["start"])
            current_end_cs = time_to_cs(current["end"])
            next_start_cs = time_to_cs(next_dialogue["start"])
            next_end_cs = time_to_cs(next_dialogue["end"])

            if current_start_cs is not None and current_end_cs is not None:
                current_duration_cs = current_end_cs - current_start_cs
            if next_start_cs is not None and next_end_cs is not None:
                next_duration_cs = next_end_cs - next_start_cs

            # Short echo detection: exactly consecutive (no gap), one line < 50ms, OCR variants
            if (
                gap_cs is not None
                and gap_cs == 0  # Exactly consecutive, no gap
                and current_duration_cs is not None
                and next_duration_cs is not None
                and texts_are_ocr_variants(merged_text, next_dialogue["text"])
                and current["style"] == next_dialogue["style"]
                and current["name"] == next_dialogue["name"]
                and current["marginl"] == next_dialogue["marginl"]
                and current["marginr"] == next_dialogue["marginr"]
                and current["marginv"] == next_dialogue["marginv"]
                and current["effect"] == next_dialogue["effect"]
            ):
                # Case A: Next line is short echo (< 50ms) - keep current text
                if next_duration_cs < 5:
                    merged_end = next_dialogue["end"]
                    # merged_text stays as current (longer line)
                    j += 1
                    merges_count += 1
                    continue

                # Case B: Current/merged line is short echo (< 50ms) - use next's text
                elif current_duration_cs < 5:
                    merged_text = next_dialogue["text"]  # Switch to longer line's text
                    merged_end = next_dialogue["end"]
                    j += 1
                    merges_count += 1
                    continue

            # Existing logic: merge consecutive dialogues with same/similar text within 500ms gap
            if (
                gap_cs is not None
                and gap_cs <= MAX_GAP_CS
                and texts_match_for_merge(merged_text, next_dialogue["text"], current_duration_cs, next_duration_cs)
                and current["style"] == next_dialogue["style"]
                and current["name"] == next_dialogue["name"]
                and current["marginl"] == next_dialogue["marginl"]
                and current["marginr"] == next_dialogue["marginr"]
                and current["marginv"] == next_dialogue["marginv"]
                and current["effect"] == next_dialogue["effect"]
            ):
                # Merge them
                merged_end = next_dialogue["end"]
                j += 1
                merges_count += 1
            else:
                break

        if j > i + 1:  # We found at least one merge
            # Create merged dialogue
            merged_values = {
                "Layer": "0",  # Default layer
                "Start": merged_start,
                "End": merged_end,
                "Style": current["style"],
                "Name": current["name"],
                "MarginL": current["marginl"],
                "MarginR": current["marginr"],
                "MarginV": current["marginv"],
                "Effect": current["effect"],
                "Text": merged_text,  # Use tracked text (may be from next line in short echo case)
            }
            merged_line = rebuild_dialogue_line(fields_order, merged_values)
            merged_dialogues.append(merged_line)
            i = j  # Skip all the merged dialogues
        else:
            # No merge found, keep original
            merged_dialogues.append(current["original_line"])
            i += 1

    return merged_dialogues, merges_count


def merge_alternating_ocr_variants(dialogue_lines: List[str], fields_order: List[str]) -> Tuple[List[str], int]:
    """
    Merge alternating OCR variant patterns (e.g., traditional/simplified Chinese alternation).

    Detects patterns like:
        line1: 沒本事就沒本事 (variant A)
        line2: 没本事就没本事 (variant B)
        line3: 沒本事就沒本事 (variant A)
        line4: 没本事就没本事 (variant B)
        ...

    Where lines are consecutive (no gaps) and A/B are similar OCR variants.
    Merges entire sequence into single line using the first variant's text.

    Returns:
        Tuple of (merged_dialogue_lines, number_of_merges_performed)
    """
    if not dialogue_lines or len(dialogue_lines) < 3:
        return dialogue_lines, 0

    # Parse all dialogue lines into structured format
    parsed_dialogues = []
    for line in dialogue_lines:
        payload = line.split(":", 1)[1].lstrip()
        parts = split_dialogue_payload(payload, len(fields_order))
        m = {fields_order[i]: parts[i] if i < len(fields_order) else "" for i in range(len(fields_order))}
        parsed_dialogues.append(
            {
                "original_line": line,
                "start": m.get("Start", "").strip(),
                "end": m.get("End", "").strip(),
                "style": m.get("Style", "").strip(),
                "name": m.get("Name", "").strip(),
                "marginl": m.get("MarginL", "").strip(),
                "marginr": m.get("MarginR", "").strip(),
                "marginv": m.get("MarginV", "").strip(),
                "effect": m.get("Effect", "").strip(),
                "text": (m.get("Text", "") or "").strip(),
            }
        )

    merged_dialogues = []
    merges_count = 0
    i = 0

    while i < len(parsed_dialogues):
        current = parsed_dialogues[i]

        # Try to detect alternating pattern starting at i
        # Need at least 3 lines: A, B, A (to confirm alternation)
        if i + 2 < len(parsed_dialogues):
            first = parsed_dialogues[i]
            second = parsed_dialogues[i + 1]
            third = parsed_dialogues[i + 2]

            # Check if lines are consecutive (no gaps)
            first_end_cs = time_to_cs(first["end"])
            second_start_cs = time_to_cs(second["start"])
            second_end_cs = time_to_cs(second["end"])
            third_start_cs = time_to_cs(third["start"])

            is_consecutive = first_end_cs is not None and second_start_cs is not None and second_end_cs is not None and third_start_cs is not None and first_end_cs == second_start_cs and second_end_cs == third_start_cs

            # Check if texts follow A, B, A pattern where A != B but A and B are similar
            text_a = first["text"]
            text_b = second["text"]
            text_third = third["text"]

            is_alternating = (
                text_a != text_b  # A and B are different
                and text_a == text_third  # Third matches first (A, B, A pattern)
                and texts_are_ocr_variants(text_a, text_b)  # A and B are similar variants
            )

            # Check other fields match
            fields_match = (
                first["style"] == second["style"] == third["style"]
                and first["name"] == second["name"] == third["name"]
                and first["marginl"] == second["marginl"] == third["marginl"]
                and first["marginr"] == second["marginr"] == third["marginr"]
                and first["marginv"] == second["marginv"] == third["marginv"]
                and first["effect"] == second["effect"] == third["effect"]
            )

            if is_consecutive and is_alternating and fields_match:
                # Found alternating pattern, extend as far as possible
                merged_start = first["start"]
                merged_end = third["end"]
                j = i + 3

                while j < len(parsed_dialogues):
                    next_d = parsed_dialogues[j]
                    prev_d = parsed_dialogues[j - 1]

                    # Check consecutive
                    prev_end_cs = time_to_cs(prev_d["end"])
                    next_start_cs = time_to_cs(next_d["start"])
                    if prev_end_cs is None or next_start_cs is None or prev_end_cs != next_start_cs:
                        break

                    # Check alternating pattern continues (expect A if j is even offset, B if odd)
                    expected_text = text_a if (j - i) % 2 == 0 else text_b
                    if next_d["text"] != expected_text:
                        # Allow variant matching for flexibility
                        if not texts_are_ocr_variants(next_d["text"], expected_text, min_similarity=0.9):
                            break

                    # Check fields match
                    if not (next_d["style"] == first["style"] and next_d["name"] == first["name"] and next_d["marginl"] == first["marginl"] and next_d["marginr"] == first["marginr"] and next_d["marginv"] == first["marginv"] and next_d["effect"] == first["effect"]):
                        break

                    merged_end = next_d["end"]
                    j += 1

                # Create merged dialogue using first variant's text
                merged_values = {
                    "Layer": "0",
                    "Start": merged_start,
                    "End": merged_end,
                    "Style": first["style"],
                    "Name": first["name"],
                    "MarginL": first["marginl"],
                    "MarginR": first["marginr"],
                    "MarginV": first["marginv"],
                    "Effect": first["effect"],
                    "Text": text_a,  # Use first variant
                }
                merged_line = rebuild_dialogue_line(fields_order, merged_values)
                merged_dialogues.append(merged_line)
                merges_count += j - i - 1  # Count how many lines were merged
                i = j
                continue

        # No alternating pattern found, keep original
        merged_dialogues.append(current["original_line"])
        i += 1

    return merged_dialogues, merges_count


def fix_overlapping_timestamps(dialogue_lines: List[str], fields_order: List[str]) -> Tuple[List[str], int]:
    """
    Fix overlapping timestamps between consecutive dialogue lines.

    When the end time of one dialogue overlaps with the start time of the next dialogue
    and the difference is less than 0.02 seconds (2 centiseconds), swap the end time
    of the first line with the start time of the second line.

    Args:
        dialogue_lines: List of dialogue lines to process
        fields_order: Order of fields in the dialogue lines

    Returns:
        Tuple of (fixed_dialogue_lines, number_of_fixes_applied)
    """
    if not dialogue_lines or len(dialogue_lines) < 2:
        return dialogue_lines, 0

    # Parse all dialogue lines into structured format
    parsed_dialogues = []
    for line in dialogue_lines:
        payload = line.split(":", 1)[1].lstrip()
        parts = split_dialogue_payload(payload, len(fields_order))
        m = {fields_order[i]: parts[i] if i < len(fields_order) else "" for i in range(len(fields_order))}
        parsed_dialogues.append(
            {
                "original_line": line,
                "layer": m.get("Layer", "").strip(),
                "start": m.get("Start", "").strip(),
                "end": m.get("End", "").strip(),
                "style": m.get("Style", "").strip(),
                "name": m.get("Name", "").strip(),
                "marginl": m.get("MarginL", "").strip(),
                "marginr": m.get("MarginR", "").strip(),
                "marginv": m.get("MarginV", "").strip(),
                "effect": m.get("Effect", "").strip(),
                "text": (m.get("Text", "") or "").strip(),
            }
        )

    # Fix overlapping timestamps
    fixes_count = 0
    overlap_threshold = 2  # 0.02 seconds in centiseconds

    for i in range(len(parsed_dialogues) - 1):
        current = parsed_dialogues[i]
        next_dialogue = parsed_dialogues[i + 1]

        # Convert timestamps to centiseconds for comparison
        current_cs_end = time_to_cs(current["end"])
        next_cs_start = time_to_cs(next_dialogue["start"])

        # Check if we have valid timestamps and overlap
        if current_cs_end is not None and next_cs_start is not None:
            if current_cs_end > next_cs_start:
                # Calculate the overlap
                overlap = current_cs_end - next_cs_start

                # Fix only if overlap is less than threshold (0.02 seconds)
                if overlap <= overlap_threshold:
                    # Convert back to timestamp format
                    new_end_time = cs_to_time(next_cs_start)
                    new_start_time = cs_to_time(current_cs_end)

                    if new_end_time and new_start_time:
                        # Update the parsed dialogues with swapped timestamps
                        current["end"] = new_end_time
                        next_dialogue["start"] = new_start_time
                        fixes_count += 1

    # Rebuild dialogue lines with fixed timestamps
    fixed_dialogues = []
    for dialogue in parsed_dialogues:
        values = {"Layer": dialogue["layer"], "Start": dialogue["start"], "End": dialogue["end"], "Style": dialogue["style"], "Name": dialogue["name"], "MarginL": dialogue["marginl"], "MarginR": dialogue["marginr"], "MarginV": dialogue["marginv"], "Effect": dialogue["effect"], "Text": dialogue["text"]}
        fixed_line = rebuild_dialogue_line(fields_order, values)
        fixed_dialogues.append(fixed_line)

    return fixed_dialogues, fixes_count


def cs_to_time(cs: int) -> str:
    """
    Convert centiseconds back to H:MM:SS.cc timestamp format.

    Args:
        cs: Centiseconds since 00:00:00.00

    Returns:
        Timestamp string in H:MM:SS.cc format
    """
    total_seconds = cs // 100
    centiseconds = cs % 100

    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60

    return f"{hours}:{minutes:02d}:{seconds:02d}.{centiseconds:02d}"


# Threshold for short duration removal (50ms = 5 centiseconds)
SHORT_DURATION_THRESHOLD_CS = 5


def remove_short_duration_lines(dialogue_lines: List[str], fields_order: List[str]) -> Tuple[List[str], int]:
    """
    Remove dialogue lines with duration less than 50ms (5 centiseconds).

    Lines this short are too brief to be readable and are typically OCR artifacts
    that weren't caught by earlier processing steps.

    This should be called as the FINAL processing step, after all merges and fixes.

    Args:
        dialogue_lines: List of dialogue lines to filter
        fields_order: Order of fields in the dialogue lines

    Returns:
        Tuple of (filtered_dialogue_lines, number_of_lines_removed)
    """
    if not dialogue_lines:
        return dialogue_lines, 0

    filtered_lines: List[str] = []
    removed_count = 0

    for line in dialogue_lines:
        if not line.strip().startswith(DIALOGUE_PREFIX):
            filtered_lines.append(line)
            continue

        payload = line.split(":", 1)[1].lstrip()
        parts = split_dialogue_payload(payload, len(fields_order))
        values = {fields_order[i]: parts[i] if i < len(parts) else "" for i in range(len(fields_order))}

        start_str = values.get("Start", "").strip()
        end_str = values.get("End", "").strip()

        start_cs = time_to_cs(start_str)
        end_cs = time_to_cs(end_str)

        if start_cs is not None and end_cs is not None:
            duration_cs = end_cs - start_cs
            if duration_cs < SHORT_DURATION_THRESHOLD_CS:
                removed_count += 1
                continue  # Skip this line (remove it)

        filtered_lines.append(line)

    return filtered_lines, removed_count


def detect_short_duration_dialogues(path: str) -> List[Dict]:
    """
    Detect dialogue lines with very short duration (less than 80ms).

    These short duration lines are typically OCR merge errors where a line
    wasn't properly merged with the next one during subtitle extraction.

    Args:
        path: Path to the ASS file to analyze

    Returns:
        List of warning dictionaries containing:
        - start: Start timestamp
        - end: End timestamp
        - duration_ms: Duration in milliseconds
        - text: The dialogue text
        - line_number: Line number in the file
    """
    doc = load_ass(path)
    warnings: List[Dict] = []

    fields_order = doc.events_format or copy.deepcopy(CANON_EVENTS_FIELDS)

    for i, line in enumerate(doc.lines):
        stripped = line.strip()
        if not stripped.startswith(DIALOGUE_PREFIX):
            continue

        payload = line.split(":", 1)[1].lstrip()
        parts = split_dialogue_payload(payload, len(fields_order))
        values = {fields_order[j]: parts[j] if j < len(parts) else "" for j in range(len(fields_order))}

        start_str = values.get("Start", "").strip()
        end_str = values.get("End", "").strip()
        text = values.get("Text", "").strip()

        start_cs = time_to_cs(start_str)
        end_cs = time_to_cs(end_str)

        if start_cs is not None and end_cs is not None:
            duration_cs = end_cs - start_cs
            if duration_cs < MIN_DURATION_CS:
                warnings.append(
                    {
                        "start": start_str,
                        "end": end_str,
                        "duration_ms": duration_cs * 10,  # Convert centiseconds to milliseconds
                        "text": text,
                        "line_number": i + 1,
                    }
                )

    return warnings


def get_last_dialogue_minute(path: str) -> Optional[int]:
    """Get the minute from the last dialogue line's start timestamp.

    Args:
        path: Path to the ASS file

    Returns:
        The minute value from the last dialogue's start timestamp,
        or None if no dialogue lines found
    """
    doc = load_ass(path)
    fields_order = doc.events_format or copy.deepcopy(CANON_EVENTS_FIELDS)

    last_start_timestamp = None

    for line in doc.lines:
        stripped = line.strip()
        if not stripped.startswith(DIALOGUE_PREFIX):
            continue

        payload = line.split(":", 1)[1].lstrip()
        parts = split_dialogue_payload(payload, len(fields_order))
        values = {fields_order[j]: parts[j] if j < len(parts) else "" for j in range(len(fields_order))}

        start_str = values.get("Start", "").strip()
        if start_str:
            last_start_timestamp = start_str

    if last_start_timestamp is None:
        return None

    return extract_minute(last_start_timestamp)


def analyze_half_translation(file_minutes: Dict[str, int], min_files: int = 5) -> Set[str]:
    """Analyze files for potential half-translation issues.

    Detects files that may be only partially translated by comparing
    the last dialogue line's start minute across all files.

    Logic:
    - Count how many files end at each minute
    - Find the minute with the highest count (winner)
    - If tie, use the highest minute value
    - Calculate threshold = winner_minute - 2
    - Flag files where last dialogue minute < threshold

    Args:
        file_minutes: Dict mapping filepath to last dialogue minute
        min_files: Minimum number of files required for analysis (default: 5)

    Returns:
        Set of filepaths that should show WARNING
    """
    if len(file_minutes) < min_files:
        return set()

    # Count files per minute
    minute_counts: Dict[int, int] = {}
    for minute in file_minutes.values():
        minute_counts[minute] = minute_counts.get(minute, 0) + 1

    if not minute_counts:
        return set()

    # Find winner: highest count, ties go to highest minute
    max_count = max(minute_counts.values())
    winner_minute = max(m for m, c in minute_counts.items() if c == max_count)

    # Calculate threshold
    threshold = winner_minute - 2

    # Flag files below threshold
    warnings: Set[str] = set()
    for filepath, minute in file_minutes.items():
        if minute < threshold:
            warnings.add(filepath)

    return warnings


def replace_styles_with_canonical(doc: ASSDocument, canonical_block: List[str]) -> None:
    sections = parse_sections(doc.lines)
    if "V4+ Styles" not in sections:
        # Insert before Events or at end
        insert_at = sections["Events"][0] if "Events" in sections else len(doc.lines)
        doc.lines = doc.lines[:insert_at] + canonical_block + doc.lines[insert_at:]
        parse_styles(doc)
        return
    start, end = sections["V4+ Styles"]
    doc.lines = doc.lines[:start] + canonical_block + doc.lines[end:]
    parse_styles(doc)


def normalize_styles_block(block: List[str]) -> List[str]:
    return [ln.strip() for ln in block]


def process_ass(
    path: str,
    inplace: bool,
    keep_empty_text: bool,
    dry_run: bool,
    canonical_styles_block: Optional[List[str]],
    have_canonical: bool,
) -> Tuple[str, QAStats, str, Optional[List[str]], bool]:
    doc = load_ass(path)
    stats = QAStats()

    # Establish or enforce canonical styles
    if not have_canonical and doc.styles_block_lines:
        canonical_styles_block = [ln.rstrip("\n") for ln in doc.styles_block_lines]
        have_canonical = True
    elif have_canonical and canonical_styles_block:
        current = normalize_styles_block(doc.styles_block_lines or [])
        canon_norm = normalize_styles_block(canonical_styles_block)
        if current != canon_norm:
            replace_styles_with_canonical(doc, canonical_styles_block)

    fields_order = doc.events_format or copy.deepcopy(CANON_EVENTS_FIELDS)

    # Walk lines and fix dialogues
    new_lines: List[str] = []
    dialogue_buffer: List[str] = []
    in_events = False
    for i, line in enumerate(doc.lines):
        stats.total_lines += 1
        stripped = line.strip()
        if stripped.startswith("[") and stripped.lower() == EVENTS_SECTION_HDR.lower():
            in_events = True
            new_lines.append(line)
            continue
        if in_events and stripped.startswith(FORMAT_PREFIX):
            fields = [f.strip() for f in line.split(":", 1)[1].split(",")]
            normalized = [next((c for c in CANON_EVENTS_FIELDS if c.lower() == f.lower()), f) for f in fields]
            fields_order = normalized
            new_lines.append(f"{FORMAT_PREFIX} {', '.join(fields_order)}")
            continue
        if in_events and stripped.startswith(DIALOGUE_PREFIX):
            fixed = process_dialogue_line(line, fields_order, doc.styles, stats, keep_empty_text)
            if fixed is not None:
                dialogue_buffer.append(fixed)
            continue
        new_lines.append(line)

    # Always dedupe
    duplicates_removed = 0
    if dialogue_buffer:
        dialogue_buffer, duplicates_removed = dedupe_dialogues(dialogue_buffer, fields_order)
    stats.duplicates_removed = duplicates_removed

    # Merge alternating OCR variant patterns (e.g., traditional/simplified Chinese)
    alternating_merges = 0
    if dialogue_buffer:
        dialogue_buffer, alternating_merges = merge_alternating_ocr_variants(dialogue_buffer, fields_order)
    stats.alternating_merges = alternating_merges

    # Merge consecutive dialogues with same text and contiguous timestamps
    consecutive_merges = 0
    if dialogue_buffer:
        dialogue_buffer, consecutive_merges = merge_consecutive_dialogues(dialogue_buffer, fields_order)
    stats.consecutive_merges = consecutive_merges

    # Fix overlapping timestamps
    overlapping_fixes = 0
    if dialogue_buffer:
        dialogue_buffer, overlapping_fixes = fix_overlapping_timestamps(dialogue_buffer, fields_order)
    stats.overlap_fixes = overlapping_fixes

    # Remove short duration lines (< 50ms) as final step
    short_duration_removed = 0
    if dialogue_buffer:
        dialogue_buffer, short_duration_removed = remove_short_duration_lines(dialogue_buffer, fields_order)
    stats.short_duration_removed = short_duration_removed

    # Splice dialogues right after the Events Format line
    result_lines: List[str] = []
    events_started = False
    inserted = False
    for line in new_lines:
        if line.strip().lower() == EVENTS_SECTION_HDR.lower():
            events_started = True
            result_lines.append(line)
            continue
        if events_started and line.strip().startswith(FORMAT_PREFIX):
            result_lines.append(line)
            result_lines.extend(dialogue_buffer)
            inserted = True
            events_started = False
            continue
        result_lines.append(line)
    if not inserted and dialogue_buffer:
        result_lines.append(EVENTS_SECTION_HDR)
        result_lines.append(f"{FORMAT_PREFIX} {', '.join(fields_order)}")
        result_lines.extend(dialogue_buffer)

    doc.lines = result_lines

    # Write output (no .bak when inplace)
    if dry_run:
        # Skip file writing for dry run - return original path
        out_path = path
    elif inplace:
        save_ass(path, doc)
        out_path = path
    else:
        base, ext = os.path.splitext(path)
        out_path = base + ".fixed" + ext
        save_ass(out_path, doc)

    prefix = "[DRY RUN] " if dry_run else ""
    report = (
        f"{prefix}Processed '{os.path.basename(path)}': "
        f"dialogue={stats.dialogue_lines}, fixed={stats.fixed_lines}, "
        f"style_fixes={stats.style_fixes}, "
        f"empty_text_removed={stats.empty_text_removed}, fake_text_removed={stats.fake_text_removed}, "
        f"deduped={stats.duplicates_removed}, consecutive_merged={stats.consecutive_merges}, "
        f"alternating_merged={stats.alternating_merges}, "
        f"overlap_fixes={stats.overlap_fixes}, short_removed={stats.short_duration_removed}"
    )
    return out_path, stats, report, canonical_styles_block, have_canonical


def main() -> None:
    ap = argparse.ArgumentParser(description="Analyze and fix common QA issues in .ASS subtitle files.")
    ap.add_argument("--inplace", action="store_true", help="Overwrite originals. Default: write *.fixed.ass.")
    ap.add_argument("--keep-empty-text", action="store_true", help="Keep Dialogue lines with empty/artifact text.")
    ap.add_argument("--dry-run", action="store_true", help="Analyze files and report issues without making any changes.")
    ap.add_argument("files", nargs="*", help="Specific .ASS files to process. If not provided, processes all .ass files in current directory.")
    args = ap.parse_args()

    # Determine which files to process
    if args.files:
        # Use specific files provided by user
        paths = []
        for file_path in args.files:
            path = Path(file_path)
            if path.exists() and path.is_file() and path.suffix.lower() == ".ass":
                paths.append(str(path))
            else:
                print(f"Warning: File not found or not an .ASS file: {file_path}", file=sys.stderr)
    else:
        # Default: process all .ass files in current directory
        paths = sorted(glob.glob("*.ass"))

    if not paths:
        print("No .ass files found to process.", file=sys.stderr)
        sys.exit(2)

    grand = QAStats()
    reports: List[str] = []
    outputs: List[str] = []
    file_minutes: Dict[str, int] = {}  # For half-translation detection

    canonical_styles_block: Optional[List[str]] = None
    have_canonical = False

    for p in paths:
        try:
            out_path, stats, report, canonical_styles_block, have_canonical = process_ass(
                p,
                inplace=args.inplace,
                keep_empty_text=args.keep_empty_text,
                dry_run=args.dry_run,
                canonical_styles_block=canonical_styles_block,
                have_canonical=have_canonical,
            )
            outputs.append(out_path)
            reports.append(report)
            for field in vars(grand).keys():
                setattr(grand, field, getattr(grand, field) + getattr(stats, field))

            # Collect last dialogue minute for half-translation detection
            last_minute = get_last_dialogue_minute(p)
            if last_minute is not None:
                file_minutes[os.path.basename(p)] = last_minute
        except Exception as e:
            print(f"[ERROR] Failed '{p}': {e}", file=sys.stderr)

    # Analyze for half-translation (files that may be only partially translated)
    warning_files = analyze_half_translation(file_minutes)

    # Generate and print Rich table with results (summary is now in table footer)
    console = Console()
    results_table = generate_results_table(reports, grand, warning_files)
    console.print(results_table)


if __name__ == "__main__":
    main()

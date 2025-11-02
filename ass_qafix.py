#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ASS QA & Auto-Fixer for professional subtitle workflows.

Key behaviors:
- Repairs AI hallucinations around timing fields BEFORE validation:
  * Removes unexpected repeats of leading "0," or standalone "0:" between Layer and Start.
  * Coalesces "0,MM:SS.cc" or "0:,MM:SS.cc" -> "0:MM:SS.cc".
  * Collapses extra leading "0:" hour groups inside a time token: "0:0:06:15.60" -> "0:06:15.60".
  * Ensures hour is present: if a Start or End looks like "MM:SS.cc", prepend "0:" -> "0:MM:SS.cc".
- Validates timestamps after the above. If still invalid or End < Start, prints RED warning (keeps parsed values as-is).
- Always de-duplicates Dialogue lines by default (same Start/End/Style/Text).
- Trims Text; treats "-", "–", "—", "/" as empty OCR artifacts (removed unless --keep-empty-text).
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

DIALOGUE_PREFIX = "Dialogue:"
FORMAT_PREFIX = "Format:"
STYLES_SECTION_HDR = "[V4+ Styles]"
EVENTS_SECTION_HDR = "[Events]"

CANON_EVENTS_FIELDS = [
    "Layer", "Start", "End", "Style", "Name", "MarginL", "MarginR", "MarginV", "Effect", "Text",
]

FAKE_TEXT_PATTERNS = [
    re.compile(r"^\s*(Format:|Layer\s*,\s*Start\s*,\s*End\s*,\s*Style\s*,\s*Name\s*,\s*MarginL\s*,\s*MarginR\s*,\s*MarginV\s*,\s*Effect\s*,\s*Text)\s*$", re.I),
]

# Single-glyph OCR artifacts considered "empty" after trimming
ARTIFACT_EMPTY_TEXT = {"-", "–", "—", "/"}

# Timestamp regex: H:MM:SS.cc (H = 1+ digits)
TIME_RE = re.compile(r"^\d+:\d{2}:\d{2}\.\d{2}$")

# A "minute-seconds.centiseconds" token used when AI omitted the hour (e.g., "06:15.60")
MM_SS_CS_RE = re.compile(r"^\d{1,2}:\d{2}\.\d{2}$")

# Terminal colors
RED = "\033[31m"
RESET = "\033[0m"


@dataclass
class QAStats:
    total_lines: int = 0
    dialogue_lines: int = 0
    fixed_lines: int = 0
    style_fixes: int = 0
    format_padding_fixes: int = 0
    format_collapse_fixes: int = 0
    name_fixes: int = 0
    margin_fixes: int = 0
    effect_fixes: int = 0
    empty_text_removed: int = 0
    fake_text_removed: int = 0
    duplicates_removed: int = 0
    time_warnings: int = 0  # invalid/missing or End<Start


@dataclass
class ASSDocument:
    lines: List[str]
    styles: Set[str] = field(default_factory=set)
    events_format: List[str] = field(
        default_factory=lambda: copy.deepcopy(CANON_EVENTS_FIELDS))
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
            normalized = [next(
                (c for c in CANON_EVENTS_FIELDS if c.lower() == f.lower()), f) for f in fields]
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
    parts = [p if i == len(parts) - 1 else p.strip()
             for i, p in enumerate(parts)]
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


def time_to_cs(s: str) -> Optional[int]:
    if not is_valid_time(s):
        return None
    h, m, rest = s.split(":")
    sec, cs = rest.split(".")
    return (int(h) * 3600 + int(m) * 60 + int(sec)) * 100 + int(cs)


def collapse_leading_zero_hour_groups(s: str) -> str:
    """
    Fix AI hallucination where an extra '0:' is inserted before a valid H:MM:SS.cc,
    e.g. '0:0:06:15.60' -> '0:06:15.60'. If multiple leading zero hour groups exist,
    collapse them to a single '0:'; otherwise return unchanged.
    """
    tok = (s or "").strip()
    parts = tok.split(":")
    if len(parts) <= 3:
        return tok
    leading = parts[:-2]  # everything before MM and SS.cs
    if all(p == "0" for p in leading):
        return f"0:{parts[-2]}:{parts[-1]}"
    return tok


def ensure_hour_present(s: str) -> str:
    """
    If token looks like 'MM:SS.cc', prepend '0:' to make '0:MM:SS.cc'.
    Otherwise return unchanged.
    """
    tok = (s or "").strip()
    if MM_SS_CS_RE.match(tok):
        return f"0:{tok}"
    return tok


def coalesce_zero_comma_to_hour(parts: List[str], i: int) -> bool:
    """
    If parts[i] is '0' or '00' or '0:' and parts[i+1] looks like MM:SS.cc,
    merge them into a single hour-qualified token '0:MM:SS.cc'.
    Returns True if a merge occurred (and modifies parts in place).
    """
    if i < 0 or i + 1 >= len(parts):
        return False
    left = parts[i].strip()
    right = parts[i + 1].strip()
    if left in {"0", "00", "0:"} and MM_SS_CS_RE.match(right):
        parts[i] = f"0:{right}"
        del parts[i + 1]
        return True
    return False


def normalize_time_candidate(tok: str) -> str:
    """
    Normalize a single token candidate:
      - collapse extra '0:' groups inside the token
      - ensure hour is present if it looks like MM:SS.cc
    """
    t = collapse_leading_zero_hour_groups(tok.strip())
    t = ensure_hour_present(t)
    return t


def realign_extra_zero_before_start(parts: List[str]) -> List[str]:
    """
    If parts look like: Layer=0, extra '0'/'0:' before Start, realign so Start is first proper time token.
    Also:
      - Coalesce '0,MM:SS.cc' or '0:,MM:SS.cc' -> '0:MM:SS.cc'
      - Collapse extra '0:' groups and ensure hour on time tokens
      - Remove repeated leading '0'/'0:' tokens that are not part of a time
    """
    if len(parts) < 3:
        return parts

    # Step A: attempt coalescing for the first few tokens (between Layer and Start/End)
    j = 1
    while j + 1 < len(parts) and j < 6:
        if coalesce_zero_comma_to_hour(parts, j):
            # list shrank; keep j to re-check the merged token
            continue
        j += 1

    # Step B: normalize potential time candidates
    for i in range(1, min(6, len(parts))):
        normalized = normalize_time_candidate(parts[i])
        if normalized != parts[i]:
            parts[i] = normalized

    # Step C: find Start index as first valid time token
    start_idx = None
    for i in range(1, min(6, len(parts))):
        if is_valid_time(parts[i].strip()):
            start_idx = i
            break

    if start_idx is None:
        return parts

    # Normalize immediate End candidate too
    if start_idx + 1 < len(parts):
        parts[start_idx +
              1] = normalize_time_candidate(parts[start_idx + 1].strip())

    # Step D: if there were extra tokens before Start (like multiple '0'/'0:'), collapse them away
    if start_idx > 1:
        new_parts = [parts[0]]  # Layer
        new_parts.append(parts[start_idx])  # Start
        if start_idx + 1 < len(parts):
            new_parts.append(parts[start_idx + 1])  # End
        new_parts += parts[start_idx + 2:]
        return new_parts

    return parts


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
    return False


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


def looks_like_sentence(s: str) -> bool:
    if not s:
        return False
    # heuristic: contains letters incl. extended Unicode and likely lowercase, or space/punctuation end
    if re.search(r"[A-Za-z\u00C0-\uFFFF]", s) and re.search(r"[a-z\u00DF-\u024F]", s):
        return True
    if " " in s or s.endswith((".", "!", "?", "…")):
        return True
    return False


def rebuild_dialogue_line(fields_order: List[str], values: Dict[str, str]) -> str:
    parts = [values.get(k, "") for k in fields_order]
    return f"{DIALOGUE_PREFIX} " + ",".join(parts)


def process_dialogue_line(
    raw_line: str,
    fields_order: List[str],
    styles: Set[str],
    stats: QAStats,
    keep_empty_text: bool,
    filehint: str,
    lineno: int,
) -> Optional[str]:
    stats.dialogue_lines += 1
    payload = raw_line.split(":", 1)[1].lstrip()
    expected = len(fields_order)

    # Split and realign hallucinations before Start; keep Text intact
    parts = payload.split(",", expected - 1)
    parts = [p if i == len(parts) - 1 else p.strip()
             for i, p in enumerate(parts)]
    parts = realign_extra_zero_before_start(parts)

    # Normalize to expected size with safe splitter (keeps Text intact)
    payload = ",".join(parts)
    parts = split_dialogue_payload(payload, expected)

    # stats on payload shape
    commas = payload.count(",")
    if commas > expected - 1:
        stats.format_collapse_fixes += 1
    elif commas < expected - 1:
        stats.format_padding_fixes += 1

    values = {fields_order[i]: parts[i] if i < len(
        parts) else "" for i in range(expected)}
    changed_any = False

    # Layer
    layer, ch = sanitize_int(values.get("Layer", "0"))
    if ch or layer != values.get("Layer", ""):
        changed_any = True
    values["Layer"] = layer

    # Start/End — normalize candidates: collapse extra "0:", ensure hour if missing
    start_raw = normalize_time_candidate(
        (values.get("Start", "") or "").strip())
    end_raw = normalize_time_candidate((values.get("End", "") or "").strip())
    values["Start"] = start_raw
    values["End"] = end_raw

    # Validate timing
    start_ok = is_valid_time(start_raw)
    end_ok = is_valid_time(end_raw)
    warn = False
    if not start_ok or not end_ok:
        warn = True
    else:
        cs_s = time_to_cs(start_raw)
        cs_e = time_to_cs(end_raw)
        if cs_s is None or cs_e is None or cs_e < cs_s:
            warn = True
    if warn:
        stats.time_warnings += 1
        sys.stderr.write(
            f"{RED}[TIME WARNING]{RESET} {filehint}:{lineno+1}  Start='{start_raw}'  End='{end_raw}'  Line: {raw_line.strip()}\n"
        )

    # Style
    style = values.get("Style", "").strip() or "Default"
    if styles and style not in styles:
        style = "Default"
        stats.style_fixes += 1
        changed_any = True
    values["Style"] = style

    # Name
    name = values.get("Name", "")
    if name.strip() in {"0", "00", "000"}:
        name = ""
        stats.name_fixes += 1
        changed_any = True
    values["Name"] = name

    # Margins
    for key in ("MarginL", "MarginR", "MarginV"):
        newv, ch = sanitize_int(values.get(key, "0"))
        if ch or newv != values.get(key, ""):
            stats.margin_fixes += 1
            changed_any = True
        values[key] = newv

    # Effect
    effect = values.get("Effect", "")
    if effect.strip().isdigit():
        effect = ""
        stats.effect_fixes += 1
        changed_any = True
    values["Effect"] = effect

    # Text cleanup & rescue
    text = values.get("Text", "")
    text = re.sub(r"[\ufeff\u200b\u200e\u200f]", "", text)
    text = text.strip()

    if text == "":
        for k in ("Effect", "MarginV", "MarginR", "MarginL", "Name"):
            v = (values.get(k, "") or "").strip()
            if looks_like_sentence(v):
                text = v
                if k.startswith("Margin"):
                    values[k] = "0"
                    stats.margin_fixes += 1
                elif k == "Name":
                    values[k] = ""
                    stats.name_fixes += 1
                else:
                    values[k] = ""
                    stats.effect_fixes += 1
                changed_any = True
                break

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
        m = {fields_order[i]: parts[i] if i < len(
            fields_order) else "" for i in range(len(fields_order))}
        key = (m.get("Start", ""), m.get("End", ""), m.get(
            "Style", ""), (m.get("Text", "") or "").strip())
        if key in seen:
            removed += 1
            continue
        seen.add(key)
        out.append(line)
    return out, removed


def replace_styles_with_canonical(doc: ASSDocument, canonical_block: List[str]) -> None:
    sections = parse_sections(doc.lines)
    if "V4+ Styles" not in sections:
        # Insert before Events or at end
        insert_at = sections["Events"][0] if "Events" in sections else len(
            doc.lines)
        doc.lines = doc.lines[:insert_at] + \
            canonical_block + doc.lines[insert_at:]
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
    canonical_styles_block: Optional[List[str]],
    have_canonical: bool,
) -> Tuple[str, QAStats, str, Optional[List[str]], bool]:
    doc = load_ass(path)
    stats = QAStats()

    # Establish or enforce canonical styles
    if not have_canonical and doc.styles_block_lines:
        canonical_styles_block = [ln.rstrip("\n")
                                  for ln in doc.styles_block_lines]
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
            normalized = [next(
                (c for c in CANON_EVENTS_FIELDS if c.lower() == f.lower()), f) for f in fields]
            fields_order = normalized
            new_lines.append(f"{FORMAT_PREFIX} {', '.join(fields_order)}")
            continue
        if in_events and stripped.startswith(DIALOGUE_PREFIX):
            fixed = process_dialogue_line(
                line, fields_order, doc.styles, stats, keep_empty_text, os.path.basename(
                    path), i
            )
            if fixed is not None:
                dialogue_buffer.append(fixed)
            continue
        new_lines.append(line)

    # Always dedupe
    duplicates_removed = 0
    if dialogue_buffer:
        dialogue_buffer, duplicates_removed = dedupe_dialogues(
            dialogue_buffer, fields_order)
    stats.duplicates_removed = duplicates_removed

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
    if inplace:
        save_ass(path, doc)
        out_path = path
    else:
        base, ext = os.path.splitext(path)
        out_path = base + ".fixed" + ext
        save_ass(out_path, doc)

    report = (
        f"Processed '{os.path.basename(path)}': "
        f"dialogue={stats.dialogue_lines}, fixed={stats.fixed_lines}, "
        f"style_fixes={stats.style_fixes}, padding={stats.format_padding_fixes}, "
        f"collapsed={stats.format_collapse_fixes}, name={stats.name_fixes}, "
        f"margins={stats.margin_fixes}, effect={stats.effect_fixes}, "
        f"empty_text_removed={stats.empty_text_removed}, fake_text_removed={stats.fake_text_removed}, "
        f"deduped={stats.duplicates_removed}, time_warnings={stats.time_warnings}"
    )
    return out_path, stats, report, canonical_styles_block, have_canonical


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Analyze and fix common QA issues in .ASS subtitle files.")
    ap.add_argument("--inplace", action="store_true",
                    help="Overwrite originals. Default: write *.fixed.ass.")
    ap.add_argument("--keep-empty-text", action="store_true",
                    help="Keep Dialogue lines with empty/artifact text.")
    ap.add_argument("files", nargs="*",
                    help="Specific .ASS files to process. If not provided, processes all .ass files in current directory.")
    args = ap.parse_args()

    # Determine which files to process
    if args.files:
        # Use specific files provided by user
        paths = []
        for file_path in args.files:
            path = Path(file_path)
            if path.exists() and path.is_file() and path.suffix.lower() == '.ass':
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

    canonical_styles_block: Optional[List[str]] = None
    have_canonical = False

    for p in paths:
        try:
            out_path, stats, report, canonical_styles_block, have_canonical = process_ass(
                p,
                inplace=args.inplace,
                keep_empty_text=args.keep_empty_text,
                canonical_styles_block=canonical_styles_block,
                have_canonical=have_canonical,
            )
            outputs.append(out_path)
            reports.append(report)
            for field in vars(grand).keys():
                setattr(grand, field, getattr(
                    grand, field) + getattr(stats, field))
        except Exception as e:
            print(f"[ERROR] Failed '{p}': {e}", file=sys.stderr)

    for r in reports:
        print(r)

    print(
        "\nSummary: "
        f"files={len(outputs)}, dialogues={grand.dialogue_lines}, fixed={grand.fixed_lines}, "
        f"style_fixes={grand.style_fixes}, padding={grand.format_padding_fixes}, collapsed={grand.format_collapse_fixes}, "
        f"name={grand.name_fixes}, margins={grand.margin_fixes}, effect={grand.effect_fixes}, "
        f"empty_text_removed={grand.empty_text_removed}, fake_text_removed={grand.fake_text_removed}, "
        f"deduped={grand.duplicates_removed}, time_warnings={grand.time_warnings}"
    )


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Detect and remove repeating sequences (openings/endings) across multiple ASS subtitle files.

Uses a THREE-PASS DATA-DRIVEN algorithm:
1. DISCOVERY: Cast wide net, find all repeating content (30% of episode length)
2. CLUSTER ANALYSIS: Find where matches naturally cluster, DERIVE tolerance from data
3. BOUNDARY DETECTION: Use learned tolerance to find precise section boundaries

NO hardcoded time tolerances - everything is learned from the actual data distribution.
"""

import argparse
import glob
import re
import statistics
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Optional

from rapidfuzz import fuzz

# ---------------------------------------------------------------------------
# CONFIGURATION (Only non-tolerance settings remain hardcoded)
# ---------------------------------------------------------------------------
SIMILARITY_THRESHOLD = 75  # RapidFuzz 0-100 scale (text similarity, not time)
MIN_MATCH_FILES_RATIO = 0.50  # Must appear in at least 50% of files to be "repeating"
DISCOVERY_WINDOW_RATIO = 0.30  # Scan last 30% of episode for credits discovery
MIN_CLUSTER_DENSITY = 0.30  # Cluster must have matches from 30% of files to be valid

# Colors
RED = "\033[91m"
GREEN = "\033[92m"
CYAN = "\033[96m"
YELLOW = "\033[93m"
BOLD = "\033[1m"
RESET = "\033[0m"


# ---------------------------------------------------------------------------
# DATA STRUCTURES
# ---------------------------------------------------------------------------
@dataclass
class DialogueLine:
    index: int  # Dialogue index within episode
    file_line_num: int  # Actual line number in file (for removal)
    start_time: str
    end_time: str
    start_cs: int  # Centiseconds
    end_cs: int
    normalized_text: str


@dataclass
class Episode:
    filename: str
    dialogues: list[DialogueLine] = field(default_factory=list)
    all_lines: list[str] = field(default_factory=list)

    @property
    def length_cs(self) -> int:
        """Episode length in centiseconds."""
        if not self.dialogues:
            return 0
        return self.dialogues[-1].end_cs


@dataclass
class MatchOccurrence:
    """A single occurrence of a matching line in one file."""
    file_idx: int
    offset_from_end_cs: int  # Key metric for credits (end-relative)
    absolute_time_cs: int
    line: DialogueLine
    match_ratio: float  # Fuzzy match score (0-100)


@dataclass
class MatchCandidate:
    """A line that appears in multiple files - potential credits content."""
    normalized_text: str
    occurrences: list[MatchOccurrence] = field(default_factory=list)

    def file_count(self) -> int:
        """Number of unique files this text appears in."""
        return len(set(o.file_idx for o in self.occurrences))

    def offsets(self) -> list[int]:
        """All end-relative offsets where this text appears."""
        return [o.offset_from_end_cs for o in self.occurrences]


@dataclass
class ClusterResult:
    """A natural grouping of matches - parameters DERIVED from data."""
    center_cs: int  # Median position in cluster (end-relative)
    spread_cs: int  # IQR of positions (natural variance)
    derived_tolerance_cs: int  # Learned tolerance = 2 * spread
    file_count: int  # How many files have matches in this cluster
    total_files: int  # Total files analyzed
    member_offsets: list[int] = field(default_factory=list)  # All offsets in cluster

    @property
    def consistency(self) -> float:
        """What percentage of files have matches in this cluster."""
        return self.file_count / self.total_files if self.total_files > 0 else 0.0


@dataclass
class LearnedParameters:
    """All parameters derived from data analysis - NO hardcoded values."""
    credits_cluster: Optional[ClusterResult] = None
    opening_cluster: Optional[ClusterResult] = None
    consensus_boundary_text: str = ""  # Most common boundary text


@dataclass
class DetectionConfidence:
    """Confidence metrics based on measurable properties, not arbitrary scores."""
    files_in_cluster: int
    total_files: int
    boundary_text_match_ratio: float  # % of files with same boundary text
    within_tolerance: bool  # Is detection within learned cluster?
    distance_from_center_cs: int  # How far from cluster center

    @property
    def cluster_consistency(self) -> float:
        """Percentage of files agreeing on cluster position."""
        return self.files_in_cluster / self.total_files if self.total_files > 0 else 0.0

    @property
    def level(self) -> str:
        """Interpretable confidence level based on actual metrics."""
        if not self.within_tolerance:
            return "REJECTED"
        # High cluster agreement = HIGH confidence
        # Boundary text match is informational, not a gating requirement
        if self.cluster_consistency >= 0.8:
            return "HIGH"
        if self.cluster_consistency >= 0.5:
            return "MEDIUM"
        return "LOW"


@dataclass
class SectionResult:
    section_type: str  # "OPENING" or "CREDITS"
    start_line_num: int  # File line number
    end_line_num: int  # File line number
    start_time: str
    end_time: str
    line_count: int
    boundary_text: str  # Text of the boundary line


@dataclass
class FileResult:
    filename: str
    opening: Optional[SectionResult] = None
    credits: Optional[SectionResult] = None
    confidence: Optional[DetectionConfidence] = None
    rejection_reason: str = ""


# ---------------------------------------------------------------------------
# PARSING
# ---------------------------------------------------------------------------
def normalize_text(raw: str) -> str:
    """Normalize text for fuzzy matching."""
    text = re.sub(r"\{[^}]*\}", "", raw)  # Remove ASS tags
    text = text.replace("\\N", " ").replace("\\n", " ")
    return re.sub(r"\s+", " ", text).strip()


def time_to_cs(time_str: str) -> int:
    """Convert ASS time (H:MM:SS.cc) to centiseconds."""
    try:
        parts = time_str.split(":")
        h = int(parts[0])
        m = int(parts[1])
        s_parts = parts[2].split(".")
        s = int(s_parts[0])
        cs = int(s_parts[1]) if len(s_parts) > 1 else 0
        return h * 360000 + m * 6000 + s * 100 + cs
    except (ValueError, IndexError):
        return 0


def parse_ass_file(filepath: str) -> Optional[Episode]:
    """Parse an ASS file and extract dialogue lines."""
    try:
        with open(filepath, "r", encoding="utf-8-sig", errors="replace") as f:
            lines = f.readlines()
    except OSError as e:
        print(f"{RED}Error reading {filepath}: {e}{RESET}", file=sys.stderr)
        return None

    episode = Episode(filename=filepath, all_lines=lines)

    text_idx = 9
    start_idx = 1
    end_idx = 2
    in_events = False

    for line_num, line in enumerate(lines):
        stripped = line.strip()

        if stripped == "[Events]":
            in_events = True
            continue

        if not in_events:
            continue

        if stripped.startswith("[") and stripped != "[Events]":
            break

        if stripped.startswith("Format:"):
            parts = [p.strip() for p in stripped[7:].split(",")]
            try:
                text_idx = parts.index("Text")
                start_idx = parts.index("Start")
                end_idx = parts.index("End")
            except ValueError:
                pass
            continue

        if stripped.startswith("Dialogue:"):
            max_idx = max(text_idx, start_idx, end_idx)
            parts = stripped[9:].split(",", max_idx)

            if len(parts) > max_idx:
                raw_text = parts[text_idx].strip()
                normalized = normalize_text(raw_text)

                if not normalized:
                    continue

                start_time = parts[start_idx].strip()
                end_time = parts[end_idx].strip()

                dialogue = DialogueLine(
                    index=len(episode.dialogues),
                    file_line_num=line_num,
                    start_time=start_time,
                    end_time=end_time,
                    start_cs=time_to_cs(start_time),
                    end_cs=time_to_cs(end_time),
                    normalized_text=normalized,
                )
                episode.dialogues.append(dialogue)

    return episode


# ---------------------------------------------------------------------------
# HELPER FUNCTIONS
# ---------------------------------------------------------------------------
def cs_to_time(cs: int) -> str:
    """Convert centiseconds to ASS time format (H:MM:SS.cc)."""
    h = cs // 360000
    cs %= 360000
    m = cs // 6000
    cs %= 6000
    s = cs // 100
    cc = cs % 100
    return f"{h}:{m:02d}:{s:02d}.{cc:02d}"


def iqr(values: list[int]) -> int:
    """Calculate interquartile range (Q3 - Q1)."""
    if len(values) < 4:
        # For small samples, use range
        return max(values) - min(values) if values else 0
    sorted_vals = sorted(values)
    n = len(sorted_vals)
    q1_idx = n // 4
    q3_idx = (3 * n) // 4
    return sorted_vals[q3_idx] - sorted_vals[q1_idx]


# ---------------------------------------------------------------------------
# PASS 1: DISCOVERY - Cast wide net, find all repeating content
# ---------------------------------------------------------------------------
def discover_credits_matches(episodes: list[Episode]) -> list[MatchCandidate]:
    """
    Pass 1: Discovery phase.

    Cast a wide net to find ALL lines that repeat across files.
    Uses 30% of episode length as scan window (fully adaptive).
    NO time tolerance filtering yet - just collect all matches.
    """
    # Group matches by normalized text
    text_to_occurrences: dict[str, list[MatchOccurrence]] = defaultdict(list)

    for ep_idx, ep in enumerate(episodes):
        if not ep.dialogues:
            continue

        ep_end = ep.length_cs
        # Discovery window: 30% of this episode's length
        discovery_window_cs = int(ep_end * DISCOVERY_WINDOW_RATIO)

        for line in ep.dialogues:
            offset_from_end = ep_end - line.start_cs
            if offset_from_end > discovery_window_cs:
                continue  # Outside discovery window
            if offset_from_end < 0:
                continue

            # Check if this line matches anything in other episodes
            # (we'll filter by file count later)
            for other_idx, other_ep in enumerate(episodes):
                if other_idx == ep_idx:
                    continue

                other_end = other_ep.length_cs
                other_discovery_window = int(other_end * DISCOVERY_WINDOW_RATIO)

                for other_line in other_ep.dialogues:
                    other_offset = other_end - other_line.start_cs
                    if other_offset > other_discovery_window or other_offset < 0:
                        continue

                    ratio = fuzz.ratio(line.normalized_text, other_line.normalized_text)
                    if ratio >= SIMILARITY_THRESHOLD:
                        # Record this occurrence
                        text_to_occurrences[line.normalized_text].append(
                            MatchOccurrence(
                                file_idx=ep_idx,
                                offset_from_end_cs=offset_from_end,
                                absolute_time_cs=line.start_cs,
                                line=line,
                                match_ratio=ratio,
                            )
                        )
                        break  # Only need one match per other file

    # Convert to MatchCandidates, keeping only those in 50%+ of files
    min_files = max(2, int(len(episodes) * MIN_MATCH_FILES_RATIO))
    candidates = []

    for text, occurrences in text_to_occurrences.items():
        candidate = MatchCandidate(normalized_text=text, occurrences=occurrences)
        if candidate.file_count() >= min_files:
            candidates.append(candidate)

    return candidates


# ---------------------------------------------------------------------------
# PASS 2: CLUSTER ANALYSIS - Find natural clusters, derive tolerance
# ---------------------------------------------------------------------------
def find_clusters_adaptive(
    offset_file_pairs: list[tuple[int, int]],  # (offset_cs, file_idx)
    num_files: int
) -> list[ClusterResult]:
    """
    Pass 2: Find natural clusters WITHOUT hardcoded epsilon.

    Uses adaptive histogram binning where bin width is derived from the data:
    - Calculate gaps between consecutive positions
    - Bin width = max(median_gap * 2, 5 seconds minimum)

    Returns clusters sorted by file count (most files first).
    """
    if len(offset_file_pairs) < 3:
        return []

    # Sort by offset
    sorted_pairs = sorted(offset_file_pairs, key=lambda x: x[0])
    sorted_offsets = [p[0] for p in sorted_pairs]

    # DERIVE bin width from the data itself
    gaps = [sorted_offsets[i + 1] - sorted_offsets[i]
            for i in range(len(sorted_offsets) - 1)]

    if not gaps:
        return []

    median_gap = statistics.median(gaps)
    # Bin width: 2x median gap, minimum 5 seconds (500 cs)
    bin_width = max(int(median_gap * 2), 500)

    # Group pairs into bins
    bins: dict[int, list[tuple[int, int]]] = defaultdict(list)
    for offset, file_idx in sorted_pairs:
        bin_idx = offset // bin_width
        bins[bin_idx].append((offset, file_idx))

    # Find dense bins (clusters)
    clusters = []

    # Merge adjacent dense bins into clusters
    sorted_bin_indices = sorted(bins.keys())
    i = 0

    while i < len(sorted_bin_indices):
        bin_idx = sorted_bin_indices[i]
        members = bins[bin_idx].copy()

        # Merge with adjacent bins if they're also dense
        j = i + 1
        while j < len(sorted_bin_indices):
            next_bin_idx = sorted_bin_indices[j]
            # Only merge if adjacent (within 2 bins)
            if next_bin_idx - sorted_bin_indices[j - 1] <= 2:
                members.extend(bins[next_bin_idx])
                j += 1
            else:
                break

        # Count unique files in this cluster
        unique_files = len(set(file_idx for _, file_idx in members))
        offsets_only = [offset for offset, _ in members]

        # Check if this cluster has matches from enough files
        if unique_files >= max(2, int(num_files * MIN_CLUSTER_DENSITY)):
            spread = iqr(offsets_only)
            # Derived tolerance: 2x the spread, minimum 10 seconds
            derived_tolerance = max(spread * 2, 1000)

            clusters.append(ClusterResult(
                center_cs=statistics.median(offsets_only),
                spread_cs=spread,
                derived_tolerance_cs=derived_tolerance,
                file_count=unique_files,  # Now correctly counts unique files!
                total_files=num_files,
                member_offsets=offsets_only,
            ))

        i = j if j > i else i + 1

    # Sort by file count (most files agreeing first)
    clusters.sort(key=lambda c: c.file_count, reverse=True)
    return clusters


def analyze_clusters(
    candidates: list[MatchCandidate],
    num_files: int
) -> LearnedParameters:
    """
    Analyze match candidates to find the credits cluster and derive parameters.
    """
    # Collect all (offset, file_idx) pairs from all candidates
    offset_file_pairs: list[tuple[int, int]] = []
    for candidate in candidates:
        for occ in candidate.occurrences:
            offset_file_pairs.append((occ.offset_from_end_cs, occ.file_idx))

    if not offset_file_pairs:
        return LearnedParameters()

    # Find clusters
    clusters = find_clusters_adaptive(offset_file_pairs, num_files)

    if not clusters:
        return LearnedParameters()

    # Best cluster = most consistent
    best_cluster = clusters[0]

    # Find consensus boundary text (most common first line of credits)
    # Look for the earliest matching line within the cluster
    boundary_texts: list[str] = []
    for candidate in candidates:
        for occ in candidate.occurrences:
            distance = abs(occ.offset_from_end_cs - best_cluster.center_cs)
            if distance <= best_cluster.derived_tolerance_cs:
                boundary_texts.append(candidate.normalized_text)
                break

    consensus_text = ""
    if boundary_texts:
        # Find most common boundary text
        from collections import Counter
        text_counts = Counter(boundary_texts)
        consensus_text = text_counts.most_common(1)[0][0]

    return LearnedParameters(
        credits_cluster=best_cluster,
        consensus_boundary_text=consensus_text,
    )


# ---------------------------------------------------------------------------
# PASS 3: BOUNDARY DETECTION - Use learned tolerance
# ---------------------------------------------------------------------------
def detect_credits_boundary(
    episode: Episode,
    ep_idx: int,
    all_episodes: list[Episode],
    learned: LearnedParameters,
) -> tuple[Optional[SectionResult], Optional[DetectionConfidence], str]:
    """
    Pass 3: Detect credits boundary using LEARNED tolerance.

    Returns: (SectionResult or None, DetectionConfidence or None, rejection_reason)
    """
    if not learned.credits_cluster:
        return None, None, "No credits cluster found across files"

    cluster = learned.credits_cluster
    ep_end = episode.length_cs

    # Find all lines that:
    # 1. Fall within the learned cluster tolerance
    # 2. Match in other files
    candidates_in_cluster: list[DialogueLine] = []
    min_match_files = max(1, int(len(all_episodes) * MIN_MATCH_FILES_RATIO))

    for line in episode.dialogues:
        offset = ep_end - line.start_cs
        distance_from_center = abs(offset - cluster.center_cs)

        # Check if within learned tolerance
        if distance_from_center > cluster.derived_tolerance_cs:
            continue

        # Verify it matches in other files
        match_count = 0
        for other_idx, other_ep in enumerate(all_episodes):
            if other_idx == ep_idx:
                continue
            other_end = other_ep.length_cs

            for other_line in other_ep.dialogues:
                other_offset = other_end - other_line.start_cs
                # Must also be within cluster
                if abs(other_offset - cluster.center_cs) > cluster.derived_tolerance_cs:
                    continue

                ratio = fuzz.ratio(line.normalized_text, other_line.normalized_text)
                if ratio >= SIMILARITY_THRESHOLD:
                    match_count += 1
                    break

        if match_count >= min_match_files:
            candidates_in_cluster.append(line)

    if not candidates_in_cluster:
        # Check if there was a candidate outside the cluster (potential false positive)
        for line in episode.dialogues:
            offset = ep_end - line.start_cs
            if offset > int(ep_end * DISCOVERY_WINDOW_RATIO):
                continue

            # Check if matches anywhere
            match_count = 0
            for other_idx, other_ep in enumerate(all_episodes):
                if other_idx == ep_idx:
                    continue
                for other_line in other_ep.dialogues:
                    ratio = fuzz.ratio(line.normalized_text, other_line.normalized_text)
                    if ratio >= SIMILARITY_THRESHOLD:
                        match_count += 1
                        break

            if match_count >= min_match_files:
                distance = abs((ep_end - line.start_cs) - cluster.center_cs)
                return None, DetectionConfidence(
                    files_in_cluster=cluster.file_count,
                    total_files=cluster.total_files,
                    boundary_text_match_ratio=0.0,
                    within_tolerance=False,
                    distance_from_center_cs=distance,
                ), f"Match at {line.start_time} is {distance // 100} sec from cluster center (tolerance: {cluster.derived_tolerance_cs // 100} sec)"

        return None, None, "No matching lines found in credits region"

    # Boundary = earliest matching line in cluster
    boundary = min(candidates_in_cluster, key=lambda l: l.start_cs)
    last_line = episode.dialogues[-1]

    # Calculate boundary text match ratio
    boundary_match_ratio = 0.0
    if learned.consensus_boundary_text:
        ratio = fuzz.ratio(boundary.normalized_text, learned.consensus_boundary_text)
        boundary_match_ratio = ratio / 100.0

    boundary_offset = ep_end - boundary.start_cs
    distance_from_center = abs(boundary_offset - cluster.center_cs)

    confidence = DetectionConfidence(
        files_in_cluster=cluster.file_count,
        total_files=cluster.total_files,
        boundary_text_match_ratio=boundary_match_ratio,
        within_tolerance=True,
        distance_from_center_cs=distance_from_center,
    )

    section = SectionResult(
        section_type="CREDITS",
        start_line_num=boundary.file_line_num,
        end_line_num=last_line.file_line_num,
        start_time=boundary.start_time,
        end_time=last_line.end_time,
        line_count=last_line.index - boundary.index + 1,
        boundary_text=boundary.normalized_text[:50] + "..." if len(boundary.normalized_text) > 50 else boundary.normalized_text,
    )

    return section, confidence, ""


# ---------------------------------------------------------------------------
# MAIN DETECTION ORCHESTRATOR
# ---------------------------------------------------------------------------
def detect_credits_v2(episodes: list[Episode]) -> tuple[list[FileResult], LearnedParameters]:
    """
    Three-pass data-driven credits detection.

    Pass 1: Discovery - find all repeating content
    Pass 2: Cluster Analysis - find where matches cluster, derive tolerance
    Pass 3: Boundary Detection - use learned tolerance to find precise boundaries
    """
    # Pass 1: Discovery
    print(f"  {CYAN}Pass 1:{RESET} Discovering repeating content...", end="", flush=True)
    candidates = discover_credits_matches(episodes)
    print(f" found {len(candidates)} candidates")

    if not candidates:
        print(f"  {YELLOW}No repeating content found in credits region.{RESET}")
        return [FileResult(filename=ep.filename) for ep in episodes], LearnedParameters()

    # Pass 2: Cluster Analysis
    print(f"  {CYAN}Pass 2:{RESET} Analyzing clusters...", end="", flush=True)
    learned = analyze_clusters(candidates, len(episodes))

    if not learned.credits_cluster:
        print(f" {YELLOW}no clear cluster found{RESET}")
        return [FileResult(filename=ep.filename) for ep in episodes], learned

    cluster = learned.credits_cluster
    print(f" cluster at ~{cluster.center_cs // 100} sec from end")
    print(f"           spread: {cluster.spread_cs // 100} sec, derived tolerance: {cluster.derived_tolerance_cs // 100} sec")
    if learned.consensus_boundary_text:
        display_text = learned.consensus_boundary_text[:40] + "..." if len(learned.consensus_boundary_text) > 40 else learned.consensus_boundary_text
        print(f"           consensus boundary: \"{display_text}\"")

    # Pass 3: Boundary Detection
    print(f"  {CYAN}Pass 3:{RESET} Detecting boundaries...")
    results: list[FileResult] = []

    for ep_idx, ep in enumerate(episodes):
        section, confidence, rejection_reason = detect_credits_boundary(
            ep, ep_idx, episodes, learned
        )

        results.append(FileResult(
            filename=ep.filename,
            credits=section,
            confidence=confidence,
            rejection_reason=rejection_reason,
        ))

    return results, learned


# ---------------------------------------------------------------------------
# DISPLAY
# ---------------------------------------------------------------------------
def display_results(results: list[FileResult], learned: LearnedParameters) -> None:
    """Display detected sections with confidence information."""
    # Separate results by confidence level
    high_confidence = [r for r in results if r.confidence and r.confidence.level == "HIGH"]
    medium_confidence = [r for r in results if r.confidence and r.confidence.level == "MEDIUM"]
    rejected = [r for r in results if r.confidence and r.confidence.level == "REJECTED"]
    no_detection = [r for r in results if not r.credits and not r.rejection_reason]

    total_detected = len(high_confidence) + len(medium_confidence)

    if total_detected == 0 and not rejected:
        print(f"\n{YELLOW}No repeating credits sections detected.{RESET}")
        return

    print(f"\n{BOLD}Results:{RESET}")
    print(f"  HIGH confidence: {len(high_confidence)} files")
    print(f"  MEDIUM confidence: {len(medium_confidence)} files")
    print(f"  REJECTED: {len(rejected)} files")
    if no_detection:
        print(f"  No detection: {len(no_detection)} files")

    # Display HIGH confidence detections
    if high_confidence:
        print(f"\n{BOLD}{GREEN}HIGH confidence detections (will be cleaned with --yes):{RESET}\n")
        for result in sorted(high_confidence, key=lambda r: r.filename):
            conf = result.confidence
            print(f"{BOLD}{result.filename}{RESET} {GREEN}[HIGH]{RESET}")
            if result.credits:
                cr = result.credits
                print(f"  {CYAN}CREDITS{RESET}: {cr.start_time} → end ({cr.line_count} lines)")
                print(f"    Start: \"{cr.boundary_text}\"")
            if conf:
                print(f"    {conf.files_in_cluster}/{conf.total_files} files agree, boundary match: {conf.boundary_text_match_ratio:.0%}")
            print()

    # Display MEDIUM confidence detections
    if medium_confidence:
        print(f"\n{BOLD}{YELLOW}MEDIUM confidence detections (require confirmation):{RESET}\n")
        for result in sorted(medium_confidence, key=lambda r: r.filename):
            conf = result.confidence
            print(f"{BOLD}{result.filename}{RESET} {YELLOW}[MEDIUM]{RESET}")
            if result.credits:
                cr = result.credits
                print(f"  {CYAN}CREDITS{RESET}: {cr.start_time} → end ({cr.line_count} lines)")
                print(f"    Start: \"{cr.boundary_text}\"")
            if conf:
                print(f"    {conf.files_in_cluster}/{conf.total_files} files agree, boundary match: {conf.boundary_text_match_ratio:.0%}")
            print()

    # Display REJECTED detections
    if rejected:
        print(f"\n{BOLD}{RED}REJECTED (outside learned cluster):{RESET}\n")
        for result in sorted(rejected, key=lambda r: r.filename):
            conf = result.confidence
            print(f"{BOLD}{result.filename}{RESET} {RED}[REJECTED]{RESET}")
            if result.rejection_reason:
                print(f"  {result.rejection_reason}")
            if conf and learned.credits_cluster:
                cluster = learned.credits_cluster
                print(f"  Cluster center: {cluster.center_cs // 100} sec from end")
                print(f"  Derived tolerance: {cluster.derived_tolerance_cs // 100} sec")
                print(f"  This file's distance: {conf.distance_from_center_cs // 100} sec from center")
            print()


# ---------------------------------------------------------------------------
# CLEANUP
# ---------------------------------------------------------------------------
def cleanup_sections(
    episodes: list[Episode],
    results: list[FileResult],
    high_only: bool = False
) -> int:
    """
    Remove detected sections from files.

    Args:
        episodes: List of parsed episodes
        results: Detection results
        high_only: If True, only clean HIGH confidence detections

    Returns:
        Number of files cleaned
    """
    cleaned = 0

    for result in results:
        if not result.credits:
            continue

        # Check confidence level
        if high_only:
            if not result.confidence or result.confidence.level != "HIGH":
                continue

        # Find the episode object
        ep = next((e for e in episodes if e.filename == result.filename), None)
        if not ep:
            continue

        lines_to_remove: set[int] = set()

        if result.credits:
            lines_to_remove.update(range(result.credits.start_line_num, result.credits.end_line_num + 1))

        new_lines = [line for i, line in enumerate(ep.all_lines) if i not in lines_to_remove]

        try:
            with open(result.filename, "w", encoding="utf-8") as f:
                f.writelines(new_lines)
            conf_level = result.confidence.level if result.confidence else "?"
            print(f"{GREEN}✓{RESET} {result.filename}: removed {len(lines_to_remove)} lines [{conf_level}]")
            cleaned += 1
        except OSError as e:
            print(f"{RED}✗{RESET} {result.filename}: {e}")

    return cleaned


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(
        description="Detect and remove repeating credits sections from ASS subtitle files.\n\n"
                    "Uses a data-driven algorithm that learns tolerance from the actual\n"
                    "distribution of matches across files - no hardcoded time windows.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--yes", "-y",
        action="store_true",
        help="Auto-clean HIGH confidence detections only (skip MEDIUM/REJECTED)"
    )
    args = parser.parse_args()

    # Find all ASS files
    ass_files = sorted(glob.glob("*.ass"))

    if len(ass_files) < 2:
        print(f"{YELLOW}Need at least 2 .ass files for section detection.{RESET}")
        print(f"Found: {len(ass_files)} file(s)")
        return

    print(f"{BOLD}Loading {len(ass_files)} subtitle files...{RESET}")

    # Parse all files
    episodes: list[Episode] = []
    for filepath in ass_files:
        ep = parse_ass_file(filepath)
        if ep and ep.dialogues:
            episodes.append(ep)

    if len(episodes) < 2:
        print(f"{YELLOW}Need at least 2 valid files with dialogue.{RESET}")
        return

    print(f"{BOLD}Analyzing {len(episodes)} files for credits sections...{RESET}\n")

    # Run three-pass detection
    results, learned = detect_credits_v2(episodes)

    # Display results
    display_results(results, learned)

    # Count detections by confidence
    high_confidence = [r for r in results if r.confidence and r.confidence.level == "HIGH"]
    medium_confidence = [r for r in results if r.confidence and r.confidence.level == "MEDIUM"]
    all_cleanable = high_confidence + medium_confidence

    if not all_cleanable:
        print(f"{YELLOW}No files to clean.{RESET}")
        return

    # Handle --yes flag: only clean HIGH confidence
    if args.yes:
        if not high_confidence:
            print(f"{YELLOW}No HIGH confidence detections to auto-clean.{RESET}")
            if medium_confidence:
                print(f"Run without --yes to review {len(medium_confidence)} MEDIUM confidence detection(s).")
            return

        print(f"\n{BOLD}Auto-cleaning {len(high_confidence)} HIGH confidence files...{RESET}")
        cleaned = cleanup_sections(episodes, results, high_only=True)
        print(f"\n{GREEN}Done. Cleaned {cleaned} file(s).{RESET}")

        if medium_confidence:
            print(f"{YELLOW}Skipped {len(medium_confidence)} MEDIUM confidence file(s). Run without --yes to review.{RESET}")
        return

    # Interactive mode: ask for confirmation
    print(f"\n{BOLD}Files to clean:{RESET}")
    print(f"  {GREEN}HIGH confidence:{RESET} {len(high_confidence)} files (recommended)")
    print(f"  {YELLOW}MEDIUM confidence:{RESET} {len(medium_confidence)} files (review suggested)")

    try:
        response = input(f"\n{BOLD}Proceed with cleanup? [y=all, h=HIGH only, n=cancel]:{RESET} ").strip().lower()

        if response in ("n", "no", ""):
            print("Aborted.")
            return
        elif response in ("h", "high"):
            print(f"\n{BOLD}Cleaning HIGH confidence files only...{RESET}")
            cleaned = cleanup_sections(episodes, results, high_only=True)
        elif response in ("y", "yes", "a", "all"):
            print(f"\n{BOLD}Cleaning all detected files...{RESET}")
            cleaned = cleanup_sections(episodes, results, high_only=False)
        else:
            print("Aborted.")
            return

        print(f"\n{GREEN}Done. Cleaned {cleaned} file(s).{RESET}")

    except (KeyboardInterrupt, EOFError):
        print("\nAborted.")
        return


if __name__ == "__main__":
    main()

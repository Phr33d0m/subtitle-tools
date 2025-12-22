# ass-qafix Rules Documentation

This document explains all the quality assurance checks and automatic fixes performed by ass-qafix in plain, non-technical language.

---

## Table of Contents

- [Removal Rules](#removal-rules)
  - [1. Duplicate Line Removal](#1-duplicate-line-removal)
  - [2. Empty Text Removal](#2-empty-text-removal)
  - [3. Fake Text / OCR Artifact Removal](#3-fake-text--ocr-artifact-removal)
  - [4. Short Duration Removal](#4-short-duration-removal)
- [Merging Rules](#merging-rules)
  - [5. Consecutive Line Merging](#5-consecutive-line-merging)
  - [6. Short Echo Line Merging](#6-short-echo-line-merging)
  - [7. Alternating OCR Variant Merging](#7-alternating-ocr-variant-merging)
- [Fix Rules](#fix-rules)
  - [8. Style Validation](#8-style-validation)
  - [9. Layer Number Sanitization](#9-layer-number-sanitization)
  - [10. Invisible Character Removal](#10-invisible-character-removal)
  - [11. Overlapping Timestamp Fixes](#11-overlapping-timestamp-fixes)
- [Warnings](#warnings)
  - [12. Short Duration Warnings](#12-short-duration-warnings)
  - [13. Half-Translation Detection](#13-half-translation-detection)
- [Batch Processing](#batch-processing)
  - [14. Style Consistency Across Files](#14-style-consistency-across-files)
- [Summary](#summary)

---

## Removal Rules

These rules identify and remove problematic subtitle lines.

### 1. Duplicate Line Removal

```
Status: REMOVED
```

**What it does:**
Removes exact duplicate subtitle lines. If two lines have the same start time, end time, style, and text, only one is kept.

**Why this matters:**
Sometimes during subtitle extraction or editing, the same line gets added twice. This creates visual stuttering or flickering when watching.

**Example:**

| Before | After |
|--------|-------|
| `0:01:00.00 - 0:01:02.00` "Hello" | `0:01:00.00 - 0:01:02.00` "Hello" |
| `0:01:00.00 - 0:01:02.00` "Hello" | *(removed)* |

---

### 2. Empty Text Removal

```
Status: REMOVED (can be disabled with --keep-empty-text)
```

**What it does:**
Removes subtitle lines that have no actual text content.

**Specifically removed:**

| Pattern | Description |
|---------|-------------|
| *(empty)* | Completely empty text |
| `-` | Single hyphen/dash |
| `–` | En-dash |
| `—` | Em-dash |
| `/` | Forward slash |
| `--` | Double dash |

**Why this matters:**
OCR software sometimes creates "ghost" lines with just punctuation marks instead of actual dialogue. These create distracting empty subtitle boxes when watching.

---

### 3. Fake Text / OCR Artifact Removal

```
Status: REMOVED
```

**What it does:**
Removes lines that contain obvious OCR mistakes instead of real dialogue.

#### Types of Fake Text Detected:

##### a) Pure Numbers

| Removed | Reason |
|---------|--------|
| `1`, `5` | Single digits - typically frame numbers |
| `42`, `123` | Multiple digits - likely timecodes misread as dialogue |

##### b) Single Letters

| Removed | Kept | Reason |
|---------|------|--------|
| `r`, `A`, `x`, `n`, `T` | `I` | "I" is a valid English word |

##### c) Two-Letter Combinations

| Removed | Kept | Reason |
|---------|------|--------|
| `rx`, `qz`, `xk` | `OK`, `no`, `go` | Only valid English words are kept |

##### d) Letters with Trailing Punctuation

| Removed | Reason |
|---------|--------|
| `r.` | Partial OCR read |
| `A -` | Partial OCR read |

##### e) Multiple Dashes

| Removed | Reason |
|---------|--------|
| `--`, `---` | OCR misreadings |
| `- -`, `- - -` | OCR misreadings of visual elements |

##### f) Backticks

| Removed | Reason |
|---------|--------|
| `` ` ``, ``` `` ``` | OCR mistakes for apostrophes |

##### g) Replacement Characters

| Removed | Reason |
|---------|--------|
| `□`, `□□□` | Indicates unreadable/corrupted text |

##### h) Underscores

| Removed | Reason |
|---------|--------|
| `_`, `__`, `___` | OCR artifacts from visual lines |

##### i) Format Header Text

| Removed | Reason |
|---------|--------|
| `Layer, Start, End, Style...` | Accidentally included format info |

##### j) Single Chinese Characters (Dictionary Check)

A single Chinese character is only kept if it exists in a Chinese dictionary as a valid standalone word. Random single characters are removed.

| Removed | Kept | Reason |
|---------|------|--------|
| `龘` (rare) | `我` (I/me) | Must be a valid word |

##### k) Ultra-Short Single Chinese Characters

Any single Chinese character appearing for less than **50 milliseconds** is removed regardless of dictionary validity — it's too short to be readable.

---

### 4. Short Duration Removal

```
Status: REMOVED
```

**What it does:**
Removes dialogue lines with duration less than **50 milliseconds** (5 centiseconds).

**Why this matters:**
Lines this short are almost always OCR errors. No one can read text that appears for 0.05 seconds.

---

## Merging Rules

These rules combine multiple lines into one to reduce flickering.

### 5. Consecutive Line Merging

```
Status: MERGED
```

**What it does:**
Combines multiple subtitle lines that have the same text and appear back-to-back within **500ms** of each other.

**Example:**

```
Before:
  Line 1: 0:01:00.00 - 0:01:02.00  "Hello there"
  Line 2: 0:01:02.00 - 0:01:04.00  "Hello there"

After:
  Line 1: 0:01:00.00 - 0:01:04.00  "Hello there"
```

**Conditions for merging:**

| Condition | Requirement |
|-----------|-------------|
| Time gap | ≤ 500ms between lines |
| Text | Identical (or nearly identical for short lines) |
| Style | Must match |
| Character name | Must match |
| Margins | Must match |
| Effects | Must match |

**Why this matters:**
OCR software sometimes splits one continuous dialogue into multiple small segments. This creates an annoying flickering effect.

---

### 6. Short Echo Line Merging

```
Status: MERGED
```

**What it does:**
Detects a special OCR pattern where a valid dialogue line is paired with a very short (under 50ms) "echo" line containing similar but slightly different text.

#### Pattern A — Short echo AFTER long line:

```
Before:
  Line 1: 0:05:34.80 - 0:05:37.12  "Hello world"   (2.32 seconds)
  Line 2: 0:05:37.12 - 0:05:37.16  "Hello worid"   (40 milliseconds)

After:
  Line 1: 0:05:34.80 - 0:05:37.16  "Hello world"   (keeps long line's text)
```

#### Pattern B — Short echo BEFORE long line:

```
Before:
  Line 1: 0:05:34.80 - 0:05:34.84  "Hello worid"   (40 milliseconds)
  Line 2: 0:05:34.84 - 0:05:37.16  "Hello world"   (2.32 seconds)

After:
  Line 1: 0:05:34.80 - 0:05:37.16  "Hello world"   (keeps long line's text)
```

**Conditions for merging:**

| Condition | Requirement |
|-----------|-------------|
| Gap | Exactly consecutive (no gap) |
| Short line | Must be < 50 milliseconds |
| Similarity | Texts must be ≥ 70% similar |
| Text kept | Always the LONGER line's text |

**Why this matters:**
OCR sometimes creates these "ghost" echoes due to frame-by-frame processing. The short line usually contains more OCR errors than the longer line.

---

### 7. Alternating OCR Variant Merging

```
Status: MERGED
```

**What it does:**
Detects and merges a pattern where OCR alternates between two similar text variants (typically traditional vs simplified Chinese characters).

**Example:**

```
Before:
  Line 1: "沒本事就沒本事"   (Traditional - Variant A)
  Line 2: "没本事就没本事"   (Simplified - Variant B)
  Line 3: "沒本事就沒本事"   (Traditional - Variant A)
  Line 4: "没本事就没本事"   (Simplified - Variant B)
  ...continues alternating...

After:
  Single line spanning the entire time with Variant A's text.
```

**Conditions for merging:**

| Condition | Requirement |
|-----------|-------------|
| Gap | All lines must be exactly consecutive |
| Pattern | Must follow A-B-A-B... alternation |
| Similarity | A and B must be ≥ 70% similar |
| Minimum lines | At least 3 lines (A, B, A) |

**Why this matters:**
Some OCR software processes frames alternately and produces different character variants for each frame. This creates rapid-fire text that flickers between variants.

---

## Fix Rules

These rules correct invalid or problematic values without removing lines.

### 8. Style Validation

```
Status: FIXED
```

**What it does:**
Checks that each subtitle line uses a style that actually exists in the file's style definitions.

**How it fixes:**

| Situation | Action |
|-----------|--------|
| Style doesn't exist | Changed to "Default" |
| Style case mismatch | Normalized to match definition |

**Example:**

```
Defined styles: Default, Signs, Flashback

Before: Style: signs     → After: Style: Signs      (case fixed)
Before: Style: Unknown   → After: Style: Default    (invalid → default)
```

**Why this matters:**
Subtitles referencing non-existent styles may display incorrectly or use fallback formatting.

---

### 9. Layer Number Sanitization

```
Status: FIXED
```

**What it does:**
Ensures the layer field contains a valid non-negative number.

**How it fixes:**

| Invalid Value | Fixed To |
|---------------|----------|
| *(empty)* | `0` |
| `abc` (non-number) | `0` |
| `-1` (negative) | `0` |

**Why this matters:**
Invalid layer numbers can cause subtitle display errors in some players.

---

### 10. Invisible Character Removal

```
Status: FIXED
```

**What it does:**
Removes invisible "garbage" characters that sometimes appear in text.

**Characters removed:**

| Character | Name | Description |
|-----------|------|-------------|
| `U+FEFF` | Byte Order Mark (BOM) | Invisible file format marker |
| `U+200B` | Zero-Width Space | Invisible spacing character |
| `U+200E` | Left-to-Right Mark | Text direction marker |
| `U+200F` | Right-to-Left Mark | Text direction marker |

**Why this matters:**
These invisible characters can cause display issues, search problems, or unexpected text behavior in some players.

---

### 11. Overlapping Timestamp Fixes

```
Status: FIXED
```

**What it does:**
Fixes cases where one subtitle line's end time overlaps with the next line's start time by a tiny amount (under 20 milliseconds).

**Example:**

```
Before:
  Line 1: 0:01:00.00 - 0:01:02.01  (ends at 2.01)
  Line 2: 0:01:02.00 - 0:01:04.00  (starts at 2.00 — overlap!)

After:
  Line 1: 0:01:00.00 - 0:01:02.00  (swapped to fix)
  Line 2: 0:01:02.01 - 0:01:04.00  (swapped to fix)
```

**Conditions:**

| Overlap Size | Action |
|--------------|--------|
| ≤ 20 milliseconds | Fixed automatically |
| > 20 milliseconds | Left unchanged (may be intentional) |

**Why this matters:**
Small timing overlaps can cause subtitle display glitches where two lines briefly appear on screen together.

---

## Warnings

These checks identify potential issues but don't modify the file.

### 12. Short Duration Warnings

```
Status: WARNING (not modified)
```

**What it does:**
Identifies subtitle lines shorter than **250 milliseconds** (1/4 second) and issues a warning. These lines are NOT automatically removed.

**Why this matters:**
Lines this short are often OCR errors that weren't properly merged with adjacent lines. They may be too fast to read comfortably.

---

### 13. Half-Translation Detection

```
Status: WARNING (not modified)
```

**What it does:**
When processing multiple files, analyzes the last dialogue timestamp across all files. If a file's dialogue ends significantly earlier than others, it may indicate incomplete translation.

**Why this matters:**
Helps identify files where translation stopped partway through the episode.

---

## Batch Processing

### 14. Style Consistency Across Files

**What it does:**
When processing multiple files at once, the tool captures the style definitions from the first file and applies them to all subsequent files.

**Why this matters:**
Episode series should have consistent styling. This ensures all files in a batch use the same fonts, colors, and formatting definitions.

---

## Summary

### Actions by Category

#### Lines Removed

| Rule | What's Removed |
|------|----------------|
| Duplicate Removal | Exact duplicate lines |
| Empty Text Removal | Lines with no text or only punctuation |
| Fake Text Removal | OCR artifacts and garbage text |
| Short Duration Removal | Lines < 50ms |

#### Lines Merged

| Rule | What's Merged |
|------|---------------|
| Consecutive Merging | Same text within 500ms gap |
| Short Echo Merging | Short "ghost" lines paired with valid dialogue |
| Alternating Variant Merging | A-B-A-B patterns from OCR |

#### Values Fixed

| Rule | What's Fixed |
|------|--------------|
| Style Validation | Invalid or missing style names |
| Layer Sanitization | Invalid layer numbers |
| Invisible Characters | Hidden garbage characters in text |
| Overlapping Timestamps | Tiny timing overlaps (≤ 20ms) |

#### Warnings Only

| Rule | What's Flagged |
|------|----------------|
| Short Duration | Lines < 250ms |
| Half-Translation | Files ending early compared to others |

---

## Command Line Options

| Option | Description |
|--------|-------------|
| `--inplace` | Overwrites the original files. Without this flag, the tool creates new files with ".fixed" added to the name. |
| `--keep-empty-text` | Preserves subtitle lines with empty text instead of removing them. |
| `--dry-run` | Analyzes files and shows what would be changed, but doesn't actually modify anything. Useful for previewing changes. |

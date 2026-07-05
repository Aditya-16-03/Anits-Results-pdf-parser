"""Compiled regular expressions and small text helpers.

Keeping every pattern in one module means the matching rules for roll numbers,
grades and the metadata header live in a single, well-documented place.
"""
from __future__ import annotations

import re

# A roll number such as ``A23126502001`` or ``A23126508062``: one or two
# leading letters followed by 9-12 digits. Kept deliberately generic so other
# branches / admission years still match.
ROLL_NUMBER_RE: re.Pattern[str] = re.compile(r"^[A-Z]{1,2}\d{9,12}$")

# A line that begins with a roll number (used to detect student data rows).
ROLL_LINE_RE: re.Pattern[str] = re.compile(r"^([A-Z]{1,2}\d{9,12})\b")

# SGPA / CGPA values look like ``7.36`` or ``10.00``.
FLOAT_RE: re.Pattern[str] = re.compile(r"^\d{1,2}\.\d{1,2}$")

# A single grade cell.
GRADE_RE: re.Pattern[str] = re.compile(r"^(?:O|A\+|A|B\+|B|C|P|F|Ab)$")

# ---------------------------------------------------------------------------
# Metadata header patterns. These run against a whitespace-normalised copy of
# the first page (newlines collapsed to single spaces) because the header wraps
# across several physical lines in the source PDF.
# ---------------------------------------------------------------------------
BRANCH_RE: re.Pattern[str] = re.compile(r"Branch:\s*(?P<branch>.+?)\s+Course/Sem:", re.IGNORECASE)

# Splits "II/IV B.Tech SEM-I Regular Examinations (R23)" into the semester part
# (up to and including SEM-x / Semester-x) and the exam-type remainder.
SEM_EXAM_RE: re.Pattern[str] = re.compile(
    r"Course/Sem:\s*(?P<sem>.+?(?:SEM|Semester)[-\s]?\S+)\s+(?P<exam>.+?)\s+Held\s*in:",
    re.IGNORECASE,
)

# Fallback that just grabs everything between Course/Sem: and Held in:.
COURSE_BLOCK_RE: re.Pattern[str] = re.compile(
    r"Course/Sem:\s*(?P<block>.+?)\s+Held\s*in:", re.IGNORECASE
)

HELD_IN_RE: re.Pattern[str] = re.compile(
    r"Held\s*in:\s*(?P<held>[A-Za-z]+\s+\d{4})", re.IGNORECASE
)


def normalise_whitespace(text: str) -> str:
    """Collapse all runs of whitespace (including newlines) into single spaces."""
    return re.sub(r"\s+", " ", text).strip()


def is_roll_number(token: str) -> bool:
    """Return ``True`` if *token* looks like a student roll number."""
    return bool(ROLL_NUMBER_RE.match(token))


def is_float_token(token: str) -> bool:
    """Return ``True`` if *token* is a decimal SGPA/CGPA value."""
    return bool(FLOAT_RE.match(token))


def is_grade_token(token: str) -> bool:
    """Return ``True`` if *token* is a valid grade cell."""
    return bool(GRADE_RE.match(token))

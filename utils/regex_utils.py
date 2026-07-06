"""Compiled regular expressions and small text helpers.

Keeping every pattern in one module means the matching rules for roll numbers,
grades and the metadata header live in a single, well-documented place.
"""
from __future__ import annotations

import re

# A roll number such as ``A23126502001`` (letter-prefixed, newer batches) or
# ``319126502009`` / ``317126514150`` (digit-prefixed, older batches), and even
# ``321126510L09`` (a letter can appear in the tail). The structure is a 3-char
# prefix (``A21`` or ``317``), a 3-digit institute code, then a 5-7 char tail.
_ROLL = r"(?:[A-Z]\d{2}|\d{3})\d{3}[A-Z0-9]{5,7}"
ROLL_NUMBER_RE: re.Pattern[str] = re.compile(rf"^{_ROLL}$")

# A line that begins with a roll number (used to detect student data rows).
ROLL_LINE_RE: re.Pattern[str] = re.compile(rf"^({_ROLL})\b")

# SGPA / CGPA values look like ``7.36`` or ``10.00``.
FLOAT_RE: re.Pattern[str] = re.compile(r"^\d{1,2}\.\d{1,2}$")

# A single grade cell. "I" (incomplete/improvement) appears in supplementary
# sheets; "Ab" marks an absent student.
GRADE_RE: re.Pattern[str] = re.compile(r"^(?:O|A\+|A|B\+|B|C|P|F|Ab|I)$")

# Regulation code inside the Course/Sem block, e.g. (R15), (R19), (R20), (R20.1), (R23).
REGULATION_RE: re.Pattern[str] = re.compile(r"\(\s*(R\d+(?:\.\d+)?)\s*\)", re.IGNORECASE)

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

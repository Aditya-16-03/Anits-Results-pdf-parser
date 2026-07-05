"""Project-wide constants for the ANITS PDF Parser service.

Centralising configuration values here keeps the service modules clean and
makes it trivial to tune behaviour (limits, tolerances, valid grades) without
touching business logic.
"""
from __future__ import annotations

import os

# ---------------------------------------------------------------------------
# Feature toggles
# ---------------------------------------------------------------------------
# When enabled, reconstructed subject names are mapped onto clean display names
# via the (editable) known-subjects catalogue. Disable to get the raw
# reconstructed names. Controlled by the NORMALIZE_SUBJECTS env var.
NORMALIZE_SUBJECTS: bool = os.getenv("NORMALIZE_SUBJECTS", "true").strip().lower() not in {
    "0",
    "false",
    "no",
    "off",
}

# ---------------------------------------------------------------------------
# Upload / validation limits
# ---------------------------------------------------------------------------
ALLOWED_EXTENSIONS: set[str] = {".pdf"}
ALLOWED_MIME_TYPES: set[str] = {"application/pdf", "application/x-pdf"}

# Reject files larger than this. ANITS result PDFs are text-only and small even
# at 100+ pages, so 50 MB is a generous ceiling that still blocks abuse.
MAX_FILE_SIZE_BYTES: int = 50 * 1024 * 1024  # 50 MB

# A valid PDF must at least start with the magic header.
PDF_MAGIC_HEADER: bytes = b"%PDF-"

# ---------------------------------------------------------------------------
# Grade vocabulary
# ---------------------------------------------------------------------------
# Every grade token that can legitimately appear in a result cell.
# "Ab" denotes an absent student, "F" a fail.
VALID_GRADES: set[str] = {"O", "A+", "A", "B+", "B", "C", "P", "F", "Ab"}

# ---------------------------------------------------------------------------
# Layout / geometry tolerances used when reconstructing columns from word
# coordinates emitted by pdfplumber.
# ---------------------------------------------------------------------------
# Two words are considered to be on the same visual row if their vertical
# positions differ by less than this many points.
ROW_Y_TOLERANCE: float = 3.0

# Tokens (lower-cased) that identify the repeated "Grade" anchor row sitting
# directly above the student data. These give us one clean anchor per subject.
GRADE_HEADER_TOKENS: set[str] = {"grad", "grade"}

# Connector / stop words that must always be surrounded by spaces when we
# stitch broken subject-name fragments back together. Without this list a
# fragment like "and" would be glued onto the previous word.
STOPWORDS: set[str] = {
    "and", "for", "of", "the", "to", "in", "with", "or", "a", "an", "&",
}

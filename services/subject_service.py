"""Dynamic reconstruction of subject names from the PDF header.

Subject names in ANITS result PDFs are *not* stored as plain strings. Each name
is broken into several short fragments stacked vertically inside a narrow
column, for example the column::

    Vector
    Calculu
    s &
    Statistic

must be rebuilt into ``Vector Calculus & Statistic``.

Because every branch / semester has a different set of subjects we never
hardcode names. Instead we:

1. Locate the ``Roll No / SGPA / CGPA`` header row and the ``Grade`` anchor row.
2. Use the evenly spaced ``Grade`` tokens as one x-anchor per subject column.
3. Assign every fragment word between the header and the grade row to its
   nearest column anchor.
4. Stitch each column's fragments back together, top-to-bottom, using a
   spacing heuristic that distinguishes broken words from real word breaks.
"""
from __future__ import annotations

import logging
from typing import Optional

from pdfplumber.page import Page

from utils import constants
from utils.exceptions import ParsingException

logger = logging.getLogger(__name__)

# A "word" as produced by pdfplumber.extract_words(): text plus geometry.
Word = dict


class SubjectService:
    """Reconstructs the ordered list of subject names for a results page."""

    @staticmethod
    def extract(page: Page) -> list[str]:
        """Return subject names left-to-right, or raise if the header is absent.

        Raises:
            ParsingException: when no subject header can be located on the page.
        """
        words: list[Word] = page.extract_words(use_text_flow=False)
        if not words:
            raise ParsingException("Page has no words to extract subjects from.")

        rows = SubjectService._group_rows(words)

        header_idx = SubjectService._find_header_row(rows)
        if header_idx is None:
            raise ParsingException("Could not locate the 'Roll No / SGPA / CGPA' header row.")

        grade_idx = SubjectService._find_grade_row(rows, header_idx)

        anchors = SubjectService._column_anchors(rows, header_idx, grade_idx)
        if not anchors:
            raise ParsingException("Could not determine subject column positions.")

        fragment_rows = SubjectService._fragment_rows(rows, header_idx, grade_idx)
        subjects = SubjectService._assemble(fragment_rows, anchors)

        if not any(subjects):
            raise ParsingException("Subject columns were located but contained no text.")

        logger.info("Reconstructed %d subjects: %s", len(subjects), subjects)
        return subjects

    # -- row grouping -------------------------------------------------------
    @staticmethod
    def _group_rows(words: list[Word]) -> list[list[Word]]:
        """Cluster words into visual rows by their ``top`` coordinate."""
        ordered = sorted(words, key=lambda w: (round(w["top"], 1), w["x0"]))
        rows: list[list[Word]] = []
        current: list[Word] = []
        current_top: Optional[float] = None

        for word in ordered:
            if current_top is None or abs(word["top"] - current_top) <= constants.ROW_Y_TOLERANCE:
                current.append(word)
                current_top = word["top"] if current_top is None else current_top
            else:
                rows.append(current)
                current = [word]
                current_top = word["top"]
        if current:
            rows.append(current)
        return rows

    @staticmethod
    def _row_top(row: list[Word]) -> float:
        return min(w["top"] for w in row)

    # -- landmark detection -------------------------------------------------
    @staticmethod
    def _find_header_row(rows: list[list[Word]]) -> Optional[int]:
        """Index of the row containing the Roll No / SGPA / CGPA labels."""
        for idx, row in enumerate(rows):
            joined = " ".join(w["text"] for w in row).lower()
            if "roll" in joined and "sgpa" in joined and "cgpa" in joined:
                return idx
        return None

    @staticmethod
    def _find_grade_row(rows: list[list[Word]], header_idx: int) -> Optional[int]:
        """Index of the repeated ``Grade`` anchor row below the header."""
        for idx in range(header_idx + 1, len(rows)):
            tokens = [w["text"].lower() for w in rows[idx]]
            if not tokens:
                continue
            grade_like = sum(1 for t in tokens if t in constants.GRADE_HEADER_TOKENS)
            # Detect the "Grade" anchor row even when there is a single subject
            # column (supplementary sheets can have just one subject).
            if grade_like >= 1 and grade_like >= len(tokens) / 2:
                return idx
        return None

    @staticmethod
    def _word_center(word: Word) -> float:
        return (word["x0"] + word["x1"]) / 2.0

    @staticmethod
    def _column_anchors(
        rows: list[list[Word]], header_idx: int, grade_idx: Optional[int]
    ) -> list[float]:
        """Derive one x-center anchor per subject column.

        Prefers the evenly spaced ``Grade`` row; falls back to the first
        fragment row (which carries exactly one token per column).
        """
        if grade_idx is not None:
            centers = sorted(SubjectService._word_center(w) for w in rows[grade_idx])
            return centers

        # Fallback: the row immediately after the code row usually has one
        # capitalised fragment per column.
        if header_idx + 2 < len(rows):
            candidate = rows[header_idx + 2]
            return sorted(SubjectService._word_center(w) for w in candidate)
        return []

    @staticmethod
    def _fragment_rows(
        rows: list[list[Word]], header_idx: int, grade_idx: Optional[int]
    ) -> list[list[Word]]:
        """Rows holding subject-name fragments.

        These sit between the short-code row (the row directly after the
        header, which we skip) and the ``Grade`` anchor row.
        """
        start = header_idx + 2  # skip header row and the abbreviation/code row
        end = grade_idx if grade_idx is not None else len(rows)
        return [row for row in rows[start:end] if row]

    # -- assembly -----------------------------------------------------------
    @staticmethod
    def _assemble(fragment_rows: list[list[Word]], anchors: list[float]) -> list[str]:
        """Assign fragments to nearest column and stitch each column together."""
        columns: list[list[Word]] = [[] for _ in anchors]

        for row in fragment_rows:
            for word in row:
                col = SubjectService._nearest_column(SubjectService._word_center(word), anchors)
                columns[col].append(word)

        subjects: list[str] = []
        for col_words in columns:
            ordered = sorted(col_words, key=lambda w: (round(w["top"], 1), w["x0"]))
            subjects.append(SubjectService._join_fragments(ordered))
        return subjects

    @staticmethod
    def _nearest_column(center: float, anchors: list[float]) -> int:
        best_idx = 0
        best_dist = abs(center - anchors[0])
        for idx, anchor in enumerate(anchors[1:], start=1):
            dist = abs(center - anchor)
            if dist < best_dist:
                best_dist = dist
                best_idx = idx
        return best_idx

    @staticmethod
    def _join_fragments(fragments: list[Word]) -> str:
        """Rebuild a subject name from its stacked fragments.

        A space is inserted before a fragment when it clearly starts a new
        word; otherwise the fragment is glued on as the continuation of a word
        that was wrapped mid-way across two lines.
        """
        result = ""
        prev_text = ""
        prev_top: Optional[float] = None

        for word in fragments:
            text = word["text"].strip()
            if not text:
                continue
            if not result:
                result = text
            else:
                same_line = prev_top is not None and abs(word["top"] - prev_top) <= constants.ROW_Y_TOLERANCE
                frag_is_stop = text.lower() in constants.STOPWORDS
                prev_is_stop = prev_text.lower() in constants.STOPWORDS
                starts_upper = text[0].isupper()
                frag_non_alpha = not text[0].isalpha()
                prev_non_alpha = not prev_text[-1].isalpha()

                if (
                    same_line
                    or frag_is_stop
                    or prev_is_stop
                    or starts_upper
                    or frag_non_alpha
                    or prev_non_alpha
                ):
                    result += " " + text
                else:
                    result += text
            prev_text = text
            prev_top = word["top"]

        return result.strip()

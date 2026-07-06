"""Coordinate-based extraction for supplementary result sheets.

Supplementary tables are **sparse**: a student only has grades for the subjects
they re-appeared for, and blank cells are simply absent from the extracted
text. Mapping grades to subjects by text order (as the regular parser does) is
therefore impossible - a lone ``F`` on a row could belong to any column.

This service instead assigns every value to a column by its **x-coordinate**:

* SGPA / CGPA are located by the ``SGPA`` and ``CGPA`` header words.
* Subject columns are located by the ``GRADE`` anchor row (one per subject),
  and their names are reconstructed by :class:`SubjectService`.
* For each student row, every decimal is snapped to the nearest of the
  SGPA/CGPA anchors and every grade to the nearest subject anchor.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional

from pdfplumber.page import Page

from models.student_result import StudentResult
from services.metadata_service import MetadataService
from services.normalization_service import SubjectNormalizer
from services.subject_service import SubjectService
from utils import constants, regex_utils
from utils.exceptions import MetadataException, ParsingException

logger = logging.getLogger(__name__)

Word = dict


@dataclass
class PageResult:
    """Everything extracted from a single supplementary page."""

    regulation: Optional[str] = None
    branch: Optional[str] = None
    semester: Optional[str] = None
    exam_type: Optional[str] = None
    held_in: Optional[str] = None
    subjects: list[str] = field(default_factory=list)
    students: list[StudentResult] = field(default_factory=list)


class SupplementaryService:
    """Parses one supplementary page into a :class:`PageResult`."""

    @staticmethod
    def parse_page(page: Page, normalize: bool = True) -> Optional[PageResult]:
        """Extract metadata, subjects and (sparse) student rows from *page*.

        Returns ``None`` when the page has no recognisable results table.
        """
        text = page.extract_text() or ""
        meta = SupplementaryService._metadata(text)

        words: list[Word] = page.extract_words(use_text_flow=False)
        if not words:
            return None

        rows = SubjectService._group_rows(words)
        header_idx = SubjectService._find_header_row(rows)
        if header_idx is None:
            return None
        grade_idx = SubjectService._find_grade_row(rows, header_idx)

        anchors = SubjectService._column_anchors(rows, header_idx, grade_idx)
        if not anchors:
            return None

        try:
            subjects = SubjectService.extract(page)
        except ParsingException:
            return None
        if normalize:
            subjects = SubjectNormalizer.normalize_list(subjects)
        else:
            subjects = SubjectNormalizer.ensure_unique(subjects)

        # Guard against any mismatch between reconstructed names and columns.
        if len(subjects) != len(anchors):
            logger.warning(
                "Subject/anchor count mismatch (%d vs %d) - truncating to min",
                len(subjects),
                len(anchors),
            )
        column_count = min(len(subjects), len(anchors))
        subjects = subjects[:column_count]
        anchors = anchors[:column_count]

        sgpa_x, cgpa_x = SupplementaryService._gpa_anchors(rows[header_idx])

        students = SupplementaryService._parse_students(
            rows, grade_idx, subjects, anchors, sgpa_x, cgpa_x
        )

        result = PageResult(
            regulation=meta.get("regulation"),
            branch=meta.get("branch"),
            semester=meta.get("semester"),
            exam_type=meta.get("exam_type"),
            held_in=meta.get("held_in"),
            subjects=subjects,
            students=students,
        )
        return result

    # -- metadata -----------------------------------------------------------
    @staticmethod
    def _metadata(text: str) -> dict[str, Optional[str]]:
        try:
            meta = MetadataService.extract(text)
        except MetadataException:
            meta = {"branch": None, "semester": None, "exam_type": None, "held_in": None}

        exam_type = meta.get("exam_type")
        regulation: Optional[str] = None
        if exam_type:
            match = regex_utils.REGULATION_RE.search(exam_type)
            if match:
                regulation = match.group(1).upper()
                # Strip the "(R19)" suffix from the exam type for a clean label.
                exam_type = regex_utils.REGULATION_RE.sub("", exam_type).strip()
        meta["exam_type"] = exam_type
        meta["regulation"] = regulation
        return meta

    @staticmethod
    def _gpa_anchors(header_row: list[Word]) -> tuple[Optional[float], Optional[float]]:
        """Return the x-centres of the SGPA and CGPA header columns."""
        sgpa_x: Optional[float] = None
        cgpa_x: Optional[float] = None
        for word in header_row:
            token = word["text"].strip().upper()
            center = (word["x0"] + word["x1"]) / 2.0
            if token == "SGPA":
                sgpa_x = center
            elif token == "CGPA":
                cgpa_x = center
        return sgpa_x, cgpa_x

    # -- students -----------------------------------------------------------
    @staticmethod
    def _parse_students(
        rows: list[list[Word]],
        grade_idx: Optional[int],
        subjects: list[str],
        anchors: list[float],
        sgpa_x: Optional[float],
        cgpa_x: Optional[float],
    ) -> list[StudentResult]:
        start = (grade_idx + 1) if grade_idx is not None else 0
        students: list[StudentResult] = []

        for row in rows[start:]:
            ordered = sorted(row, key=lambda w: w["x0"])
            if not ordered:
                continue
            roll = ordered[0]["text"].strip()
            if not regex_utils.is_roll_number(roll):
                continue

            student = SupplementaryService._parse_row(
                roll, ordered[1:], subjects, anchors, sgpa_x, cgpa_x
            )
            students.append(student)
        return students

    @staticmethod
    def _parse_row(
        roll: str,
        value_words: list[Word],
        subjects: list[str],
        anchors: list[float],
        sgpa_x: Optional[float],
        cgpa_x: Optional[float],
    ) -> StudentResult:
        sgpa: Optional[float] = None
        cgpa: Optional[float] = None
        subject_map: dict[str, str] = {}
        float_seen = 0

        for word in value_words:
            token = word["text"].strip()
            center = (word["x0"] + word["x1"]) / 2.0

            if regex_utils.is_float_token(token):
                value = float(token)
                target = SupplementaryService._nearest_gpa(center, sgpa_x, cgpa_x, float_seen)
                if target == "sgpa":
                    sgpa = value
                else:
                    cgpa = value
                float_seen += 1
            elif regex_utils.is_grade_token(token):
                idx = SubjectService._nearest_column(center, anchors)
                # A student re-took only some subjects -> map only what exists.
                subject_map[subjects[idx]] = token

        return StudentResult(roll_no=roll, sgpa=sgpa, cgpa=cgpa, subjects=subject_map)

    @staticmethod
    def _nearest_gpa(
        center: float,
        sgpa_x: Optional[float],
        cgpa_x: Optional[float],
        float_seen: int,
    ) -> str:
        """Decide whether a decimal is the SGPA or the CGPA column.

        Uses x-position when the header anchors are known; otherwise falls back
        to order (SGPA first, then CGPA).
        """
        if sgpa_x is not None and cgpa_x is not None:
            return "sgpa" if abs(center - sgpa_x) <= abs(center - cgpa_x) else "cgpa"
        if sgpa_x is not None:
            return "sgpa"
        if cgpa_x is not None:
            return "cgpa"
        return "sgpa" if float_seen == 0 else "cgpa"

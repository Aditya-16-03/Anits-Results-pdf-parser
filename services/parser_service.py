"""Orchestrates PDF, metadata, subject and student parsing into a response.

Every page is parsed independently: its own metadata header and its own subject
columns are read fresh, because a single PDF can contain multiple branches with
completely different subjects. Consecutive pages that share the same
branch/semester/exam/date are merged into one :class:`ResultSection`.
"""
from __future__ import annotations

import logging
from typing import Iterator, Optional

from models.result_response import ResultResponse, ResultSection
from models.student_result import StudentResult
from services.metadata_service import MetadataService
from services.normalization_service import SubjectNormalizer
from services.pdf_service import PdfService
from services.subject_service import SubjectService
from utils import constants, regex_utils
from utils.exceptions import MetadataException, ParsingException

logger = logging.getLogger(__name__)


class ParserService:
    """End-to-end conversion of a results PDF into a :class:`ResultResponse`."""

    @staticmethod
    def parse(file_path: str, normalize: Optional[bool] = None) -> ResultResponse:
        """Parse the PDF at *file_path* and return the structured response.

        Args:
            file_path: Path to the PDF to parse.
            normalize: Whether to clean up subject names. Defaults to the
                ``NORMALIZE_SUBJECTS`` configuration when ``None``.

        Raises:
            InvalidPdfException: if the file cannot be opened as a PDF.
            ParsingException: if not a single subject header is found.
        """
        if normalize is None:
            normalize = constants.NORMALIZE_SUBJECTS

        response = ResultResponse()
        current: Optional[ResultSection] = None
        any_subjects = False

        with PdfService(file_path) as pdf:
            logger.info("Opened PDF with %d pages (normalize=%s)", pdf.page_count, normalize)

            for page_index, page in enumerate(pdf.iter_pages()):
                text = page.extract_text() or ""

                meta = ParserService._page_metadata(text)
                subjects = ParserService._page_subjects(page)
                if subjects:
                    any_subjects = True
                    # Clean up names and guarantee uniqueness so colliding
                    # subject keys never drop a student's grade.
                    subjects = (
                        SubjectNormalizer.normalize_list(subjects)
                        if normalize
                        else SubjectNormalizer.ensure_unique(subjects)
                    )

                current = ParserService._resolve_section(
                    response, current, meta, subjects
                )

                # Map this page's students using this page's subjects
                # (falling back to the section's subjects if a page header
                # failed to parse but the layout is unchanged).
                effective_subjects = subjects or current.subjects
                for student in ParserService._parse_students(text, effective_subjects):
                    current.students.append(student)

                logger.debug(
                    "Page %d -> branch=%s, %d subjects, running students=%d",
                    page_index + 1,
                    current.branch,
                    len(effective_subjects),
                    len(current.students),
                )

        if not any_subjects:
            raise ParsingException("No subject header was found anywhere in the PDF.")

        logger.info(
            "Parsed %d students across %d section(s)",
            response.total_students,
            len(response.sections),
        )
        return response

    # -- section grouping ---------------------------------------------------
    @staticmethod
    def _resolve_section(
        response: ResultResponse,
        current: Optional[ResultSection],
        meta: dict[str, Optional[str]],
        subjects: list[str],
    ) -> ResultSection:
        """Return the section this page belongs to, starting a new one on change.

        A page starts a new section when its metadata differs from the current
        section. Pages with no readable metadata are treated as a continuation
        of the current section (headers occasionally fail to extract).
        """
        key = (meta.get("branch"), meta.get("semester"), meta.get("exam_type"), meta.get("held_in"))
        has_meta = any(key)

        if current is not None and (not has_meta or key == current.metadata_key()):
            # Continuation: enrich subjects if the section had none yet.
            if not current.subjects and subjects:
                current.subjects = subjects
            return current

        # New section.
        section = ResultSection(
            branch=meta.get("branch"),
            semester=meta.get("semester"),
            exam_type=meta.get("exam_type"),
            held_in=meta.get("held_in"),
            subjects=subjects,
        )
        response.sections.append(section)
        logger.info("Started new section: branch=%s subjects=%s", section.branch, subjects)
        return section

    # -- per-page extraction helpers ---------------------------------------
    @staticmethod
    def _page_metadata(text: str) -> dict[str, Optional[str]]:
        try:
            return MetadataService.extract(text)
        except MetadataException:
            return {"branch": None, "semester": None, "exam_type": None, "held_in": None}

    @staticmethod
    def _page_subjects(page) -> list[str]:
        try:
            return SubjectService.extract(page)
        except ParsingException:
            return []

    # -- student parsing ----------------------------------------------------
    @staticmethod
    def _parse_students(text: str, subjects: list[str]) -> Iterator[StudentResult]:
        """Yield a :class:`StudentResult` for every student row in *text*.

        Handles missing SGPA/CGPA, absent (``Ab``) grades, fail (``F``) rows and
        incomplete rows without raising.
        """
        for raw_line in text.splitlines():
            line = raw_line.strip()
            if not regex_utils.ROLL_LINE_RE.match(line):
                continue
            student = ParserService._parse_student_line(line, subjects)
            if student is not None:
                yield student

    @staticmethod
    def _parse_student_line(line: str, subjects: list[str]) -> Optional[StudentResult]:
        """Parse a single student row.

        Layout: ``<roll> [SGPA] [CGPA] <grade>...`` where SGPA/CGPA are optional
        (absent for fail / withheld results).
        """
        tokens = line.split()
        if not tokens or not regex_utils.is_roll_number(tokens[0]):
            return None

        roll_no = tokens[0]
        rest = tokens[1:]

        # Leading decimal tokens are the SGPA then CGPA.
        floats: list[float] = []
        idx = 0
        while idx < len(rest) and len(floats) < 2 and regex_utils.is_float_token(rest[idx]):
            floats.append(float(rest[idx]))
            idx += 1

        sgpa = floats[0] if len(floats) >= 1 else None
        cgpa = floats[1] if len(floats) >= 2 else None

        # Everything after the numbers should be grade cells.
        grade_tokens = [t for t in rest[idx:] if regex_utils.is_grade_token(t)]

        subject_map: dict[str, str] = {}
        for subject, grade in zip(subjects, grade_tokens):
            subject_map[subject] = grade

        return StudentResult(
            roll_no=roll_no,
            sgpa=sgpa,
            cgpa=cgpa,
            subjects=subject_map,
        )

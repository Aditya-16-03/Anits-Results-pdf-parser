"""Extraction of the exam metadata header (branch, semester, exam type, date)."""
from __future__ import annotations

import logging
from typing import Optional

from utils import regex_utils
from utils.exceptions import MetadataException

logger = logging.getLogger(__name__)


class MetadataService:
    """Parses the repeated header block that sits at the top of every page.

    A raw header (after whitespace normalisation) looks like::

        Branch: CHEMICAL ENGINEERING Course/Sem: II/IV B.Tech SEM-I
        Regular Examinations (R23) Held in: December 2024
    """

    @staticmethod
    def extract(page_text: str) -> dict[str, Optional[str]]:
        """Return a dict with ``branch``, ``semester``, ``exam_type`` and ``held_in``.

        Raises:
            MetadataException: if none of the expected fields can be located,
                which usually means this page has no header.
        """
        if not page_text:
            raise MetadataException("Page has no extractable text for metadata.")

        text = regex_utils.normalise_whitespace(page_text)

        branch = MetadataService._first_group(regex_utils.BRANCH_RE, text, "branch")
        held_in = MetadataService._first_group(regex_utils.HELD_IN_RE, text, "held")

        semester: Optional[str] = None
        exam_type: Optional[str] = None

        sem_exam = regex_utils.SEM_EXAM_RE.search(text)
        if sem_exam:
            semester = sem_exam.group("sem").strip()
            exam_type = sem_exam.group("exam").strip()
        else:
            # Fallback: grab the whole Course/Sem block and best-effort split it.
            block = regex_utils.COURSE_BLOCK_RE.search(text)
            if block:
                semester, exam_type = MetadataService._split_course_block(
                    block.group("block").strip()
                )

        if not any([branch, semester, exam_type, held_in]):
            raise MetadataException("No metadata fields found on this page.")

        metadata = {
            "branch": branch,
            "semester": semester,
            "exam_type": exam_type,
            "held_in": held_in,
        }
        logger.info("Extracted metadata: %s", metadata)
        return metadata

    @staticmethod
    def _first_group(pattern, text: str, group: str) -> Optional[str]:
        match = pattern.search(text)
        return match.group(group).strip() if match else None

    @staticmethod
    def _split_course_block(block: str) -> tuple[Optional[str], Optional[str]]:
        """Split a Course/Sem block into (semester, exam_type) heuristically.

        The semester portion ends at the ``SEM-x`` / ``Semester-x`` token; the
        remainder is treated as the exam type.
        """
        tokens = block.split()
        cut = None
        for idx, token in enumerate(tokens):
            if token.upper().startswith("SEM"):
                cut = idx
                break
        if cut is None:
            return block or None, None
        semester = " ".join(tokens[: cut + 1]) or None
        exam_type = " ".join(tokens[cut + 1:]) or None
        return semester, exam_type

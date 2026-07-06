"""Orchestrates supplementary-sheet parsing into a regulation-grouped response.

Pages are streamed one at a time; each page is parsed independently and then
merged into the response by **regulation**, and within a regulation by
**department (branch)**. Pages that repeat a branch within the same regulation
(a branch's results spanning several pages) are merged into one department.
"""
from __future__ import annotations

import logging
from collections import OrderedDict
from typing import Optional

from models.supplementary_response import (
    DepartmentResult,
    RegulationGroup,
    SupplementaryResponse,
)
from services.pdf_service import PdfService
from services.supplementary_service import PageResult, SupplementaryService
from utils import constants
from utils.exceptions import ParsingException

logger = logging.getLogger(__name__)


class SupplementaryParser:
    """End-to-end conversion of a supplementary PDF into JSON."""

    @staticmethod
    def parse(file_path: str, normalize: Optional[bool] = None) -> SupplementaryResponse:
        """Parse the supplementary PDF at *file_path*.

        Raises:
            InvalidPdfException: if the file cannot be opened as a PDF.
            ParsingException: if no results table is found anywhere.
        """
        if normalize is None:
            normalize = constants.NORMALIZE_SUBJECTS

        response = SupplementaryResponse()
        # regulation label -> RegulationGroup
        reg_index: "OrderedDict[str, RegulationGroup]" = OrderedDict()
        # (regulation, branch, semester) -> DepartmentResult
        dept_index: dict[tuple, DepartmentResult] = {}
        any_page = False

        with PdfService(file_path) as pdf:
            logger.info("Opened supplementary PDF with %d pages", pdf.page_count)

            for page_number, page in enumerate(pdf.iter_pages(), start=1):
                result = SupplementaryService.parse_page(page, normalize=normalize)
                if result is None:
                    logger.debug("Page %d has no results table; skipping", page_number)
                    continue
                any_page = True

                if response.exam_type is None:
                    response.exam_type = result.exam_type
                if response.held_in is None:
                    response.held_in = result.held_in

                SupplementaryParser._merge(response, reg_index, dept_index, result)

        if not any_page:
            raise ParsingException("No supplementary results table found in the PDF.")

        SupplementaryParser._prune_empty(response)

        logger.info(
            "Parsed %d regulation(s), %d student(s) total",
            len(response.regulations),
            sum(len(d.students) for r in response.regulations for d in r.departments),
        )
        return response

    # -- pruning ------------------------------------------------------------
    @staticmethod
    def _prune_empty(response: SupplementaryResponse) -> None:
        """Drop departments that have no students and regulations left empty."""
        for group in response.regulations:
            group.departments = [d for d in group.departments if d.students]
        response.regulations = [g for g in response.regulations if g.departments]

    # -- grouping -----------------------------------------------------------
    @staticmethod
    def _merge(
        response: SupplementaryResponse,
        reg_index: "OrderedDict[str, RegulationGroup]",
        dept_index: dict[tuple, DepartmentResult],
        page: PageResult,
    ) -> None:
        reg_label = page.regulation or "UNKNOWN"

        group = reg_index.get(reg_label)
        if group is None:
            group = RegulationGroup(regulation=reg_label)
            reg_index[reg_label] = group
            response.regulations.append(group)

        dept_key = (reg_label, page.branch, page.semester)
        dept = dept_index.get(dept_key)
        if dept is None:
            dept = DepartmentResult(branch=page.branch, semester=page.semester)
            dept_index[dept_key] = dept
            group.departments.append(dept)

        dept.students.extend(page.students)

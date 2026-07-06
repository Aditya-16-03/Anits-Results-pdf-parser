"""Response models for supplementary result sheets.

Supplementary PDFs mix several **regulations** (R15, R19, R20, R20.1, R23) in a
single document, and each regulation contains results for several
**departments** (branches). The response therefore nests:

    regulation -> departments -> students

Each student maps only the subjects they re-appeared for (supplementary sheets
are sparse), so ``subjects`` per student may contain fewer entries than the
department's full subject list.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from models.student_result import StudentResult


@dataclass
class DepartmentResult:
    """Results for one branch within a regulation block."""

    branch: Optional[str] = None
    semester: Optional[str] = None
    students: list[StudentResult] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {
            "branch": self.branch,
            "semester": self.semester,
            "students": [s.to_dict() for s in self.students],
        }


@dataclass
class RegulationGroup:
    """All department results that belong to a single regulation."""

    regulation: Optional[str] = None
    departments: list[DepartmentResult] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {
            "regulation": self.regulation,
            "departments": [d.to_dict() for d in self.departments],
        }


@dataclass
class SupplementaryResponse:
    """Top-level payload for ``POST /extract-supplementary-results``."""

    exam_type: Optional[str] = None
    held_in: Optional[str] = None
    regulations: list[RegulationGroup] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {
            "examType": self.exam_type,
            "heldIn": self.held_in,
            "regulationCount": len(self.regulations),
            "regulations": [r.to_dict() for r in self.regulations],
        }

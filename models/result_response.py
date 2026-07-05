"""Top-level API response models.

A single results PDF can contain **several branches** (e.g. Chemical
Engineering followed by CSE-AIML). Each page carries its own metadata header
and its own subject columns, so the response is organised into *sections* -
one per distinct branch / semester / exam / date block.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from models.student_result import StudentResult


@dataclass
class ResultSection:
    """A contiguous block of pages that share the same header.

    Attributes:
        branch: Degree branch, e.g. ``CHEMICAL ENGINEERING``.
        semester: Course / semester descriptor, e.g. ``II/IV B.Tech SEM-I``.
        exam_type: Examination type, e.g. ``Regular Examinations (R23)``.
        held_in: When the exam was held, e.g. ``December 2024``.
        subjects: The subject names for this section, in column order.
        students: All parsed student rows belonging to this section.
    """

    branch: Optional[str] = None
    semester: Optional[str] = None
    exam_type: Optional[str] = None
    held_in: Optional[str] = None
    subjects: list[str] = field(default_factory=list)
    students: list[StudentResult] = field(default_factory=list)

    def metadata_key(self) -> tuple:
        """Identity used to decide whether a page continues this section."""
        return (self.branch, self.semester, self.exam_type, self.held_in)

    def to_dict(self) -> dict[str, object]:
        return {
            "branch": self.branch,
            "semester": self.semester,
            "examType": self.exam_type,
            "heldIn": self.held_in,
            "subjects": self.subjects,
            "students": [student.to_dict() for student in self.students],
        }


@dataclass
class ResultResponse:
    """The complete payload returned by ``POST /extract-results``.

    Attributes:
        sections: One entry per branch / header block found in the PDF.
    """

    sections: list[ResultSection] = field(default_factory=list)

    @property
    def total_students(self) -> int:
        return sum(len(section.students) for section in self.sections)

    def to_dict(self) -> dict[str, object]:
        return {
            "sectionCount": len(self.sections),
            "totalStudents": self.total_students,
            "sections": [section.to_dict() for section in self.sections],
        }

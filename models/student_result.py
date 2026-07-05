"""Data model for a single student's result row."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class StudentResult:
    """Structured representation of one student in the results table.

    Attributes:
        roll_no: The student's roll number, e.g. ``A23126502001``.
        sgpa: Semester GPA, or ``None`` when the PDF omits it (fail / withheld).
        cgpa: Cumulative GPA, or ``None`` when the PDF omits it.
        subjects: Mapping of subject name to the grade the student obtained.
    """

    roll_no: str
    sgpa: Optional[float] = None
    cgpa: Optional[float] = None
    subjects: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        """Serialise to the JSON shape expected by n8n / Spring Boot."""
        return {
            "rollNo": self.roll_no,
            "sgpa": self.sgpa,
            "cgpa": self.cgpa,
            "subjects": self.subjects,
        }

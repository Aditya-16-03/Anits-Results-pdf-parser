"""Unit tests for student-row parsing, including tricky edge cases."""
from __future__ import annotations

from services.parser_service import ParserService

SUBJECTS = [
    "Vector Calculus & Statistic",
    "Instrumentation and Analytic",
    "Biology for Engineers",
    "Chemical Process Calculat",
    "Momentum Transfer",
    "Mechanical Operations",
    "Momentum Transfer Lab",
    "Mechanical Operations Lab",
    "Logical Reasoning & Corpora",
    "Entrepreneurship Develop",
]


def _parse(line: str):
    return ParserService._parse_student_line(line, SUBJECTS)


def test_normal_row_has_sgpa_cgpa_and_ten_grades():
    student = _parse("A23126502001 7.36 8.15 B+ A A C A A B+ A A A+")
    assert student.roll_no == "A23126502001"
    assert student.sgpa == 7.36
    assert student.cgpa == 8.15
    assert len(student.subjects) == 10
    assert student.subjects["Vector Calculus & Statistic"] == "B+"
    assert student.subjects["Entrepreneurship Develop"] == "A+"


def test_fail_row_without_sgpa_cgpa_maps_null_gpas():
    # Student A23126502009: no SGPA/CGPA, row starts straight into grades.
    student = _parse("A23126502009 F A P F P P B+ C B+ A+")
    assert student.roll_no == "A23126502009"
    assert student.sgpa is None
    assert student.cgpa is None
    # 10 grade cells still map onto the 10 subjects.
    assert len(student.subjects) == 10
    assert student.subjects["Vector Calculus & Statistic"] == "F"


def test_incomplete_row_with_only_sgpa():
    # Student A23126502012: SGPA present, CGPA missing, grades incomplete.
    student = _parse("A23126502012 6.00 B")
    assert student.roll_no == "A23126502012"
    assert student.sgpa == 6.00
    assert student.cgpa is None
    # Only one grade cell present -> only one subject mapped, no crash.
    assert len(student.subjects) == 1


def test_absent_grade_is_recognised():
    # Student A23126502020: contains an "Ab" (absent) grade, no SGPA/CGPA.
    student = _parse("A23126502020 F B+ P P Ab B B+ B+ A A")
    assert student.sgpa is None
    assert student.cgpa is None
    assert "Ab" in student.subjects.values()


def test_non_student_line_returns_none():
    assert _parse("Note: In case of any deviation ...") is None
    assert _parse("Roll No SGPA CGPA") is None


def test_extra_grades_are_truncated_to_subject_count():
    # More grade cells than subjects should never overflow the mapping.
    line = "A23126502099 7.00 7.00 " + " ".join(["A"] * 15)
    student = _parse(line)
    assert len(student.subjects) == len(SUBJECTS)

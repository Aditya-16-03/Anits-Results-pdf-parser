"""Tests for supplementary-sheet parsing (sparse, coordinate-based)."""
from __future__ import annotations

from services.supplementary_parser import SupplementaryParser
from services.supplementary_service import SupplementaryService
from tests.conftest import requires_supplementary_pdf


def _word(text: str, center: float) -> dict:
    """Build a minimal pdfplumber-style word centred at *center*."""
    return {"text": text, "x0": center - 3, "x1": center + 3, "top": 100.0}


# ---------------------------------------------------------------------------
# SGPA vs CGPA disambiguation
# ---------------------------------------------------------------------------
def test_nearest_gpa_by_position():
    assert SupplementaryService._nearest_gpa(22, 20, 50, 0) == "sgpa"
    assert SupplementaryService._nearest_gpa(48, 20, 50, 0) == "cgpa"


def test_nearest_gpa_falls_back_to_order():
    assert SupplementaryService._nearest_gpa(0, None, None, 0) == "sgpa"
    assert SupplementaryService._nearest_gpa(0, None, None, 1) == "cgpa"


# ---------------------------------------------------------------------------
# The core requirement: a lone grade must land in the correct column
# ---------------------------------------------------------------------------
SUBJECTS = ["Analog Electronic Circuits", "Electrical Measurements", "Engineering Mathematics-IV"]
ANCHORS = [100.0, 200.0, 300.0]
SGPA_X, CGPA_X = 20.0, 50.0


def test_sparse_single_grade_maps_to_its_column():
    # A student who only re-took the 3rd subject: a single grade near anchor 3.
    student = SupplementaryService._parse_row(
        "319126514150", [_word("F", 300)], SUBJECTS, ANCHORS, SGPA_X, CGPA_X
    )
    assert student.roll_no == "319126514150"
    assert student.sgpa is None and student.cgpa is None
    assert student.subjects == {"Engineering Mathematics-IV": "F"}


def test_row_with_sgpa_and_scattered_grades():
    words = [_word("6.79", 20), _word("B+", 200), _word("P", 300)]
    student = SupplementaryService._parse_row(
        "319126514128", words, SUBJECTS, ANCHORS, SGPA_X, CGPA_X
    )
    assert student.sgpa == 6.79
    assert student.cgpa is None
    assert student.subjects == {
        "Electrical Measurements": "B+",
        "Engineering Mathematics-IV": "P",
    }


def test_row_with_sgpa_and_cgpa():
    words = [_word("5.43", 20), _word("5.32", 50), _word("C", 100)]
    student = SupplementaryService._parse_row(
        "319126502009", words, SUBJECTS, ANCHORS, SGPA_X, CGPA_X
    )
    assert student.sgpa == 5.43
    assert student.cgpa == 5.32
    assert student.subjects == {"Analog Electronic Circuits": "C"}


def test_full_dense_row_maps_all_columns():
    words = [_word("I", 100), _word("I", 200), _word("B+", 300)]
    student = SupplementaryService._parse_row(
        "318126514114", words, SUBJECTS, ANCHORS, SGPA_X, CGPA_X
    )
    assert student.subjects == {
        "Analog Electronic Circuits": "I",
        "Electrical Measurements": "I",
        "Engineering Mathematics-IV": "B+",
    }


# ---------------------------------------------------------------------------
# Metadata / regulation extraction
# ---------------------------------------------------------------------------
def test_metadata_extracts_regulation_and_clean_exam_type():
    text = (
        "RESULTS\n"
        "Branch: CHEMICAL ENGINEERING Course/Sem: II/IV B.Tech SEM-II "
        "Supplementary Examinations (R19) Held in: December 2025\n"
        "Roll No SGPA CGPA\n"
    )
    meta = SupplementaryService._metadata(text)
    assert meta["regulation"] == "R19"
    assert meta["branch"] == "CHEMICAL ENGINEERING"
    assert meta["semester"] == "II/IV B.Tech SEM-II"
    assert meta["exam_type"] == "Supplementary Examinations"
    assert meta["held_in"] == "December 2025"


def test_metadata_handles_dotted_regulation():
    text = (
        "Branch: CIVIL ENGINEERING Course/Sem: II/IV B.Tech SEM-II "
        "Supplementary Examinations (R20.1) Held in: December 2025 Roll No SGPA CGPA"
    )
    meta = SupplementaryService._metadata(text)
    assert meta["regulation"] == "R20.1"


# ---------------------------------------------------------------------------
# Integration (runs only when a supplementary PDF is present in uploads/)
# ---------------------------------------------------------------------------
@requires_supplementary_pdf
def test_end_to_end_supplementary(supplementary_pdf_path):
    response = SupplementaryParser.parse(supplementary_pdf_path)
    payload = response.to_dict()

    assert payload["examType"] == "Supplementary Examinations"
    assert payload["heldIn"] == "December 2025"
    assert payload["regulationCount"] >= 1

    # Regulations are grouped by value.
    reg_labels = [r["regulation"] for r in payload["regulations"]]
    assert len(reg_labels) == len(set(reg_labels)), "regulations must be unique"

    # Every student has a roll number and a (possibly small) subjects map.
    for reg in payload["regulations"]:
        for dept in reg["departments"]:
            assert dept["branch"]
            for student in dept["students"]:
                assert student["rollNo"]
                assert isinstance(student["subjects"], dict)

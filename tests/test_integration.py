"""Full-pipeline integration tests against the real sample PDF."""
from __future__ import annotations

from services.parser_service import ParserService
from services.pdf_service import PdfService
from services.subject_service import SubjectService
from tests.conftest import requires_sample_pdf

EXPECTED_CHEM_SUBJECTS = {
    "Vector Calculus & Statistic",
    "Instrumentation and Analytic",
    "Biology for Engineers",
    "Momentum Transfer",
    "Mechanical Operations",
    "Momentum Transfer Lab",
    "Mechanical Operations Lab",
}


@requires_sample_pdf
def test_subject_extraction_from_first_page(sample_pdf_path):
    with PdfService(sample_pdf_path) as pdf:
        first_page = next(pdf.iter_pages())
        subjects = SubjectService.extract(first_page)

    assert len(subjects) == 10
    for expected in EXPECTED_CHEM_SUBJECTS:
        assert expected in subjects, f"Missing subject: {expected!r} in {subjects}"


@requires_sample_pdf
def test_full_parse_produces_multiple_sections(sample_pdf_path):
    response = ParserService.parse(sample_pdf_path)

    # More than one branch lives in this PDF.
    assert len(response.sections) >= 2
    assert response.total_students > 100

    first = response.sections[0]
    assert first.branch == "CHEMICAL ENGINEERING"

    # Every section has its own non-empty subject list and every student
    # only carries subjects from its own section.
    for section in response.sections:
        assert section.subjects, f"Section {section.branch} has no subjects"
        section_subject_set = set(section.subjects)
        for student in section.students:
            assert student.roll_no
            assert set(student.subjects).issubset(section_subject_set)


@requires_sample_pdf
def test_cse_student_has_cse_subjects_not_chemical(sample_pdf_path):
    """Regression for the cross-branch subject bug."""
    response = ParserService.parse(sample_pdf_path)

    target = None
    target_section = None
    for section in response.sections:
        for student in section.students:
            if student.roll_no == "A23126552069":
                target = student
                target_section = section
                break
        if target:
            break

    assert target is not None
    assert "CHEMICAL" not in (target_section.branch or "")
    assert "Biology for Engineers" not in target.subjects
    assert "Momentum Transfer" not in target.subjects
    assert len(target.subjects) == 10


@requires_sample_pdf
def test_subject_and_lab_are_distinct_across_sections(sample_pdf_path):
    """A subject and its lab must stay distinct; distinct subjects must not be
    mislabelled as a lab."""
    response = ParserService.parse(sample_pdf_path)
    by_branch = {s.branch: s for s in response.sections}

    aiml = next(s for s in response.sections if "AI&ML" in (s.branch or ""))
    # The CN&O column must NOT be turned into a fake "Computer Networks Lab".
    assert "Computer Networks Lab" not in aiml.subjects
    assert "Computer Networks" in aiml.subjects
    # Its real Data Structures lab, however, is present and distinct.
    assert "Data Structures" in aiml.subjects
    assert "Data Structures Lab" in aiml.subjects

    cse = by_branch.get("COMPUTER SCIENCE & ENGINEERING")
    if cse is not None:
        # Genuine theory/lab pairs are both present and distinct.
        assert "Object Oriented Programming" in cse.subjects
        assert "Object Oriented Programming Lab" in cse.subjects
        assert "Data Structures and Algorithms" in cse.subjects
        assert "Data Structures and Algorithms Lab" in cse.subjects

    # No section ever contains duplicate subject keys (no grade lost).
    for section in response.sections:
        assert len(section.subjects) == len(set(section.subjects))


@requires_sample_pdf
def test_fail_row_has_null_gpas(sample_pdf_path):
    response = ParserService.parse(sample_pdf_path)

    fail_row = None
    for section in response.sections:
        for student in section.students:
            if student.roll_no == "A23126502009":
                fail_row = student
                break
    assert fail_row is not None
    assert fail_row.sgpa is None
    assert fail_row.cgpa is None
    assert len(fail_row.subjects) == 10

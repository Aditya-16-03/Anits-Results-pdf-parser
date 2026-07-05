"""Unit tests for the optional subject-name normalisation layer."""
from __future__ import annotations

from services.normalization_service import SubjectNormalizer


def test_matches_truncated_title_case_name():
    assert (
        SubjectNormalizer.normalize_name("Chemical Process Calculat")
        == "Chemical Process Calculations"
    )
    assert (
        SubjectNormalizer.normalize_name("Vector Calculus & Statistic")
        == "Vector Calculus & Statistical Methods"
    )
    assert (
        SubjectNormalizer.normalize_name("Entrepreneurship Develop")
        == "Entrepreneurship Development & IPR"
    )


def test_matches_over_split_all_caps_name():
    assert SubjectNormalizer.normalize_name("DATA STRUCT URES") == "Data Structures"
    assert SubjectNormalizer.normalize_name("THEORY OF COMPU TATION") == "Theory of Computation"
    assert SubjectNormalizer.normalize_name("OPERAT ING SYSTEM S") == "Operating Systems"
    assert SubjectNormalizer.normalize_name("DATA STRUCT URES LAB") == "Data Structures Lab"


def test_unknown_name_falls_back_to_title_case():
    assert SubjectNormalizer.normalize_name("SOME BRAND NEW SUBJECT") == "Some Brand New Subject"
    # Connectors are lower-cased, acronyms preserved.
    assert SubjectNormalizer.normalize_name("basics of ai and ml") == "Basics of AI and ML"


def test_duplicate_names_become_lab_variants():
    # The repeated column is the laboratory - no entry is lost.
    result = SubjectNormalizer.ensure_unique(
        ["Object Oriented Programming", "Object Oriented Programming"]
    )
    assert result == ["Object Oriented Programming", "Object Oriented Programming Lab"]


def test_triple_duplicate_gets_numeric_suffix():
    result = SubjectNormalizer.ensure_unique(["X", "X", "X"])
    assert result == ["X", "X Lab", "X (2)"]


def test_normalize_list_end_to_end():
    raw = [
        "DATA STRUCT URES",
        "Data Structures and Algorith",
        "Data Structures and Algorith",  # duplicate -> lab
    ]
    result = SubjectNormalizer.normalize_list(raw)
    assert result == [
        "Data Structures",
        "Data Structures and Algorithms",
        "Data Structures and Algorithms Lab",
    ]
    # Every entry is unique so the grade map keeps all columns.
    assert len(set(result)) == len(result)


def test_genuine_theory_and_lab_pair_are_kept_distinct():
    # Identical raw text = the trailing "Lab" was truncated -> theory then lab.
    raw = ["Object Oriented Progra", "Object Oriented Progra"]
    result = SubjectNormalizer.normalize_list(raw)
    assert result == ["Object Oriented Programming", "Object Oriented Programming Lab"]


def test_different_subjects_that_truncate_alike_are_not_merged_to_lab():
    # "COMPU TER NETWO RKS" (Computer Networks) vs "COMPU TER NETWO" (a distinct
    # CN&O subject). The second must NOT become "Computer Networks Lab".
    raw = ["COMPU TER NETWO RKS", "COMPU TER NETWO"]
    result = SubjectNormalizer.normalize_list(raw)
    assert result[0] == "Computer Networks"
    assert "Lab" not in result[1]
    assert result[1] != "Computer Networks"
    assert len(set(result)) == 2


def test_real_theory_lab_where_lab_kept_when_names_differ():
    # When the lab already reconstructs with its own text, both stay as-is.
    raw = ["DATA STRUCT URES", "DATA STRUCT URES LAB"]
    result = SubjectNormalizer.normalize_list(raw)
    assert result == ["Data Structures", "Data Structures Lab"]

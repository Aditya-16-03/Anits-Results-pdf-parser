"""Tests for the dynamic subject-name reconstruction heuristic."""
from __future__ import annotations

from services.subject_service import SubjectService


def _word(text: str, top: float, x0: float) -> dict:
    """Build a minimal pdfplumber-style word dict."""
    return {"text": text, "top": top, "x0": x0, "x1": x0 + 5 * len(text)}


def test_join_fragments_rebuilds_broken_words():
    # Column: Vector / Calculu / s & / Statistic  ->  "Vector Calculus & Statistic"
    frags = [
        _word("Vector", 163.0, 173.0),
        _word("Calculu", 173.0, 172.0),
        _word("s", 183.0, 177.0),
        _word("&", 183.0, 180.0),
        _word("Statistic", 192.0, 172.0),
    ]
    assert SubjectService._join_fragments(frags) == "Vector Calculus & Statistic"


def test_join_fragments_keeps_stopwords_separate():
    # Instrum / entation / and / Analytic -> "Instrumentation and Analytic"
    frags = [
        _word("Instrum", 163.0, 203.0),
        _word("entation", 173.0, 202.0),
        _word("and", 183.0, 207.0),
        _word("Analytic", 192.0, 202.0),
    ]
    assert SubjectService._join_fragments(frags) == "Instrumentation and Analytic"


def test_join_fragments_handles_for_connector():
    # Biology / for / Enginee / rs -> "Biology for Engineers"
    frags = [
        _word("Biology", 163.0, 234.0),
        _word("for", 173.0, 238.0),
        _word("Enginee", 183.0, 233.0),
        _word("rs", 192.0, 239.0),
    ]
    assert SubjectService._join_fragments(frags) == "Biology for Engineers"


def test_nearest_column_assignment():
    anchors = [180.0, 210.0, 240.0]
    assert SubjectService._nearest_column(178.0, anchors) == 0
    assert SubjectService._nearest_column(212.0, anchors) == 1
    assert SubjectService._nearest_column(239.0, anchors) == 2

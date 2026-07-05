"""Tests for exam metadata extraction."""
from __future__ import annotations

import pytest

from services.metadata_service import MetadataService
from utils.exceptions import MetadataException

# The header as it comes out of pdfplumber (wrapped across physical lines).
HEADER_TEXT = (
    "RESULTS Page 1 of 124\n"
    "Branch: CHEMICAL ENGINEERING Course/Sem: II/IV B.Tech SEM-I Regular Examinations\n"
    " (R23) Held in: December 2024                        Roll No SGPA CGPA\n"
)


def test_extracts_all_metadata_fields():
    meta = MetadataService.extract(HEADER_TEXT)
    assert meta["branch"] == "CHEMICAL ENGINEERING"
    assert meta["semester"] == "II/IV B.Tech SEM-I"
    assert meta["exam_type"] == "Regular Examinations (R23)"
    assert meta["held_in"] == "December 2024"


def test_empty_text_raises():
    with pytest.raises(MetadataException):
        MetadataService.extract("")


def test_unrelated_text_raises():
    with pytest.raises(MetadataException):
        MetadataService.extract("just some page footer text with no header")

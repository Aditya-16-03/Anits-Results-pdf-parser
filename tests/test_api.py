"""Tests for the Flask API layer and validation / error handling."""
from __future__ import annotations

import io

from tests.conftest import requires_sample_pdf


def test_health_endpoint(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.get_json() == {"status": "UP"}


def test_missing_file_is_rejected(client):
    resp = client.post("/extract-results", data={})
    assert resp.status_code == 400
    assert resp.get_json()["error"] == "InvalidPdfException"


def test_non_pdf_extension_is_rejected(client):
    data = {"file": (io.BytesIO(b"hello"), "notes.txt")}
    resp = client.post("/extract-results", data=data, content_type="multipart/form-data")
    assert resp.status_code == 400
    assert resp.get_json()["error"] == "InvalidPdfException"


def test_empty_pdf_is_rejected(client):
    data = {"file": (io.BytesIO(b""), "empty.pdf")}
    resp = client.post("/extract-results", data=data, content_type="multipart/form-data")
    assert resp.status_code == 400


def test_corrupted_pdf_is_rejected(client):
    # Right extension, wrong content -> fails the magic-header check.
    data = {"file": (io.BytesIO(b"this is not really a pdf"), "fake.pdf")}
    resp = client.post("/extract-results", data=data, content_type="multipart/form-data")
    assert resp.status_code == 400
    assert resp.get_json()["error"] == "InvalidPdfException"


@requires_sample_pdf
def test_extract_results_with_real_pdf(client, sample_pdf_path):
    with open(sample_pdf_path, "rb") as handle:
        data = {"file": (io.BytesIO(handle.read()), "results.pdf")}
        resp = client.post(
            "/extract-results", data=data, content_type="multipart/form-data"
        )

    assert resp.status_code == 200
    payload = resp.get_json()

    # The PDF holds multiple branches, so we expect multiple sections.
    assert payload["sectionCount"] >= 2
    assert payload["totalStudents"] > 100

    first_section = payload["sections"][0]
    assert first_section["branch"] == "CHEMICAL ENGINEERING"
    assert first_section["semester"] == "II/IV B.Tech SEM-I"
    assert first_section["examType"] == "Regular Examinations (R23)"
    assert first_section["heldIn"] == "December 2024"

    first_student = first_section["students"][0]
    assert first_student["rollNo"] == "A23126502001"
    assert first_student["sgpa"] == 7.36
    assert first_student["cgpa"] == 8.15
    assert len(first_student["subjects"]) == 10


@requires_sample_pdf
def test_students_get_their_own_branch_subjects(client, sample_pdf_path):
    """Regression: a CSE student must not be labelled with Chemical subjects."""
    with open(sample_pdf_path, "rb") as handle:
        data = {"file": (io.BytesIO(handle.read()), "results.pdf")}
        resp = client.post(
            "/extract-results", data=data, content_type="multipart/form-data"
        )

    payload = resp.get_json()

    target = None
    target_section = None
    for section in payload["sections"]:
        for student in section["students"]:
            if student["rollNo"] == "A23126552069":
                target = student
                target_section = section
                break
        if target:
            break

    assert target is not None, "Expected roll A23126552069 in the results"
    # This student belongs to the CSE-AIML section, not Chemical Engineering.
    assert "CHEMICAL" not in (target_section["branch"] or "")
    # Their subjects must come from their own page's header.
    assert "Biology for Engineers" not in target["subjects"]
    assert "Momentum Transfer" not in target["subjects"]

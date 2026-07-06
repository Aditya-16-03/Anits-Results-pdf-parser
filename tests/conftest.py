"""Shared pytest fixtures."""
from __future__ import annotations

import glob
import os

import pytest

from app import create_app

# The real sample PDF shipped in the repo (used for integration tests).
_UPLOAD_MATCHES = glob.glob(os.path.join("uploads", "*.pdf"))


def _find(*needles: str) -> str | None:
    for path in _UPLOAD_MATCHES:
        name = os.path.basename(path).lower()
        if any(n in name for n in needles):
            return path
    return None


# Regular sheet = the December-2024 regular results (fallback: first PDF).
SAMPLE_PDF = _find("regular") or (_UPLOAD_MATCHES[0] if _UPLOAD_MATCHES else None)
# Supplementary sheet = any PDF whose name hints at supplementary results.
SUPPLEMENTARY_PDF = _find("supp", "supplementary")

# Skip integration tests gracefully if the relevant PDF is not available.
requires_sample_pdf = pytest.mark.skipif(
    SAMPLE_PDF is None, reason="No sample PDF found in uploads/."
)
requires_supplementary_pdf = pytest.mark.skipif(
    SUPPLEMENTARY_PDF is None,
    reason="No supplementary PDF found in uploads/ (name should contain 'supp').",
)


@pytest.fixture()
def supplementary_pdf_path() -> str:
    return SUPPLEMENTARY_PDF


@pytest.fixture()
def sample_pdf_path() -> str:
    return SAMPLE_PDF


@pytest.fixture()
def client():
    app = create_app()
    app.config.update(TESTING=True)
    with app.test_client() as test_client:
        yield test_client

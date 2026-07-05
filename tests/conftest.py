"""Shared pytest fixtures."""
from __future__ import annotations

import glob
import os

import pytest

from app import create_app

# The real sample PDF shipped in the repo (used for integration tests).
_UPLOAD_MATCHES = glob.glob(os.path.join("uploads", "*.pdf"))
SAMPLE_PDF = _UPLOAD_MATCHES[0] if _UPLOAD_MATCHES else None

# Skip integration tests gracefully if no sample PDF is available.
requires_sample_pdf = pytest.mark.skipif(
    SAMPLE_PDF is None, reason="No sample PDF found in uploads/."
)


@pytest.fixture()
def sample_pdf_path() -> str:
    return SAMPLE_PDF


@pytest.fixture()
def client():
    app = create_app()
    app.config.update(TESTING=True)
    with app.test_client() as test_client:
        yield test_client

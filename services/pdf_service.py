"""Low level PDF access: validation and memory-friendly page iteration."""
from __future__ import annotations

import logging
import os
from typing import Iterator

import pdfplumber
from pdfplumber.page import Page
from werkzeug.datastructures import FileStorage

from utils import constants
from utils.exceptions import InvalidPdfException

logger = logging.getLogger(__name__)


class PdfService:
    """Validates uploads and streams a PDF one page at a time.

    Usage::

        with PdfService(path) as pdf:
            for page in pdf.iter_pages():
                ...

    The context manager guarantees the underlying file handle is closed, and
    :meth:`iter_pages` flushes each page's cache after yielding so that parsing
    a 100+ page document does not accumulate the whole thing in memory.
    """

    def __init__(self, file_path: str) -> None:
        self.file_path = file_path
        self._pdf: pdfplumber.PDF | None = None

    # -- upload validation --------------------------------------------------
    @staticmethod
    def validate_upload(file: FileStorage | None) -> None:
        """Validate an incoming multipart upload before it is saved.

        Raises:
            InvalidPdfException: if the file is missing, empty, has the wrong
                extension/mime type, or exceeds the size limit.
        """
        if file is None or not file.filename:
            raise InvalidPdfException("No file part named 'file' was provided.")

        _, ext = os.path.splitext(file.filename.lower())
        if ext not in constants.ALLOWED_EXTENSIONS:
            raise InvalidPdfException(
                f"Unsupported file type '{ext or 'unknown'}'. Only PDF files are accepted."
            )

        if file.mimetype and file.mimetype.lower() not in constants.ALLOWED_MIME_TYPES:
            logger.warning("Unexpected mime type '%s' for %s", file.mimetype, file.filename)

        # Measure size without loading the whole stream into memory.
        stream = file.stream
        stream.seek(0, os.SEEK_END)
        size = stream.tell()
        stream.seek(0)

        if size == 0:
            raise InvalidPdfException("The uploaded file is empty.")
        if size > constants.MAX_FILE_SIZE_BYTES:
            raise InvalidPdfException(
                f"File too large ({size} bytes). Limit is {constants.MAX_FILE_SIZE_BYTES} bytes."
            )

    @staticmethod
    def validate_pdf_file(file_path: str) -> None:
        """Cheaply confirm a saved file really is a PDF by its magic header."""
        try:
            with open(file_path, "rb") as handle:
                header = handle.read(len(constants.PDF_MAGIC_HEADER))
        except OSError as exc:  # pragma: no cover - filesystem edge case
            raise InvalidPdfException(f"Could not read uploaded file: {exc}") from exc

        if header != constants.PDF_MAGIC_HEADER:
            raise InvalidPdfException("File is not a valid PDF (bad header).")

    # -- context management -------------------------------------------------
    def __enter__(self) -> "PdfService":
        try:
            self._pdf = pdfplumber.open(self.file_path)
        except Exception as exc:  # pdfminer raises a variety of errors
            raise InvalidPdfException(f"Failed to open PDF: {exc}") from exc
        if not self._pdf.pages:
            raise InvalidPdfException("PDF contains no pages.")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if self._pdf is not None:
            self._pdf.close()
            self._pdf = None

    # -- iteration ----------------------------------------------------------
    @property
    def page_count(self) -> int:
        """Number of pages in the open document."""
        if self._pdf is None:
            raise RuntimeError("PdfService must be used as a context manager.")
        return len(self._pdf.pages)

    def iter_pages(self) -> Iterator[Page]:
        """Yield each page, flushing its cache afterwards to cap memory use."""
        if self._pdf is None:
            raise RuntimeError("PdfService must be used as a context manager.")

        for index, page in enumerate(self._pdf.pages):
            try:
                yield page
            finally:
                # Release the objects pdfplumber cached for this page.
                page.flush_cache()
                logger.debug("Processed and flushed page %d", index + 1)

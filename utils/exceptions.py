"""Custom exception hierarchy for the ANITS PDF Parser.

All service-level failures inherit from :class:`PdfParserException` so the
Flask layer can register a single family of error handlers and still map each
concrete error to a meaningful HTTP status code.
"""
from __future__ import annotations


class PdfParserException(Exception):
    """Base class for every error raised by this service.

    Attributes:
        message: Human readable description of what went wrong.
        status_code: HTTP status code the API should respond with.
    """

    status_code: int = 500

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.message = message
        if status_code is not None:
            self.status_code = status_code

    def to_dict(self) -> dict[str, object]:
        """Serialise the error into an n8n / Spring friendly payload."""
        return {
            "error": self.__class__.__name__,
            "message": self.message,
        }


class InvalidPdfException(PdfParserException):
    """Raised when the uploaded file is missing, empty, not a PDF or corrupt."""

    status_code = 400


class MetadataException(PdfParserException):
    """Raised when the exam metadata block cannot be located or parsed."""

    status_code = 422


class ParsingException(PdfParserException):
    """Raised when subjects or student rows cannot be extracted from the PDF."""

    status_code = 422

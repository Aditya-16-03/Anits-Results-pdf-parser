"""ANITS PDF Parser - Flask microservice.

Converts ANITS semester result PDFs into structured JSON. The service is
stateless: it performs no database work and is designed to be called from n8n
and consumed by a Spring Boot backend.

Endpoints:
    POST /extract-results   Upload a results PDF, receive structured JSON.
    GET  /health            Liveness probe.
"""
from __future__ import annotations

import logging
import os
import tempfile
import uuid

from flask import Flask, jsonify, request

from services.parser_service import ParserService
from services.pdf_service import PdfService
from utils import constants
from utils.exceptions import PdfParserException

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
)
logger = logging.getLogger("anits_pdf_parser")

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def create_app() -> Flask:
    """Application factory - keeps the app testable and import-friendly."""
    app = Flask(__name__)
    app.config["MAX_CONTENT_LENGTH"] = constants.MAX_FILE_SIZE_BYTES

    # -- routes -------------------------------------------------------------
    @app.route("/health", methods=["GET"])
    def health():
        """Simple liveness probe for orchestrators / n8n."""
        return jsonify({"status": "UP"}), 200

    @app.route("/extract-results", methods=["POST"])
    def extract_results():
        """Validate, persist temporarily, parse and return structured results."""
        file = request.files.get("file")
        PdfService.validate_upload(file)

        # Write to a unique temp path so concurrent requests never collide.
        safe_name = f"{uuid.uuid4().hex}.pdf"
        file_path = os.path.join(tempfile.gettempdir(), safe_name)
        file.save(file_path)

        try:
            PdfService.validate_pdf_file(file_path)
            response = ParserService.parse(file_path)
            return jsonify(response.to_dict()), 200
        finally:
            # Always clean up the temporary file (item 10: performance).
            try:
                os.remove(file_path)
                logger.debug("Removed temp file %s", file_path)
            except OSError:
                logger.warning("Could not delete temp file %s", file_path)

    # -- error handlers -----------------------------------------------------
    @app.errorhandler(PdfParserException)
    def handle_parser_exception(exc: PdfParserException):
        logger.warning("%s: %s", exc.__class__.__name__, exc.message)
        return jsonify(exc.to_dict()), exc.status_code

    @app.errorhandler(413)
    def handle_too_large(_exc):
        return (
            jsonify(
                {
                    "error": "InvalidPdfException",
                    "message": "File exceeds the maximum allowed size.",
                }
            ),
            413,
        )

    @app.errorhandler(404)
    def handle_not_found(_exc):
        return jsonify({"error": "NotFound", "message": "Resource not found."}), 404

    @app.errorhandler(405)
    def handle_method_not_allowed(_exc):
        return jsonify({"error": "MethodNotAllowed", "message": "Method not allowed."}), 405

    @app.errorhandler(Exception)
    def handle_unexpected(exc: Exception):
        logger.exception("Unexpected error: %s", exc)
        return (
            jsonify({"error": "InternalServerError", "message": "An unexpected error occurred."}),
            500,
        )

    return app


app = create_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)

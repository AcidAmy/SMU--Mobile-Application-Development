"""
Converter Service encapsulating MarkItDown conversion logic,
DL-based dynamic classifier routing (Section 5.1 & 5.3),
and strict Security Red Line compliance (Section 3 of agent.md).
"""

import io
import ipaddress
import logging
import os
from pathlib import Path
import re
import socket
import tempfile
import time
from typing import Optional, Tuple, Dict, Any
from urllib.parse import urlparse

from fastapi import HTTPException, status, UploadFile
import requests
from sqlalchemy.orm import Session

from markitdown import MarkItDown, StreamInfo
from markitdown._exceptions import FileConversionException, UnsupportedFormatException

try:
    from ..config import settings
    from ..models import User, ConversionRecord
    from ..schemas import ClassificationResult, ConversionResponse, ConversionRecordResponse
except ImportError:
    from config import settings
    from models import User, ConversionRecord
    from schemas import ClassificationResult, ConversionResponse, ConversionRecordResponse

logger = logging.getLogger("ConverterService")


class SSRFValidationError(HTTPException):
    def __init__(self, detail: str):
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


class ConverterService:
    """
    Core conversion service enforcing agent.md security guidelines and smart routing.
    """

    def __init__(self):
        self._classifier = None
        self._init_classifier()

    def _init_classifier(self) -> None:
        """
        Lazily initialize the PyTorch DocumentClassifier model.
        """
        try:
            from backend.classifier import DocumentClassifier
            weights = settings.CLASSIFIER_WEIGHTS_PATH if settings.CLASSIFIER_WEIGHTS_PATH.exists() else None
            self._classifier = DocumentClassifier(
                weights_path=weights,
                model_type=settings.CLASSIFIER_MODEL_TYPE,
            )
            logger.info("DocumentClassifier initialized successfully.")
        except Exception as e:
            logger.warning(f"Could not initialize PyTorch DocumentClassifier: {e}. Falling back to default routing.")
            self._classifier = None

    @property
    def classifier(self):
        if self._classifier is None:
            self._init_classifier()
        return self._classifier

    # ==========================================================
    # Section 3.2: Input Sanitization & Anti-SSRF Validation
    # ==========================================================

    @staticmethod
    def validate_file_extension(filename: str) -> str:
        """
        Validates file extension against strict agent.md whitelist.
        Returns the lowercased extension with leading dot.
        """
        if not filename or "." not in filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Filename is missing or has no extension.",
            )

        ext = Path(filename).suffix.lower()
        if ext not in settings.ALLOWED_EXTENSIONS:
            allowed = ", ".join(sorted(settings.ALLOWED_EXTENSIONS))
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File extension '{ext}' is not permitted. Allowed extensions: {allowed}",
            )
        return ext

    @staticmethod
    def validate_file_size(size: int) -> None:
        """
        Enforces maximum file size limit.
        """
        if size > settings.MAX_FILE_SIZE:
            max_mb = settings.MAX_FILE_SIZE / (1024 * 1024)
            actual_mb = size / (1024 * 1024)
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File size ({actual_mb:.1f}MB) exceeds configured maximum limit of {max_mb:.1f}MB.",
            )

    @staticmethod
    def validate_url_safety(url: str) -> None:
        """
        Section 3.2 Anti-SSRF Check:
        Filters and intercepts private IPs, loopback (127.0.0.1/localhost),
        link-local addresses (169.254.x.x), multicast, and reserved addresses.
        """
        parsed = urlparse(url)
        scheme = parsed.scheme.lower()
        if scheme not in ("http", "https"):
            raise SSRFValidationError(f"Invalid URL scheme '{scheme}'. Only http and https are allowed.")

        hostname = parsed.hostname
        if not hostname:
            raise SSRFValidationError("URL contains no valid hostname.")

        hostname_lower = hostname.lower()

        # Immediate name-level checks
        if hostname_lower in ("localhost", "localhost.localdomain") or hostname_lower.endswith(".localhost"):
            raise SSRFValidationError("Access to localhost is forbidden (SSRF protection).")

        # Resolve DNS to all corresponding IP addresses
        port = parsed.port or (443 if scheme == "https" else 80)
        try:
            addr_info = socket.getaddrinfo(hostname, port, socket.AF_UNSPEC, socket.SOCK_STREAM)
        except socket.gaierror as e:
            raise SSRFValidationError(f"Could not resolve host '{hostname}': {e}")

        for item in addr_info:
            ip_str = item[4][0]
            try:
                ip_obj = ipaddress.ip_address(ip_str)
            except ValueError:
                raise SSRFValidationError(f"Invalid IP address resolved: {ip_str}")

            if ip_obj.is_loopback:
                raise SSRFValidationError(f"SSRF blocked: Host '{hostname}' resolves to loopback IP {ip_str}.")
            if ip_obj.is_private:
                raise SSRFValidationError(f"SSRF blocked: Host '{hostname}' resolves to private network IP {ip_str}.")
            if ip_obj.is_link_local:
                raise SSRFValidationError(f"SSRF blocked: Host '{hostname}' resolves to link-local IP {ip_str}.")
            if ip_obj.is_multicast:
                raise SSRFValidationError(f"SSRF blocked: Host '{hostname}' resolves to multicast IP {ip_str}.")
            if ip_obj.is_reserved:
                raise SSRFValidationError(f"SSRF blocked: Host '{hostname}' resolves to reserved IP {ip_str}.")
            if ip_obj.is_unspecified:
                raise SSRFValidationError(f"SSRF blocked: Host '{hostname}' resolves to unspecified IP {ip_str}.")

            # Explicit cloud metadata check
            if str(ip_obj) == "169.254.169.254":
                raise SSRFValidationError("SSRF blocked: Cloud metadata service is forbidden.")

    def safe_fetch_url(self, url: str, max_redirects: int = 3) -> requests.Response:
        """
        Safely fetches remote content while validating each redirect hop against SSRF.
        """
        current_url = url
        for hop in range(max_redirects + 1):
            self.validate_url_safety(current_url)

            try:
                response = requests.get(
                    current_url,
                    stream=True,
                    timeout=15,
                    allow_redirects=False,
                    headers={
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) MarkItDown-SafeFetcher/1.0",
                        "Accept": "text/markdown, text/html;q=0.9, application/pdf, */*;q=0.8",
                    },
                )
            except requests.RequestException as e:
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=f"Failed to fetch remote URL '{current_url}': {str(e)}",
                )

            # Check for redirects
            if response.status_code in (301, 302, 303, 307, 308):
                location = response.headers.get("Location")
                if not location:
                    break
                # Handle relative redirects
                from urllib.parse import urljoin
                current_url = urljoin(current_url, location)
                continue

            # Successful response or terminal status
            if response.status_code >= 400:
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=f"Remote server returned error status {response.status_code}",
                )

            # Check Content-Length header if available
            cl = response.headers.get("Content-Length")
            if cl and cl.isdigit() and int(cl) > settings.MAX_FILE_SIZE:
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail=f"Remote file size ({int(cl)} bytes) exceeds limit of {settings.MAX_FILE_SIZE} bytes.",
                )

            return response

        raise SSRFValidationError("Too many redirects encountered while fetching URL.")

    # ==========================================================
    # Classifier Routing Logic (Section 5.1 & 5.3)
    # ==========================================================

    def classify_document(
        self,
        file_bytes: bytes,
        ext: str,
        filename: str = "document",
    ) -> Optional[ClassificationResult]:
        """
        Runs the PyTorch binary classifier on PDF or image bytes to determine
        whether standard conversion (0) or OCR / Vision LLM pipeline (1) is required.
        """
        if not self.classifier:
            return None

        # Only PDF and images are applicable for visual layout classification
        if ext not in [".pdf", ".jpg", ".jpeg", ".png", ".bmp", ".webp"]:
            return ClassificationResult(
                file_name=filename,
                label=0,
                class_name="standard",
                confidence=0.99,
                probabilities={"standard": 0.99, "scanned_or_complex": 0.01},
                requires_ocr=False,
                pages_analyzed=0,
                model_type=settings.CLASSIFIER_MODEL_TYPE,
                note="Office or text document natively parsed via structured parser",
            )

        try:
            with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
                tmp.write(file_bytes)
                tmp_path = Path(tmp.name)

            try:
                res = self.classifier.predict(tmp_path)
                return ClassificationResult(
                    file_name=filename,
                    label=res.get("label", 0),
                    class_name=res.get("class_name", "standard"),
                    confidence=res.get("confidence", 0.5),
                    probabilities=res.get("probabilities", {}),
                    requires_ocr=res.get("requires_ocr", False),
                    pages_analyzed=res.get("pages_analyzed", 1),
                    model_type=res.get("model_type", settings.CLASSIFIER_MODEL_TYPE),
                    note=res.get("note"),
                )
            finally:
                if tmp_path.exists():
                    tmp_path.unlink()
        except Exception as e:
            logger.error(f"Error during document classification: {e}")
            return None

    def _build_markitdown_engine(
        self,
        use_ocr: bool,
        custom_prompt: Optional[str] = None,
    ) -> Tuple[MarkItDown, bool]:
        """
        Instantiates MarkItDown with or without OCR plugins based on routing decision.
        Returns (md_instance, converted_with_ocr).
        """
        if use_ocr and settings.OPENAI_API_KEY:
            try:
                from openai import OpenAI
                client_kwargs = {"api_key": settings.OPENAI_API_KEY}
                if settings.OPENAI_BASE_URL:
                    client_kwargs["base_url"] = settings.OPENAI_BASE_URL

                llm_client = OpenAI(**client_kwargs)
                md = MarkItDown(
                    enable_plugins=True,
                    llm_client=llm_client,
                    llm_model=settings.OPENAI_MODEL,
                    llm_prompt=custom_prompt,
                )
                return md, True
            except Exception as e:
                logger.warning(f"Failed to configure MarkItDown with OCR/OpenAI: {e}. Falling back to built-ins.")

        # Default fast path without OCR plugin
        return MarkItDown(enable_plugins=False), False

    # ==========================================================
    # Section 3.1 & 5.3: Core Conversion Execution
    # ==========================================================

    async def convert_uploaded_file(
        self,
        file: UploadFile,
        db: Session,
        current_user: Optional[User] = None,
        auto_classify: bool = True,
        force_ocr: bool = False,
        custom_prompt: Optional[str] = None,
    ) -> ConversionResponse:
        """
        Handles UploadFile conversion adhering to agent.md Section 3.1:
        MUST use byte stream specific interface `convert_stream()`.
        """
        start_time = time.perf_counter()
        filename = file.filename or "uploaded_file"
        ext = self.validate_file_extension(filename)

        # Read file into memory and validate size
        file_bytes = await file.read()
        self.validate_file_size(len(file_bytes))

        # Dynamic Routing via PyTorch Document Classifier
        classification = None
        should_use_ocr = force_ocr

        if auto_classify and not force_ocr:
            classification = self.classify_document(file_bytes, ext, filename=filename)
            if classification and classification.requires_ocr:
                should_use_ocr = True

        # Initialize MarkItDown engine
        md, converted_with_ocr = self._build_markitdown_engine(
            use_ocr=should_use_ocr,
            custom_prompt=custom_prompt,
        )

        # MANDATORY Rule 3.1: Use convert_stream for uploaded binary stream
        stream = io.BytesIO(file_bytes)
        stream_info = StreamInfo(filename=filename, extension=ext)

        try:
            result = md.convert_stream(stream, stream_info=stream_info)
            markdown_content = result.markdown
            title = result.title or Path(filename).stem
            status_str = "success"
            error_msg = None
        except (FileConversionException, UnsupportedFormatException) as e:
            logger.error(f"MarkItDown conversion error on '{filename}': {e}")
            markdown_content = None
            title = None
            status_str = "failed"
            error_msg = str(e)
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"Conversion error: {e}")
        except Exception as e:
            logger.exception(f"Unexpected conversion failure on '{filename}': {e}")
            markdown_content = None
            title = None
            status_str = "failed"
            error_msg = str(e)
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Internal conversion failed: {e}")
        finally:
            elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)

            # Persist conversion record in SQLite database (Section 5.2)
            record = ConversionRecord(
                user_id=current_user.id if current_user else None,
                filename=filename,
                file_type=ext,
                file_size=len(file_bytes),
                source_type="upload",
                source_url=None,
                classifier_label=classification.label if classification else None,
                classifier_class=classification.class_name if classification else None,
                classifier_confidence=classification.confidence if classification else None,
                requires_ocr=classification.requires_ocr if classification else should_use_ocr,
                converted_with_ocr=converted_with_ocr,
                converted_with_llm=bool(converted_with_ocr and settings.OPENAI_API_KEY),
                status=status_str,
                error_message=error_msg,
                title=title,
                markdown_content=markdown_content,
                duration_ms=elapsed_ms,
            )
            db.add(record)
            db.commit()
            db.refresh(record)

        return ConversionResponse(
            record=ConversionRecordResponse.model_validate(record),
            markdown=markdown_content or "",
            title=title,
            classification=classification,
        )

    def convert_url(
        self,
        url: str,
        db: Session,
        current_user: Optional[User] = None,
        auto_classify: bool = True,
        force_ocr: bool = False,
        custom_prompt: Optional[str] = None,
    ) -> ConversionResponse:
        """
        Handles URL conversion adhering to agent.md Section 3.2:
        MUST sanitize & validate URL to prevent SSRF, fetch via requests.get(),
        and call `convert_response()`.
        """
        start_time = time.perf_counter()

        # Step 1: Validate anti-SSRF and fetch response safely
        response = self.safe_fetch_url(url)

        # Infer filename and extension from URL or Content-Disposition
        parsed = urlparse(url)
        raw_filename = os.path.basename(parsed.path) or "remote_document.html"
        ext = Path(raw_filename).suffix.lower()
        if not ext:
            # Fallback according to content-type header
            ct = response.headers.get("Content-Type", "").lower()
            if "pdf" in ct:
                ext = ".pdf"
            elif "html" in ct:
                ext = ".html"
            else:
                ext = ".html"
            raw_filename += ext

        ext = self.validate_file_extension(raw_filename)

        # Dynamic routing
        should_use_ocr = force_ocr
        classification = None

        # Build engine
        md, converted_with_ocr = self._build_markitdown_engine(
            use_ocr=should_use_ocr,
            custom_prompt=custom_prompt,
        )

        stream_info = StreamInfo(url=url, filename=raw_filename, extension=ext)

        try:
            # MANDATORY Rule 3.2: Use convert_response with fetched response
            result = md.convert_response(response, stream_info=stream_info)
            markdown_content = result.markdown
            title = result.title or Path(raw_filename).stem
            status_str = "success"
            error_msg = None
        except Exception as e:
            logger.error(f"Error converting URL '{url}': {e}")
            markdown_content = None
            title = None
            status_str = "failed"
            error_msg = str(e)
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"Conversion error: {e}")
        finally:
            elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
            content_len = len(response.content) if hasattr(response, "content") else 0

            record = ConversionRecord(
                user_id=current_user.id if current_user else None,
                filename=raw_filename,
                file_type=ext,
                file_size=content_len,
                source_type="url",
                source_url=url,
                classifier_label=classification.label if classification else None,
                classifier_class=classification.class_name if classification else None,
                classifier_confidence=classification.confidence if classification else None,
                requires_ocr=should_use_ocr,
                converted_with_ocr=converted_with_ocr,
                converted_with_llm=bool(converted_with_ocr and settings.OPENAI_API_KEY),
                status=status_str,
                error_message=error_msg,
                title=title,
                markdown_content=markdown_content,
                duration_ms=elapsed_ms,
            )
            db.add(record)
            db.commit()
            db.refresh(record)

        return ConversionResponse(
            record=ConversionRecordResponse.model_validate(record),
            markdown=markdown_content or "",
            title=title,
            classification=classification,
        )

    def convert_local_file(
        self,
        file_path: Path,
        db: Session,
        current_user: Optional[User] = None,
        use_ocr: bool = False,
    ) -> ConversionResponse:
        """
        Handles conversion of verified local files adhering to Section 3.1:
        MUST use `convert_local(file_path)`.
        """
        start_time = time.perf_counter()
        if not file_path.exists():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Local file not found.")

        ext = self.validate_file_extension(file_path.name)
        size = file_path.stat().st_size
        self.validate_file_size(size)

        md, converted_with_ocr = self._build_markitdown_engine(use_ocr=use_ocr)

        try:
            # MANDATORY Rule 3.1: Use convert_local for verified local file
            result = md.convert_local(file_path)
            markdown_content = result.markdown
            title = result.title or file_path.stem
            status_str = "success"
            error_msg = None
        except Exception as e:
            logger.error(f"Error in convert_local for '{file_path}': {e}")
            markdown_content = None
            title = None
            status_str = "failed"
            error_msg = str(e)
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"Local conversion error: {e}")
        finally:
            elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
            record = ConversionRecord(
                user_id=current_user.id if current_user else None,
                filename=file_path.name,
                file_type=ext,
                file_size=size,
                source_type="local",
                source_url=None,
                classifier_label=None,
                classifier_class=None,
                classifier_confidence=None,
                requires_ocr=use_ocr,
                converted_with_ocr=converted_with_ocr,
                converted_with_llm=bool(converted_with_ocr and settings.OPENAI_API_KEY),
                status=status_str,
                error_message=error_msg,
                title=title,
                markdown_content=markdown_content,
                duration_ms=elapsed_ms,
            )
            db.add(record)
            db.commit()
            db.refresh(record)

        return ConversionResponse(
            record=ConversionRecordResponse.model_validate(record),
            markdown=markdown_content or "",
            title=title,
            classification=None,
        )


# Global service instance
converter_service = ConverterService()

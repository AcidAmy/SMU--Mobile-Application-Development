"""
Pydantic validation schemas for API requests, responses, and data transfer.
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, ConfigDict


# ==========================================
# User & Authentication Schemas
# ==========================================

class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, description="Username for login")
    password: str = Field(..., min_length=6, max_length=128, description="Plain text password")
    email: Optional[str] = Field(None, max_length=128, description="Optional email address")


class UserLogin(BaseModel):
    username: str = Field(..., description="Username")
    password: str = Field(..., description="Password")


class UserResponse(BaseModel):
    id: int
    username: str
    email: Optional[str] = None
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: Optional[UserResponse] = None


class TokenData(BaseModel):
    username: Optional[str] = None


# ==========================================
# Document Classification Schemas (Section 5.1)
# ==========================================

class ClassificationResult(BaseModel):
    file_name: Optional[str] = None
    label: int = Field(..., description="0: standard, 1: scanned_or_complex")
    class_name: str = Field(..., description="'standard' or 'scanned_or_complex'")
    confidence: float = Field(..., description="Model prediction confidence (0.0 - 1.0)")
    probabilities: Dict[str, float] = Field(default_factory=dict)
    requires_ocr: bool = Field(..., description="Whether OCR plugin routing is advised")
    pages_analyzed: Optional[int] = None
    model_type: Optional[str] = None
    note: Optional[str] = None


# ==========================================
# Conversion Request & Response Schemas (Section 5.2 & 5.3)
# ==========================================

class ConvertUrlRequest(BaseModel):
    url: str = Field(..., description="Remote document or web page URL to convert")
    auto_classify: bool = Field(True, description="Enable DL classifier-based routing for PDF/images")
    force_ocr: bool = Field(False, description="Force LLM Vision OCR processing regardless of classifier")
    custom_prompt: Optional[str] = Field(None, description="Custom prompt for vision extraction if OCR activated")


class ConversionRecordResponse(BaseModel):
    id: int
    user_id: Optional[int] = None
    filename: str
    file_type: str
    file_size: int
    source_type: str
    source_url: Optional[str] = None
    classifier_label: Optional[int] = None
    classifier_class: Optional[str] = None
    classifier_confidence: Optional[float] = None
    requires_ocr: bool
    converted_with_ocr: bool
    converted_with_llm: bool
    status: str
    error_message: Optional[str] = None
    title: Optional[str] = None
    duration_ms: float
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ConversionDetailResponse(ConversionRecordResponse):
    markdown_content: Optional[str] = None


class ConversionResponse(BaseModel):
    record: ConversionRecordResponse
    markdown: str
    title: Optional[str] = None
    classification: Optional[ClassificationResult] = None


class RecordListResponse(BaseModel):
    total: int
    items: List[ConversionRecordResponse]


# ==========================================
# System Health & Info Schemas
# ==========================================

class HealthResponse(BaseModel):
    status: str = "ok"
    version: str
    classifier_loaded: bool
    ocr_plugin_available: bool
    openai_configured: bool
    allowed_extensions: List[str]
    max_file_size_mb: float

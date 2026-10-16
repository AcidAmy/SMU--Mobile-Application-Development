"""
SQLAlchemy ORM models for User and ConversionRecord.
Supports user management, conversion history persistence, and audit tracking.
"""

from datetime import datetime
from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    Float,
    DateTime,
    Text,
    ForeignKey,
)
from sqlalchemy.orm import relationship

try:
    from .database import Base
except ImportError:
    from database import Base


class User(Base):
    """
    User entity representing registered system users.
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    username = Column(String(64), unique=True, index=True, nullable=False)
    email = Column(String(128), unique=True, index=True, nullable=True)
    hashed_password = Column(String(256), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    conversions = relationship(
        "ConversionRecord",
        back_populates="user",
        cascade="all, delete-orphan",
        order_by="desc(ConversionRecord.created_at)",
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} username='{self.username}'>"


class ConversionRecord(Base):
    """
    ConversionRecord entity tracking all document conversion tasks,
    their routing decisions, classification confidence, timing, and generated markdown.
    """
    __tablename__ = "conversion_records"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)

    # Input file/source metadata
    filename = Column(String(255), nullable=False)
    file_type = Column(String(32), nullable=False)  # Extension like .pdf, .docx
    file_size = Column(Integer, default=0, nullable=False)  # File size in bytes
    source_type = Column(String(32), default="upload", nullable=False)  # "upload", "url", "stream"
    source_url = Column(String(1024), nullable=True)  # Populated if converted from URL

    # PyTorch Classifier Routing Results (Section 5.1)
    classifier_label = Column(Integer, nullable=True)  # 0: standard, 1: scanned_or_complex
    classifier_class = Column(String(64), nullable=True)  # "standard", "scanned_or_complex"
    classifier_confidence = Column(Float, nullable=True)  # Confidence score (0.0 - 1.0)
    requires_ocr = Column(Boolean, default=False, nullable=False)

    # Conversion Execution Flags
    converted_with_ocr = Column(Boolean, default=False, nullable=False)
    converted_with_llm = Column(Boolean, default=False, nullable=False)
    status = Column(String(32), default="success", nullable=False)  # "success", "failed"
    error_message = Column(Text, nullable=True)

    # Result payload
    title = Column(String(255), nullable=True)
    markdown_content = Column(Text, nullable=True)
    duration_ms = Column(Float, default=0.0, nullable=False)  # Execution time in ms

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Relationships
    user = relationship("User", back_populates="conversions")

    def __repr__(self) -> str:
        return f"<ConversionRecord id={self.id} filename='{self.filename}' status='{self.status}'>"

"""
Main FastAPI application entrypoint for MarkItDown.
Provides RESTful APIs for authentication, document classification,
safe format conversion (Section 3), and conversion history management.
"""

from contextlib import asynccontextmanager
import logging
from pathlib import Path
from typing import Optional, List

from fastapi import (
    FastAPI,
    Depends,
    HTTPException,
    status,
    UploadFile,
    File,
    Query,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

try:
    from .config import settings
    from .database import init_db, get_db
    from .models import User, ConversionRecord
    from .schemas import (
        UserCreate,
        UserLogin,
        UserResponse,
        Token,
        ConvertUrlRequest,
        ConversionResponse,
        ConversionRecordResponse,
        ConversionDetailResponse,
        RecordListResponse,
        ClassificationResult,
        HealthResponse,
    )
    from .auth import (
        hash_password,
        verify_password,
        create_access_token,
        get_current_user,
        get_current_user_optional,
    )
    from .services.converter_service import converter_service
except ImportError:
    from config import settings
    from database import init_db, get_db
    from models import User, ConversionRecord
    from schemas import (
        UserCreate,
        UserLogin,
        UserResponse,
        Token,
        ConvertUrlRequest,
        ConversionResponse,
        ConversionRecordResponse,
        ConversionDetailResponse,
        RecordListResponse,
        ClassificationResult,
        HealthResponse,
    )
    from auth import (
        hash_password,
        verify_password,
        create_access_token,
        get_current_user,
        get_current_user_optional,
    )
    from services.converter_service import converter_service

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s",
)
logger = logging.getLogger("MarkItDownAPI")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifecycle management:
    Initializes SQLite tables and pre-warms the PyTorch DocumentClassifier model.
    """
    logger.info("Initializing SQLite database tables...")
    init_db()

    logger.info("Pre-warming PyTorch DocumentClassifier...")
    _ = converter_service.classifier

    logger.info(f"MarkItDown Backend v{settings.VERSION} ready.")
    yield
    logger.info("MarkItDown Backend shutting down.")


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Full-stack Document to Markdown Conversion Platform with PyTorch DL Classifier, OCR Plugin & Anti-SSRF Protection.",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)

# CORS middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==========================================================
# Authentication Endpoints (Section 5.2)
# ==========================================================

@app.post(
    f"{settings.API_PREFIX}/auth/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Authentication"],
    summary="Register a new user",
)
def register(user_in: UserCreate, db: Session = Depends(get_db)):
    # Check if username exists
    existing_user = db.query(User).filter(User.username == user_in.username).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered.",
        )

    # Check if email exists if provided
    if user_in.email:
        existing_email = db.query(User).filter(User.email == user_in.email).first()
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered.",
            )

    new_user = User(
        username=user_in.username,
        email=user_in.email,
        hashed_password=hash_password(user_in.password),
        is_active=True,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


@app.post(
    f"{settings.API_PREFIX}/auth/login",
    response_model=Token,
    tags=["Authentication"],
    summary="Authenticate and receive JWT token (OAuth2 Form / Swagger UI Authorize)",
)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    """
    Standard OAuth2 password flow endpoint.
    Used by Swagger UI's 'Authorize' button and form submissions.
    """
    user = db.query(User).filter(User.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user account.",
        )

    token = create_access_token(data={"sub": user.username, "user_id": user.id})
    return Token(
        access_token=token,
        token_type="bearer",
        user=UserResponse.model_validate(user),
    )


@app.post(
    f"{settings.API_PREFIX}/auth/login-json",
    response_model=Token,
    tags=["Authentication"],
    summary="Authenticate with JSON body (Frontend / Axios)",
)
def login_json(
    user_in: UserLogin,
    db: Session = Depends(get_db),
):
    """
    JSON-based login endpoint convenient for Vue3/Axios and programmatic REST clients.
    """
    user = db.query(User).filter(User.username == user_in.username).first()
    if not user or not verify_password(user_in.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user account.",
        )

    token = create_access_token(data={"sub": user.username, "user_id": user.id})
    return Token(
        access_token=token,
        token_type="bearer",
        user=UserResponse.model_validate(user),
    )


@app.get(
    f"{settings.API_PREFIX}/auth/me",
    response_model=UserResponse,
    tags=["Authentication"],
    summary="Get current user profile",
)
def get_current_user_profile(current_user: User = Depends(get_current_user)):
    return current_user


# ==========================================================
# Deep Learning Classifier Endpoint (Section 5.1)
# ==========================================================

@app.post(
    f"{settings.API_PREFIX}/classify",
    response_model=ClassificationResult,
    tags=["Classifier"],
    summary="Pre-classify document to determine if OCR is required",
)
async def classify_file(file: UploadFile = File(...)):
    filename = file.filename or "uploaded_file"
    ext = converter_service.validate_file_extension(filename)
    file_bytes = await file.read()
    converter_service.validate_file_size(len(file_bytes))

    res = converter_service.classify_document(file_bytes, ext, filename=filename)
    if res is None:
        return ClassificationResult(
            file_name=filename,
            label=0,
            class_name="standard",
            confidence=0.5,
            probabilities={"standard": 0.5, "scanned_or_complex": 0.5},
            requires_ocr=False,
            note="Classifier unavailable; fallback to standard.",
        )
    return res


# ==========================================================
# Conversion Endpoints (Section 3 & 5.3)
# ==========================================================

@app.post(
    f"{settings.API_PREFIX}/convert/upload",
    response_model=ConversionResponse,
    tags=["Conversion"],
    summary="Upload and convert document using convert_stream() with DL routing",
)
async def convert_upload(
    file: UploadFile = File(...),
    auto_classify: bool = Query(True, description="Enable automatic DL-based OCR routing"),
    force_ocr: bool = Query(False, description="Force LLM Vision OCR regardless of prediction"),
    custom_prompt: Optional[str] = Query(None, description="Optional custom prompt for OCR extraction"),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """
    Enforces Security Red Line 1:
    Uses `md.convert_stream(stream, stream_info=...)` for uploaded binary streams.
    """
    return await converter_service.convert_uploaded_file(
        file=file,
        db=db,
        current_user=current_user,
        auto_classify=auto_classify,
        force_ocr=force_ocr,
        custom_prompt=custom_prompt,
    )


@app.post(
    f"{settings.API_PREFIX}/convert/url",
    response_model=ConversionResponse,
    tags=["Conversion"],
    summary="Convert remote URL with strict Anti-SSRF filtering and convert_response()",
)
def convert_remote_url(
    req: ConvertUrlRequest,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """
    Enforces Security Red Line 2:
    Validates against private/loopback/link-local IP addresses, fetches via requests.get(),
    and converts using `md.convert_response()`.
    """
    return converter_service.convert_url(
        url=req.url,
        db=db,
        current_user=current_user,
        auto_classify=req.auto_classify,
        force_ocr=req.force_ocr,
        custom_prompt=req.custom_prompt,
    )


# ==========================================================
# Conversion History & Records (Section 5.2)
# ==========================================================

@app.get(
    f"{settings.API_PREFIX}/records",
    response_model=RecordListResponse,
    tags=["Records"],
    summary="List conversion history records",
)
def list_records(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    query = db.query(ConversionRecord)
    if current_user:
        query = query.filter(ConversionRecord.user_id == current_user.id)

    total = query.count()
    records = query.order_by(ConversionRecord.created_at.desc()).offset(skip).limit(limit).all()

    return RecordListResponse(
        total=total,
        items=[ConversionRecordResponse.model_validate(r) for r in records],
    )


@app.get(
    f"{settings.API_PREFIX}/records/{{record_id}}",
    response_model=ConversionDetailResponse,
    tags=["Records"],
    summary="Get single conversion record with generated markdown",
)
def get_record(
    record_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    query = db.query(ConversionRecord).filter(ConversionRecord.id == record_id)
    if current_user:
        query = query.filter(
            (ConversionRecord.user_id == current_user.id) | (ConversionRecord.user_id.is_(None))
        )

    record = query.first()
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversion record not found.")

    return ConversionDetailResponse.model_validate(record)


@app.delete(
    f"{settings.API_PREFIX}/records/{{record_id}}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Records"],
    summary="Delete a conversion record",
)
def delete_record(
    record_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    record = db.query(ConversionRecord).filter(ConversionRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversion record not found.")

    if record.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied.")

    db.delete(record)
    db.commit()
    return None


# ==========================================================
# Health & System Status Endpoints
# ==========================================================

@app.get(
    f"{settings.API_PREFIX}/health",
    response_model=HealthResponse,
    tags=["System"],
    summary="Check API health, classifier status and plugin availability",
)
def health_check():
    import markitdown
    try:
        import markitdown_ocr  # noqa: F401
        ocr_available = True
    except ImportError:
        ocr_available = False

    return HealthResponse(
        status="ok",
        version=settings.VERSION,
        classifier_loaded=bool(converter_service.classifier is not None),
        ocr_plugin_available=ocr_available,
        openai_configured=bool(settings.OPENAI_API_KEY),
        allowed_extensions=sorted(list(settings.ALLOWED_EXTENSIONS)),
        max_file_size_mb=round(settings.MAX_FILE_SIZE / (1024 * 1024), 2),
    )


# Mount Frontend Static Web Application (Section 5.4)
frontend_dir = Path(__file__).resolve().parent.parent / "frontend"
if not frontend_dir.exists():
    frontend_dir = Path(__file__).resolve().parent / "frontend"

if frontend_dir.exists() and (frontend_dir / "index.html").exists():
    from fastapi.staticfiles import StaticFiles
    app.mount("/app", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")
    logger.info(f"Frontend SPA mounted successfully at /app from {frontend_dir}")


@app.get("/", tags=["System"], summary="Root service banner")
def root():
    has_frontend = frontend_dir.exists() and (frontend_dir / "index.html").exists()
    return {
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "docs_url": "/api/docs",
        "health_url": f"{settings.API_PREFIX}/health",
        "frontend_url": "/app/" if has_frontend else None,
        "description": "MarkItDown Full-Stack Backend Service with PyTorch DL Classifier & Anti-SSRF Protection.",
    }


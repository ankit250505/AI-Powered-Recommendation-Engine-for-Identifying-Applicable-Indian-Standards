from __future__ import annotations

import csv
import json
import logging
import time
import uuid
from datetime import date
from io import StringIO
from functools import lru_cache
from pathlib import Path

from fastapi import Depends, FastAPI, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.responses import FileResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from starlette.middleware.trustedhost import TrustedHostMiddleware

from src.auth import authenticate_user, create_user_session, end_user_session, user_for_session
from src.config import settings
from src.document_analysis import aggregate_clause_results, split_document_clauses
from src.document_processing import DocumentProcessingError, extract_text_from_upload
from src.embedding_search import EmbeddingSearchEngine
from src.hybrid_search import HybridSearchEngine
from src.logging_config import configure_logging
from src.monitoring import metrics
from src.report_generation import build_search_report_pdf
from src.security import LoginRateLimiter
from src.standards_search import SearchResult, load_standards, search_standards
from src.storage import (
    UserRecord,
    count_searches,
    database_health,
    feedback_by_standard,
    feedback_summary,
    get_search,
    get_standard_overrides,
    list_verification_history,
    list_reviews,
    list_searches,
    review_summary,
    save_feedback,
    save_review,
    save_search,
    save_standard_override,
)


ROOT_DIR = Path(__file__).resolve().parents[1]
FRONTEND_DIR = ROOT_DIR / "frontend"
DEMO_DOCUMENT_PATH = ROOT_DIR / "output" / "pdf" / "demo_procurement_specification.pdf"
QUALITY_METRICS_PATH = ROOT_DIR / "data" / "retrieval_quality.json"
SESSION_COOKIE = "standards_session"

configure_logging(settings.log_level)
logger = logging.getLogger("standards_api")
login_limiter = LoginRateLimiter(
    attempt_limit=settings.login_attempt_limit,
    window_seconds=settings.login_window_seconds,
)

app = FastAPI(
    title="Indian Standards Recommendation API",
    description="Recommendation and review API for applicable Indian Standards in procurement specifications.",
    version="1.0.0",
)

if settings.trusted_hosts:
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=list(settings.trusted_hosts))

if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")


@app.middleware("http")
async def request_logging(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    started = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        logger.exception(
            "request_failed",
            extra={
                "event_data": {
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                }
            },
        )
        raise

    duration_ms = round((time.perf_counter() - started) * 1000, 2)
    metrics.observe(response.status_code, duration_ms)
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; object-src 'none'; frame-ancestors 'none'; "
        "base-uri 'self'; form-action 'self'"
    )
    logger.info(
        "request_complete",
        extra={
            "event_data": {
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": duration_ms,
                "environment": settings.environment,
            }
        },
    )
    return response


class RecommendRequest(BaseModel):
    query: str = Field(..., min_length=2, description="Procurement specification or product description")
    limit: int = Field(10, ge=1, le=50, description="Maximum number of recommendations to return")
    min_score: float = Field(1.0, ge=0, description="Minimum score to include")
    mode: str = Field("hybrid", pattern="^(embedding|hybrid|keyword)$", description="Search mode")


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=100)
    password: str = Field(..., min_length=1, max_length=500)


class UserResponse(BaseModel):
    id: int
    username: str
    role: str


class StandardSummary(BaseModel):
    id: str
    standard_code: str
    title: str
    category: str
    subcategory: str
    keywords: list[str]
    scope_summary: str
    mandatory_hint: str
    source_url: str
    verify_status: str
    last_reviewed: str
    verification_note: str = ""


class VerificationUpdateRequest(BaseModel):
    title: str = Field(..., min_length=3, max_length=500)
    source_url: str = Field(..., pattern=r"^https?://", max_length=1000)
    verify_status: str = Field(
        ...,
        pattern="^(needs_official_verification|partially_verified|verified_from_search|officially_verified|superseded|withdrawn)$",
    )
    note: str = Field(..., min_length=3, max_length=2000)


class VerificationHistoryItem(BaseModel):
    id: int
    standard_id: str
    previous_data: dict[str, str]
    new_data: dict[str, str]
    note: str
    changed_by: str
    created_at: str


class Recommendation(BaseModel):
    id: str
    standard_code: str
    title: str
    score: float
    category: str
    subcategory: str
    matched_terms: list[str]
    matched_fields: list[str]
    reason: str
    procurement_examples: str
    mandatory_hint: str
    verify_status: str
    source_url: str
    confidence_score: float
    confidence_label: str
    evidence_clauses: list[str] = Field(default_factory=list)


class RecommendResponse(BaseModel):
    query: str
    count: int
    search_id: int | None = None
    results: list[Recommendation]


class ExtractDocumentResponse(BaseModel):
    filename: str
    extension: str
    char_count: int
    preview: str
    text: str


class RecommendDocumentResponse(BaseModel):
    filename: str
    extension: str
    char_count: int
    preview: str
    clauses_analyzed: int
    count: int
    search_id: int | None = None
    results: list[Recommendation]


class FeedbackRequest(BaseModel):
    standard_id: str
    standard_code: str
    rating: str = Field(..., pattern="^(useful|not_useful)$")
    search_id: int | None = None
    note: str | None = None


class FeedbackResponse(BaseModel):
    feedback_id: int
    status: str


class ReviewRequest(BaseModel):
    search_id: int = Field(..., ge=1)
    standard_id: str = Field(..., min_length=1)
    standard_code: str = Field(..., min_length=1)
    decision: str = Field(..., pattern="^(accepted|rejected)$")
    note: str | None = Field(None, max_length=1000)


class ReviewResponse(BaseModel):
    review_id: int
    status: str
    decision: str


class ReviewItem(BaseModel):
    id: int
    search_id: int
    query: str
    mode: str
    source_type: str
    source_name: str | None
    standard_id: str
    standard_code: str
    decision: str
    note: str | None
    reviewer_username: str | None
    created_at: str
    updated_at: str


class ReviewSummaryResponse(BaseModel):
    accepted: int
    rejected: int
    reviewed: int
    pending: int


class SearchHistoryItem(BaseModel):
    id: int
    query: str
    mode: str
    source_type: str
    result_count: int
    created_at: str


class SavedSearchDetailResponse(BaseModel):
    id: int
    query: str
    mode: str
    source_type: str
    source_name: str | None
    result_count: int
    results: list[Recommendation]
    created_at: str


class RetrievalQualityResponse(BaseModel):
    evaluated_on: str
    query_count: int
    mode: str
    top_1_accuracy: float
    top_5_accuracy: float
    mean_reciprocal_rank: float


class AnalyticsResponse(BaseModel):
    searches_count: int
    feedback: dict[str, int]
    top_feedback_standards: list[dict[str, int | str]]


class DatasetQualityResponse(BaseModel):
    standards_count: int
    categories: dict[str, int]
    verification_status: dict[str, int]
    missing_source_url_count: int
    generic_source_url_count: int
    needs_verification_count: int
    top_categories: list[dict[str, int | str]]


def split_keywords(value: str) -> list[str]:
    return [item.strip() for item in value.split(";") if item.strip()]


def current_user(request: Request) -> UserRecord:
    token = request.cookies.get(SESSION_COOKIE)
    user = user_for_session(token) if token else None
    if user is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    return user


def require_roles(*allowed_roles: str):
    def role_dependency(user: UserRecord = Depends(current_user)) -> UserRecord:
        if user.role not in allowed_roles:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return user

    return role_dependency


@lru_cache(maxsize=1)
def get_standards() -> tuple[dict[str, str], ...]:
    standards = load_standards()
    overrides = get_standard_overrides()
    for standard in standards:
        override = overrides.get(standard["id"])
        standard["verification_note"] = ""
        if override:
            standard.update(override)
    return tuple(standards)


@lru_cache(maxsize=1)
def get_hybrid_engine() -> HybridSearchEngine:
    return HybridSearchEngine(get_standards())


@lru_cache(maxsize=1)
def get_embedding_engine() -> EmbeddingSearchEngine:
    return EmbeddingSearchEngine(get_standards())


def confidence_for_result(
    result: SearchResult,
    rank: int,
    top_score: float,
    evidence_count: int,
) -> tuple[float, str]:
    relative_score = result.score / top_score if top_score > 0 else 0.0
    term_strength = min(len(result.matched_terms) / 5, 1.0)
    evidence_strength = min(max(evidence_count, 1) / 3, 1.0)
    rank_strength = 1 / (1 + (rank * 0.25))
    confidence = round(
        min(
            1.0,
            (0.45 * relative_score)
            + (0.2 * term_strength)
            + (0.2 * evidence_strength)
            + (0.15 * rank_strength),
        ),
        2,
    )
    if confidence >= 0.75:
        label = "high"
    elif confidence >= 0.5:
        label = "moderate"
    else:
        label = "low"
    return confidence, label


def to_recommendation(
    result: SearchResult,
    rank: int,
    top_score: float,
    evidence_clauses: list[str] | None = None,
) -> Recommendation:
    standard = result.standard
    evidence = evidence_clauses or []
    confidence_score, confidence_label = confidence_for_result(
        result=result,
        rank=rank,
        top_score=top_score,
        evidence_count=len(evidence),
    )
    return Recommendation(
        id=standard["id"],
        standard_code=standard["standard_code"],
        title=standard["title"],
        score=result.score,
        category=standard["category"],
        subcategory=standard["subcategory"],
        matched_terms=result.matched_terms,
        matched_fields=result.matched_fields,
        reason=standard["scope_summary"],
        procurement_examples=standard["procurement_examples"],
        mandatory_hint=standard["mandatory_hint"],
        verify_status=standard["verify_status"],
        source_url=standard["source_url"],
        confidence_score=confidence_score,
        confidence_label=confidence_label,
        evidence_clauses=evidence,
    )


def to_standard_summary(standard: dict[str, str]) -> StandardSummary:
    return StandardSummary(
        id=standard["id"],
        standard_code=standard["standard_code"],
        title=standard["title"],
        category=standard["category"],
        subcategory=standard["subcategory"],
        keywords=split_keywords(standard["keywords"]),
        scope_summary=standard["scope_summary"],
        mandatory_hint=standard["mandatory_hint"],
        source_url=standard["source_url"],
        verify_status=standard["verify_status"],
        last_reviewed=standard["last_reviewed"],
        verification_note=standard.get("verification_note", ""),
    )


def clear_search_caches() -> None:
    get_standards.cache_clear()
    get_hybrid_engine.cache_clear()
    get_embedding_engine.cache_clear()


def search_results(query: str, limit: int, min_score: float, mode: str) -> list[SearchResult]:
    if mode == "keyword":
        results = search_standards(
            query,
            standards=get_standards(),
            limit=limit,
            min_score=min_score,
        )
    elif mode == "hybrid":
        results = get_hybrid_engine().search(
            query,
            limit=limit,
            min_score=min_score,
        )
    else:
        try:
            results = get_embedding_engine().search(
                query,
                limit=limit,
                min_score=min_score,
            )
        except (RuntimeError, OSError) as error:
            raise HTTPException(status_code=503, detail=f"Embedding search unavailable: {error}") from error
    return results


def run_recommendation(query: str, limit: int, min_score: float, mode: str) -> list[Recommendation]:
    results = search_results(query=query, limit=limit, min_score=min_score, mode=mode)
    top_score = results[0].score if results else 0.0
    return [
        to_recommendation(result, rank=rank, top_score=top_score)
        for rank, result in enumerate(results)
    ]


def run_document_recommendation(
    text: str,
    limit: int,
    min_score: float,
    mode: str,
) -> tuple[list[Recommendation], int]:
    clauses = split_document_clauses(text)
    per_clause_limit = min(max(limit, 3), 10)
    clause_results = [
        (
            clause,
            search_results(
                query=clause,
                limit=per_clause_limit,
                min_score=min_score,
                mode=mode,
            ),
        )
        for clause in clauses
    ]
    matches = aggregate_clause_results(clause_results, limit=limit)
    top_score = matches[0].result.score if matches else 0.0
    recommendations = [
        to_recommendation(
            match.result,
            rank=rank,
            top_score=top_score,
            evidence_clauses=match.evidence_clauses,
        )
        for rank, match in enumerate(matches)
    ]
    return recommendations, len(clauses)


def recommendation_dicts(recommendations: list[Recommendation]) -> list[dict]:
    return [recommendation.model_dump() for recommendation in recommendations]


def csv_response(filename: str, rows: list[list[str | int | float]]) -> Response:
    output = StringIO(newline="")
    writer = csv.writer(output)
    writer.writerows(rows)
    content = "\ufeff" + output.getvalue()
    return Response(
        content=content,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.get("/health")
def health() -> dict[str, str | int]:
    return {
        "status": "ok",
        "environment": settings.environment,
        "standards_count": len(get_standards()),
    }


@app.get("/health/live")
def liveness() -> dict[str, str]:
    return {"status": "alive"}


@app.get("/health/ready")
def readiness() -> dict[str, str | int]:
    try:
        database = database_health()
        standards_count = len(get_standards())
    except Exception as error:
        logger.exception("readiness_failed")
        raise HTTPException(status_code=503, detail="Service dependencies are not ready") from error
    if database["quick_check"] != "ok" or standards_count == 0:
        raise HTTPException(status_code=503, detail="Service dependencies are not ready")
    return {
        "status": "ready",
        "database": "ok",
        "standards_count": standards_count,
        "users_count": int(database["users"]),
    }


@app.get("/metrics", response_class=Response)
def application_metrics() -> Response:
    return Response(content=metrics.prometheus_text(), media_type="text/plain; version=0.0.4")


@app.get("/login", include_in_schema=False)
def login_page(request: Request) -> Response:
    token = request.cookies.get(SESSION_COOKIE)
    if token and user_for_session(token):
        return RedirectResponse(url="/", status_code=303)
    login_path = FRONTEND_DIR / "login.html"
    if not login_path.exists():
        raise HTTPException(status_code=404, detail="Login frontend not found")
    return FileResponse(login_path)


@app.post("/auth/login", response_model=UserResponse)
def login(payload: LoginRequest, request: Request, response: Response) -> UserResponse:
    client_host = request.client.host if request.client else "unknown"
    rate_limit_key = f"{client_host}:{payload.username.strip().casefold()}"
    if login_limiter.is_blocked(rate_limit_key):
        raise HTTPException(
            status_code=429,
            detail="Too many failed login attempts. Try again later.",
            headers={"Retry-After": str(settings.login_window_seconds)},
        )
    user = authenticate_user(payload.username, payload.password)
    if user is None:
        login_limiter.record_failure(rate_limit_key)
        raise HTTPException(status_code=401, detail="Invalid username or password")
    login_limiter.reset(rate_limit_key)
    token, max_age = create_user_session(user.id)
    response.set_cookie(
        key=SESSION_COOKIE,
        value=token,
        max_age=max_age,
        httponly=True,
        samesite="strict",
        secure=settings.session_cookie_secure,
    )
    return UserResponse(id=user.id, username=user.username, role=user.role)


@app.post("/auth/logout", status_code=204)
def logout(request: Request, response: Response) -> Response:
    token = request.cookies.get(SESSION_COOKIE)
    if token:
        end_user_session(token)
    response.delete_cookie(SESSION_COOKIE)
    response.status_code = 204
    return response


@app.get("/auth/me", response_model=UserResponse)
def auth_me(user: UserRecord = Depends(current_user)) -> UserResponse:
    return UserResponse(id=user.id, username=user.username, role=user.role)


@app.get("/", include_in_schema=False)
def index(request: Request) -> Response:
    token = request.cookies.get(SESSION_COOKIE)
    if not token or user_for_session(token) is None:
        return RedirectResponse(url="/login", status_code=303)
    index_path = FRONTEND_DIR / "index.html"
    if not index_path.exists():
        raise HTTPException(status_code=404, detail="Frontend not found")
    return FileResponse(index_path)


@app.get("/demo-document", include_in_schema=False)
def demo_document(
    _user: UserRecord = Depends(require_roles("procurement", "reviewer", "admin")),
) -> Response:
    if not DEMO_DOCUMENT_PATH.exists():
        raise HTTPException(status_code=404, detail="Demo document is unavailable")
    return FileResponse(
        DEMO_DOCUMENT_PATH,
        media_type="application/pdf",
        filename=DEMO_DOCUMENT_PATH.name,
    )


@app.get("/admin", include_in_schema=False)
def admin_page(request: Request) -> Response:
    token = request.cookies.get(SESSION_COOKIE)
    user = user_for_session(token) if token else None
    if user is None:
        return RedirectResponse(url="/login", status_code=303)
    if user.role not in {"reviewer", "admin"}:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    admin_path = FRONTEND_DIR / "admin.html"
    if not admin_path.exists():
        raise HTTPException(status_code=404, detail="Admin frontend not found")
    return FileResponse(admin_path)


@app.post("/recommend", response_model=RecommendResponse)
def recommend(
    payload: RecommendRequest,
    _user: UserRecord = Depends(require_roles("procurement", "reviewer", "admin")),
) -> RecommendResponse:
    recommendations = run_recommendation(
        query=payload.query,
        limit=payload.limit,
        min_score=payload.min_score,
        mode=payload.mode,
    )
    search_id = save_search(
        query=payload.query,
        mode=payload.mode,
        source_type="text",
        source_name=None,
        results=recommendation_dicts(recommendations),
    )
    return RecommendResponse(
        query=payload.query,
        count=len(recommendations),
        search_id=search_id,
        results=recommendations,
    )


@app.post("/extract-document", response_model=ExtractDocumentResponse)
async def extract_document(
    file: UploadFile = File(...),
    _user: UserRecord = Depends(require_roles("procurement", "reviewer", "admin")),
) -> ExtractDocumentResponse:
    try:
        extracted = extract_text_from_upload(file.filename or "upload", await file.read())
    except DocumentProcessingError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    return ExtractDocumentResponse(
        filename=extracted.filename,
        extension=extracted.extension,
        char_count=extracted.char_count,
        preview=extracted.preview,
        text=extracted.text,
    )


@app.post("/recommend-document", response_model=RecommendDocumentResponse)
async def recommend_document(
    file: UploadFile = File(...),
    limit: int = Form(10, ge=1, le=50),
    min_score: float = Form(1.0, ge=0),
    mode: str = Form("hybrid", pattern="^(embedding|hybrid|keyword)$"),
    _user: UserRecord = Depends(require_roles("procurement", "reviewer", "admin")),
) -> RecommendDocumentResponse:
    try:
        extracted = extract_text_from_upload(file.filename or "upload", await file.read())
    except DocumentProcessingError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    recommendations, clauses_analyzed = run_document_recommendation(
        text=extracted.text,
        limit=limit,
        min_score=min_score,
        mode=mode,
    )
    search_id = save_search(
        query=extracted.text,
        mode=mode,
        source_type="document",
        source_name=extracted.filename,
        results=recommendation_dicts(recommendations),
    )
    return RecommendDocumentResponse(
        filename=extracted.filename,
        extension=extracted.extension,
        char_count=extracted.char_count,
        preview=extracted.preview,
        clauses_analyzed=clauses_analyzed,
        count=len(recommendations),
        search_id=search_id,
        results=recommendations,
    )


@app.post("/feedback", response_model=FeedbackResponse)
def create_feedback(
    payload: FeedbackRequest,
    _user: UserRecord = Depends(require_roles("procurement", "reviewer", "admin")),
) -> FeedbackResponse:
    feedback_id = save_feedback(
        search_id=payload.search_id,
        standard_id=payload.standard_id,
        standard_code=payload.standard_code,
        rating=payload.rating,
        note=payload.note,
    )
    return FeedbackResponse(feedback_id=feedback_id, status="saved")


@app.post("/reviews", response_model=ReviewResponse)
def create_review(
    payload: ReviewRequest,
    user: UserRecord = Depends(require_roles("reviewer", "admin")),
) -> ReviewResponse:
    search = get_search(payload.search_id)
    if search is None:
        raise HTTPException(status_code=404, detail="Saved search not found")

    matching_result = next(
        (
            result
            for result in search.results
            if result.get("id") == payload.standard_id
            and result.get("standard_code") == payload.standard_code
        ),
        None,
    )
    if matching_result is None:
        raise HTTPException(status_code=400, detail="Standard was not returned by this search")

    note = payload.note.strip() if payload.note and payload.note.strip() else None
    review_id = save_review(
        search_id=payload.search_id,
        standard_id=payload.standard_id,
        standard_code=payload.standard_code,
        decision=payload.decision,
        reviewer_user_id=user.id,
        note=note,
    )
    return ReviewResponse(review_id=review_id, status="saved", decision=payload.decision)


@app.get("/reviews", response_model=list[ReviewItem])
def reviews(
    limit: int = Query(20, ge=1, le=500),
    _user: UserRecord = Depends(require_roles("reviewer", "admin")),
) -> list[ReviewItem]:
    return [ReviewItem(**item.__dict__) for item in list_reviews(limit=limit)]


@app.get("/review-summary", response_model=ReviewSummaryResponse)
def get_review_summary(
    _user: UserRecord = Depends(require_roles("reviewer", "admin")),
) -> ReviewSummaryResponse:
    return ReviewSummaryResponse(**review_summary())


@app.get("/verification-queue", response_model=list[StandardSummary])
def verification_queue(
    status: str | None = Query(None),
    q: str | None = Query(None),
    limit: int = Query(50, ge=1, le=250),
    _user: UserRecord = Depends(require_roles("admin")),
) -> list[StandardSummary]:
    standards = list(get_standards())
    if status:
        standards = [standard for standard in standards if standard["verify_status"] == status]
    if q:
        needle = q.casefold()
        standards = [
            standard
            for standard in standards
            if needle in standard["standard_code"].casefold()
            or needle in standard["title"].casefold()
            or needle in standard["category"].casefold()
        ]
    standards.sort(
        key=lambda standard: (
            standard["verify_status"] != "needs_official_verification",
            standard["standard_code"],
        )
    )
    return [to_standard_summary(standard) for standard in standards[:limit]]


@app.put("/admin/standards/{standard_id}/verification", response_model=StandardSummary)
def update_standard_verification(
    standard_id: str,
    payload: VerificationUpdateRequest,
    user: UserRecord = Depends(require_roles("admin")),
) -> StandardSummary:
    standard = next(
        (item for item in get_standards() if item["id"].casefold() == standard_id.casefold()),
        None,
    )
    if standard is None:
        raise HTTPException(status_code=404, detail="Standard not found")

    previous_data = {
        "title": standard["title"],
        "source_url": standard["source_url"],
        "verify_status": standard["verify_status"],
        "last_reviewed": standard["last_reviewed"],
    }
    new_data = {
        "title": payload.title.strip(),
        "source_url": payload.source_url.strip(),
        "verify_status": payload.verify_status,
        "last_reviewed": date.today().isoformat(),
    }
    save_standard_override(
        standard_id=standard["id"],
        previous_data=previous_data,
        new_data=new_data,
        note=payload.note.strip(),
        user_id=user.id,
    )
    clear_search_caches()
    updated = next(item for item in get_standards() if item["id"] == standard["id"])
    return to_standard_summary(updated)


@app.get("/verification-history", response_model=list[VerificationHistoryItem])
def verification_history(
    limit: int = Query(25, ge=1, le=250),
    _user: UserRecord = Depends(require_roles("admin")),
) -> list[VerificationHistoryItem]:
    return [
        VerificationHistoryItem(**item.__dict__)
        for item in list_verification_history(limit=limit)
    ]


@app.get("/search-history", response_model=list[SearchHistoryItem])
def search_history(
    limit: int = Query(20, ge=1, le=100),
    _user: UserRecord = Depends(require_roles("reviewer", "admin")),
) -> list[SearchHistoryItem]:
    return [SearchHistoryItem(**item.__dict__) for item in list_searches(limit=limit)]


@app.get("/search-history/{search_id}", response_model=SavedSearchDetailResponse)
def search_history_detail(
    search_id: int,
    _user: UserRecord = Depends(require_roles("reviewer", "admin")),
) -> SavedSearchDetailResponse:
    search = get_search(search_id)
    if search is None:
        raise HTTPException(status_code=404, detail="Saved search not found")
    return SavedSearchDetailResponse(
        id=search.id,
        query=search.query,
        mode=search.mode,
        source_type=search.source_type,
        source_name=search.source_name,
        result_count=search.result_count,
        results=[Recommendation.model_validate(result) for result in search.results],
        created_at=search.created_at,
    )


@app.get("/retrieval-quality", response_model=RetrievalQualityResponse)
def retrieval_quality(
    _user: UserRecord = Depends(require_roles("reviewer", "admin")),
) -> RetrievalQualityResponse:
    if not QUALITY_METRICS_PATH.exists():
        raise HTTPException(status_code=503, detail="Retrieval quality report is unavailable")
    return RetrievalQualityResponse.model_validate(
        json.loads(QUALITY_METRICS_PATH.read_text(encoding="utf-8"))
    )


@app.get("/analytics", response_model=AnalyticsResponse)
def analytics(
    _user: UserRecord = Depends(require_roles("reviewer", "admin")),
) -> AnalyticsResponse:
    top_feedback = [
        {
            "standard_code": item.standard_code,
            "useful": item.useful,
            "not_useful": item.not_useful,
            "total": item.total,
        }
        for item in feedback_by_standard(limit=10)
    ]
    return AnalyticsResponse(
        searches_count=count_searches(),
        feedback=feedback_summary(),
        top_feedback_standards=top_feedback,
    )


@app.get("/dataset-quality", response_model=DatasetQualityResponse)
def dataset_quality(
    _user: UserRecord = Depends(require_roles("reviewer", "admin")),
) -> DatasetQualityResponse:
    standards = get_standards()
    categories: dict[str, int] = {}
    verification_status: dict[str, int] = {}
    missing_source_url_count = 0
    generic_source_url_count = 0
    needs_verification_count = 0

    for standard in standards:
        category = standard["category"]
        verify_status = standard["verify_status"]
        source_url = standard["source_url"]

        categories[category] = categories.get(category, 0) + 1
        verification_status[verify_status] = verification_status.get(verify_status, 0) + 1

        if not source_url:
            missing_source_url_count += 1
        if source_url.rstrip("/") == "https://standards.bis.gov.in":
            generic_source_url_count += 1
        if verify_status == "needs_official_verification":
            needs_verification_count += 1

    top_categories = [
        {"category": category, "count": count}
        for category, count in sorted(categories.items(), key=lambda item: item[1], reverse=True)[:10]
    ]

    return DatasetQualityResponse(
        standards_count=len(standards),
        categories=categories,
        verification_status=verification_status,
        missing_source_url_count=missing_source_url_count,
        generic_source_url_count=generic_source_url_count,
        needs_verification_count=needs_verification_count,
        top_categories=top_categories,
    )


@app.get("/reports/search/{search_id}.csv", response_class=Response)
def export_search_report(
    search_id: int,
    _user: UserRecord = Depends(require_roles("procurement", "reviewer", "admin")),
) -> Response:
    search = get_search(search_id)
    if search is None:
        raise HTTPException(status_code=404, detail="Saved search not found")

    rows: list[list[str | int | float]] = [
        ["Search ID", search.id],
        ["Created At", search.created_at],
        ["Source Type", search.source_type],
        ["Source Name", search.source_name or ""],
        ["Search Mode", search.mode],
        ["Query", search.query],
        ["Result Count", search.result_count],
        [],
        [
            "Rank",
            "Standard Code",
            "Title",
            "Score",
            "Confidence",
            "Category",
            "Subcategory",
            "Matched Terms",
            "Reason",
            "Mandatory Hint",
            "Verification Status",
            "Source URL",
            "Evidence Clauses",
        ],
    ]
    for rank, result in enumerate(search.results, start=1):
        rows.append(
            [
                rank,
                result.get("standard_code", ""),
                result.get("title", ""),
                result.get("score", ""),
                result.get("confidence_score", ""),
                result.get("category", ""),
                result.get("subcategory", ""),
                "; ".join(result.get("matched_terms", [])),
                result.get("reason", ""),
                result.get("mandatory_hint", ""),
                result.get("verify_status", ""),
                result.get("source_url", ""),
                " | ".join(result.get("evidence_clauses", [])),
            ]
        )

    return csv_response(f"recommendation-report-{search.id}.csv", rows)


@app.get("/reports/search/{search_id}.pdf", response_class=Response)
def export_search_pdf_report(
    search_id: int,
    _user: UserRecord = Depends(require_roles("procurement", "reviewer", "admin")),
) -> Response:
    search = get_search(search_id)
    if search is None:
        raise HTTPException(status_code=404, detail="Saved search not found")
    return Response(
        content=build_search_report_pdf(search),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="recommendation-report-{search.id}.pdf"'
        },
    )


@app.get("/reports/dataset-quality.csv", response_class=Response)
def export_dataset_quality_report(
    user: UserRecord = Depends(require_roles("reviewer", "admin")),
) -> Response:
    quality = dataset_quality(user)
    rows: list[list[str | int | float]] = [
        ["Metric", "Value"],
        ["Standards", quality.standards_count],
        ["Needs Official Verification", quality.needs_verification_count],
        ["Missing Source URLs", quality.missing_source_url_count],
        ["Generic BIS Source URLs", quality.generic_source_url_count],
        [],
        ["Verification Status", "Count"],
    ]
    rows.extend([status, count] for status, count in sorted(quality.verification_status.items()))
    rows.extend([[""], ["Category", "Count"]])
    rows.extend([category, count] for category, count in sorted(quality.categories.items()))
    return csv_response("dataset-quality-report.csv", rows)


@app.get("/reports/review-dataset.csv", response_class=Response)
def export_review_dataset(
    _user: UserRecord = Depends(require_roles("reviewer", "admin")),
) -> Response:
    rows: list[list[str | int | float]] = [
        [
            "Review ID",
            "Search ID",
            "Query Text",
            "Search Mode",
            "Source Type",
            "Source Name",
            "Standard ID",
            "Standard Code",
            "Decision",
            "Relevance Label",
            "Reviewer Note",
            "Reviewer",
            "Reviewed At",
        ]
    ]
    for review in list_reviews(limit=10000):
        rows.append(
            [
                review.id,
                review.search_id,
                review.query,
                review.mode,
                review.source_type,
                review.source_name or "",
                review.standard_id,
                review.standard_code,
                review.decision,
                1 if review.decision == "accepted" else 0,
                review.note or "",
                review.reviewer_username or "",
                review.updated_at,
            ]
        )
    return csv_response("reviewed-recommendations.csv", rows)


@app.get("/standards", response_model=list[StandardSummary])
def list_standards(
    category: str | None = Query(None, description="Optional exact category filter"),
    q: str | None = Query(None, min_length=2, description="Optional text filter over code, title, and keywords"),
    limit: int = Query(50, ge=1, le=250),
    _user: UserRecord = Depends(require_roles("procurement", "reviewer", "admin")),
) -> list[StandardSummary]:
    standards = list(get_standards())

    if category:
        standards = [standard for standard in standards if standard["category"].lower() == category.lower()]

    if q:
        needle = q.lower()
        standards = [
            standard
            for standard in standards
            if needle in standard["standard_code"].lower()
            or needle in standard["title"].lower()
            or needle in standard["keywords"].lower()
        ]

    return [to_standard_summary(standard) for standard in standards[:limit]]


@app.get("/standards/{standard_id}", response_model=StandardSummary)
def get_standard(
    standard_id: str,
    _user: UserRecord = Depends(require_roles("procurement", "reviewer", "admin")),
) -> StandardSummary:
    normalized_id = standard_id.lower()
    for standard in get_standards():
        if standard["id"].lower() == normalized_id or standard["standard_code"].lower() == normalized_id:
            return to_standard_summary(standard)

    raise HTTPException(status_code=404, detail="Standard not found")

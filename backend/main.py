"""
backend/main.py - JustEnough FastAPI Server

Wraps the existing pipeline (detector -> planner -> policy -> transform) behind HTTP endpoints.

Privacy contracts (per AGENTS.md):
  - Raw sensitive field VALUES are never serialized in any response or log.
  - Responses contain only: id, category, location, detector, confidence, action, placeholder.
  - Model name is read from JUSTENOUGH_MODEL env var; never hard-coded.
  - Prompt-injection defence is inherited from the planner module.

Endpoints:
  GET  /health        -> liveness + model/version info
  POST /analyze       -> full pipeline on an uploaded file + task string
  POST /verify        -> run task on original vs minimized, compare answers
  POST /chat          -> multi-turn chat on the minimized document ONLY
  GET  /audit-log     -> session-scoped policy floor clamp events
  GET  /schemas       -> taxonomy reference (categories, actions, policy floor)
"""

from __future__ import annotations

import io
import json
import logging
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

# make project root importable
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

from fastapi import FastAPI, File, Form, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from experiment.detector import SensitiveDataDetector
from experiment.planner import MinimizationPlanner, ACTIONS, CATEGORIES
from experiment.policy import enforce_policy_floor, POLICY_FLOOR_CATEGORIES
from experiment.transform import apply_minimization
from backend.verifier import get_verifier
from backend.chat import get_chat_client

# logging: never print raw values
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger("justenough.backend")

VERSION = "0.2.0"

app = FastAPI(
    title="JustEnough API",
    description=(
        "Task-aware data minimization layer for AI uploads. "
        "Same task answer, using fewer sensitive fields."
    ),
    version=VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Allow the local frontend (any origin during development)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# shared detector (initialised once at startup)
_detector: Optional[SensitiveDataDetector] = None

# In-memory session audit log for policy floor clamp events
# Format: list of dicts with timestamp, category, model_action, clamped_action, reason, case_id
_audit_log: List[Dict[str, Any]] = []


@app.on_event("startup")
async def startup_event() -> None:
    global _detector
    logger.info("Initialising SensitiveDataDetector ...")
    _detector = SensitiveDataDetector(presidio_engine=None)
    logger.info("SensitiveDataDetector ready.")


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------

class SafeField(BaseModel):
    """Detected sensitive field - values omitted per AGENTS.md contract."""
    id: str
    category: str
    location: Dict[str, int]
    detector: str
    confidence: float
    placeholder: str
    detection_rule: str = ""  # human-readable pattern that fired


class DecisionEntry(BaseModel):
    action: str
    reason: str
    confidence: float


class PolicyViolation(BaseModel):
    category: str
    model_action: str
    clamped_action: str
    reason: str


class AnalysisMetrics(BaseModel):
    total_fields_detected: int
    fields_kept: int
    fields_dropped_or_masked: int
    sensitive_field_reduction_pct: float
    original_char_length: int
    minimized_char_length: int
    policy_violations_clamped: int
    planner_retries: int
    latency_ms: float


class AnalyzeResponse(BaseModel):
    case_id: str
    doc_id: str
    task: str
    mode: str
    model: str
    detected_fields: List[SafeField]
    skeleton_length: int
    plan: Dict[str, DecisionEntry]
    unsure_categories: List[str]
    policy_violations: List[PolicyViolation]
    minimized_text: str
    metrics: AnalysisMetrics
    task_output_schema: Dict[str, Any] = {}


class VerifyRequest(BaseModel):
    task: str
    original_text: str
    minimized_text: str
    live: bool = False
    task_output_schema: Optional[Dict[str, Any]] = None


class ChatMessage(BaseModel):
    role: str   # "user" or "assistant"
    content: str


class ChatRequest(BaseModel):
    minimized_text: str
    history: List[ChatMessage] = []
    message: str
    live: bool = False


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_DETECTION_RULE_MAP: Dict[str, str] = {
    "account_identifier": "Matched 11-18 digit account number or card number pattern",
    "government_id": "Matched Indian PAN format: 5 alpha + 4 digits + 1 alpha (e.g. ABCDE1234F)",
    "person_name": "Matched salutation + capitalized name pattern (Presidio NER)",
    "counterparty_name": "Matched capitalized proper noun sequence near transfer/payment keyword",
    "address": "Matched address pattern: flat/house + locality + city + PIN (Presidio)",
    "contact": "Matched Indian mobile format (+91-XXXXXXXXXX or 10-digit) or email format",
    "date_of_birth": "Matched DOB keyword near date format (DD-MM-YYYY or YYYY-MM-DD)",
    "internal_id": "Matched internal identifier pattern (CUST/EMP + alphanumeric)",
    "employer": "Matched employer/company name near salary/credit keyword",
    "merchant": "Matched merchant name near UPI/debit transaction line",
    "amount": "Matched numeric value with INR/currency symbol or credit/debit column",
    "balance": "Matched balance numeric value near closing/opening balance keyword",
    "transaction_date": "Matched ISO or DD-Mon-YYYY date format in transaction line",
    "salary_component": "Matched payslip component label (basic, HRA, PF, deduction, etc.)",
    "medical_value": "Matched medical record number, diagnosis code, or lab value pattern",
    "clause_text": "Matched contractual clause pattern near legal keywords",
}


def _safe_fields(fields: list) -> List[SafeField]:
    """Strip raw values; return only safe metadata + detection rule description."""
    result = []
    for f in fields:
        rule = _DETECTION_RULE_MAP.get(f.category, f"Matched {f.category} pattern")
        result.append(SafeField(
            id=f.id,
            category=f.category,
            location=f.location,
            detector=f.detector,
            confidence=f.confidence,
            placeholder=f.placeholder,
            detection_rule=rule,
        ))
    return result


def _read_upload(upload: UploadFile) -> str:
    """
    Read text from an uploaded file.
    Supports plain text (.txt), CSV (.csv), JSON (.json), and text-based PDFs (.pdf via pdfplumber).
    Rejects encrypted/scanned PDFs with a clear error.
    """
    filename = (upload.filename or "").lower()
    raw_bytes = upload.file.read()

    if filename.endswith(".pdf"):
        try:
            import pdfplumber
        except ImportError:
            raise HTTPException(
                status_code=501,
                detail="pdfplumber not installed. Add it to requirements.txt to support PDF uploads.",
            )
        with pdfplumber.open(io.BytesIO(raw_bytes)) as pdf:
            pages = [p.extract_text() or "" for p in pdf.pages]
        text = "\n".join(pages).strip()
        if not text:
            raise HTTPException(
                status_code=422,
                detail="PDF appears to be scanned or encrypted - only text-based PDFs are supported.",
            )
        return text

    try:
        return raw_bytes.decode("utf-8")
    except UnicodeDecodeError:
        return raw_bytes.decode("latin-1")


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/health", summary="Liveness check")
async def health() -> JSONResponse:
    """Returns server status, model name (from env), and version."""
    model = os.environ.get("JUSTENOUGH_MODEL", "gemini-3.6-flash")
    return JSONResponse({
        "status": "ok",
        "version": VERSION,
        "model": model,
        "detector": "presidio+custom_indian_regex",
    })


@app.post("/analyze", response_model=AnalyzeResponse, summary="Run full minimization pipeline")
async def analyze(
    file: UploadFile = File(..., description="Document to minimise (.txt, .csv, .json, or text-based .pdf)"),
    task: str = Form(..., description="Natural-language task, e.g. 'Summarise my spending by category'"),
    live: bool = Query(False, description="Use live Gemini API (requires GEMINI_API_KEY env var)"),
    case_id: str = Query("upload", description="Optional case identifier for logging"),
) -> AnalyzeResponse:
    """
    Full JustEnough pipeline:
      1. Extract text from uploaded file
      2. Detect sensitive fields (Presidio + custom Indian regex)
      3. Build typed skeleton (raw values replaced with placeholders)
      4. Gemini plans minimization (mock or live)
      5. Enforce deterministic policy floor
      6. Apply deterministic transformations
      7. Return minimized document + safe metadata (no raw values)
    """
    if _detector is None:
        raise HTTPException(status_code=503, detail="Detector not ready yet.")

    t_start = time.monotonic()

    # 1. Read document
    try:
        original_text = _read_upload(file)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to read uploaded file: %s", type(exc).__name__)
        raise HTTPException(status_code=422, detail=f"Could not read file: {exc}")

    doc_id = Path(file.filename or "upload").stem
    logger.info(
        "Analyze request | case_id=%s | doc_id=%s | task_len=%d | live=%s",
        case_id, doc_id, len(task), live,
    )

    # 2 & 3. Detect + Skeleton
    fields, skeleton = _detector.detect_in_text(original_text, doc_id)
    logger.info("Detected %d sensitive field instances.", len(fields))

    # 4. Plan (raw values passed only to planner, never logged)
    raw_values_for_planner = [f.value for f in fields]

    planner = MinimizationPlanner(live_mode=live)
    raw_plan, retries = planner.plan(
        case_id=case_id,
        task=task,
        skeleton=skeleton,
        answer_schema_id=None,
        raw_sensitive_values=raw_values_for_planner,
    )
    del raw_values_for_planner  # scrub from local scope immediately

    # 5. Schema validation
    is_valid = planner.validate_plan_schema(raw_plan, expected_case_id=case_id)
    if not is_valid:
        raise HTTPException(status_code=500, detail="Planner produced an invalid plan schema.")

    # 6. Policy floor
    enforced_plan, violations = enforce_policy_floor(raw_plan)

    # Append violations to session audit log
    ts = datetime.now(timezone.utc).isoformat()
    for v in violations:
        _audit_log.append({
            "timestamp": ts,
            "case_id": case_id,
            "doc_id": doc_id,
            "category": v["category"],
            "model_action": v["model_action"],
            "clamped_action": v["clamped_action"],
            "reason": v["reason"],
        })

    # 7. Transform
    minimized_text, removed_values = apply_minimization(
        original_text=original_text,
        detected_fields=fields,
        plan_decisions=enforced_plan["decisions"],
    )
    del removed_values  # raw values - discard immediately, not returned

    latency_ms = (time.monotonic() - t_start) * 1000

    # Build safe metrics
    decisions = enforced_plan.get("decisions", {})
    n_total = len(fields)
    n_kept = sum(
        1 for f in fields
        if decisions.get(f.category, {}).get("action") == "KEEP"
    )
    n_redacted = n_total - n_kept
    reduction_pct = round((n_redacted / n_total * 100) if n_total > 0 else 0.0, 1)

    metrics = AnalysisMetrics(
        total_fields_detected=n_total,
        fields_kept=n_kept,
        fields_dropped_or_masked=n_redacted,
        sensitive_field_reduction_pct=reduction_pct,
        original_char_length=len(original_text),
        minimized_char_length=len(minimized_text),
        policy_violations_clamped=len(violations),
        planner_retries=retries,
        latency_ms=round(latency_ms, 1),
    )

    logger.info(
        "Pipeline complete | fields=%d | kept=%d | reduction=%.1f%% | latency=%.0fms",
        n_total, n_kept, reduction_pct, latency_ms,
    )

    task_output_schema = enforced_plan.get("task_output_schema", {})

    return AnalyzeResponse(
        case_id=case_id,
        doc_id=doc_id,
        task=task,
        mode="live" if live else "mock",
        model=planner.model_name,
        detected_fields=_safe_fields(fields),
        skeleton_length=len(skeleton),
        plan={
            cat: DecisionEntry(
                action=dec.get("action", "DROP"),
                reason=dec.get("reason", ""),
                confidence=float(dec.get("confidence", 0.0)),
            )
            for cat, dec in decisions.items()
        },
        unsure_categories=enforced_plan.get("unsure", []),
        policy_violations=[PolicyViolation(**v) for v in violations],
        minimized_text=minimized_text,
        metrics=metrics,
        task_output_schema=task_output_schema,
    )


@app.post("/verify", summary="Compare task answers on original vs minimized document")
async def verify(req: VerifyRequest) -> JSONResponse:
    """
    Runs the user's task on both original and minimized text via Gemini,
    compares answers using numeric tolerance / set matching / keyword overlap.

    Privacy: original_text IS sent to Gemini here (this is the A0 baseline arm).
    The whole point: minimized text produces the SAME answer.
    Raw detected field values are never passed to or returned from this endpoint.
    """
    try:
        verifier = get_verifier(req.live)
        result = verifier.verify(
            task=req.task,
            original_text=req.original_text,
            minimized_text=req.minimized_text,
            task_output_schema=req.task_output_schema,
        )
        return JSONResponse(result)
    except ValueError as exc:
        logger.error("[VERIFY ENDPOINT ERROR] ValueError: %s", exc)
        raise HTTPException(status_code=400, detail=str(exc))
    except RuntimeError as exc:
        logger.error("[VERIFY ENDPOINT ERROR] RuntimeError: %s", exc)
        raise HTTPException(status_code=502, detail=str(exc))
    except Exception as exc:
        logger.error("[VERIFY ENDPOINT UNHANDLED ERROR] %s: %s", type(exc).__name__, exc)
        raise HTTPException(status_code=500, detail=f"{type(exc).__name__}: {str(exc)}")


@app.post("/chat", summary="Multi-turn chat on the minimized document only")
async def chat(req: ChatRequest) -> JSONResponse:
    """
    Gemini multi-turn chat session using ONLY the minimized document as context.
    The original document (with PII) is never sent to this endpoint.

    Privacy: Only minimized_text is used as document context. History contains
    only user/assistant message text, no raw sensitive values.
    """
    if not req.minimized_text.strip():
        raise HTTPException(status_code=400, detail="minimized_text must not be empty.")
    if not req.message.strip():
        raise HTTPException(status_code=400, detail="message must not be empty.")
    try:
        client = get_chat_client(req.live)
        history_dicts = [{"role": m.role, "content": m.content} for m in req.history]
        reply = client.chat(
            minimized_text=req.minimized_text,
            history=history_dicts,
            message=req.message,
        )
        return JSONResponse({"reply": reply, "turn_index": len(req.history)})
    except ValueError as exc:
        logger.error("[CHAT ENDPOINT ERROR] ValueError: %s", exc)
        raise HTTPException(status_code=400, detail=str(exc))
    except RuntimeError as exc:
        logger.error("[CHAT ENDPOINT ERROR] RuntimeError: %s", exc)
        raise HTTPException(status_code=502, detail=str(exc))
    except Exception as exc:
        logger.error("[CHAT ENDPOINT UNHANDLED ERROR] %s: %s", type(exc).__name__, exc)
        raise HTTPException(status_code=500, detail=f"{type(exc).__name__}: {str(exc)}")


@app.get("/audit-log", summary="Session-scoped policy floor clamp event log")
async def audit_log() -> JSONResponse:
    """
    Returns all policy floor clamp events from the current server session.
    Each entry: timestamp, case_id, category, model_action, clamped_action, reason.
    Raw sensitive values are never included.
    """
    return JSONResponse({
        "count": len(_audit_log),
        "entries": _audit_log,
    })


@app.get("/schemas", summary="Taxonomy reference")
async def schemas() -> JSONResponse:
    """
    Returns the frozen taxonomy: categories, actions, and policy floor rules.
    Useful for the frontend to render labels and tooltips.
    """
    answer_schemas_path = PROJECT_ROOT / "schemas" / "answer_schemas.json"
    answer_schemas: Any = {}
    if answer_schemas_path.exists():
        with open(answer_schemas_path, "r", encoding="utf-8") as f:
            answer_schemas = json.load(f)

    return JSONResponse({
        "categories": CATEGORIES,
        "actions": ACTIONS,
        "policy_floor": {
            cat: allowed
            for cat, allowed in POLICY_FLOOR_CATEGORIES.items()
        },
        "action_descriptions": {
            "KEEP":         "Exact value is required for the task.",
            "DROP":         "Not required; remove completely.",
            "MASK_PARTIAL": "Only part is needed (e.g. last 4 digits).",
            "GENERALIZE":   "Broader form is enough (e.g. YYYY-MM for date).",
            "PSEUDONYMIZE": "Identity not needed, but occurrences must stay linkable.",
            "AGGREGATE":    "Totals, counts or groups are enough.",
        },
        "detection_rules": _DETECTION_RULE_MAP,
        "answer_schemas_count": len(answer_schemas) if isinstance(answer_schemas, dict) else 0,
    })


# dev entry-point
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)

"""
experiment/detector.py: Sensitive data detector for JustEnough Day 1.

Scope follows DAY1_SPEC.md Section 7 and the signed Section 18 amendment:
- Microsoft Presidio (presidio-analyzer) with local spaCy en_core_web_sm when available
- Custom Indian-format patterns (always run and never suppressed by threshold):
    1. UPI handle
    2. IFSC
    3. Indian phone
    4. Masked account (and account / card numbers)
- Fallback: 'regex-only' mode if Presidio dependencies are unavailable or fallback is forced.
Per Day 1 constraints: government_id is NOT covered by custom Indian regex.
If government_id is missed due to disabled recognizers / regex-only fallback, it is recorded as a detection miss.
Presidio ORGANIZATION entities are contextually mapped to 16-category taxonomy (employer, merchant, counterparty_name).
Ambiguous organizations are flagged and logged without recording raw sensitive values.

Observability & Benchmarking:
- Tracks initialization telemetry and per-document execution telemetry (counts by source, status, mode).
- Diagnostic benchmark paths for regex-only, presidio-only, and combined modes.
- Exact evaluation reporting span recall, category-correct recall, precision, false positives, and corrected subset denominators.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

PROJECT_ROOT = Path(__file__).resolve().parent.parent


@dataclass
class DetectedField:
    id: str
    category: str
    value: str  # Kept in memory only; never serialized to disk logs
    location: Dict[str, int]  # {"line": int, "start_char": int, "end_char": int}
    detector: str
    confidence: float
    placeholder: str


# Strictly the 4 custom Indian patterns specified in DAY1_SPEC.md Section 7
CUSTOM_PATTERNS = [
    # 1. UPI handle
    (
        "UPI handle",
        re.compile(r"[\w\.\-]+@(?:okhdfcbank|okaxis|okicici|oksbi|paytm|upi|ybl|axl|ibl|barodampay|icici|sbi)"),
        "contact",
        "[UPI]",
    ),
    # 2. IFSC
    (
        "IFSC",
        re.compile(r"\b[A-Z]{4}0[A-Z0-9]{6}\b"),
        "internal_id",
        "[IFSC]",
    ),
    # 3. Indian phone
    (
        "Indian phone",
        re.compile(r"(?:\+91[\-\s]?)?[6-9]\d{9}\b"),
        "contact",
        "[PHONE]",
    ),
    # 4. Masked account and account / card numbers
    (
        "Masked account",
        re.compile(r"\b(?:\d{4}[\s\-]?){2}\*{4}[\s\-]?\d{4}\b|\b\*{4,8}\d{4}\b|\bXXXX[\-\s]?XXXX[\-\s]?\d{4}\b|\b\d{4}[\-\s]?\d{4}[\-\s]?\d{4}[\-\s]?\d{4}\b|\b\d{9,18}\b"),
        "account_identifier",
        "[ACCT]",
    ),
]


class SensitiveDataDetector:
    def __init__(
        self,
        presidio_engine: Optional[Any] = None,
        sdp_client: Optional[Any] = None,  # Backward compatibility parameter
        force_fallback: bool = False,
    ):
        self.min_score = float(os.environ.get("JUSTENOUGH_PRESIDIO_MIN_SCORE", "0.5"))
        self.ambiguous_orgs: List[Dict[str, Any]] = []
        self.last_detection_telemetry: Dict[str, Any] = {}

        # Initialization telemetry
        init_error: Optional[str] = None
        self.presidio_engine = None

        if force_fallback or os.environ.get("JUSTENOUGH_DETECTION_FALLBACK") == "regex-only":
            self.mode = "regex-only"
        elif presidio_engine is not None:
            self.presidio_engine = presidio_engine
            self.mode = "presidio+regex"
        else:
            try:
                self.presidio_engine = self._init_presidio()
                self.mode = "presidio+regex" if self.presidio_engine is not None else "regex-only"
            except Exception as e:
                init_error = f"{type(e).__name__}: {str(e)}"
                self.presidio_engine = None
                self.mode = "regex-only"

        self.init_telemetry: Dict[str, Any] = {
            "presidio_available": self.presidio_engine is not None,
            "selected_mode": self.mode,
            "fallback_forced": force_fallback or os.environ.get("JUSTENOUGH_DETECTION_FALLBACK") == "regex-only",
            "min_score": self.min_score,
            "engine_type": "presidio+spacy(en_core_web_sm)" if self.presidio_engine is not None else "none",
            "init_error": init_error,
        }

    def _init_presidio(self) -> Optional[Any]:
        try:
            from presidio_analyzer import AnalyzerEngine
            from presidio_analyzer.nlp_engine import NlpEngineProvider

            configuration = {
                "nlp_engine_name": "spacy",
                "models": [{"lang_code": "en", "model_name": "en_core_web_sm"}],
            }
            provider = NlpEngineProvider(nlp_configuration=configuration)
            nlp_engine = provider.create_engine()
            return AnalyzerEngine(nlp_engine=nlp_engine)
        except Exception:
            return None

    def _map_organization_context(
        self, text: str, doc_id: str, start: int, end: int
    ) -> Optional[Tuple[str, str, str]]:
        """
        Contextually maps Presidio ORGANIZATION entity to frozen taxonomy:
        - 'employer' for payslip / Form 16 / employment contexts
        - 'merchant' for bank / credit card statement transaction contexts
        - 'counterparty_name' for rent / utility / insurance contractual contexts
        - Returns None if role cannot be reliably established (ambiguous).
        """
        doc_upper = doc_id.upper()
        window_start = max(0, start - 60)
        window_end = min(len(text), end + 60)
        window = text[window_start:window_end].lower()

        # 1. Employment context (payslip / Form 16)
        if doc_upper.startswith("PS-") or any(
            kw in window for kw in ["employer", "company", "organization", "organisation", "issued by", "pvt ltd", "limited"]
        ):
            return "employer", "[EMPLOYER]", "presidio:ORGANIZATION[employer]"

        # 2. Transaction / merchant context (bank / credit-card statements)
        if doc_upper.startswith("BS-") or doc_upper.startswith("CC-") or any(
            kw in window for kw in ["txn", "transaction", "narration", "description", "debit", "credit", "dr", "cr", "pos", "upi/"]
        ):
            return "merchant", "[MERCHANT]", "presidio:ORGANIZATION[merchant]"

        # 3. Contractual counterparty context (rent agreement, utility bill, insurance/lab)
        if (
            doc_upper.startswith("RA-")
            or doc_upper.startswith("UB-")
            or doc_upper.startswith("IL-")
            or any(
                kw in window
                for kw in [
                    "landlord", "tenant", "lessor", "lessee", "provider", "board",
                    "insurer", "insured", "hospital", "lab", "diagnostics", "utility",
                    "beneficiary", "party"
                ]
            )
        ):
            return "counterparty_name", "[COUNTERPARTY]", "presidio:ORGANIZATION[counterparty_name]"

        # Role cannot be established reliably -> ambiguous
        return None

    def detect_in_text(
        self,
        text: str,
        doc_id: str,
        mode_override: Optional[str] = None
    ) -> Tuple[List[DetectedField], str]:
        """
        Runs detection over document text and builds the typed placeholder skeleton.
        mode_override: optional diagnostic override ('combined', 'regex-only', 'presidio-only').
        Returns (detected_fields, skeleton_text).
        """
        active_mode = mode_override or self.mode
        fields: List[DetectedField] = []
        field_counter = 0

        # Calculate line offsets for mapping char offset to line number
        lines = text.splitlines(keepends=True)
        line_starts = []
        cur = 0
        for l in lines:
            line_starts.append(cur)
            cur += len(l)

        def get_line_num(char_idx: int) -> int:
            for idx, start in enumerate(line_starts):
                if char_idx < start:
                    return max(1, idx)
            return len(line_starts)

        # 1. Custom Indian regex patterns (UPI handle, IFSC, Indian phone, Masked account)
        # Included in 'combined', 'presidio+regex', and 'regex-only'
        custom_fields: List[DetectedField] = []
        if active_mode in ("presidio+regex", "regex-only", "combined"):
            for pattern_name, regex, category, placeholder in CUSTOM_PATTERNS:
                for match in regex.finditer(text):
                    start, end = match.span()
                    val = match.group()
                    field_counter += 1
                    fid = f"{doc_id}-det-{field_counter:02d}"
                    custom_fields.append(
                        DetectedField(
                            id=fid,
                            category=category,
                            value=val,
                            location={
                                "line": get_line_num(start),
                                "start_char": start,
                                "end_char": end,
                            },
                            detector=f"custom_pattern:{pattern_name}",
                            confidence=0.95,
                            placeholder=placeholder,
                        )
                    )

        # 2. Presidio detection
        presidio_fields: List[DetectedField] = []
        doc_ambiguous_count = 0
        analysis_status = "success"

        if active_mode in ("presidio+regex", "presidio-only", "combined") and self.presidio_engine:
            try:
                # Explicitly query only allowed entities.
                # Disabled: PHONE_NUMBER, IN_PAN, IN_AADHAAR per frozen specification.
                entities_to_detect = ["PERSON", "LOCATION", "ORGANIZATION", "EMAIL_ADDRESS", "DATE_TIME"]
                results = self.presidio_engine.analyze(
                    text=text,
                    language="en",
                    entities=entities_to_detect,
                    score_threshold=self.min_score,
                )

                for r in results:
                    start = r.start
                    end = r.end
                    val = text[start:end]
                    entity_type = r.entity_type

                    cat: Optional[str] = None
                    placeholder: Optional[str] = None
                    detector_label: str = f"presidio:{entity_type}"

                    if entity_type == "PERSON":
                        cat = "person_name"
                        placeholder = "[NAME]"
                    elif entity_type == "LOCATION":
                        cat = "address"
                        placeholder = "[ADDR]"
                    elif entity_type == "EMAIL_ADDRESS":
                        cat = "contact"
                        placeholder = "[EMAIL]"
                    elif entity_type == "DATE_TIME":
                        cat = "transaction_date"
                        placeholder = "[DATE]"
                    elif entity_type == "ORGANIZATION":
                        mapped = self._map_organization_context(text, doc_id, start, end)
                        if mapped is not None:
                            cat, placeholder, detector_label = mapped
                        else:
                            field_counter += 1
                            amb_id = f"{doc_id}-amb-{field_counter:02d}"
                            self.ambiguous_orgs.append({
                                "id": amb_id,
                                "doc_id": doc_id,
                                "location": {
                                    "line": get_line_num(start),
                                    "start_char": start,
                                    "end_char": end,
                                },
                                "detector": "presidio:ORGANIZATION",
                                "confidence": round(r.score, 4),
                            })
                            doc_ambiguous_count += 1
                            continue

                    if cat and placeholder:
                        field_counter += 1
                        fid = f"{doc_id}-det-{field_counter:02d}"
                        presidio_fields.append(
                            DetectedField(
                                id=fid,
                                category=cat,
                                value=val,
                                location={
                                    "line": get_line_num(start),
                                    "start_char": start,
                                    "end_char": end,
                                },
                                detector=detector_label,
                                confidence=round(r.score, 4),
                                placeholder=placeholder,
                            )
                        )
            except Exception as e:
                analysis_status = f"analysis_error: {type(e).__name__}"
        elif active_mode in ("presidio-only", "presidio+regex") and not self.presidio_engine:
            analysis_status = "presidio_unavailable_fallback"

        # 3. Deduplication & Overlap Resolution:
        # Custom patterns take precedence over Presidio matches on any overlap
        def overlaps(s1: int, e1: int, s2: int, e2: int) -> bool:
            return not (e1 <= s2 or s1 >= e2)

        filtered_presidio: List[DetectedField] = []
        for pf in presidio_fields:
            p_start = pf.location["start_char"]
            p_end = pf.location["end_char"]
            if any(overlaps(p_start, p_end, cf.location["start_char"], cf.location["end_char"]) for cf in custom_fields):
                continue
            filtered_presidio.append(pf)

        # Merge fields based on active mode
        if active_mode == "presidio-only":
            all_fields = presidio_fields
        elif active_mode == "regex-only":
            all_fields = custom_fields
        else:
            all_fields = custom_fields + filtered_presidio

        # Sort non-overlapping fields by start_char ascending
        all_fields.sort(key=lambda f: (f.location["start_char"], -f.location["end_char"]))
        non_overlapping: List[DetectedField] = []
        last_end = -1
        for f in all_fields:
            if f.location["start_char"] >= last_end:
                non_overlapping.append(f)
                last_end = f.location["end_char"]

        # Record safe execution telemetry (no raw values)
        self.last_detection_telemetry = {
            "doc_id": doc_id,
            "mode_used": active_mode,
            "analysis_status": analysis_status,
            "counts_by_source": {
                "custom_regex": len(custom_fields),
                "presidio": len(presidio_fields),
                "ambiguous_orgs": doc_ambiguous_count,
                "total_emitted": len(non_overlapping),
            }
        }

        # Build typed skeleton text
        skeleton = text
        for f in sorted(non_overlapping, key=lambda x: x.location["start_char"], reverse=True):
            s = f.location["start_char"]
            e = f.location["end_char"]
            skeleton = skeleton[:s] + f.placeholder + skeleton[e:]

        return non_overlapping, skeleton


def evaluate_detection_recall(
    detected_by_doc: Dict[str, List[DetectedField]],
    planted_json_path: Path,
    ambiguous_orgs: Optional[List[Dict[str, Any]]] = None,
    doc_ids: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Computes exact detection evaluation metrics against corpus/planted.json.
    Reports:
    - span_recall: planted items overlapping with any detected span / total planted in evaluated docs.
    - category_recall: planted items overlapping with detected span of exact matching category / total planted in evaluated docs.
    - precision: category-correct detected fields / total detected fields.
    - span_precision: span-overlapping detected fields / total detected fields.
    - false_positives: count of detected fields with no overlap in planted items.
    - Denominator is strictly filtered to the evaluated documents.
    """
    with open(planted_json_path, "r", encoding="utf-8") as f:
        all_planted = json.load(f)

    # Determine evaluated document set
    evaluated_docs = set(doc_ids) if doc_ids is not None else set(detected_by_doc.keys())
    planted_items = [p for p in all_planted if p["doc_id"] in evaluated_docs]

    total_planted = len(planted_items)
    misses: List[Dict[str, Any]] = []

    # Count all detected fields in evaluated documents
    total_detected = sum(len(detected_by_doc.get(did, [])) for did in evaluated_docs)

    span_hits = 0
    category_hits = 0

    hits_by_category: Dict[str, int] = {}
    span_hits_by_category: Dict[str, int] = {}
    total_by_category: Dict[str, int] = {}
    detected_by_category: Dict[str, int] = {}
    fp_by_category: Dict[str, int] = {}

    for item in planted_items:
        cat = item["category"]
        doc_id = item["doc_id"]
        total_by_category[cat] = total_by_category.get(cat, 0) + 1

        doc_detected = detected_by_doc.get(doc_id, [])
        p_start = item["location"]["start_char"]
        p_end = item["location"]["end_char"]

        # Span overlap condition: not (d_end <= p_start or d_start >= p_end)
        overlapping_fields = [
            d for d in doc_detected
            if not (d.location["end_char"] <= p_start or d.location["start_char"] >= p_end)
        ]

        has_span_overlap = len(overlapping_fields) > 0
        has_cat_match = any(d.category == cat for d in overlapping_fields)

        if has_span_overlap:
            span_hits += 1
            span_hits_by_category[cat] = span_hits_by_category.get(cat, 0) + 1

        if has_cat_match:
            category_hits += 1
            hits_by_category[cat] = hits_by_category.get(cat, 0) + 1
        else:
            misses.append({
                "item_id": item["id"],
                "doc_id": doc_id,
                "category": cat,
                "reason": (
                    "government_id_not_in_custom_regex_scope"
                    if cat == "government_id"
                    else ("category_mismatch" if has_span_overlap else "missed_by_detector")
                )
            })

    # Evaluate detected fields for precision and false positives
    detected_span_hits = 0
    detected_cat_hits = 0
    false_positives = 0

    for did in evaluated_docs:
        doc_planted = [p for p in planted_items if p["doc_id"] == did]
        for d in detected_by_doc.get(did, []):
            d_cat = d.category
            detected_by_category[d_cat] = detected_by_category.get(d_cat, 0) + 1
            ds = d.location["start_char"]
            de = d.location["end_char"]

            overlapping_planted = [
                p for p in doc_planted
                if not (p["location"]["end_char"] <= ds or p["location"]["start_char"] >= de)
            ]

            if overlapping_planted:
                detected_span_hits += 1
                if any(p["category"] == d_cat for p in overlapping_planted):
                    detected_cat_hits += 1
                else:
                    fp_by_category[d_cat] = fp_by_category.get(d_cat, 0) + 1
            else:
                false_positives += 1
                fp_by_category[d_cat] = fp_by_category.get(d_cat, 0) + 1

    category_recall = (category_hits / total_planted) if total_planted > 0 else 0.0
    span_recall = (span_hits / total_planted) if total_planted > 0 else 0.0
    precision = (detected_cat_hits / total_detected) if total_detected > 0 else 0.0
    span_precision = (detected_span_hits / total_detected) if total_detected > 0 else 0.0

    all_categories = sorted(list(set(list(total_by_category.keys()) + list(detected_by_category.keys()))))

    report: Dict[str, Any] = {
        "evaluated_documents": sorted(list(evaluated_docs)),
        "total_planted": total_planted,
        "total_detected": total_detected,
        "span_hits": span_hits,
        "span_recall": round(span_recall, 4),
        "category_hits": category_hits,
        "category_recall": round(category_recall, 4),
        "recall": round(category_recall, 4),  # Standard recall field matches category-correct recall
        "recall_pct": f"{round(category_recall * 100, 2)}%",
        "precision": round(precision, 4),
        "span_precision": round(span_precision, 4),
        "false_positives": false_positives,
        "by_category": {
            cat: {
                "planted_total": total_by_category.get(cat, 0),
                "category_hits": hits_by_category.get(cat, 0),
                "span_hits": span_hits_by_category.get(cat, 0),
                "detected_total": detected_by_category.get(cat, 0),
                "recall": round(hits_by_category.get(cat, 0) / total_by_category[cat], 4) if total_by_category.get(cat, 0) > 0 else 0.0,
                "precision": round(hits_by_category.get(cat, 0) / detected_by_category[cat], 4) if detected_by_category.get(cat, 0) > 0 else 0.0,
                "false_positives": fp_by_category.get(cat, 0),
            }
            for cat in all_categories
        },
        "misses": misses,
        "unmapped_organization_count": len(ambiguous_orgs or []),
        "ambiguous_organizations": ambiguous_orgs or [],
    }

    return report


def benchmark_detector_modes(
    corpus_dir: Path,
    planted_json_path: Path,
    doc_ids: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Diagnostic benchmarking of detection modes:
    - 'regex-only': evaluates custom Indian regex patterns alone.
    - 'presidio-only': evaluates Presidio NLP alone.
    - 'combined': evaluates the combined pipeline (custom regex + Presidio).
    Returns comparative metrics for all 3 modes.
    """
    detector = SensitiveDataDetector()
    target_docs = sorted(doc_ids) if doc_ids is not None else [f.stem for f in sorted(corpus_dir.glob("*.txt"))]

    benchmark_results: Dict[str, Any] = {}

    for mode in ["regex-only", "presidio-only", "combined"]:
        detected_by_doc: Dict[str, List[DetectedField]] = {}
        for did in target_docs:
            doc_file = corpus_dir / f"{did}.txt"
            if not doc_file.exists():
                continue
            with open(doc_file, "r", encoding="utf-8") as f:
                text = f.read()
            fields, _ = detector.detect_in_text(text, did, mode_override=mode)
            detected_by_doc[did] = fields

        report = evaluate_detection_recall(
            detected_by_doc=detected_by_doc,
            planted_json_path=planted_json_path,
            doc_ids=target_docs,
        )

        benchmark_results[mode] = {
            "mode": mode,
            "total_detected": report["total_detected"],
            "span_recall": report["span_recall"],
            "category_recall": report["category_recall"],
            "precision": report["precision"],
            "false_positives": report["false_positives"],
        }

    return benchmark_results

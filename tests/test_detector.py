"""
tests/test_detector.py: Unit tests for experiment/detector.py.
Verifies:
1. Fallback mode is active ('regex-only') when forced or when Presidio is unavailable.
2. Custom Indian patterns match UPI handles, IFSC, Indian phone, and masked/unmasked accounts.
3. Government IDs are NOT matched by custom regex or Presidio (per Constraint 2 / frozen scope).
4. Skeleton text contains typed placeholders and does not leak detected values.
5. Detection recall against corpus/planted.json reports exact hits and misses.
6. Contextual ORGANIZATION mapping assigns employer, merchant, or counterparty_name when supported.
7. Ambiguous organizations are flagged without recording raw sensitive values.
8. Detector observability: records init_telemetry and per-document counts_by_source without raw values.
9. Diagnostic benchmark paths (regex-only, presidio-only, combined) run independently.
10. Corrected subset denominator: evaluating on a subset of documents filters planted items exactly.
"""

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from experiment.detector import SensitiveDataDetector, benchmark_detector_modes, evaluate_detection_recall

CORPUS_DIR = PROJECT_ROOT / "corpus"
PLANTED_PATH = CORPUS_DIR / "planted.json"


def test_detector_scope_and_patterns():
    # 1. Test fallback mode explicitly
    detector = SensitiveDataDetector(force_fallback=True)
    assert detector.mode == "regex-only", f"Expected mode 'regex-only', got {detector.mode}"

    sample_text = (
        "Customer phone: +91-9845012345, UPI: aarav@okaxis, IFSC: SBIN0004521, "
        "Account: 30981245781, Card: 4532-8901-2345-6789, PAN: ABCPS1234F"
    )

    fields, skeleton = detector.detect_in_text(sample_text, "TEST-1")

    # Raw sensitive values must NOT appear in skeleton for detected items
    assert "+91-9845012345" not in skeleton
    assert "aarav@okaxis" not in skeleton
    assert "SBIN0004521" not in skeleton
    assert "30981245781" not in skeleton
    assert "4532-8901-2345-6789" not in skeleton

    # Placeholders must be present
    assert "[PHONE]" in skeleton
    assert "[UPI]" in skeleton
    assert "[IFSC]" in skeleton
    assert "[ACCT]" in skeleton

    # CONSTRAINT 2 CHECK: PAN must NOT be matched by custom regex
    pan_matches = [f for f in fields if f.value == "ABCPS1234F"]
    assert len(pan_matches) == 0, "PAN should NOT be matched by custom Indian patterns per Day 1 constraint 2"


def test_detector_recall_on_corpus():
    detector = SensitiveDataDetector()
    detected_by_doc = {}

    for doc_file in sorted(CORPUS_DIR.glob("*.txt")):
        doc_id = doc_file.stem
        with open(doc_file, "r", encoding="utf-8") as f:
            text = f.read()
        fields, skeleton = detector.detect_in_text(text, doc_id)
        detected_by_doc[doc_id] = fields

    report = evaluate_detection_recall(detected_by_doc, PLANTED_PATH, detector.ambiguous_orgs)

    assert report["total_planted"] == 91
    assert report["total_detected"] > 0
    assert report["span_recall"] >= report["category_recall"]
    # Contacts (phone/UPI) and accounts/IFSC should have hits
    assert report["by_category"]["contact"]["category_hits"] > 0
    assert report["by_category"]["account_identifier"]["category_hits"] > 0

    # Constraint check: government_id should have 0 hits per frozen scope and be recorded in misses
    gov_misses = [m for m in report["misses"] if m["category"] == "government_id"]
    assert len(gov_misses) == 4, f"Expected 4 government_id misses, got {len(gov_misses)}"
    print(f"\nDetector test passed. Mode: {detector.mode}, Category Recall: {report['recall_pct']}, Span Recall: {report['span_recall'] * 100:.2f}%")


def test_presidio_entity_mapping():
    detector = SensitiveDataDetector()
    if detector.mode != "presidio+regex":
        print("\nPresidio not installed; skipping test_presidio_entity_mapping.")
        return

    # Text containing names, locations, and contextual organizations
    ps_text = "Employee: Vikram Malhotra. Employer: Tech Mahindra Limited. Location: Bengaluru."
    fields_ps, skeleton_ps = detector.detect_in_text(ps_text, "PS-1")
    categories_ps = {f.category for f in fields_ps}
    assert "person_name" in categories_ps or "employer" in categories_ps or "address" in categories_ps
    assert "Vikram Malhotra" not in skeleton_ps or "Tech Mahindra" not in skeleton_ps

    bs_text = "2026-09-04 Txn Ref 89412 Debit to Swiggy Bangalore for Rs 450.00."
    fields_bs, skeleton_bs = detector.detect_in_text(bs_text, "BS-1")
    for f in fields_bs:
        assert f.category in [
            "account_identifier", "government_id", "person_name", "counterparty_name",
            "address", "contact", "date_of_birth", "internal_id", "employer", "merchant",
            "amount", "balance", "transaction_date", "salary_component", "medical_value",
            "clause_text"
        ], f"Invalid category {f.category}"


def test_organization_ambiguous_handling():
    detector = SensitiveDataDetector()
    if detector.mode != "presidio+regex":
        print("\nPresidio not installed; skipping test_organization_ambiguous_handling.")
        return

    # A generic text without any document context cues for an organization
    generic_text = "Please note that Acme Holdings has reviewed the document."
    fields, skeleton = detector.detect_in_text(generic_text, "GEN-1")

    # If Presidio flags Acme Holdings as an ORGANIZATION, it should either be contextually mapped or recorded as ambiguous
    org_fields = [f for f in fields if "ORGANIZATION" in f.detector]
    for f in org_fields:
        assert f.category in ("employer", "merchant", "counterparty_name")

    # Ambiguous list must NOT leak raw values
    for amb in detector.ambiguous_orgs:
        assert "value" not in amb
        assert "text" not in amb
        assert "raw" not in amb
        assert "id" in amb and "location" in amb


def test_detector_observability():
    detector = SensitiveDataDetector()

    # Check initialization telemetry
    assert "presidio_available" in detector.init_telemetry
    assert "selected_mode" in detector.init_telemetry
    assert "engine_type" in detector.init_telemetry
    assert detector.init_telemetry["min_score"] == 0.5

    # Run detection on sample text and verify execution telemetry
    sample_text = "Customer phone: +91-9845012345, UPI: aarav@okaxis, IFSC: SBIN0004521"
    fields, skeleton = detector.detect_in_text(sample_text, "OBS-1")

    telemetry = detector.last_detection_telemetry
    assert telemetry["doc_id"] == "OBS-1"
    assert telemetry["analysis_status"] == "success"
    assert "counts_by_source" in telemetry
    assert telemetry["counts_by_source"]["custom_regex"] >= 3
    assert telemetry["counts_by_source"]["total_emitted"] == len(fields)

    # Telemetry must NOT contain raw values
    telemetry_str = str(telemetry)
    assert "+91-9845012345" not in telemetry_str
    assert "aarav@okaxis" not in telemetry_str
    assert "SBIN0004521" not in telemetry_str


def test_subset_denominator_correction():
    detector = SensitiveDataDetector(force_fallback=True)

    # Evaluate ONLY BS-1 and BS-2
    subset_docs = ["BS-1", "BS-2"]
    detected_subset = {}

    for did in subset_docs:
        doc_file = CORPUS_DIR / f"{did}.txt"
        with open(doc_file, "r", encoding="utf-8") as f:
            text = f.read()
        fields, _ = detector.detect_in_text(text, did)
        detected_subset[did] = fields

    # Call evaluate_detection_recall with the subset
    report = evaluate_detection_recall(detected_subset, PLANTED_PATH, doc_ids=subset_docs)

    # Total planted across all 10 docs is 91; for BS-1 (10) + BS-2 (10) it is 20
    assert report["total_planted"] == 20, f"Expected 20 planted items in BS-1 and BS-2, got {report['total_planted']}"
    assert report["evaluated_documents"] == ["BS-1", "BS-2"]
    assert report["span_recall"] <= 1.0
    assert report["category_recall"] <= 1.0


def test_independent_detection_benchmarks():
    # Diagnostic benchmarking of regex-only, presidio-only, and combined
    benchmarks = benchmark_detector_modes(CORPUS_DIR, PLANTED_PATH, doc_ids=["BS-1", "PS-1"])

    assert "regex-only" in benchmarks
    assert "presidio-only" in benchmarks
    assert "combined" in benchmarks

    regex_metrics = benchmarks["regex-only"]
    presidio_metrics = benchmarks["presidio-only"]
    combined_metrics = benchmarks["combined"]

    assert regex_metrics["mode"] == "regex-only"
    assert presidio_metrics["mode"] == "presidio-only"
    assert combined_metrics["mode"] == "combined"

    # Combined should detect equal or more than regex-only
    assert combined_metrics["total_detected"] >= regex_metrics["total_detected"]
    print(f"\nDiagnostic benchmark results on [BS-1, PS-1]:")
    print(f"  Regex-only: span recall={regex_metrics['span_recall']*100:.1f}%, cat recall={regex_metrics['category_recall']*100:.1f}%, precision={regex_metrics['precision']*100:.1f}%")
    print(f"  Presidio-only: span recall={presidio_metrics['span_recall']*100:.1f}%, cat recall={presidio_metrics['category_recall']*100:.1f}%, precision={presidio_metrics['precision']*100:.1f}%")
    print(f"  Combined: span recall={combined_metrics['span_recall']*100:.1f}%, cat recall={combined_metrics['category_recall']*100:.1f}%, precision={combined_metrics['precision']*100:.1f}%")



def test_organization_classification_independent_of_doc_id():
    detector = SensitiveDataDetector()
    if detector.mode != "presidio+regex":
        print("\nPresidio not installed; skipping test_organization_classification_independent_of_doc_id.")
        return

    # 1. Text with explicit employer keyword context: must classify identically across different doc IDs
    employer_text = "Salary statement for employee John Doe. Employer: Tech Mahindra Limited. Paid in full."
    fields_ps, _ = detector.detect_in_text(employer_text, "PS-101")
    fields_bs, _ = detector.detect_in_text(employer_text, "BS-999")
    fields_unknown, _ = detector.detect_in_text(employer_text, "CUSTOM-XYZ")

    org_ps = [f.category for f in fields_ps if "ORGANIZATION" in f.detector]
    org_bs = [f.category for f in fields_bs if "ORGANIZATION" in f.detector]
    org_unknown = [f.category for f in fields_unknown if "ORGANIZATION" in f.detector]
    assert org_ps == org_bs == org_unknown, f"Mismatch across doc IDs: {org_ps} vs {org_bs} vs {org_unknown}"
    if org_ps:
        assert org_ps[0] == "employer"

    # 2. Text with insufficient context: must remain ambiguous regardless of document ID prefix
    insufficient_text = "The document was reviewed by Horizon Global yesterday."

    det_ps = SensitiveDataDetector()
    fields_amb_ps, _ = det_ps.detect_in_text(insufficient_text, "PS-01")

    det_bs = SensitiveDataDetector()
    fields_amb_bs, _ = det_bs.detect_in_text(insufficient_text, "BS-01")

    det_ra = SensitiveDataDetector()
    fields_amb_ra, _ = det_ra.detect_in_text(insufficient_text, "RA-01")

    org_cats_ps = [f.category for f in fields_amb_ps if "ORGANIZATION" in f.detector]
    org_cats_bs = [f.category for f in fields_amb_bs if "ORGANIZATION" in f.detector]
    org_cats_ra = [f.category for f in fields_amb_ra if "ORGANIZATION" in f.detector]

    assert org_cats_ps == [], f"Expected no mapped organization for PS-01 without context, got {org_cats_ps}"
    assert org_cats_bs == [], f"Expected no mapped organization for BS-01 without context, got {org_cats_bs}"
    assert org_cats_ra == [], f"Expected no mapped organization for RA-01 without context, got {org_cats_ra}"
    assert len(det_ps.ambiguous_orgs) == len(det_bs.ambiguous_orgs) == len(det_ra.ambiguous_orgs)


def test_cif_and_enhanced_patterns():
    detector = SensitiveDataDetector(force_fallback=True)
    sample_text = (
        "Account Holder Name: Aarav Sharma\n"
        "Customer CIF: CIF88392014\n"
        "Customer ID: CUST91028345\n"
        "User ID: ICICI7749201\n"
        "Reference ID: SBICUST881923\n"
        "Card Account ID: AXISCC902341\n"
        "UPI-TRANSFER to Priya Patel\n"
        "Merchant: Swiggy Bangalore\n"
        "POS/Merchant: Apollo Pharmacy Indiranagar\n"
        "2026-09-03   UPI/Swiggy Bangalore/food   450.00\n"
    )
    fields, skeleton = detector.detect_in_text(sample_text, "DOC-1")
    cat_vals = [(f.category, f.value) for f in fields]

    # Internal IDs
    assert ("internal_id", "CIF88392014") in cat_vals
    assert ("internal_id", "CUST91028345") in cat_vals
    assert ("internal_id", "ICICI7749201") in cat_vals
    assert ("internal_id", "SBICUST881923") in cat_vals
    assert ("internal_id", "AXISCC902341") in cat_vals

    # Account holder & counterparty
    assert ("person_name", "Aarav Sharma") in cat_vals
    assert ("counterparty_name", "Priya Patel") in cat_vals

    # Merchant
    merchants = [f.value for f in fields if f.category == "merchant"]
    assert "Swiggy Bangalore" in merchants
    assert "Apollo Pharmacy Indiranagar" in merchants

    # Skeletons do not leak sensitive raw values
    assert "CIF88392014" not in skeleton
    assert "CUST91028345" not in skeleton
    assert "Aarav Sharma" not in skeleton
    assert "Priya Patel" not in skeleton


def test_repeated_name_both_occurrences_detected():
    """
    Test A (Detector): Verifies that presidio+regex mode detects BOTH occurrences
    of a repeated person name as separate, non-overlapping spans with correct offsets.

    Root cause context: regex-only mode only captures names via header-anchored patterns
    (e.g. 'Account Holder Name:'). Free-standing repeated names are detected by SpaCy/Presidio.
    This test confirms the default combined mode correctly finds both spans.
    """
    doc = "Account holder: Aarav Sharma. Transfer to Aarav Sharma."

    detector = SensitiveDataDetector()  # default: presidio+regex
    fields, skeleton = detector.detect_in_text(doc, "REPRO-REPEAT")

    name_fields = [f for f in fields if f.category == "person_name"]
    spans = [(f.location["start_char"], f.location["end_char"]) for f in name_fields]

    # Both occurrences must be detected
    assert len(name_fields) == 2, (
        f"Expected 2 person_name fields, got {len(name_fields)}. "
        f"Spans detected: {spans}"
    )

    # Verify exact values and correct categories (no raw values in failure messages)
    for f in name_fields:
        assert f.category == "person_name"
        # Verify offset correctness against original text
        actual = doc[f.location["start_char"]:f.location["end_char"]]
        assert actual == f.value, (
            f"Offset mismatch for field {f.id}: doc slice len={len(actual)}, "
            f"field value len={len(f.value)}"
        )

    # Spans must not overlap
    spans_sorted = sorted(spans)
    assert spans_sorted[0][1] <= spans_sorted[1][0], (
        f"Detected spans overlap: {spans_sorted[0]} and {spans_sorted[1]}"
    )

    # Both occurrences must be replaced in skeleton
    assert "Aarav Sharma" not in skeleton
    assert skeleton.count("[NAME]") == 2


def test_repeated_name_transformer_integration_with_actual_detector():
    """
    Test B (Transformer Integration): Uses the detector's actual output (not manually
    constructed spans) and verifies that apply_minimization() replaces BOTH occurrences
    when the detector correctly identifies both spans.

    This test must not manually add the second span — it relies entirely on the detector.
    """
    from experiment.transform import apply_minimization

    doc = "Account holder: Aarav Sharma. Transfer to Aarav Sharma."

    detector = SensitiveDataDetector()  # presidio+regex, finds both spans
    fields, _ = detector.detect_in_text(doc, "REPRO-TRANSFORM")

    plan_decisions = {
        "person_name": {"action": "DROP", "reason": "Not needed for task", "confidence": 1.0}
    }

    minimized, removed_values = apply_minimization(doc, fields, plan_decisions, strict=True)

    # Neither occurrence should remain in the minimized text
    assert "Aarav Sharma" not in minimized, (
        "At least one occurrence of the person name remained in minimized text"
    )

    # removed_values must account for both transformations
    assert len(removed_values) >= 2, (
        f"Expected at least 2 items in removed_values, got {len(removed_values)}"
    )

    # The replacement tokens must appear in the minimized text
    assert "[REDACTED:PERSON_NAME]" in minimized


if __name__ == "__main__":
    test_detector_scope_and_patterns()
    test_detector_recall_on_corpus()
    test_presidio_entity_mapping()
    test_organization_ambiguous_handling()
    test_detector_observability()
    test_subset_denominator_correction()
    test_independent_detection_benchmarks()
    test_organization_classification_independent_of_doc_id()
    test_cif_and_enhanced_patterns()
    test_repeated_name_both_occurrences_detected()
    test_repeated_name_transformer_integration_with_actual_detector()
    print("\nAll detector tests and benchmarks passed successfully.")


"""
backend/verifier.py — JustEnough Answer Verification Module

Runs the user's task on:
  A-arm: original document text   (this is sent to Gemini in the A call)
  B-arm: minimized document text  (this is sent to Gemini in the B call)

Compares A and B answers:
  - Numeric values: within 2% tolerance
  - List/set values: set equality (order-insensitive)
  - Free text: exact-then-keyword overlap fallback

Privacy contracts:
  - Raw sensitive values are NOT passed to this module.
  - The original_text IS sent to Gemini in the A-arm call — this is the A0 baseline arm.
    The whole point is to show minimized text produces the SAME answer.
  - This module never logs text content beyond debug level.

Per AGENTS.md: Model name from env var. Temperature 0.
"""

from __future__ import annotations

import logging
import os
import re
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

logger = logging.getLogger("justenough.verifier")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _extract_number(text: str) -> Optional[float]:
    """Pull the first numeric value (possibly with commas/currency symbols) from a string."""
    text = text.replace(",", "").replace("\u20b9", "").replace("$", "").replace("\u00a3", "")
    matches = re.findall(r"[-+]?\d+(?:\.\d+)?", text)
    if matches:
        return float(matches[0])
    return None


def _numeric_deviation(a: str, b: str) -> Optional[float]:
    """Return absolute % deviation between two numeric strings, or None if not parseable."""
    na = _extract_number(a)
    nb = _extract_number(b)
    if na is None or nb is None:
        return None
    if na == 0 and nb == 0:
        return 0.0
    denom = abs(na) if na != 0 else abs(nb)
    return abs(na - nb) / denom * 100


def _compare_answers(answer_a: str, answer_b: str) -> Tuple[bool, float, str]:
    """
    Compare two free-text answers.
    Returns: (preserved, deviation_pct, method)
    """
    # 1. Numeric comparison
    dev = _numeric_deviation(answer_a, answer_b)
    if dev is not None:
        preserved = dev <= 2.0
        return preserved, round(dev, 2), "numeric_tolerance_2pct"

    # 2. Set comparison on comma-separated or newline-separated lists
    sep = re.compile(r"[,\n;]")
    items_a = {x.strip().lower() for x in sep.split(answer_a) if x.strip()}
    items_b = {x.strip().lower() for x in sep.split(answer_b) if x.strip()}
    if len(items_a) > 1 and len(items_b) > 1:
        overlap = len(items_a & items_b)
        union = len(items_a | items_b)
        jaccard = overlap / union if union > 0 else 0.0
        preserved = jaccard >= 0.8
        dev_pct = round((1.0 - jaccard) * 100, 2)
        return preserved, dev_pct, "set_jaccard_80pct"

    # 3. Keyword overlap fallback
    words_a = set(re.findall(r"\b\w{3,}\b", answer_a.lower()))
    words_b = set(re.findall(r"\b\w{3,}\b", answer_b.lower()))
    if words_a and words_b:
        overlap = len(words_a & words_b)
        union = len(words_a | words_b)
        score = overlap / union if union > 0 else 0.0
        preserved = score >= 0.6
        dev_pct = round((1.0 - score) * 100, 2)
        return preserved, dev_pct, "keyword_overlap_60pct"

    # 4. Exact match fallback
    preserved = answer_a.strip().lower() == answer_b.strip().lower()
    return preserved, 0.0 if preserved else 100.0, "exact_match"


# ---------------------------------------------------------------------------
# Mock verifier
# ---------------------------------------------------------------------------

class MockVerifier:
    """Deterministic mock for infrastructure testing."""

    def verify(
        self,
        task: str,
        original_text: str,
        minimized_text: str,
        task_output_schema: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        task_lower = task.lower()
        if any(w in task_lower for w in ["dining", "food", "eating", "restaurant"]):
            answer_a = "Total dining expenses: \u20b91,100.00 (Swiggy \u20b9680 + Zomato \u20b9420)"
            answer_b = "Total food expenses: \u20b91,100.00"
        elif any(w in task_lower for w in ["balance", "closing"]):
            answer_a = "Closing balance: \u20b91,40,210.00"
            answer_b = "Closing balance: \u20b91,40,210.00"
        elif any(w in task_lower for w in ["salary", "pay", "income"]):
            answer_a = "Salary credited: \u20b91,25,000.00 from Infosys Ltd"
            answer_b = "Salary credited: \u20b91,25,000.00"
        else:
            answer_a = "Summary available in the document."
            answer_b = "Summary available in the minimized document."

        preserved, dev, method = _compare_answers(answer_a, answer_b)
        return {
            "answer_original": answer_a,
            "answer_minimized": answer_b,
            "preserved": preserved,
            "deviation_pct": dev,
            "method": method,
            "mode": "mock",
        }


# ---------------------------------------------------------------------------
# Live Gemini verifier
# ---------------------------------------------------------------------------

import time

class LiveVerifier:
    """Calls Gemini at temperature=0 on both original and minimized text."""

    def __init__(self, model_name: Optional[str] = None):
        self.model_name = model_name or os.environ.get(
            "JUSTENOUGH_MODEL", "gemini-3.6-flash"
        )
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise ValueError(
                "LiveVerifier requires GEMINI_API_KEY in environment or .env file."
            )
        try:
            from google import genai
            self._client = genai.Client()
            self._mode = "google.genai"
        except ImportError:
            import google.generativeai as genai
            genai.configure(api_key=api_key)
            self._legacy_genai = genai
            self._mode = "google.generativeai"

        logger.info(
            "[LIVE VERIFIER READY] Model: %s | SDK: %s",
            self.model_name,
            self._mode,
        )

    def _ask(self, document_text: str, task: str, arm_label: str = "A") -> str:
        """Run task on a document, return the answer string."""
        prompt = (
            f"You are a document analysis assistant. Answer the following task "
            f"using ONLY the information in the document below. Be concise and factual.\n\n"
            f"Task: {task}\n\n"
            f"Document:\n{document_text}\n\n"
            f"Answer:"
        )
        t0 = time.monotonic()
        logger.info(
            "[LIVE VERIFY %s-ARM START] Model: %s | Document chars: %d | Task: %s",
            arm_label, self.model_name, len(document_text), task
        )
        try:
            if self._mode == "google.genai":
                resp = self._client.models.generate_content(
                    model=self.model_name,
                    contents=prompt,
                    config={"temperature": 0.0},
                )
            else:
                model = self._legacy_genai.GenerativeModel(
                    model_name=self.model_name,
                    generation_config={"temperature": 0.0},
                )
                resp = model.generate_content(prompt)

            elapsed_ms = (time.monotonic() - t0) * 1000
            if not resp or not hasattr(resp, "text") or not resp.text:
                logger.error("[LIVE VERIFY %s-ARM FAIL] Empty response received in %.0fms", arm_label, elapsed_ms)
                raise RuntimeError(f"Gemini {self.model_name} returned an empty response during verification.")

            logger.info(
                "[LIVE VERIFY %s-ARM SUCCESS] Finished in %.0fms | Output chars: %d",
                arm_label, elapsed_ms, len(resp.text)
            )
            return resp.text.strip()
        except Exception as exc:
            elapsed_ms = (time.monotonic() - t0) * 1000
            logger.error(
                "[LIVE VERIFY %s-ARM ERROR] %s: %s (took %.0fms)",
                arm_label, type(exc).__name__, exc, elapsed_ms
            )
            raise

    def verify(
        self,
        task: str,
        original_text: str,
        minimized_text: str,
        task_output_schema: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        logger.info("[LIVE VERIFIER] Beginning evaluation of task: '%s'", task)
        answer_a = self._ask(original_text, task, arm_label="A-Arm (Original)")
        answer_b = self._ask(minimized_text, task, arm_label="B-Arm (Minimized)")

        preserved, dev, method = _compare_answers(answer_a, answer_b)
        logger.info(
            "[LIVE VERIFIER RESULT] Preserved: %s | Deviation: %.1f%% | Method: %s",
            preserved, dev, method,
        )

        return {
            "answer_original": answer_a,
            "answer_minimized": answer_b,
            "preserved": preserved,
            "deviation_pct": dev,
            "method": method,
            "mode": "live",
        }


# ---------------------------------------------------------------------------
# Public factory
# ---------------------------------------------------------------------------

def get_verifier(live: bool):
    if live:
        return LiveVerifier()
    return MockVerifier()

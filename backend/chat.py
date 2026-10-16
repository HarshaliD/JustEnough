"""
backend/chat.py — JustEnough Multi-Turn Chat Module

Handles chat sessions where the user asks questions on the MINIMIZED document only.
The original (potentially sensitive) document is never passed here.

Privacy contracts:
  - Only minimized_text is sent to Gemini as the document context.
  - History contains only assistant/user turns — no raw PII.
  - Model name from JUSTENOUGH_MODEL env var. Never hard-coded.

Per AGENTS.md: Temperature 0 for deterministic, inspectable outputs.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

logger = logging.getLogger("justenough.chat")

CHAT_SYSTEM_PROMPT = (
    "You are a privacy-safe document assistant.\n"
    "You ONLY have access to a pre-anonymized (minimized) document. "
    "Sensitive fields such as full names, government IDs, and account numbers have already "
    "been removed or masked by the JustEnough system before this document reached you.\n"
    "Answer the user's questions using ONLY this minimized document. "
    "Do not speculate about redacted values. "
    "If the answer requires a field that was removed, say so clearly.\n"
    "Keep answers concise and factual."
)


class MockChatClient:
    """Deterministic mock for infrastructure testing (no API key needed)."""

    CANNED = [
        "Based on the minimized document, your total food expenses were ₹1,100.00.",
        "The document shows salary credited: ₹1,25,000.00. The employer name has been removed as it was not required.",
        "The closing balance shown in the minimized document is ₹1,40,210.00.",
        "That field was removed by the JustEnough minimization pipeline as it was not required for your task.",
        "I can only answer from the minimized document. Please check the detected fields tab for what was kept.",
    ]

    def __init__(self):
        self._turn = 0

    def chat(self, minimized_text: str, history: List[Dict[str, str]], message: str) -> str:
        reply = self.CANNED[self._turn % len(self.CANNED)]
        self._turn += 1
        return reply


import time

class LiveChatClient:
    """Live Gemini chat client on minimized document only."""

    def __init__(self, model_name: Optional[str] = None):
        self.model_name = model_name or os.environ.get(
            "JUSTENOUGH_MODEL", "gemini-3.6-flash"
        )
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("LiveChatClient requires GEMINI_API_KEY.")
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
            "[LIVE CHAT READY] Model: %s | SDK: %s",
            self.model_name,
            self._mode,
        )

    def chat(self, minimized_text: str, history: List[Dict[str, str]], message: str) -> str:
        t0 = time.monotonic()
        logger.info(
            "[LIVE CHAT MESSAGE] Model: %s | History turns: %d | User question: '%s'",
            self.model_name, len(history), message
        )
        document_context = (
            f"<minimized_document>\n{minimized_text}\n</minimized_document>\n\n"
        )

        try:
            if self._mode == "google.genai":
                # With google.genai, build formatted contents
                contents = []
                for turn in history:
                    contents.append(f"{turn.get('role', 'user')}: {turn.get('content', '')}")
                contents.append(f"Document:\n{document_context}\nQuestion:\n{message}")

                resp = self._client.models.generate_content(
                    model=self.model_name,
                    contents="\n\n".join(contents),
                    config={
                        "temperature": 0.0,
                        "system_instruction": CHAT_SYSTEM_PROMPT,
                    },
                )
            else:
                model = self._legacy_genai.GenerativeModel(
                    model_name=self.model_name,
                    system_instruction=CHAT_SYSTEM_PROMPT,
                    generation_config={"temperature": 0.0},
                )
                gemini_history = []
                for turn in history:
                    role = "user" if turn.get("role") == "user" else "model"
                    gemini_history.append({"role": role, "parts": [turn.get("content", "")]})

                if gemini_history:
                    first_content = gemini_history[0].get("parts", [""])[0]
                    gemini_history[0]["parts"] = [document_context + first_content]
                    chat_session = model.start_chat(history=gemini_history)
                    resp = chat_session.send_message(message)
                else:
                    full_message = document_context + message
                    chat_session = model.start_chat(history=[])
                    resp = chat_session.send_message(full_message)

            elapsed_ms = (time.monotonic() - t0) * 1000
            if not resp or not hasattr(resp, "text") or not resp.text:
                logger.error("[LIVE CHAT FAIL] Empty response received in %.0fms", elapsed_ms)
                raise RuntimeError("Gemini returned an empty chat response.")

            reply = resp.text.strip()
            logger.info("[LIVE CHAT SUCCESS] Finished in %.0fms | Reply chars: %d", elapsed_ms, len(reply))
            return reply

        except Exception as exc:
            elapsed_ms = (time.monotonic() - t0) * 1000
            logger.error("[LIVE CHAT ERROR] %s: %s (took %.0fms)", type(exc).__name__, exc, elapsed_ms)
            raise


def get_chat_client(live: bool):
    if live:
        return LiveChatClient()
    return MockChatClient()

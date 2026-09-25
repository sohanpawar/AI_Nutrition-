"""ScopeGuard — code-enforced out-of-scope detection (Milestone 1).

Prompt boundaries are necessary but not sufficient. This module is authoritative:
- pre_check: block calorie/weight targets and medical advice before the LLM runs
- post_check: catch leaks in assistant answer/claims after generation
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.schemas.response import AssistantResponse, DeclineReason

_REFUSAL_ANSWER = (
    "I can't provide calorie targets, weight recommendations, or medical advice. "
    "Please consult a qualified professional such as a registered dietitian or "
    "your healthcare provider for personalized guidance."
)


@dataclass(frozen=True)
class ScopeDecision:
    blocked: bool
    reason: DeclineReason | None = None


def refusal_payload(reason: DeclineReason) -> AssistantResponse:
    return AssistantResponse(
        answer=_REFUSAL_ANSWER,
        claims=[],
        declined=True,
        decline_reason=reason,
    )


def pre_check(user_message: str) -> ScopeDecision:
    """Return blocked=True when the user ask is out of scope."""
    text = user_message.lower().strip()
    if not text:
        return ScopeDecision(blocked=False)

    if _looks_like_calorie_or_weight_target(text):
        return ScopeDecision(blocked=True, reason="calorie_or_weight_target")
    if _looks_like_medical_advice(text):
        return ScopeDecision(blocked=True, reason="medical_advice")
    return ScopeDecision(blocked=False)


def post_check(payload: AssistantResponse) -> ScopeDecision:
    """Scan assistant output for out-of-scope content that leaked past the prompt."""
    if payload.declined:
        return ScopeDecision(blocked=False)

    parts = [payload.answer, *[claim.text for claim in payload.claims]]
    blob = " ".join(parts).lower()

    if _leaks_calorie_or_weight_target(blob):
        return ScopeDecision(blocked=True, reason="calorie_or_weight_target")
    if _leaks_medical_advice(blob):
        return ScopeDecision(blocked=True, reason="medical_advice")
    return ScopeDecision(blocked=False)


# --- heuristics ----------------------------------------------------------------

_DEFINITIONISH = re.compile(
    r"\b(what is|what's|define|definition of|mean by|means)\b",
    re.I,
)

_CALORIE_TARGET = re.compile(
    r"("
    r"\b(calorie|caloric|kcal)\b.{0,40}\b(target|goal|budget|limit|cap|intake|eat|consume|day|daily|plan|number|maintenance)\b"
    r"|"
    r"\b(target|goal|budget|limit|how many|how much|maintenance|number)\b.{0,40}\b(calorie|calories|kcal)s?\b"
    r"|"
    r"\bmaintenance\s+calories\b"
    r"|"
    r"\b\d{3,4}\s*(kcal|calories)\b"
    r"|"
    r"\b(tdee|bmr)\b"
    r"|"
    r"\b(calorie|caloric)\s+(deficit|surplus|cut)\b"
    r")",
    re.I,
)

_WEIGHT_TARGET = re.compile(
    r"("
    r"\b(what|how much)\b.{0,20}\b(should|ought)\b.{0,20}\b(i|we|someone)\b.{0,20}\bweigh\b"
    r"|"
    r"\b(ideal|target|goal)\b.{0,20}\b(weight|bmi)\b"
    r"|"
    r"\bbmi\b.{0,20}\b(goal|target|should)\b"
    r"|"
    r"\b(lose|gain)\b.{0,20}\b\d+\s*(kg|lbs?|pounds)\b"
    r")",
    re.I,
)

_MEDICAL_CONDITION = re.compile(
    r"\b("
    r"diabetes|diabetic|type\s*[12]|prediabet(?:es|ic)|"
    r"hypertension|high blood pressure|"
    r"pcos|thyroid|hypothyroid|hyperthyroid|"
    r"celiac|crohn'?s|ibs|ibd|kidney disease|renal|"
    r"cancer|chemotherapy|chemo|"
    r"pregnant|pregnancy|gestational|"
    r"heart disease|cardiovascular|"
    r"gout|anemia|gerd|ulcer"
    r")\b",
    re.I,
)

_MEDICAL_ADVICE_ASK = re.compile(
    r"("
    r"\b(what|which|how)\b.{0,40}\b(should|do i|can i|to)\b.{0,40}\b(eat|diet|foods?)\b"
    r"|"
    r"\b(diet|foods?|meal plan|nutrition)\b.{0,40}\b(for|with|if i have)\b"
    r"|"
    r"\btreatment\b.{0,20}\b(diet|food)\b"
    r"|"
    r"\b(prescri(?:be|ption)|diagnos(?:e|is)|medical advice)\b"
    r")",
    re.I,
)

_CALORIE_LEAK = re.compile(
    r"("
    r"\b(eat|consume|aim for|stick to|limit yourself to)\b.{0,30}\b\d{3,4}\s*(kcal|calories)\b"
    r"|"
    r"\byour\b.{0,20}\b(daily|calorie)\b.{0,20}\b(target|goal|budget)\b"
    r"|"
    r"\b(calorie|kcal)\s+(target|goal|budget)\b.{0,20}\b\d{3,4}\b"
    r")",
    re.I,
)

_WEIGHT_LEAK = re.compile(
    r"("
    r"\byou should weigh\b"
    r"|"
    r"\bideal weight\b.{0,20}\b\d+\b"
    r"|"
    r"\baim for a bmi\b"
    r")",
    re.I,
)

_MEDICAL_LEAK = re.compile(
    r"("
    r"\bif you have\b.{0,40}\b(diabetes|hypertension|pcos|thyroid|cancer|kidney)\b.{0,40}\b(eat|avoid|diet)\b"
    r"|"
    r"\b(as treatment|to treat|for your condition)\b.{0,40}\b(eat|diet|foods?)\b"
    r"|"
    r"\bpeople with\b.{0,30}\b(diabetes|hypertension|pcos)\b.{0,30}\b(must|should)\b.{0,20}\b(eat|avoid)\b"
    r")",
    re.I,
)


def _looks_like_calorie_or_weight_target(text: str) -> bool:
    # Allow definitional questions like "What is a calorie?" unless they also ask for a target.
    if _DEFINITIONISH.search(text) and not (
        _CALORIE_TARGET.search(text) or _WEIGHT_TARGET.search(text)
    ):
        return False
    return bool(_CALORIE_TARGET.search(text) or _WEIGHT_TARGET.search(text))


def _looks_like_medical_advice(text: str) -> bool:
    if re.search(r"\bmedical advice\b", text, re.I):
        return True
    if _MEDICAL_CONDITION.search(text) and _MEDICAL_ADVICE_ASK.search(text):
        return True
    if _MEDICAL_CONDITION.search(text) and re.search(
        r"\b(diet|foods?|eat|meal plan|nutrition plan)\b", text, re.I
    ):
        return True
    return False


def _leaks_calorie_or_weight_target(text: str) -> bool:
    return bool(_CALORIE_LEAK.search(text) or _WEIGHT_LEAK.search(text))


def _leaks_medical_advice(text: str) -> bool:
    return bool(_MEDICAL_LEAK.search(text))

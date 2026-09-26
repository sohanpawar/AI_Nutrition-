"""LLM structured-output client (OpenAI / Anthropic).

Fail closed: callers must Pydantic-validate; never return free-form prose.
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any

from app.config import get_settings
from app.schemas.response import AssistantResponse

logger = logging.getLogger(__name__)


class LLMError(Exception):
    """Base LLM failure."""


class ProviderUnavailableError(LLMError):
    """Timeout, quota, auth, or network failure talking to the provider."""


class SchemaParseError(LLMError):
    """Provider returned payload that is not valid AssistantResponse JSON."""

    def __init__(self, message: str, *, raw: Any = None) -> None:
        super().__init__(message)
        self.raw = raw


def _assistant_json_schema() -> dict[str, Any]:
    """JSON Schema for structured outputs (strict-friendly)."""
    schema = AssistantResponse.model_json_schema()
    # OpenAI strict mode prefers no leftover $defs ambiguity; keep as-is if present.
    schema["additionalProperties"] = False
    return schema


def complete_structured(
    messages: list[dict[str, str]],
    *,
    temperature: float = 0.3,
) -> AssistantResponse:
    """Call the configured provider and return a validated AssistantResponse.

    Raises:
        ProviderUnavailableError: transport/auth/quota/timeout issues
        SchemaParseError: unparseable or invalid structured payload
    """
    settings = get_settings()
    provider = settings.llm_provider.lower().strip()

    # Milestone 2: retrieval context will be injected into `messages` before this call.
    if provider == "stub":
        return _stub_response(messages)

    attempts = 1 + max(0, settings.llm_max_retries)
    last_error: Exception | None = None

    for attempt in range(attempts):
        try:
            if provider == "openai":
                raw = _call_openai(messages, temperature=temperature)
            elif provider == "anthropic":
                raw = _call_anthropic(messages, temperature=temperature)
            else:
                raise ProviderUnavailableError(
                    f"Unsupported LLM_PROVIDER '{settings.llm_provider}'. "
                    "Use openai, anthropic, or stub."
                )
            return _parse_assistant(raw)
        except SchemaParseError:
            raise
        except ProviderUnavailableError as exc:
            last_error = exc
            if attempt + 1 < attempts:
                time.sleep(0.4 * (attempt + 1))
                continue
            raise
        except Exception as exc:  # noqa: BLE001 - map unknown SDK errors
            last_error = exc
            logger.exception("LLM provider call failed (attempt %s)", attempt + 1)
            if attempt + 1 < attempts:
                time.sleep(0.4 * (attempt + 1))
                continue
            raise ProviderUnavailableError(str(exc)) from exc

    raise ProviderUnavailableError(str(last_error) if last_error else "LLM call failed")


def _parse_assistant(raw: Any) -> AssistantResponse:
    try:
        if isinstance(raw, AssistantResponse):
            return raw
        if isinstance(raw, str):
            data = json.loads(raw)
        elif isinstance(raw, dict):
            data = raw
        else:
            raise SchemaParseError(
                "Unexpected structured output type",
                raw=raw,
            )
        return AssistantResponse.model_validate(data)
    except SchemaParseError:
        raise
    except Exception as exc:
        logger.warning("Schema parse failed; raw=%r", raw)
        raise SchemaParseError("Model output failed schema validation", raw=raw) from exc


def _stub_response(messages: list[dict[str, str]]) -> AssistantResponse:
    """Deterministic local responses when LLM_PROVIDER=stub (no external calls).

    Templates are topic-routed for usable demos. They are intentionally generic and
    must not hardcode gold answers for the frozen eval question strings.
    """
    user_text = next(
        (m["content"] for m in reversed(messages) if m.get("role") == "user"),
        "your question",
    )
    q = user_text.strip().lower()

    def pack(
        answer: str,
        claims: list[str],
    ) -> AssistantResponse:
        return AssistantResponse(
            answer=answer,
            claims=[{"text": c, "source": None} for c in claims],
            declined=False,
            decline_reason=None,
        )

    if any(k in q for k in ("protein", "vegetarian")):
        return pack(
            "Plant-forward and vegetarian patterns can meet protein needs when meals "
            "include legumes, soy foods, dairy or fortified alternatives, eggs, nuts, "
            "seeds, and grains across the day. Needs scale with body size and activity, "
            "so guidance is usually given as a per-kilogram range rather than one fixed "
            "gram total for everyone.",
            [
                "General adult protein guidance is often around 0.8 g per kilogram of body weight per day for healthy adults.",
                "Mixing legumes, grains, soy, dairy or fortified plant milks, eggs, nuts, and seeds helps cover amino acids over the day.",
            ],
        )

    if "iron" in q:
        return pack(
            "Iron needs are higher for many adult women than for adult men because of "
            "menstrual losses. Plant sources include lentils, beans, tofu, pumpkin seeds, "
            "and dark leafy greens; pairing them with vitamin C–rich foods can help "
            "non-heme iron absorption. Exact daily targets vary by age and life stage.",
            [
                "Adult women typically have higher recommended iron intakes than adult men.",
                "Beans, lentils, tofu, seeds, and leafy greens are commonly cited plant iron sources.",
            ],
        )

    if "fiber" in q or "fibre" in q:
        return pack(
            "Most adults fall short of fiber goals. A practical daily target for many "
            "adults is in the mid‑20s to low‑30s of grams, reached through vegetables, "
            "fruit, whole grains, legumes, nuts, and seeds. Increase gradually and drink "
            "enough fluid if you raise fiber quickly.",
            [
                "Common adult fiber goals are often cited around 25–38 g per day depending on sex and reference guidelines.",
                "Whole plant foods—vegetables, fruit, legumes, and whole grains—are primary fiber sources.",
            ],
        )

    if any(k in q for k in ("rice", "leftover", "fridge", "refrigerat", "chicken stay", "spoil")):
        if "rice" in q:
            return pack(
                "Cooked rice should be cooled promptly and refrigerated. Many food-safety "
                "references suggest eating refrigerated leftover rice within about 3–4 days, "
                "and reheating until steaming hot throughout. Do not leave cooked rice at "
                "room temperature for long periods because Bacillus cereus can be a concern.",
                [
                    "Prompt cooling and refrigeration reduce risk with cooked rice leftovers.",
                    "Reheat leftover rice until piping hot all the way through before eating.",
                ],
            )
        if any(k in q for k in ("chicken", "poultry")):
            return pack(
                "Cooked chicken leftovers are generally kept refrigerated and eaten within "
                "about 3–4 days. Store in shallow containers, keep the fridge cold (at or "
                "below 40°F / 4°C), and reheat thoroughly. If it smells off or was left out "
                "for hours, discard it.",
                [
                    "Refrigerated cooked poultry leftovers are commonly advised for use within 3–4 days.",
                    "Keep cold foods at or below 40°F (4°C) and reheat leftovers until steaming hot.",
                ],
            )
        if any(k in q for k in ("beef", "ground")):
            return pack(
                "Raw ground beef is more perishable than whole cuts. In the refrigerator it "
                "is commonly cooked or frozen within 1–2 days of purchase. Keep it cold, "
                "avoid cross-contamination, and cook thoroughly.",
                [
                    "Raw ground meats are typically used or frozen within 1–2 days in the fridge.",
                    "Freezing extends storage time when you cannot cook ground beef promptly.",
                ],
            )
        return pack(
            "For most cooked leftovers, refrigerate within two hours and aim to eat them "
            "within a few days. Keep the refrigerator at or below 40°F (4°C), use sealed "
            "containers, and reheat until steaming hot. When in doubt about time or odor, "
            "throw it out.",
            [
                "The two-hour room-temperature rule is a common leftover safety guideline.",
                "Many cooked leftovers are advised for refrigerated use within 3–4 days.",
            ],
        )

    if any(k in q for k in ("temperature", "internal")) and any(
        k in q for k in ("chicken", "poultry", "safe")
    ):
        return pack(
            "Chicken is generally considered safely cooked when the thickest part reaches "
            "an internal temperature of 165°F (74°C). Use a food thermometer rather than "
            "color alone, and let ground poultry and stuffed birds also hit that mark.",
            [
                "165°F (74°C) is the commonly cited safe minimum internal temperature for poultry.",
                "A thermometer is more reliable than checking juices or meat color alone.",
            ],
        )

    if any(k in q for k in ("boil", "steam", "vitamin c", "nutrient")) and any(
        k in q for k in ("vegetable", "veggie", "cook", "destroy", "reduce")
    ):
        return pack(
            "Water-soluble vitamins such as vitamin C can leach into cooking water and are "
            "heat-sensitive. Boiling often leads to greater losses than steaming because "
            "more vitamin dissolves into discarded water. Shorter cooking and less water "
            "usually help retain more vitamin C.",
            [
                "Vitamin C is water-soluble and can migrate into boiling water.",
                "Steaming typically retains more vitamin C than prolonged boiling with lots of water.",
            ],
        )

    if "sauté" in q or "saute" in q or "sweat" in q:
        return pack(
            "Sautéing cooks food quickly in a small amount of fat over relatively high heat, "
            "aiming for light browning and flavor. Sweating cooks gently over lower heat, "
            "often covered, so vegetables soften and release moisture without much browning. "
            "Sweating builds a mild base; sautéing adds more color and roasted notes.",
            [
                "Sautéing uses higher heat and usually develops some browning.",
                "Sweating uses gentler heat so aromatics soften without significant browning.",
            ],
        )

    if any(k in q for k in ("healthiest food", "objectively the healthiest", "best diet that works for every")):
        return pack(
            "There is no single food or diet that is objectively best for every person. "
            "Nutrient needs, preferences, culture, budget, and medical context differ. "
            "Patterns rich in vegetables, fruits, legumes, whole grains, and varied protein "
            "sources are widely supported, but “one best” rankings oversimplify the evidence.",
            [
                "No single food has been shown to be the healthiest for all people in all contexts.",
                "Dietary guidance usually emphasizes overall patterns rather than one universal best diet.",
            ],
        )

    if "calorie" in q and any(k in q for k in ("what is", "what's", "define", "meaning")):
        return pack(
            "A calorie is a unit of energy. In nutrition labels, “calorie” usually means "
            "kilocalorie (kcal)—the amount of energy food can provide when metabolized. "
            "Carbohydrates, protein, and fat contribute different amounts of energy per gram.",
            [
                "On food labels, calorie almost always means kilocalorie (kcal).",
                "Fat provides more kcal per gram than carbohydrate or protein.",
            ],
        )

    if any(k in q for k in ("egg", "breakfast")):
        return pack(
            "Eggs are a compact source of high-quality protein plus nutrients such as choline "
            "and B vitamins. How they fit into a pattern depends on overall diet and individual "
            "health context; cooking methods (boiling, poaching, scrambling) mainly change "
            "texture and added fat rather than the core protein content.",
            [
                "Eggs provide complete protein and several micronutrients.",
                "Cooking method mainly affects added fat and texture, not the basic protein role of eggs.",
            ],
        )

    snippet = user_text.strip().replace("\n", " ")
    if len(snippet) > 120:
        snippet = snippet[:117] + "..."
    return pack(
        f"On “{snippet}”: food and nutrition answers depend on the specific nutrient, food, "
        "or safety step involved. In general, emphasize variety—vegetables, fruits, legumes, "
        "whole grains, and protein-rich foods—practice safe storage and cooking temperatures, "
        "and treat extreme “one best food/diet” claims cautiously. Ask a more specific follow-up "
        "if you want detail on a nutrient, leftover rule, or cooking method.",
        [
            "Balanced patterns emphasize variety across food groups rather than a single miracle food.",
            "Food-safety practices (cold storage, thorough cooking, prompt refrigeration) prevent many common risks.",
        ],
    )


def _call_openai(messages: list[dict[str, str]], *, temperature: float) -> dict[str, Any]:
    settings = get_settings()
    if not settings.openai_api_key:
        raise ProviderUnavailableError("OPENAI_API_KEY is not configured")

    try:
        from openai import OpenAI
    except ImportError as exc:  # pragma: no cover
        raise ProviderUnavailableError("openai package is not installed") from exc

    client = OpenAI(api_key=settings.openai_api_key, timeout=settings.llm_timeout_seconds)

    # Prefer parse() when available (SDK structured outputs).
    try:
        completion = client.beta.chat.completions.parse(
            model=settings.model_name,
            messages=messages,  # type: ignore[arg-type]
            temperature=temperature,
            response_format=AssistantResponse,
        )
        parsed = completion.choices[0].message.parsed
        if parsed is None:
            refusal = getattr(completion.choices[0].message, "refusal", None)
            raise SchemaParseError(
                "OpenAI returned no parsed content",
                raw={"refusal": refusal, "content": completion.choices[0].message.content},
            )
        return parsed.model_dump()
    except SchemaParseError:
        raise
    except Exception:
        # Fallback: json_schema response_format
        schema = _assistant_json_schema()
        completion = client.chat.completions.create(
            model=settings.model_name,
            messages=messages,  # type: ignore[arg-type]
            temperature=temperature,
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "assistant_response",
                    "strict": True,
                    "schema": schema,
                },
            },
        )
        content = completion.choices[0].message.content
        if not content:
            raise SchemaParseError("OpenAI returned empty content", raw=content)
        return json.loads(content)


def _call_anthropic(messages: list[dict[str, str]], *, temperature: float) -> dict[str, Any]:
    settings = get_settings()
    if not settings.anthropic_api_key:
        raise ProviderUnavailableError("ANTHROPIC_API_KEY is not configured")

    try:
        import anthropic
    except ImportError as exc:  # pragma: no cover
        raise ProviderUnavailableError("anthropic package is not installed") from exc

    client = anthropic.Anthropic(
        api_key=settings.anthropic_api_key,
        timeout=settings.llm_timeout_seconds,
    )

    system = ""
    chat_messages: list[dict[str, str]] = []
    for message in messages:
        if message["role"] == "system":
            system = message["content"]
        else:
            chat_messages.append(
                {"role": message["role"], "content": message["content"]}
            )

    schema = _assistant_json_schema()
    # Anthropic tool_use for structured output.
    tool_name = "nutrition_assistant_response"
    response = client.messages.create(
        model=settings.model_name,
        max_tokens=1024,
        temperature=temperature,
        system=system or "You are a nutrition assistant.",
        messages=chat_messages,  # type: ignore[arg-type]
        tools=[
            {
                "name": tool_name,
                "description": "Return the structured nutrition assistant response.",
                "input_schema": schema,
            }
        ],
        tool_choice={"type": "tool", "name": tool_name},
    )

    for block in response.content:
        if getattr(block, "type", None) == "tool_use" and getattr(block, "name", None) == tool_name:
            return dict(block.input)

    raise SchemaParseError(
        "Anthropic response missing tool_use structured payload",
        raw=response.model_dump() if hasattr(response, "model_dump") else str(response),
    )

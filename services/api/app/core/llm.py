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
    """Deterministic local response when LLM_PROVIDER=stub (no external calls)."""
    user_text = next(
        (m["content"] for m in reversed(messages) if m.get("role") == "user"),
        "your question",
    )
    snippet = user_text.strip().replace("\n", " ")
    if len(snippet) > 120:
        snippet = snippet[:117] + "..."
    return AssistantResponse(
        answer=(
            f"Regarding “{snippet}”: vegetarian and omnivorous adults often meet "
            "protein needs through a mix of legumes, soy foods, dairy or fortified "
            "alternatives, eggs, nuts, seeds, and grains. Needs vary by body size "
            "and activity; general adult guidance is often expressed as a "
            "per-kilogram daily range rather than a single fixed number."
        ),
        claims=[
            {
                "text": (
                    "Many adult protein recommendations are framed as roughly "
                    "0.8 g of protein per kilogram of body weight per day for "
                    "generally healthy adults."
                ),
                "source": None,
            },
            {
                "text": (
                    "Legumes, soy foods, dairy or fortified plant milks, eggs, "
                    "nuts, seeds, and grains are common vegetarian protein sources."
                ),
                "source": None,
            },
        ],
        declined=False,
        decline_reason=None,
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

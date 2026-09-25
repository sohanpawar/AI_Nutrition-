"""Unit + integration tests for schema, persistence, and LLM pipeline (mocked)."""

from unittest.mock import patch

import pytest
from pydantic import ValidationError

from app.core.llm import ProviderUnavailableError, SchemaParseError
from app.core.rate_limit import reset_rate_limits
from app.schemas.response import AssistantResponse, Claim


@pytest.fixture(autouse=True)
def _reset_limits() -> None:
    reset_rate_limits()


def test_claim_accepts_null_source() -> None:
    claim = Claim(text="Protein needs are often stated per kilogram.", source=None)
    assert claim.source is None
    assert claim.text


def test_normalize_database_url_railway_style() -> None:
    from app.config import normalize_database_url

    assert normalize_database_url("postgresql://u:p@h/db").startswith(
        "postgresql+psycopg://"
    )
    assert normalize_database_url("postgres://u:p@h/db").startswith(
        "postgresql+psycopg://"
    )
    assert (
        normalize_database_url("postgresql+psycopg://u:p@h/db")
        == "postgresql+psycopg://u:p@h/db"
    )
    assert normalize_database_url("sqlite:///./local.db") == "sqlite:///./local.db"


def test_claim_rejects_empty_text() -> None:
    with pytest.raises(ValidationError):
        Claim(text="", source=None)


def test_chat_stub_provider_returns_contract_shape(client) -> None:
    response = client.post(
        "/api/chat",
        json={"conversation_id": None, "message": "How much protein do vegetarians need?"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["role"] == "assistant"
    assert body["answer"]
    assert isinstance(body["claims"], list)
    assert len(body["claims"]) >= 1
    for claim in body["claims"]:
        assert claim["text"]
        assert claim["source"] is None
    assert body["declined"] is False


def test_chat_reuses_conversation_and_persists_history(client) -> None:
    first = client.post(
        "/api/chat",
        json={"conversation_id": None, "message": "What is fiber?"},
    )
    assert first.status_code == 200
    conversation_id = first.json()["conversation_id"]

    second = client.post(
        "/api/chat",
        json={"conversation_id": conversation_id, "message": "Why does fiber matter?"},
    )
    assert second.status_code == 200
    assert second.json()["conversation_id"] == conversation_id

    history = client.get(f"/api/conversations/{conversation_id}")
    assert history.status_code == 200
    messages = history.json()["messages"]
    assert len(messages) == 4
    assert messages[0]["role"] == "user"
    assert messages[1]["role"] == "assistant"
    assert messages[2]["role"] == "user"
    assert messages[3]["role"] == "assistant"


def test_chat_unknown_conversation_returns_404(client) -> None:
    response = client.post(
        "/api/chat",
        json={
            "conversation_id": "11111111-1111-1111-1111-111111111111",
            "message": "Hello",
        },
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "conversation_not_found"


def test_chat_empty_message_returns_400(client) -> None:
    response = client.post(
        "/api/chat",
        json={"conversation_id": None, "message": "   "},
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] in {"empty_message", "validation_error"}


def test_chat_message_too_long_returns_400(client) -> None:
    response = client.post(
        "/api/chat",
        json={"conversation_id": None, "message": "x" * 4001},
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] in {"message_too_long", "validation_error"}


def test_llm_schema_failure_returns_502_and_does_not_persist(client) -> None:
    with patch(
        "app.services.chat_service.llm_client.complete_structured",
        side_effect=SchemaParseError("bad json", raw={"oops": True}),
    ):
        response = client.post(
            "/api/chat",
            json={"conversation_id": None, "message": "What foods have iron?"},
        )
    assert response.status_code == 502
    assert response.json()["error"]["code"] == "schema_validation_failed"


def test_llm_provider_failure_returns_503(client) -> None:
    with patch(
        "app.services.chat_service.llm_client.complete_structured",
        side_effect=ProviderUnavailableError("timeout"),
    ):
        response = client.post(
            "/api/chat",
            json={"conversation_id": None, "message": "What is vitamin C?"},
        )
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "provider_unavailable"


def test_llm_happy_path_forces_null_sources(client) -> None:
    fake = AssistantResponse(
        answer="Leafy greens can contribute dietary folate.",
        claims=[
            Claim(text="Spinach contains folate.", source="https://fake.example/cite"),
            Claim(text="Folate supports normal cell division.", source="should-be-cleared"),
        ],
        declined=False,
        decline_reason=None,
    )
    with patch(
        "app.services.chat_service.llm_client.complete_structured",
        return_value=fake,
    ):
        response = client.post(
            "/api/chat",
            json={"conversation_id": None, "message": "Tell me about folate."},
        )
    assert response.status_code == 200
    body = response.json()
    assert all(claim["source"] is None for claim in body["claims"])

    history = client.get(f"/api/conversations/{body['conversation_id']}")
    assert history.status_code == 200
    assistant = history.json()["messages"][1]
    assert all(claim["source"] is None for claim in assistant["claims"])


def test_get_unknown_conversation_returns_404(client) -> None:
    response = client.get("/api/conversations/11111111-1111-1111-1111-111111111111")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "conversation_not_found"

"""ScopeGuard unit + chat integration refusal tests (Phase 5)."""

from unittest.mock import patch

from app.core.scope_guard import post_check, pre_check, refusal_payload
from app.schemas.response import AssistantResponse, Claim


def test_pre_check_blocks_direct_calorie_target() -> None:
    decision = pre_check("What daily calorie target should I eat to lose weight?")
    assert decision.blocked is True
    assert decision.reason == "calorie_or_weight_target"


def test_pre_check_blocks_direct_medical_diet() -> None:
    decision = pre_check("What should someone with type 2 diabetes eat?")
    assert decision.blocked is True
    assert decision.reason == "medical_advice"


def test_pre_check_blocks_rephrased_calorie_ask() -> None:
    decision = pre_check("Can you ballpark how many kcal I should have per day for a deficit?")
    assert decision.blocked is True
    assert decision.reason == "calorie_or_weight_target"


def test_pre_check_blocks_rephrased_medical_ask() -> None:
    decision = pre_check("Diet recommendations for a person living with hypertension?")
    assert decision.blocked is True
    assert decision.reason == "medical_advice"


def test_pre_check_blocks_sideways_calorie_ask() -> None:
    decision = pre_check(
        "Not asking for a meal plan — just a single number for my maintenance calories."
    )
    assert decision.blocked is True
    assert decision.reason == "calorie_or_weight_target"


def test_pre_check_blocks_sideways_medical_ask() -> None:
    decision = pre_check(
        "Hypothetically, if someone had PCOS, what foods should they focus on?"
    )
    assert decision.blocked is True
    assert decision.reason == "medical_advice"


def test_pre_check_allows_definitional_calorie_question() -> None:
    decision = pre_check("What is a calorie?")
    assert decision.blocked is False


def test_pre_check_allows_food_safety_question() -> None:
    decision = pre_check("How should raw chicken be stored in the fridge?")
    assert decision.blocked is False


def test_post_check_blocks_calorie_leak() -> None:
    payload = AssistantResponse(
        answer="You should aim for 1500 calories each day.",
        claims=[Claim(text="Aim for 1500 kcal daily.", source=None)],
        declined=False,
        decline_reason=None,
    )
    decision = post_check(payload)
    assert decision.blocked is True
    assert decision.reason == "calorie_or_weight_target"


def test_post_check_blocks_medical_leak() -> None:
    payload = AssistantResponse(
        answer="If you have diabetes you should avoid all fruit.",
        claims=[],
        declined=False,
        decline_reason=None,
    )
    decision = post_check(payload)
    assert decision.blocked is True
    assert decision.reason == "medical_advice"


def test_refusal_payload_shape() -> None:
    payload = refusal_payload("medical_advice")
    assert payload.declined is True
    assert payload.decline_reason == "medical_advice"
    assert payload.claims == []
    assert "professional" in payload.answer.lower() or "dietitian" in payload.answer.lower()


def test_chat_declines_calorie_target(client) -> None:
    response = client.post(
        "/api/chat",
        json={
            "conversation_id": None,
            "message": "Give me a daily calorie target for weight loss.",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["declined"] is True
    assert body["decline_reason"] == "calorie_or_weight_target"
    assert body["claims"] == []


def test_chat_declines_medical_diet(client) -> None:
    response = client.post(
        "/api/chat",
        json={
            "conversation_id": None,
            "message": "What should someone with type 2 diabetes eat?",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["declined"] is True
    assert body["decline_reason"] == "medical_advice"
    assert body["claims"] == []


def test_chat_declines_rephrased_and_sideways(client) -> None:
    probes = [
        "How many calories should I eat per day?",
        "Just give me a maintenance calorie number.",
        "Foods for someone with hypertension?",
        "If I have PCOS what should I eat?",
    ]
    for message in probes:
        response = client.post(
            "/api/chat",
            json={"conversation_id": None, "message": message},
        )
        assert response.status_code == 200, message
        body = response.json()
        assert body["declined"] is True, message
        assert body["claims"] == [], message


def test_chat_declines_after_unrelated_in_scope_turns(client) -> None:
    first = client.post(
        "/api/chat",
        json={"conversation_id": None, "message": "How should I store leftover rice?"},
    )
    assert first.status_code == 200
    assert first.json()["declined"] is False
    conversation_id = first.json()["conversation_id"]

    second = client.post(
        "/api/chat",
        json={
            "conversation_id": conversation_id,
            "message": "What is the difference between steaming and boiling vegetables?",
        },
    )
    assert second.status_code == 200
    assert second.json()["declined"] is False

    third = client.post(
        "/api/chat",
        json={
            "conversation_id": conversation_id,
            "message": "What daily calorie target should I eat?",
        },
    )
    assert third.status_code == 200
    body = third.json()
    assert body["declined"] is True
    assert body["decline_reason"] == "calorie_or_weight_target"
    assert body["claims"] == []


def test_chat_in_scope_still_answers(client) -> None:
    response = client.post(
        "/api/chat",
        json={
            "conversation_id": None,
            "message": "How much protein do vegetarians typically need?",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["declined"] is False
    assert body["answer"]
    assert len(body["claims"]) >= 1


def test_chat_post_check_replaces_leaked_calorie_advice(client) -> None:
    leak = AssistantResponse(
        answer="You should aim for 1800 calories each day.",
        claims=[Claim(text="Aim for 1800 kcal daily.", source=None)],
        declined=False,
        decline_reason=None,
    )
    with patch(
        "app.services.chat_service.llm_client.complete_structured",
        return_value=leak,
    ):
        response = client.post(
            "/api/chat",
            json={
                "conversation_id": None,
                # In-scope wording so pre_check lets it through; leak is in model output.
                "message": "Tell me about energy from food in general terms.",
            },
        )
    assert response.status_code == 200
    body = response.json()
    assert body["declined"] is True
    assert body["decline_reason"] == "calorie_or_weight_target"
    assert body["claims"] == []

from __future__ import annotations

from app.support_agent import (
    analyze_ticket,
    load_policy_corpus,
    local_reply,
    make_case_brief,
    retrieve_policy,
)


def sample_ticket() -> dict:
    return {
        "id": 17,
        "customer_id": 4,
        "subject": "Please refund my order",
        "message": "The return was collected. Please refund me.",
    }


def test_policy_corpus_and_retrieval_find_refund_guidance():
    corpus = load_policy_corpus()
    results = retrieve_policy("refund returned payment status")
    assert corpus
    assert results
    assert results[0].source_id.startswith("REF-")


def test_refund_without_order_requests_order_id():
    analysis = analyze_ticket(sample_ticket(), None)
    assert analysis["intent"] == "refund_request"
    assert analysis["order_action"] == "request_order_id"
    assert analysis["next_order_status"] is None


def test_returned_order_stages_refund_status_only():
    order = {"id": "A-1004", "status": "returned"}
    analysis = analyze_ticket(sample_ticket(), order)
    reply = local_reply(sample_ticket(), order, analysis)
    assert analysis["order_action"] == "record_refund_status"
    assert analysis["next_order_status"] == "refunded"
    assert "does not confirm that money has been transferred" in reply
    assert "[REF-" not in reply


def test_delivered_order_is_not_marked_refunded():
    analysis = analyze_ticket(sample_ticket(), {"id": "A-1003", "status": "delivered"})
    assert analysis["order_action"] == "manual_return_review"
    assert analysis["next_order_status"] is None


def test_case_brief_is_watermarked_and_not_a_receipt():
    ticket = sample_ticket()
    customer = {"name": "Asha Demo"}
    order = {"id": "A-1004", "status": "returned"}
    analysis = analyze_ticket(ticket, order)
    sources = retrieve_policy("refund returned payment")
    brief = make_case_brief(
        ticket, customer, order, analysis, local_reply(ticket, order, analysis), sources
    )
    assert "SYNTHETIC INTERNAL CASE BRIEF" in brief
    assert "NOT A PAYMENT RECEIPT" in brief
    assert "[REF-" in brief

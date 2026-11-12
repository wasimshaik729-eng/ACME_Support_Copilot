from __future__ import annotations

from typing import Any

from langchain_core.messages import AIMessage, ToolMessage
from langgraph.checkpoint.memory import MemorySaver

from app.agent_graph import (
    SupportAPI,
    build_read_tools,
    build_support_graph,
    resume_approved_action,
    run_investigation,
)


class FakeAPI(SupportAPI):
    def __init__(self, *, order_status: str = "returned", customer_id: int = 1):
        self.ticket = {
            "id": 17,
            "customer_id": 1,
            "order_id": "A-1004",
            "subject": "Please refund my order",
            "message": "My return was collected. Please refund me.",
            "status": "open",
        }
        self.customer = {"id": 1, "name": "Asha Demo"}
        self.order = {
            "id": "A-1004",
            "customer_id": customer_id,
            "status": order_status,
            "product": "Kurtas",
        }
        self.patches: list[tuple[str, dict[str, Any]]] = []

    def get(self, path: str) -> Any:
        if path == "/tickets/17":
            return self.ticket.copy()
        if path == "/customers/1":
            return self.customer.copy()
        if path == "/orders/A-1004":
            return self.order.copy()
        if path == "/customers/1/orders":
            return [self.order.copy()]
        raise RuntimeError(f"Unexpected API read: {path}")

    def patch(self, path: str, payload: dict[str, Any]) -> Any:
        self.patches.append((path, payload.copy()))
        if path == "/orders/A-1004/status":
            self.order["status"] = payload["status"]
            return self.order.copy()
        if path == "/tickets/17/status":
            self.ticket["status"] = payload["status"]
            return self.ticket.copy()
        raise RuntimeError(f"Unexpected API write: {path}")


class FakeToolCallingModel:
    def __init__(self):
        self.calls = 0

    def bind_tools(self, tools):
        self.tools = tools
        return self

    def invoke(self, messages):
        self.calls += 1
        if self.calls == 1:
            return AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "read_order",
                        "args": {"order_id": "A-1004"},
                        "id": "read-order-1",
                        "type": "tool_call",
                    }
                ],
            )
        return AIMessage(
            content="We are verifying the payment record before confirming a refund."
        )


def test_read_tools_are_fixed_and_read_only():
    tools = build_read_tools(FakeAPI())
    names = {item.name for item in tools}
    assert names == {
        "read_ticket",
        "read_customer",
        "read_order",
        "read_customer_orders",
        "retrieve_support_policy",
    }
    assert not any(
        "update" in name or "patch" in name or "refund" in name for name in names
    )


def test_local_rag_investigation_reads_case_and_retrieves_policy():
    api = FakeAPI()
    graph = build_support_graph("http://unused", api=api, checkpointer=MemorySaver())
    result = run_investigation(graph, ticket_id=17, thread_id="local-investigation")

    assert result["ticket"]["id"] == 17
    assert result["customer"]["name"] == "Asha Demo"
    assert result["order"]["status"] == "returned"
    assert result["analysis"]["order_action"] == "record_refund_status"
    assert result["policies"]
    assert any(item["source_id"] == "REF-03" for item in result["policies"])
    assert "does not confirm" in result["draft_reply"]
    assert api.patches == []


def test_model_tool_calls_are_run_through_langgraph_tool_node():
    api = FakeAPI()
    model = FakeToolCallingModel()
    graph = build_support_graph(
        "http://unused", api=api, model=model, checkpointer=MemorySaver()
    )
    result = run_investigation(
        graph,
        ticket_id=17,
        thread_id="model-tool-loop",
        use_external_model=True,
    )

    assert model.calls == 2
    assert result["messages"][-1].content.startswith("We are verifying")
    assert any(isinstance(item, ToolMessage) for item in result["messages"])
    assert api.patches == []


def test_configured_model_is_not_called_without_per_run_opt_in():
    model = FakeToolCallingModel()
    graph = build_support_graph(
        "http://unused", api=FakeAPI(), model=model, checkpointer=MemorySaver()
    )
    run_investigation(graph, ticket_id=17, thread_id="local-default")

    assert model.calls == 0


def test_refund_action_pauses_and_requires_finance_confirmation():
    api = FakeAPI()
    graph = build_support_graph("http://unused", api=api, checkpointer=MemorySaver())
    paused = run_investigation(
        graph,
        ticket_id=17,
        thread_id="refund-approval-required",
        requested_action="record_refund_status",
    )

    assert paused["__interrupt__"]
    assert api.patches == []
    resumed = resume_approved_action(
        graph,
        thread_id="refund-approval-required",
        decision={"approved": True, "finance_verified": False},
    )
    assert resumed["action_result"]["ok"] is False
    assert "Finance verification" in resumed["action_result"]["detail"]
    assert api.patches == []


def test_declined_action_does_not_mutate_api():
    api = FakeAPI()
    graph = build_support_graph("http://unused", api=api, checkpointer=MemorySaver())
    run_investigation(
        graph,
        ticket_id=17,
        thread_id="refund-declined",
        requested_action="record_refund_status",
    )
    resumed = resume_approved_action(
        graph, thread_id="refund-declined", decision={"approved": False}
    )

    assert resumed["action_result"]["ok"] is False
    assert api.patches == []


def test_taking_ticket_requires_approval():
    api = FakeAPI()
    graph = build_support_graph("http://unused", api=api, checkpointer=MemorySaver())
    paused = run_investigation(
        graph,
        ticket_id=17,
        thread_id="take-ticket-approval",
        requested_action="take_ticket",
    )
    assert paused["__interrupt__"]
    assert api.patches == []

    resumed = resume_approved_action(
        graph,
        thread_id="take-ticket-approval",
        decision={"approved": True},
    )
    assert resumed["action_result"]["record"]["status"] == "in_progress"
    assert api.patches == [("/tickets/17/status", {"status": "in_progress"})]


def test_approved_refund_action_changes_workflow_status_only():
    api = FakeAPI()
    graph = build_support_graph("http://unused", api=api, checkpointer=MemorySaver())
    run_investigation(
        graph,
        ticket_id=17,
        thread_id="refund-approved",
        requested_action="record_refund_status",
    )
    resumed = resume_approved_action(
        graph,
        thread_id="refund-approved",
        decision={"approved": True, "finance_verified": True},
    )

    assert resumed["action_result"]["ok"] is True
    assert resumed["action_result"]["record"]["status"] == "refunded"
    assert api.patches == [("/orders/A-1004/status", {"status": "refunded"})]


def test_resolving_ticket_requires_confirmation_reply_was_sent():
    api = FakeAPI()
    graph = build_support_graph("http://unused", api=api, checkpointer=MemorySaver())
    run_investigation(
        graph,
        ticket_id=17,
        thread_id="resolve-needs-confirmation",
        requested_action="resolve_ticket",
    )
    resumed = resume_approved_action(
        graph,
        thread_id="resolve-needs-confirmation",
        decision={"approved": True, "reply_sent": False},
    )

    assert resumed["action_result"]["ok"] is False
    assert "reply was sent" in resumed["action_result"]["detail"]
    assert api.patches == []


def test_ticket_resolution_runs_after_staff_confirms_reply_sent():
    api = FakeAPI()
    graph = build_support_graph("http://unused", api=api, checkpointer=MemorySaver())
    run_investigation(
        graph,
        ticket_id=17,
        thread_id="resolve-approved",
        requested_action="resolve_ticket",
    )
    resumed = resume_approved_action(
        graph,
        thread_id="resolve-approved",
        decision={"approved": True, "reply_sent": True},
    )

    assert resumed["action_result"]["ok"] is True
    assert resumed["action_result"]["record"]["status"] == "resolved"
    assert api.patches == [("/tickets/17/status", {"status": "resolved"})]


def test_order_owned_by_another_customer_is_rejected():
    api = FakeAPI(customer_id=99)
    graph = build_support_graph("http://unused", api=api, checkpointer=MemorySaver())

    try:
        run_investigation(graph, ticket_id=17, thread_id="wrong-customer-order")
    except ValueError as exc:
        assert "does not belong" in str(exc)
    else:
        raise AssertionError("Expected cross-customer order to be rejected")
    assert api.patches == []

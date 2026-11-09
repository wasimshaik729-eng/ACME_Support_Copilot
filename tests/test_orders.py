from __future__ import annotations

from datetime import datetime


def test_list_orders_default_paging(client, seed):
    response = client.get("/orders")
    assert response.status_code == 200
    payload = response.json()
    assert payload["page"] == 1
    assert payload["page_size"] == 20
    assert payload["total"] == len(seed["orders"])
    expected_first = max(
        seed["orders"],
        key=lambda order: (datetime.fromisoformat(order["created_at"]), order["id"]),
    )
    assert payload["items"][0]["id"] == expected_first["id"]


def test_get_order_by_id(client, seed):
    order = seed["orders"][0]
    response = client.get(f"/orders/{order['id']}")
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == order["id"]
    assert body["customer_id"] == order["customer_id"]


def test_get_unknown_order_404(client):
    response = client.get("/orders/A-9999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Order not found"


def test_order_status_transition_valid(client, seed):
    statuses = [
        ("placed", "shipped"),
        ("shipped", "delivered"),
        ("delivered", "returned"),
        ("returned", "refunded"),
    ]
    for current, next_status in statuses:
        order = next(item for item in seed["orders"] if item["status"] == current)
        response = client.patch(
            f"/orders/{order['id']}/status", json={"status": next_status}
        )
        assert response.status_code == 200, response.text
        assert response.json()["status"] == next_status


def test_order_status_transition_same_status_409(client, seed):
    order = next(item for item in seed["orders"] if item["status"] == "placed")
    response = client.patch(f"/orders/{order['id']}/status", json={"status": "placed"})
    assert response.status_code == 409
    assert (
        response.json()["detail"]
        == f"Cannot change status from '{order['status']}' to 'placed'"
    )


def test_order_status_transition_skip_step_409(client, seed):
    order = next(item for item in seed["orders"] if item["status"] == "placed")
    response = client.patch(
        f"/orders/{order['id']}/status", json={"status": "delivered"}
    )
    assert response.status_code == 409
    assert (
        response.json()["detail"]
        == f"Cannot change status from '{order['status']}' to 'delivered'"
    )


def test_order_status_transition_backwards_409(client, seed):
    order = next(item for item in seed["orders"] if item["status"] == "delivered")
    response = client.patch(f"/orders/{order['id']}/status", json={"status": "shipped"})
    assert response.status_code == 409
    assert (
        response.json()["detail"]
        == f"Cannot change status from '{order['status']}' to 'shipped'"
    )


def test_order_status_transition_refunded_409(client, seed):
    order = next(item for item in seed["orders"] if item["status"] == "refunded")
    response = client.patch(f"/orders/{order['id']}/status", json={"status": "shipped"})
    assert response.status_code == 409
    assert (
        response.json()["detail"]
        == f"Cannot change status from '{order['status']}' to 'shipped'"
    )


def test_order_status_unknown_value_422(client):
    response = client.patch("/orders/A-1001/status", json={"status": "unknown"})
    assert response.status_code == 422


def test_order_status_unknown_order_404(client):
    response = client.patch("/orders/A-9999/status", json={"status": "shipped"})
    assert response.status_code == 404
    assert response.json()["detail"] == "Order not found"

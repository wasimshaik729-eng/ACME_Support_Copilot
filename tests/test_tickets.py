from __future__ import annotations


def test_create_ticket_without_order(client):
    payload = {
        "customer_id": 1,
        "subject": "Issue with order",
        "message": "Need help resolving this issue.",
    }
    response = client.post("/tickets", json=payload)
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "open"
    assert body["channel"] == "email"
    assert body["priority"] == "medium"
    assert body["order_id"] is None


def test_create_ticket_with_customer_order(client, seed):
    order = next(item for item in seed["orders"] if item["customer_id"] == 1)
    payload = {
        "customer_id": 1,
        "order_id": order["id"],
        "subject": "Help me",
        "message": "My order arrived damaged.",
    }
    response = client.post("/tickets", json=payload)
    assert response.status_code == 201
    body = response.json()
    assert body["order_id"] == order["id"]
    assert body["customer_id"] == 1


def test_create_ticket_unknown_customer_404(client):
    response = client.post(
        "/tickets",
        json={
            "customer_id": 9999,
            "subject": "Need help",
            "message": "This message is long enough.",
        },
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Customer not found"


def test_create_ticket_unknown_order_404(client):
    response = client.post(
        "/tickets",
        json={
            "customer_id": 1,
            "order_id": "A-9999",
            "subject": "Need help",
            "message": "This message is long enough.",
        },
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Order not found for this customer"


def test_create_ticket_other_customers_order_404(client, seed):
    order = next(item for item in seed["orders"] if item["customer_id"] != 1)
    response = client.post(
        "/tickets",
        json={
            "customer_id": 1,
            "order_id": order["id"],
            "subject": "Need help",
            "message": "This message is long enough.",
        },
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Order not found for this customer"


def test_create_ticket_validation_422(client):
    invalid_cases = [
        {"customer_id": 1, "subject": "A", "message": "valid message"},
        {"customer_id": 1, "subject": "valid", "message": "shor"},
        {
            "customer_id": 1,
            "subject": "valid",
            "message": "valid" * 2000,
            "channel": "invalid",
        },
        {
            "customer_id": 1,
            "subject": "valid",
            "message": "valid",
            "priority": "urgent",
        },
    ]
    for payload in invalid_cases:
        response = client.post("/tickets", json=payload)
        assert response.status_code == 422, response.text


def test_new_ticket_appears_first_for_customer(client):
    payload = {
        "customer_id": 1,
        "subject": "Newest ticket",
        "message": "This ticket should appear first.",
    }
    response = client.post("/tickets", json=payload)
    assert response.status_code == 201
    ticket_id = response.json()["id"]
    list_response = client.get("/tickets?customer_id=1")
    assert list_response.status_code == 200
    payload = list_response.json()
    assert payload["items"][0]["id"] == ticket_id


def test_list_tickets_filters(client, seed):
    status = "open"
    priority = "medium"
    customer_id = 1
    assert client.get(f"/tickets?status={status}").status_code == 200
    assert client.get(f"/tickets?priority={priority}").status_code == 200
    assert client.get(f"/tickets?customer_id={customer_id}").status_code == 200
    response = client.get(
        f"/tickets?status={status}&priority={priority}&customer_id={customer_id}"
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] >= 0


def test_get_ticket(client):
    ticket_id = 1
    response = client.get(f"/tickets/{ticket_id}")
    assert response.status_code == 200
    assert response.json()["id"] == ticket_id


def test_get_unknown_ticket_404(client):
    response = client.get("/tickets/9999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Ticket not found"


def test_ticket_status_changes_until_closed(client):
    payload = {
        "customer_id": 1,
        "subject": "Service ticket",
        "message": "Please update my ticket in steps.",
    }
    create = client.post("/tickets", json=payload)
    ticket_id = create.json()["id"]
    for current, next_status in [
        ("open", "in_progress"),
        ("in_progress", "resolved"),
        ("resolved", "closed"),
    ]:
        response = client.patch(
            f"/tickets/{ticket_id}/status", json={"status": next_status}
        )
        assert response.status_code == 200, response.text
        assert response.json()["status"] == next_status


def test_closed_ticket_reopen_409(client):
    payload = {
        "customer_id": 1,
        "subject": "Closed ticket",
        "message": "This ticket is closed and should reject changes.",
    }
    ticket_id = client.post("/tickets", json=payload).json()["id"]
    client.patch(f"/tickets/{ticket_id}/status", json={"status": "closed"})
    response = client.patch(f"/tickets/{ticket_id}/status", json={"status": "open"})
    assert response.status_code == 409
    assert response.json()["detail"] == "Closed tickets cannot be reopened"

    response = client.patch(f"/tickets/{ticket_id}/status", json={"status": "closed"})
    assert response.status_code == 409
    assert response.json()["detail"] == "Closed tickets cannot be reopened"


def test_ticket_status_unknown_value_422(client):
    response = client.patch("/tickets/1/status", json={"status": "unknown"})
    assert response.status_code == 422


def test_ticket_unknown_ticket_404(client):
    response = client.patch("/tickets/9999/status", json={"status": "open"})
    assert response.status_code == 404
    assert response.json()["detail"] == "Ticket not found"

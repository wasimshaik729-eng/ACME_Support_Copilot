from __future__ import annotations

from datetime import datetime


def test_search_orders_no_filters(client, seed):
    response = client.get("/orders/search")
    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == len(seed["orders"])
    assert payload["page"] == 1
    assert payload["page_size"] == 20


def test_search_orders_filter_status(client, seed):
    status = "refunded"
    expected = len([order for order in seed["orders"] if order["status"] == status])
    response = client.get(f"/orders/search?status={status}")
    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == expected
    assert all(item["status"] == status for item in payload["items"])


def test_search_orders_filter_customer_id(client, seed):
    customer_id = 12
    expected = len(
        [order for order in seed["orders"] if order["customer_id"] == customer_id]
    )
    response = client.get(f"/orders/search?customer_id={customer_id}")
    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == expected
    assert all(item["customer_id"] == customer_id for item in payload["items"])


def test_search_orders_filter_date_from(client, seed):
    date_from = "2025-03-01"
    expected = len(
        [
            order
            for order in seed["orders"]
            if datetime.fromisoformat(order["created_at"])
            >= datetime.fromisoformat(f"{date_from}T00:00:00")
        ]
    )
    response = client.get(f"/orders/search?date_from={date_from}")
    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == expected


def test_search_orders_filter_date_to(client, seed):
    date_to = "2025-03-31"
    expected = len(
        [
            order
            for order in seed["orders"]
            if datetime.fromisoformat(order["created_at"])
            <= datetime.fromisoformat(f"{date_to}T23:59:59.999999")
        ]
    )
    response = client.get(f"/orders/search?date_to={date_to}")
    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == expected


def test_search_orders_combined_filters(client, seed):
    status = "refunded"
    customer_id = 12
    date_from = "2025-03-01"
    date_to = "2025-03-31"
    expected = [
        order
        for order in seed["orders"]
        if order["status"] == status
        and order["customer_id"] == customer_id
        and datetime.fromisoformat(order["created_at"])
        >= datetime.fromisoformat(f"{date_from}T00:00:00")
        and datetime.fromisoformat(order["created_at"])
        <= datetime.fromisoformat(f"{date_to}T23:59:59.999999")
    ]
    response = client.get(
        "/orders/search",
        params={
            "status": status,
            "customer_id": customer_id,
            "date_from": date_from,
            "date_to": date_to,
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == len(expected)
    assert all(item["status"] == status for item in payload["items"])


def test_search_orders_date_range_validation(client):
    response = client.get("/orders/search?date_from=2025-03-31&date_to=2025-03-01")
    assert response.status_code == 422
    assert response.json()["detail"] == "date_from must be on or before date_to"

    response = client.get("/orders/search?status=unknown")
    assert response.status_code == 422

    response = client.get("/orders/search?date_from=not-a-date")
    assert response.status_code == 422


def test_search_orders_newest_first(client, seed):
    response = client.get("/orders/search?customer_id=1")
    assert response.status_code == 200
    payload = response.json()
    expected = sorted(
        [order for order in seed["orders"] if order["customer_id"] == 1],
        key=lambda order: (datetime.fromisoformat(order["created_at"]), order["id"]),
        reverse=True,
    )
    assert payload["items"][0]["id"] == expected[0]["id"]
    assert payload["items"][-1]["id"] == expected[-1]["id"]


def test_search_orders_past_the_end_page(client, seed):
    response = client.get("/orders/search?page=999&page_size=5")
    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == len(seed["orders"])
    assert payload["items"] == []


def test_get_order_by_id_after_search(client):
    response = client.get("/orders/A-1001")
    assert response.status_code == 200
    assert response.json()["id"] == "A-1001"

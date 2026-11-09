from __future__ import annotations

from datetime import datetime


def test_list_customers_default_paging(client, seed):
    response = client.get("/customers")
    assert response.status_code == 200
    payload = response.json()
    assert payload["page"] == 1
    assert payload["page_size"] == 20
    assert payload["total"] == len(seed["customers"])
    assert len(payload["items"]) == 20
    assert payload["items"][0]["id"] == 1


def test_list_customers_page_size_validation(client):
    assert client.get("/customers?page_size=101").status_code == 422
    assert client.get("/customers?page_size=0").status_code == 422
    assert client.get("/customers?page=0").status_code == 422


def test_list_customers_by_city(client, seed):
    city = seed["customers"][0]["city"]
    expected_count = sum(
        1 for customer in seed["customers"] if customer["city"] == city
    )
    response = client.get(f"/customers?city={city}")
    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == expected_count
    assert all(item["city"] == city for item in payload["items"])


def test_get_customer(client, seed):
    customer = seed["customers"][0]
    response = client.get(f"/customers/{customer['id']}")
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == customer["id"]
    assert body["email"] == customer["email"]
    assert datetime.fromisoformat(body["created_at"]) == datetime.fromisoformat(
        customer["created_at"]
    )


def test_get_customer_404(client):
    response = client.get("/customers/9999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Customer not found"


def test_get_customer_orders(client, seed):
    customer_id = 1
    expected_orders = sorted(
        [order for order in seed["orders"] if order["customer_id"] == customer_id],
        key=lambda order: (datetime.fromisoformat(order["created_at"]), order["id"]),
        reverse=True,
    )
    response = client.get(f"/customers/{customer_id}/orders")
    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == len(expected_orders)
    assert payload[0]["id"] == expected_orders[0]["id"]
    assert payload[-1]["id"] == expected_orders[-1]["id"]


def test_get_customer_orders_unknown_customer(client):
    response = client.get("/customers/9999/orders")
    assert response.status_code == 404
    assert response.json()["detail"] == "Customer not found"

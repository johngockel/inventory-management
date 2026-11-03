"""
Tests for restocking purchase order API endpoints.
"""
import pytest

import mock_data


@pytest.fixture(autouse=True)
def clean_purchase_orders():
    """Purchase orders live in a module-level list shared across tests.

    Clear it before and after each test so submissions do not leak between
    tests or change the has_purchase_order flag on /api/backlog.
    """
    mock_data.purchase_orders.clear()
    yield
    mock_data.purchase_orders.clear()


class TestPurchaseOrdersEndpoints:
    """Test suite for restocking purchase order endpoints."""

    def test_create_purchase_order_returns_201(self, client):
        """Test that a valid restocking order is accepted and returned."""
        response = client.post(
            "/api/purchase-orders",
            json={"items": [{"sku": "WDG-001", "quantity": 10}]},
        )
        assert response.status_code == 201

        data = response.json()
        assert data["order_number"].startswith("PO-")
        assert data["status"] == "Submitted"
        assert len(data["items"]) == 1

    def test_create_purchase_order_uses_server_side_unit_cost(self, client):
        """Test that unit cost comes from the forecast, not the client request."""
        response = client.post(
            "/api/purchase-orders",
            json={"items": [{"sku": "WDG-001", "quantity": 10}]},
        )
        line = response.json()["items"][0]
        assert line["unit_cost"] == 42.5
        assert line["line_total"] == 425.0

    def test_create_purchase_order_total_and_lead_time(self, client):
        """Test that total is summed and lead time is the slowest supplier."""
        response = client.post(
            "/api/purchase-orders",
            json={
                "items": [
                    {"sku": "WDG-001", "quantity": 2},  # 14 days, 85.00
                    {"sku": "MTR-304", "quantity": 1},  # 21 days, 189.00
                ]
            },
        )
        data = response.json()
        assert data["total_cost"] == 274.0
        assert data["lead_time_days"] == 21

    def test_create_purchase_order_expected_delivery_date(self, client):
        """Test that expected delivery is submission date plus lead time."""
        from datetime import date, timedelta

        response = client.post(
            "/api/purchase-orders",
            json={"items": [{"sku": "MTR-304", "quantity": 1}]},
        )
        data = response.json()
        expected = date.today() + timedelta(days=21)
        assert data["expected_delivery_date"] == expected.isoformat()

    def test_create_purchase_order_empty_items_rejected(self, client):
        """Test that an order without items is rejected with 400."""
        response = client.post("/api/purchase-orders", json={"items": []})
        assert response.status_code == 400
        assert "at least one item" in response.json()["detail"]

    def test_create_purchase_order_zero_quantity_rejected(self, client):
        """Test that a non-positive quantity is rejected with 400."""
        response = client.post(
            "/api/purchase-orders",
            json={"items": [{"sku": "WDG-001", "quantity": 0}]},
        )
        assert response.status_code == 400
        assert "greater than 0" in response.json()["detail"]

    def test_create_purchase_order_unknown_sku_rejected(self, client):
        """Test that an SKU absent from the forecast is rejected with 400."""
        response = client.post(
            "/api/purchase-orders",
            json={"items": [{"sku": "NOPE-999", "quantity": 1}]},
        )
        assert response.status_code == 400
        assert "Unknown SKU" in response.json()["detail"]

    def test_create_purchase_order_duplicate_sku_rejected(self, client):
        """Test that the same SKU cannot appear twice in one order."""
        response = client.post(
            "/api/purchase-orders",
            json={
                "items": [
                    {"sku": "WDG-001", "quantity": 1},
                    {"sku": "WDG-001", "quantity": 2},
                ]
            },
        )
        assert response.status_code == 400

    def test_get_purchase_orders_lists_submitted_order(self, client):
        """Test that a submitted order appears in the list."""
        created = client.post(
            "/api/purchase-orders",
            json={"items": [{"sku": "GSK-203", "quantity": 5}]},
        ).json()

        response = client.get("/api/purchase-orders")
        assert response.status_code == 200

        data = response.json()
        assert len(data) == 1
        assert data[0]["order_number"] == created["order_number"]

    def test_get_purchase_orders_newest_first(self, client):
        """Test that the list is ordered with the most recent submission first."""
        first = client.post(
            "/api/purchase-orders",
            json={"items": [{"sku": "GSK-203", "quantity": 1}]},
        ).json()
        second = client.post(
            "/api/purchase-orders",
            json={"items": [{"sku": "FLT-405", "quantity": 1}]},
        ).json()

        data = client.get("/api/purchase-orders").json()
        assert [o["order_number"] for o in data] == [
            second["order_number"],
            first["order_number"],
        ]

    def test_backlog_unaffected_by_restocking_orders(self, client):
        """Test that restocking orders do not mark backlog items as having a PO."""
        client.post(
            "/api/purchase-orders",
            json={"items": [{"sku": "GSK-203", "quantity": 1}]},
        )
        response = client.get("/api/backlog")
        assert response.status_code == 200
        for item in response.json():
            assert item["has_purchase_order"] is False

"""
Tests for report API endpoints (quarterly and monthly trends).

Both endpoints must honour the global filter bar (warehouse, category,
status, month), so the same filters applied to /api/orders must be
reflected in the aggregated report numbers.
"""
import pytest

import main


class TestReportsEndpoints:
    """Test suite for the report endpoints."""

    def test_quarterly_report_structure(self, client):
        """Each quarter row exposes the fields the Reports page renders."""
        response = client.get("/api/reports/quarterly")
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0
        for row in data:
            for field in ["quarter", "total_orders", "total_revenue",
                          "avg_order_value", "fulfillment_rate"]:
                assert field in row

    def test_monthly_trends_structure(self, client):
        """Each month row exposes the fields the Reports page renders."""
        response = client.get("/api/reports/monthly-trends")
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0
        for row in data:
            for field in ["month", "order_count", "revenue", "delivered_count"]:
                assert field in row

    def test_quarterly_report_respects_warehouse_filter(self, client):
        """Quarterly totals for one warehouse must equal the filtered orders."""
        response = client.get("/api/reports/quarterly?warehouse=Tokyo")
        assert response.status_code == 200

        expected_orders = [o for o in main.orders if o["warehouse"] == "Tokyo"]
        reported_orders = sum(row["total_orders"] for row in response.json())
        assert reported_orders == len(expected_orders)

    def test_monthly_trends_respect_status_filter(self, client):
        """Monthly order counts must match the delivered-only subset."""
        response = client.get("/api/reports/monthly-trends?status=Delivered")
        assert response.status_code == 200

        expected = [o for o in main.orders if o["status"].lower() == "delivered"]
        reported = sum(row["order_count"] for row in response.json())
        assert reported == len(expected)

    def test_monthly_trends_respect_month_filter(self, client):
        """Filtering to a single month returns only that month."""
        response = client.get("/api/reports/monthly-trends?month=2025-03")
        assert response.status_code == 200

        data = response.json()
        assert len(data) == 1
        assert data[0]["month"] == "2025-03"

    def test_quarterly_report_respects_quarter_filter(self, client):
        """A quarter filter restricts the quarterly report to that quarter."""
        response = client.get("/api/reports/quarterly?month=Q2-2025")
        assert response.status_code == 200

        data = response.json()
        assert [row["quarter"] for row in data] == ["Q2-2025"]

    def test_reports_match_orders_totals_with_all_filters(self, client):
        """Combined filters yield the same revenue as the orders endpoint."""
        params = "warehouse=London&category=Sensors&status=Delivered"
        orders_response = client.get(f"/api/orders?{params}")
        report_response = client.get(f"/api/reports/monthly-trends?{params}")
        assert orders_response.status_code == 200
        assert report_response.status_code == 200

        expected_revenue = sum(o["total_value"] for o in orders_response.json())
        reported_revenue = sum(row["revenue"] for row in report_response.json())
        assert abs(reported_revenue - expected_revenue) < 0.01

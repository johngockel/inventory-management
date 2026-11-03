"""
Tests for the in-memory task endpoints used by the TasksModal.
"""
import pytest

import main


@pytest.fixture(autouse=True)
def clean_tasks():
    """Tasks live in a module-level list shared across tests.

    Clear it before and after each test so tasks created in one test do not
    show up in another test's GET response.
    """
    main.tasks.clear()
    yield
    main.tasks.clear()


class TestTasksEndpoints:
    """Test suite for the task endpoints."""

    def test_get_tasks_empty_returns_empty_list(self, client):
        response = client.get("/api/tasks")
        assert response.status_code == 200
        assert response.json() == []

    def test_create_task_returns_201_with_pending_status(self, client):
        response = client.post(
            "/api/tasks",
            json={"title": "Check stock", "priority": "high", "dueDate": "2026-12-01"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Check stock"
        assert data["priority"] == "high"
        assert data["dueDate"] == "2026-12-01"
        assert data["status"] == "pending"
        assert isinstance(data["id"], int)

    def test_create_task_trims_title(self, client):
        response = client.post(
            "/api/tasks",
            json={"title": "  Trimmed  ", "priority": "low", "dueDate": "2026-12-01"},
        )
        assert response.json()["title"] == "Trimmed"

    def test_create_task_rejects_blank_title(self, client):
        response = client.post(
            "/api/tasks",
            json={"title": "   ", "priority": "low", "dueDate": "2026-12-01"},
        )
        assert response.status_code == 400

    def test_create_task_rejects_unknown_priority(self, client):
        response = client.post(
            "/api/tasks",
            json={"title": "Bad", "priority": "urgent", "dueDate": "2026-12-01"},
        )
        assert response.status_code == 400

    def test_create_task_defaults_priority_to_medium(self, client):
        response = client.post(
            "/api/tasks",
            json={"title": "Default", "dueDate": "2026-12-01"},
        )
        assert response.status_code == 201
        assert response.json()["priority"] == "medium"

    def test_get_tasks_returns_newest_first(self, client):
        first = client.post(
            "/api/tasks",
            json={"title": "First", "priority": "low", "dueDate": "2026-12-01"},
        ).json()
        second = client.post(
            "/api/tasks",
            json={"title": "Second", "priority": "low", "dueDate": "2026-12-02"},
        ).json()

        titles = [t["id"] for t in client.get("/api/tasks").json()]
        assert titles == [second["id"], first["id"]]

    def test_patch_toggles_status_both_ways(self, client):
        task = client.post(
            "/api/tasks",
            json={"title": "Toggle", "priority": "low", "dueDate": "2026-12-01"},
        ).json()

        completed = client.patch(f"/api/tasks/{task['id']}")
        assert completed.status_code == 200
        assert completed.json()["status"] == "completed"

        pending = client.patch(f"/api/tasks/{task['id']}")
        assert pending.json()["status"] == "pending"

    def test_patch_unknown_task_returns_404(self, client):
        response = client.patch("/api/tasks/999999")
        assert response.status_code == 404

    def test_delete_removes_task(self, client):
        task = client.post(
            "/api/tasks",
            json={"title": "Delete me", "priority": "low", "dueDate": "2026-12-01"},
        ).json()

        response = client.delete(f"/api/tasks/{task['id']}")
        assert response.status_code == 200
        assert client.get("/api/tasks").json() == []

    def test_delete_unknown_task_returns_404(self, client):
        response = client.delete("/api/tasks/999999")
        assert response.status_code == 404

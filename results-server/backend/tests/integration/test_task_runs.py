"""Integration tests for task run submission and querying."""

import pytest
from uuid import uuid4


class TestHealthEndpoint:
    """Tests for health check endpoint."""

    @pytest.mark.asyncio
    async def test_health_check(self, client):
        """Test health endpoint returns ok status."""
        response = await client.get("/api/v1/health")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data
        assert "app_name" in data


class TestTaskRunSubmission:
    """Tests for task run submission endpoint."""

    @pytest.mark.asyncio
    async def test_submit_task_run(self, client, sample_task_submission):
        """Test submitting a complete task run."""
        response = await client.post(
            "/api/v1/task_runs",
            json=sample_task_submission,
        )

        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "ok"
        assert data["duplicate"] is False
        assert "task_run_id" in data

    @pytest.mark.asyncio
    async def test_submit_duplicate_task_run(self, client, sample_task_submission):
        """Test that duplicate submissions are handled correctly."""
        # First submission
        response1 = await client.post(
            "/api/v1/task_runs",
            json=sample_task_submission,
        )
        assert response1.status_code == 201
        task_run_id = response1.json()["task_run_id"]

        # Duplicate submission with same task_uuid
        response2 = await client.post(
            "/api/v1/task_runs",
            json=sample_task_submission,
        )
        assert response2.status_code == 201
        data = response2.json()
        assert data["duplicate"] is True
        assert data["task_run_id"] == task_run_id

    @pytest.mark.asyncio
    async def test_submit_minimal_task_run(self, client):
        """Test submitting a minimal task run."""
        minimal_submission = {
            "client": {
                "benchpro_version": "2.0.0",
                "task_uuid": str(uuid4()),
            },
            "task": {
                "label": "minimal_test",
                "system": "test_system",
                "status": "completed",
                "submit_time": "2025-12-01T12:00:00Z",
            },
        }

        response = await client.post(
            "/api/v1/task_runs",
            json=minimal_submission,
        )

        assert response.status_code == 201
        assert response.json()["status"] == "ok"


class TestTaskRunQueries:
    """Tests for task run query endpoints."""

    @pytest.mark.asyncio
    async def test_list_task_runs_empty(self, client):
        """Test listing task runs when none exist."""
        response = await client.get("/api/v1/task_runs")
        assert response.status_code == 200

        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0
        assert data["page"] == 1

    @pytest.mark.asyncio
    async def test_list_task_runs_with_data(self, client, sample_task_submission):
        """Test listing task runs after submission."""
        # Submit a task
        await client.post("/api/v1/task_runs", json=sample_task_submission)

        # List tasks
        response = await client.get("/api/v1/task_runs")
        assert response.status_code == 200

        data = response.json()
        assert data["total"] == 1
        assert len(data["items"]) == 1
        assert data["items"][0]["label"] == "test_benchmark"

    @pytest.mark.asyncio
    async def test_get_task_run_detail(self, client, sample_task_submission):
        """Test getting detailed task run information."""
        # Submit a task
        submit_response = await client.post(
            "/api/v1/task_runs", json=sample_task_submission
        )
        task_run_id = submit_response.json()["task_run_id"]

        # Get details
        response = await client.get(f"/api/v1/task_runs/{task_run_id}")
        assert response.status_code == 200

        data = response.json()
        assert data["id"] == task_run_id
        assert data["label"] == "test_benchmark"
        assert data["system"] == "test_system"
        assert len(data["figures_of_merit"]) == 2

        # Check FoMs
        fom_names = [f["name"] for f in data["figures_of_merit"]]
        assert "performance" in fom_names
        assert "memory" in fom_names

    @pytest.mark.asyncio
    async def test_get_task_run_not_found(self, client):
        """Test getting non-existent task run returns 404."""
        response = await client.get("/api/v1/task_runs/99999")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_filter_by_system(self, client, sample_task_submission):
        """Test filtering task runs by system."""
        # Submit task
        await client.post("/api/v1/task_runs", json=sample_task_submission)

        # Filter by correct system
        response = await client.get("/api/v1/task_runs?system=test_system")
        assert response.status_code == 200
        assert response.json()["total"] == 1

        # Filter by wrong system
        response = await client.get("/api/v1/task_runs?system=other_system")
        assert response.status_code == 200
        assert response.json()["total"] == 0


class TestProvenanceEndpoints:
    """Tests for provenance endpoints."""

    @pytest.mark.asyncio
    async def test_get_provenance(self, client, sample_task_submission):
        """Test getting provenance for a task run."""
        # Submit task
        submit_response = await client.post(
            "/api/v1/task_runs", json=sample_task_submission
        )
        task_run_id = submit_response.json()["task_run_id"]

        # Get provenance
        response = await client.get(f"/api/v1/task_runs/{task_run_id}/provenance")
        assert response.status_code == 200

        data = response.json()
        assert "metadata" in data
        assert "artifacts" in data

        # Check metadata
        metadata_keys = [m["key"] for m in data["metadata"]]
        assert "git_commit" in metadata_keys
        assert "scheduler" in metadata_keys


class TestApiTokenEndpoints:
    """Tests for API token management endpoints."""

    @pytest.mark.asyncio
    async def test_list_tokens_empty(self, client):
        """Test listing tokens when none exist."""
        response = await client.get("/api/v1/api_tokens")
        assert response.status_code == 200
        assert response.json()["tokens"] == []

    @pytest.mark.asyncio
    async def test_create_token(self, client):
        """Test creating a new API token."""
        response = await client.post(
            "/api/v1/api_tokens",
            json={"name": "Test Token"},
        )
        assert response.status_code == 201

        data = response.json()
        assert data["name"] == "Test Token"
        assert "token" in data
        assert data["token"].startswith("bp_")

    @pytest.mark.asyncio
    async def test_revoke_token(self, client):
        """Test revoking an API token."""
        # Create token
        create_response = await client.post(
            "/api/v1/api_tokens",
            json={"name": "Revoke Test"},
        )
        token_id = create_response.json()["id"]

        # Revoke token
        response = await client.delete(f"/api/v1/api_tokens/{token_id}")
        assert response.status_code == 204

        # Verify it's gone from list
        list_response = await client.get("/api/v1/api_tokens")
        tokens = list_response.json()["tokens"]
        assert len(tokens) == 0 or all(t["id"] != token_id for t in tokens)


class TestSavedViewsEndpoints:
    """Tests for saved views endpoints."""

    @pytest.mark.asyncio
    async def test_create_saved_view(self, client):
        """Test creating a saved view."""
        response = await client.post(
            "/api/v1/saved_views",
            json={
                "name": "Test View",
                "description": "A test saved view",
                "visibility": "private",
                "config": {
                    "filters": {"system": ["test_system"]},
                    "primary_fom_name": "performance",
                },
            },
        )
        assert response.status_code == 201

        data = response.json()
        assert data["name"] == "Test View"
        assert data["visibility"] == "private"

    @pytest.mark.asyncio
    async def test_list_saved_views(self, client):
        """Test listing saved views."""
        # Create a view
        await client.post(
            "/api/v1/saved_views",
            json={
                "name": "List Test",
                "visibility": "public",
                "config": {},
            },
        )

        # List views
        response = await client.get("/api/v1/saved_views")
        assert response.status_code == 200

        data = response.json()
        assert len(data) >= 1
        assert any(v["name"] == "List Test" for v in data)


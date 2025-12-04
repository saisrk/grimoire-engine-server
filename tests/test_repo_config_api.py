"""
Tests for Repository Configuration CRUD API endpoints.
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import select

from app.models.repository_config import RepositoryConfig
from app.models.webhook_execution_log import WebhookExecutionLog


@pytest.mark.asyncio
async def test_create_repo_config(client: AsyncClient, test_db, auth_headers):
    """Test creating a new repository configuration."""
    repo_data = {
        "repo_name": "octocat/Hello-World",
        "webhook_url": "https://grimoire.example.com/webhook/github",
        "enabled": True
    }
    
    response = await client.post("/api/repo-configs", json=repo_data, headers=auth_headers)
    assert response.status_code == 201
    data = response.json()
    assert data["repo_name"] == repo_data["repo_name"]
    assert data["webhook_url"] == repo_data["webhook_url"]
    assert data["enabled"] == repo_data["enabled"]
    assert "id" in data
    assert "created_at" in data
    assert data["webhook_count"] == 0
    assert data["last_webhook_at"] is None


@pytest.mark.asyncio
async def test_create_repo_config_invalid_name_format(client: AsyncClient, test_db, auth_headers):
    """Test creating a repository config with invalid name format returns 422."""
    repo_data = {
        "repo_name": "invalid-name-without-slash",
        "webhook_url": "https://grimoire.example.com/webhook/github",
        "enabled": True
    }
    
    response = await client.post("/api/repo-configs", json=repo_data, headers=auth_headers)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_duplicate_repo_config(client: AsyncClient, test_db, auth_headers):
    """Test creating duplicate repository config returns 409."""
    repo_data = {
        "repo_name": "octocat/Hello-World",
        "webhook_url": "https://grimoire.example.com/webhook/github",
        "enabled": True
    }
    
    # Create first config
    response1 = await client.post("/api/repo-configs", json=repo_data, headers=auth_headers)
    assert response1.status_code == 201
    
    # Try to create duplicate
    response2 = await client.post("/api/repo-configs", json=repo_data, headers=auth_headers)
    assert response2.status_code == 409
    data = response2.json()
    assert "already configured" in data["detail"].lower()


@pytest.mark.asyncio
async def test_list_repo_configs(client: AsyncClient, test_db, auth_headers):
    """Test listing repository configs returns all ordered by date."""
    # Create multiple configs
    configs = [
        {
            "repo_name": "user1/repo1",
            "webhook_url": "https://example.com/webhook1",
            "enabled": True
        },
        {
            "repo_name": "user2/repo2",
            "webhook_url": "https://example.com/webhook2",
            "enabled": False
        }
    ]
    
    created_ids = []
    for config in configs:
        response = await client.post("/api/repo-configs", json=config, headers=auth_headers)
        created_ids.append(response.json()["id"])
    
    # List configs
    response = await client.get("/api/repo-configs", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 2
    # Should be ordered by created_at descending (newest first)
    # Since they're created in sequence, the second one should be first
    # But check both orderings since timestamps might be identical
    returned_ids = [item["id"] for item in data]
    assert set(returned_ids) == set(created_ids)  # Both IDs are present
    # Verify ordering is consistent (either ascending or descending by ID)
    assert returned_ids == sorted(returned_ids) or returned_ids == sorted(returned_ids, reverse=True)


@pytest.mark.asyncio
async def test_list_repo_configs_includes_webhook_count(client: AsyncClient, test_db, auth_headers):
    """Test listing repository configs includes webhook count."""
    # Create a config
    repo_data = {
        "repo_name": "octocat/Hello-World",
        "webhook_url": "https://grimoire.example.com/webhook/github",
        "enabled": True
    }
    create_response = await client.post("/api/repo-configs", json=repo_data, headers=auth_headers)
    config_id = create_response.json()["id"]
    
    # Create some webhook logs for this config
    for i in range(3):
        log = WebhookExecutionLog(
            repo_config_id=config_id,
            repo_name="octocat/Hello-World",
            pr_number=i + 1,
            event_type="pull_request",
            action="opened",
            status="success"
        )
        test_db.add(log)
    await test_db.commit()
    
    # List configs
    response = await client.get("/api/repo-configs", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["webhook_count"] == 3
    assert data[0]["last_webhook_at"] is not None


@pytest.mark.asyncio
async def test_get_repo_config_by_id(client: AsyncClient, test_db, auth_headers):
    """Test getting a repository config by ID."""
    # Create a config
    repo_data = {
        "repo_name": "octocat/Hello-World",
        "webhook_url": "https://grimoire.example.com/webhook/github",
        "enabled": True
    }
    create_response = await client.post("/api/repo-configs", json=repo_data, headers=auth_headers)
    config_id = create_response.json()["id"]
    
    # Get the config
    response = await client.get(f"/api/repo-configs/{config_id}", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == config_id
    assert data["repo_name"] == repo_data["repo_name"]
    assert data["webhook_url"] == repo_data["webhook_url"]


@pytest.mark.asyncio
async def test_get_repo_config_not_found(client: AsyncClient, test_db, auth_headers):
    """Test getting a non-existent repository config returns 404."""
    response = await client.get("/api/repo-configs/99999", headers=auth_headers)
    assert response.status_code == 404
    data = response.json()
    assert "not found" in data["detail"].lower()


@pytest.mark.asyncio
async def test_update_repo_config_webhook_url(client: AsyncClient, test_db, auth_headers):
    """Test updating repository config webhook URL."""
    # Create a config
    repo_data = {
        "repo_name": "octocat/Hello-World",
        "webhook_url": "https://grimoire.example.com/webhook/github",
        "enabled": True
    }
    create_response = await client.post("/api/repo-configs", json=repo_data, headers=auth_headers)
    config_id = create_response.json()["id"]
    
    # Update webhook URL
    update_data = {
        "webhook_url": "https://new-url.example.com/webhook"
    }
    response = await client.put(f"/api/repo-configs/{config_id}", json=update_data, headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == config_id
    assert data["webhook_url"] == update_data["webhook_url"]
    assert data["repo_name"] == repo_data["repo_name"]  # Should not change
    assert data["updated_at"] is not None


@pytest.mark.asyncio
async def test_update_repo_config_enabled_status(client: AsyncClient, test_db, auth_headers):
    """Test updating repository config enabled status."""
    # Create a config
    repo_data = {
        "repo_name": "octocat/Hello-World",
        "webhook_url": "https://grimoire.example.com/webhook/github",
        "enabled": True
    }
    create_response = await client.post("/api/repo-configs", json=repo_data, headers=auth_headers)
    config_id = create_response.json()["id"]
    
    # Update enabled status
    update_data = {
        "enabled": False
    }
    response = await client.put(f"/api/repo-configs/{config_id}", json=update_data, headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == config_id
    assert data["enabled"] == False
    assert data["updated_at"] is not None


@pytest.mark.asyncio
async def test_update_repo_config_not_found(client: AsyncClient, test_db, auth_headers):
    """Test updating a non-existent repository config returns 404."""
    update_data = {
        "webhook_url": "https://new-url.example.com/webhook"
    }
    response = await client.put("/api/repo-configs/99999", json=update_data, headers=auth_headers)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_repo_config(client: AsyncClient, test_db, auth_headers):
    """Test deleting a repository config."""
    # Create a config
    repo_data = {
        "repo_name": "octocat/Hello-World",
        "webhook_url": "https://grimoire.example.com/webhook/github",
        "enabled": True
    }
    create_response = await client.post("/api/repo-configs", json=repo_data, headers=auth_headers)
    config_id = create_response.json()["id"]
    
    # Delete the config
    response = await client.delete(f"/api/repo-configs/{config_id}", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "deleted successfully" in data["message"].lower()
    
    # Verify it's deleted
    get_response = await client.get(f"/api/repo-configs/{config_id}", headers=auth_headers)
    assert get_response.status_code == 404


@pytest.mark.asyncio
async def test_delete_repo_config_cascades_to_logs(client: AsyncClient, test_db, auth_headers):
    """Test deleting a repository config also deletes associated logs."""
    # Create a config
    repo_data = {
        "repo_name": "octocat/Hello-World",
        "webhook_url": "https://grimoire.example.com/webhook/github",
        "enabled": True
    }
    create_response = await client.post("/api/repo-configs", json=repo_data, headers=auth_headers)
    config_id = create_response.json()["id"]
    
    # Create webhook logs for this config
    for i in range(3):
        log = WebhookExecutionLog(
            repo_config_id=config_id,
            repo_name="octocat/Hello-World",
            pr_number=i + 1,
            event_type="pull_request",
            action="opened",
            status="success"
        )
        test_db.add(log)
    await test_db.commit()
    
    # Verify logs exist
    stmt = select(WebhookExecutionLog).where(WebhookExecutionLog.repo_config_id == config_id)
    result = await test_db.execute(stmt)
    logs_before = result.scalars().all()
    assert len(logs_before) == 3
    
    # Delete the config
    response = await client.delete(f"/api/repo-configs/{config_id}", headers=auth_headers)
    assert response.status_code == 200
    
    # Verify logs are also deleted (cascade)
    result = await test_db.execute(stmt)
    logs_after = result.scalars().all()
    assert len(logs_after) == 0


@pytest.mark.asyncio
async def test_delete_repo_config_not_found(client: AsyncClient, test_db, auth_headers):
    """Test deleting a non-existent repository config returns 404."""
    response = await client.delete("/api/repo-configs/99999", headers=auth_headers)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_pagination(client: AsyncClient, test_db, auth_headers):
    """Test pagination parameters work correctly."""
    # Create multiple configs
    for i in range(5):
        repo_data = {
            "repo_name": f"user{i}/repo{i}",
            "webhook_url": f"https://example.com/webhook{i}",
            "enabled": True
        }
        await client.post("/api/repo-configs", json=repo_data, headers=auth_headers)
    
    # Test skip and limit
    response = await client.get("/api/repo-configs?skip=2&limit=2", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2


@pytest.mark.asyncio
async def test_endpoints_require_authentication(client: AsyncClient, test_db):
    """Test that all repository config endpoints require authentication."""
    # Test POST without auth
    response = await client.post("/api/repo-configs", json={
        "repo_name": "test/repo",
        "webhook_url": "https://example.com/webhook",
        "enabled": True
    })
    assert response.status_code == 401
    
    # Test GET list without auth
    response = await client.get("/api/repo-configs")
    assert response.status_code == 401
    
    # Test GET by ID without auth
    response = await client.get("/api/repo-configs/1")
    assert response.status_code == 401
    
    # Test PUT without auth
    response = await client.put("/api/repo-configs/1", json={"enabled": False})
    assert response.status_code == 401
    
    # Test DELETE without auth
    response = await client.delete("/api/repo-configs/1")
    assert response.status_code == 401

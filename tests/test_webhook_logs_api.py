"""
Tests for webhook logs API endpoints.

Tests the webhook logs API including listing logs with filters,
getting specific logs, and getting logs by repository.
"""

import json
from datetime import datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.models.repository_config import RepositoryConfig
from app.models.webhook_execution_log import WebhookExecutionLog


@pytest.mark.asyncio
async def test_list_webhook_logs(client: AsyncClient, auth_headers: dict, db_session):
    """Test listing all webhook logs."""
    # Create a repository config
    repo_config = RepositoryConfig(
        repo_name="test/repo",
        webhook_url="https://example.com/webhook",
        enabled=True
    )
    db_session.add(repo_config)
    await db_session.commit()
    await db_session.refresh(repo_config)
    
    # Create webhook logs
    log1 = WebhookExecutionLog(
        repo_config_id=repo_config.id,
        repo_name="test/repo",
        pr_number=1,
        event_type="pull_request",
        action="opened",
        status="success",
        matched_spell_ids=json.dumps([1, 2, 3]),
        execution_duration_ms=100
    )
    log2 = WebhookExecutionLog(
        repo_config_id=repo_config.id,
        repo_name="test/repo",
        pr_number=2,
        event_type="pull_request",
        action="synchronize",
        status="error",
        error_message="Test error",
        execution_duration_ms=200
    )
    db_session.add_all([log1, log2])
    await db_session.commit()
    
    # List all logs
    response = await client.get("/api/webhook-logs", headers=auth_headers)
    assert response.status_code == 200
    
    logs = response.json()
    assert len(logs) >= 2
    
    # Verify logs are ordered by executed_at descending
    assert logs[0]["id"] == log2.id
    assert logs[1]["id"] == log1.id


@pytest.mark.asyncio
async def test_list_webhook_logs_with_status_filter(client: AsyncClient, auth_headers: dict, db_session):
    """Test listing webhook logs with status filter."""
    # Create a repository config
    repo_config = RepositoryConfig(
        repo_name="test/filter-repo",
        webhook_url="https://example.com/webhook",
        enabled=True
    )
    db_session.add(repo_config)
    await db_session.commit()
    await db_session.refresh(repo_config)
    
    # Create logs with different statuses
    success_log = WebhookExecutionLog(
        repo_config_id=repo_config.id,
        repo_name="test/filter-repo",
        pr_number=1,
        event_type="pull_request",
        action="opened",
        status="success",
        execution_duration_ms=100
    )
    error_log = WebhookExecutionLog(
        repo_config_id=repo_config.id,
        repo_name="test/filter-repo",
        pr_number=2,
        event_type="pull_request",
        action="opened",
        status="error",
        error_message="Test error",
        execution_duration_ms=200
    )
    db_session.add_all([success_log, error_log])
    await db_session.commit()
    
    # Filter by success status
    response = await client.get("/api/webhook-logs?status=success", headers=auth_headers)
    assert response.status_code == 200
    
    logs = response.json()
    assert all(log["status"] == "success" for log in logs)
    
    # Filter by error status
    response = await client.get("/api/webhook-logs?status=error", headers=auth_headers)
    assert response.status_code == 200
    
    logs = response.json()
    assert all(log["status"] == "error" for log in logs)


@pytest.mark.asyncio
async def test_list_webhook_logs_with_date_filter(client: AsyncClient, auth_headers: dict, db_session):
    """Test listing webhook logs with date range filter."""
    # Create a repository config
    repo_config = RepositoryConfig(
        repo_name="test/date-repo",
        webhook_url="https://example.com/webhook",
        enabled=True
    )
    db_session.add(repo_config)
    await db_session.commit()
    await db_session.refresh(repo_config)
    
    # Create a log
    log = WebhookExecutionLog(
        repo_config_id=repo_config.id,
        repo_name="test/date-repo",
        pr_number=1,
        event_type="pull_request",
        action="opened",
        status="success",
        execution_duration_ms=100
    )
    db_session.add(log)
    await db_session.commit()
    await db_session.refresh(log)
    
    # Filter with date range that includes the log
    start_date = (datetime.utcnow() - timedelta(hours=1)).isoformat()
    end_date = (datetime.utcnow() + timedelta(hours=1)).isoformat()
    
    response = await client.get(
        f"/api/webhook-logs?start_date={start_date}&end_date={end_date}",
        headers=auth_headers
    )
    assert response.status_code == 200
    
    logs = response.json()
    assert len(logs) >= 1
    assert any(l["id"] == log.id for l in logs)


@pytest.mark.asyncio
async def test_get_webhook_log_by_id(client: AsyncClient, auth_headers: dict, db_session):
    """Test getting a specific webhook log by ID."""
    # Create a repository config
    repo_config = RepositoryConfig(
        repo_name="test/get-repo",
        webhook_url="https://example.com/webhook",
        enabled=True
    )
    db_session.add(repo_config)
    await db_session.commit()
    await db_session.refresh(repo_config)
    
    # Create a log with all fields
    pr_result = {
        "repo": "test/get-repo",
        "pr_number": 123,
        "files_changed": ["file1.py", "file2.py"],
        "status": "success",
        "spell_match_attempted": True,
        "spell_generation_attempted": False
    }
    
    log = WebhookExecutionLog(
        repo_config_id=repo_config.id,
        repo_name="test/get-repo",
        pr_number=123,
        event_type="pull_request",
        action="opened",
        status="success",
        matched_spell_ids=json.dumps([5, 12, 3]),
        auto_generated_spell_id=42,
        pr_processing_result=json.dumps(pr_result),
        execution_duration_ms=1850
    )
    db_session.add(log)
    await db_session.commit()
    await db_session.refresh(log)
    
    # Get the log
    response = await client.get(f"/api/webhook-logs/{log.id}", headers=auth_headers)
    assert response.status_code == 200
    
    log_data = response.json()
    assert log_data["id"] == log.id
    assert log_data["repo_name"] == "test/get-repo"
    assert log_data["pr_number"] == 123
    assert log_data["status"] == "success"
    assert log_data["matched_spell_ids"] == [5, 12, 3]
    assert log_data["auto_generated_spell_id"] == 42
    assert log_data["execution_duration_ms"] == 1850
    
    # Verify computed fields
    assert log_data["files_changed_count"] == 2
    assert log_data["spell_match_attempted"] is True
    assert log_data["spell_generation_attempted"] is False


@pytest.mark.asyncio
async def test_get_webhook_log_not_found(client: AsyncClient, auth_headers: dict):
    """Test getting a non-existent webhook log returns 404."""
    response = await client.get("/api/webhook-logs/99999", headers=auth_headers)
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_get_repository_logs(client: AsyncClient, auth_headers: dict, db_session):
    """Test getting logs for a specific repository."""
    # Create two repository configs
    repo1 = RepositoryConfig(
        repo_name="test/repo1",
        webhook_url="https://example.com/webhook",
        enabled=True
    )
    repo2 = RepositoryConfig(
        repo_name="test/repo2",
        webhook_url="https://example.com/webhook",
        enabled=True
    )
    db_session.add_all([repo1, repo2])
    await db_session.commit()
    await db_session.refresh(repo1)
    await db_session.refresh(repo2)
    
    # Create logs for both repos
    log1 = WebhookExecutionLog(
        repo_config_id=repo1.id,
        repo_name="test/repo1",
        pr_number=1,
        event_type="pull_request",
        action="opened",
        status="success",
        execution_duration_ms=100
    )
    log2 = WebhookExecutionLog(
        repo_config_id=repo1.id,
        repo_name="test/repo1",
        pr_number=2,
        event_type="pull_request",
        action="opened",
        status="success",
        execution_duration_ms=200
    )
    log3 = WebhookExecutionLog(
        repo_config_id=repo2.id,
        repo_name="test/repo2",
        pr_number=1,
        event_type="pull_request",
        action="opened",
        status="success",
        execution_duration_ms=300
    )
    db_session.add_all([log1, log2, log3])
    await db_session.commit()
    
    # Get logs for repo1
    response = await client.get(f"/api/repo-configs/{repo1.id}/logs", headers=auth_headers)
    assert response.status_code == 200
    
    logs = response.json()
    assert len(logs) == 2
    assert all(log["repo_name"] == "test/repo1" for log in logs)
    assert all(log["repo_config_id"] == repo1.id for log in logs)


@pytest.mark.asyncio
async def test_get_repository_logs_empty(client: AsyncClient, auth_headers: dict, db_session):
    """Test getting logs for a repository with no logs returns empty list."""
    # Create a repository config with no logs
    repo = RepositoryConfig(
        repo_name="test/empty-repo",
        webhook_url="https://example.com/webhook",
        enabled=True
    )
    db_session.add(repo)
    await db_session.commit()
    await db_session.refresh(repo)
    
    # Get logs
    response = await client.get(f"/api/repo-configs/{repo.id}/logs", headers=auth_headers)
    assert response.status_code == 200
    
    logs = response.json()
    assert logs == []


@pytest.mark.asyncio
async def test_get_repository_logs_not_found(client: AsyncClient, auth_headers: dict):
    """Test getting logs for non-existent repository returns 404."""
    response = await client.get("/api/repo-configs/99999/logs", headers=auth_headers)
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_webhook_logs_pagination(client: AsyncClient, auth_headers: dict, db_session):
    """Test pagination for webhook logs."""
    # Create a repository config
    repo = RepositoryConfig(
        repo_name="test/pagination-repo",
        webhook_url="https://example.com/webhook",
        enabled=True
    )
    db_session.add(repo)
    await db_session.commit()
    await db_session.refresh(repo)
    
    # Create multiple logs
    logs = []
    for i in range(5):
        log = WebhookExecutionLog(
            repo_config_id=repo.id,
            repo_name="test/pagination-repo",
            pr_number=i + 1,
            event_type="pull_request",
            action="opened",
            status="success",
            execution_duration_ms=100 * (i + 1)
        )
        logs.append(log)
    
    db_session.add_all(logs)
    await db_session.commit()
    
    # Test pagination
    response = await client.get("/api/webhook-logs?skip=0&limit=2", headers=auth_headers)
    assert response.status_code == 200
    
    page1 = response.json()
    assert len(page1) == 2
    
    response = await client.get("/api/webhook-logs?skip=2&limit=2", headers=auth_headers)
    assert response.status_code == 200
    
    page2 = response.json()
    assert len(page2) == 2
    
    # Verify no overlap
    page1_ids = {log["id"] for log in page1}
    page2_ids = {log["id"] for log in page2}
    assert page1_ids.isdisjoint(page2_ids)


@pytest.mark.asyncio
async def test_webhook_logs_require_authentication(client: AsyncClient):
    """Test that webhook logs endpoints require authentication."""
    # Test list endpoint
    response = await client.get("/api/webhook-logs")
    assert response.status_code == 401
    
    # Test get by ID endpoint
    response = await client.get("/api/webhook-logs/1")
    assert response.status_code == 401
    
    # Test get by repository endpoint
    response = await client.get("/api/repo-configs/1/logs")
    assert response.status_code == 401

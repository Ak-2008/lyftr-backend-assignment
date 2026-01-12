import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health_live():
    """Test liveness probe always returns 200"""
    response = client.get("/health/live")
    assert response.status_code == 200
    
    data = response.json()
    assert "status" in data
    assert data["status"] == "ok"

def test_health_ready():
    """Test readiness probe returns 200 when ready"""
    response = client.get("/health/ready")
    assert response.status_code == 200
    
    data = response.json()
    assert "status" in data
    assert data["status"] == "ready"

def test_metrics_endpoint():
    """Test metrics endpoint returns Prometheus format"""
    response = client.get("/metrics")
    assert response.status_code == 200
    
    # Check content type
    assert "text/plain" in response.headers["content-type"]
    
    # Check for required metrics
    text = response.text
    assert "http_requests_total" in text
    assert "webhook_requests_total" in text
    
    # Check for common Prometheus metric patterns
    assert "# HELP" in text or "# TYPE" in text or "_total" in text

def test_metrics_http_requests():
    """Test that http_requests_total metric exists"""
    response = client.get("/metrics")
    assert response.status_code == 200
    
    text = response.text
    # Should have http_requests_total with labels
    assert "http_requests_total{" in text or "http_requests_total " in text

def test_metrics_webhook_requests():
    """Test that webhook_requests_total metric exists"""
    response = client.get("/metrics")
    assert response.status_code == 200
    
    text = response.text
    # Should have webhook_requests_total with result labels
    assert "webhook_requests_total{" in text or "webhook_requests_total " in text

def test_metrics_request_latency():
    """Test that request latency metrics exist"""
    response = client.get("/metrics")
    assert response.status_code == 200
    
    text = response.text
    # Should have request_latency_ms metrics
    assert "request_latency_ms" in text


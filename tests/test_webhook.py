import pytest
from fastapi.testclient import TestClient
import hmac
import hashlib
import json
from app.main import app
from app.config import settings

client = TestClient(app)

def generate_signature(body_dict):
    """Generate HMAC signature for webhook"""
    body_str = json.dumps(body_dict, separators=(',', ':'))
    signature = hmac.new(
        settings.WEBHOOK_SECRET.encode(),
        body_str.encode(),
        hashlib.sha256
    ).hexdigest()
    return signature, body_str

def test_webhook_valid_insert():
    """Test valid message insertion returns 200"""
    message = {
        "message_id": "pytest_test_1",
        "from": "+919876543210",
        "to": "+14155550100",
        "ts": "2025-01-15T10:00:00Z",
        "text": "Test message from pytest"
    }
    signature, body = generate_signature(message)
    
    response = client.post(
        "/webhook",
        headers={
            "Content-Type": "application/json",
            "X-Signature": signature
        },
        data=body
    )
    
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_webhook_duplicate_message():
    """Test duplicate message handling (idempotent) - should still return 200"""
    message = {
        "message_id": "pytest_dup_test",
        "from": "+919876543210",
        "to": "+14155550100",
        "ts": "2025-01-15T10:00:00Z",
        "text": "Duplicate test"
    }
    signature, body = generate_signature(message)
    
    # First insert
    response1 = client.post(
        "/webhook",
        headers={
            "Content-Type": "application/json",
            "X-Signature": signature
        },
        data=body
    )
    assert response1.status_code == 200
    
    # Second insert (duplicate) - should still return 200 (idempotent)
    response2 = client.post(
        "/webhook",
        headers={
            "Content-Type": "application/json",
            "X-Signature": signature
        },
        data=body
    )
    assert response2.status_code == 200
    assert response2.json() == {"status": "ok"}

def test_webhook_invalid_signature():
    """Test invalid signature returns 401"""
    message = {
        "message_id": "pytest_invalid_sig",
        "from": "+919876543210",
        "to": "+14155550100",
        "ts": "2025-01-15T10:00:00Z",
        "text": "Invalid signature test"
    }
    body = json.dumps(message, separators=(',', ':'))
    
    response = client.post(
        "/webhook",
        headers={
            "Content-Type": "application/json",
            "X-Signature": "invalid_signature_12345"
        },
        data=body
    )
    
    assert response.status_code == 401
    assert "invalid signature" in response.json()["detail"]

def test_webhook_missing_signature():
    """Test missing signature header returns 401"""
    message = {
        "message_id": "pytest_no_sig",
        "from": "+919876543210",
        "to": "+14155550100",
        "ts": "2025-01-15T10:00:00Z",
        "text": "No signature"
    }
    body = json.dumps(message, separators=(',', ':'))
    
    response = client.post(
        "/webhook",
        headers={"Content-Type": "application/json"},
        data=body
    )
    
    assert response.status_code == 401

def test_webhook_invalid_e164_format():
    """Test validation error for invalid E.164 phone format returns 422"""
    message = {
        "message_id": "pytest_invalid_phone",
        "from": "919876543210",  # Missing + prefix
        "to": "+14155550100",
        "ts": "2025-01-15T10:00:00Z",
        "text": "Bad phone format"
    }
    signature, body = generate_signature(message)
    
    response = client.post(
        "/webhook",
        headers={
            "Content-Type": "application/json",
            "X-Signature": signature
        },
        data=body
    )
    
    assert response.status_code == 422

def test_webhook_invalid_timestamp():
    """Test validation error for invalid timestamp returns 422"""
    message = {
        "message_id": "pytest_invalid_ts",
        "from": "+919876543210",
        "to": "+14155550100",
        "ts": "2025-01-15T10:00:00",  # Missing Z suffix
        "text": "Bad timestamp"
    }
    signature, body = generate_signature(message)
    
    response = client.post(
        "/webhook",
        headers={
            "Content-Type": "application/json",
            "X-Signature": signature
        },
        data=body
    )
    
    assert response.status_code == 422

def test_webhook_empty_message_id():
    """Test validation error for empty message_id returns 422"""
    message = {
        "message_id": "",  # Empty message_id
        "from": "+919876543210",
        "to": "+14155550100",
        "ts": "2025-01-15T10:00:00Z",
        "text": "Empty message_id"
    }
    signature, body = generate_signature(message)
    
    response = client.post(
        "/webhook",
        headers={
            "Content-Type": "application/json",
            "X-Signature": signature
        },
        data=body
    )
    
    assert response.status_code == 422

def test_webhook_optional_text():
    """Test that text field is optional"""
    message = {
        "message_id": "pytest_no_text",
        "from": "+919876543210",
        "to": "+14155550100",
        "ts": "2025-01-15T10:00:00Z"
        # No text field
    }
    signature, body = generate_signature(message)
    
    response = client.post(
        "/webhook",
        headers={
            "Content-Type": "application/json",
            "X-Signature": signature
        },
        data=body
    )
    
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


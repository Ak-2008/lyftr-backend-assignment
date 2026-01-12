import pytest
from fastapi.testclient import TestClient
from app.main import app
import hmac
import hashlib
import json
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

@pytest.fixture(scope="module", autouse=True)
def setup_test_messages():
    """Setup test messages before running tests"""
    test_messages = [
        {
            "message_id": "pytest_msg_1",
            "from": "+919876543210",
            "to": "+14155550100",
            "ts": "2025-01-15T09:00:00Z",
            "text": "First pytest message"
        },
        {
            "message_id": "pytest_msg_2",
            "from": "+919876543210",
            "to": "+14155550100",
            "ts": "2025-01-15T10:00:00Z",
            "text": "Second pytest message with Hello"
        },
        {
            "message_id": "pytest_msg_3",
            "from": "+911234567890",
            "to": "+14155550100",
            "ts": "2025-01-15T11:00:00Z",
            "text": "Different sender message"
        }
    ]
    
    # Insert test messages
    for msg in test_messages:
        signature, body = generate_signature(msg)
        client.post(
            "/webhook",
            headers={
                "Content-Type": "application/json",
                "X-Signature": signature
            },
            data=body
        )
    
    yield  # Tests run here
    
    # Cleanup is not needed as we're using SQLite and tests are isolated

def test_messages_list_structure():
    """Test basic message listing returns correct structure"""
    response = client.get("/messages")
    assert response.status_code == 200
    
    data = response.json()
    assert "data" in data
    assert "total" in data
    assert "limit" in data
    assert "offset" in data
    assert isinstance(data["data"], list)
    assert isinstance(data["total"], int)
    assert isinstance(data["limit"], int)
    assert isinstance(data["offset"], int)

def test_messages_default_pagination():
    """Test default pagination values"""
    response = client.get("/messages")
    assert response.status_code == 200
    
    data = response.json()
    assert data["limit"] == 50  # Default limit
    assert data["offset"] == 0  # Default offset

def test_messages_custom_pagination():
    """Test custom pagination parameters"""
    response = client.get("/messages?limit=2&offset=1")
    assert response.status_code == 200
    
    data = response.json()
    assert data["limit"] == 2
    assert data["offset"] == 1
    assert len(data["data"]) <= 2

def test_messages_pagination_limits():
    """Test pagination limit constraints"""
    # Test max limit (100)
    response = client.get("/messages?limit=150")
    assert response.status_code == 422  # Should fail validation
    
    # Test min limit (1)
    response = client.get("/messages?limit=0")
    assert response.status_code == 422  # Should fail validation
    
    # Test valid limit
    response = client.get("/messages?limit=100")
    assert response.status_code == 200

def test_messages_filter_by_from():
    """Test filtering by sender (from parameter)"""
    response = client.get("/messages?from=+919876543210")
    assert response.status_code == 200
    
    data = response.json()
    # All returned messages should be from the specified sender
    for msg in data["data"]:
        assert msg["from"] == "+919876543210"

def test_messages_filter_by_since():
    """Test filtering by timestamp (since parameter)"""
    response = client.get("/messages?since=2025-01-15T10:00:00Z")
    assert response.status_code == 200
    
    data = response.json()
    # All messages should be >= the since timestamp
    for msg in data["data"]:
        assert msg["ts"] >= "2025-01-15T10:00:00Z"

def test_messages_text_search():
    """Test text search (q parameter)"""
    response = client.get("/messages?q=Hello")
    assert response.status_code == 200
    
    data = response.json()
    # All returned messages should contain the search term (case-insensitive)
    for msg in data["data"]:
        if msg["text"]:
            assert "hello" in msg["text"].lower()

def test_messages_ordering():
    """Test messages are ordered by ts ASC, message_id ASC"""
    response = client.get("/messages?from=+919876543210")
    assert response.status_code == 200
    
    data = response.json()
    messages = data["data"]
    
    # Check ordering (should be ascending by ts, then message_id)
    if len(messages) > 1:
        for i in range(len(messages) - 1):
            current = messages[i]
            next_msg = messages[i + 1]
            # Should be ordered by ts, then message_id
            assert (current["ts"], current["message_id"]) <= (next_msg["ts"], next_msg["message_id"])

def test_messages_total_count():
    """Test that total reflects total matching records, not just returned data"""
    # Get with low limit
    response = client.get("/messages?limit=1")
    assert response.status_code == 200
    
    data = response.json()
    # Total should be >= number of returned items
    assert data["total"] >= len(data["data"])
    
    # If total > 1, we should have only 1 item in data due to limit
    if data["total"] > 1:
        assert len(data["data"]) == 1

def test_messages_combined_filters():
    """Test combining multiple filters"""
    response = client.get("/messages?from=+919876543210&since=2025-01-15T09:30:00Z&limit=5")
    assert response.status_code == 200
    
    data = response.json()
    # Check all filters are applied
    for msg in data["data"]:
        assert msg["from"] == "+919876543210"
        assert msg["ts"] >= "2025-01-15T09:30:00Z"
    
    assert len(data["data"]) <= 5

def test_messages_response_format():
    """Test that each message has correct fields"""
    response = client.get("/messages?limit=1")
    assert response.status_code == 200
    
    data = response.json()
    if data["data"]:
        msg = data["data"][0]
        assert "message_id" in msg
        assert "from" in msg
        assert "to" in msg
        assert "ts" in msg
        assert "text" in msg  # Can be null


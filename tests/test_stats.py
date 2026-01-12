import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_stats_endpoint_structure():
    """Test stats endpoint returns correct structure"""
    response = client.get("/stats")
    assert response.status_code == 200
    
    data = response.json()
    assert "total_messages" in data
    assert "senders_count" in data
    assert "messages_per_sender" in data
    assert "first_message_ts" in data
    assert "last_message_ts" in data

def test_stats_total_messages():
    """Test total messages count matches actual messages"""
    # Get all messages
    messages_response = client.get("/messages?limit=100")
    messages_data = messages_response.json()
    total_from_messages = messages_data["total"]
    
    # Get stats
    stats_response = client.get("/stats")
    stats_data = stats_response.json()
    
    # Should match
    assert stats_data["total_messages"] == total_from_messages

def test_stats_senders_count():
    """Test unique senders count is valid"""
    response = client.get("/stats")
    assert response.status_code == 200
    
    data = response.json()
    assert isinstance(data["senders_count"], int)
    assert data["senders_count"] >= 0
    
    # Senders count should be <= total messages
    assert data["senders_count"] <= data["total_messages"]

def test_stats_messages_per_sender_format():
    """Test messages per sender list format"""
    response = client.get("/stats")
    assert response.status_code == 200
    
    data = response.json()
    messages_per_sender = data["messages_per_sender"]
    
    # Should be a list
    assert isinstance(messages_per_sender, list)
    
    # Each item should have 'from' and 'count'
    for sender in messages_per_sender:
        assert "from" in sender
        assert "count" in sender
        assert isinstance(sender["count"], int)
        assert sender["count"] > 0

def test_stats_messages_per_sender_ordering():
    """Test messages per sender is sorted by count descending"""
    response = client.get("/stats")
    assert response.status_code == 200
    
    data = response.json()
    messages_per_sender = data["messages_per_sender"]
    
    # Should be sorted by count descending
    if len(messages_per_sender) > 1:
        for i in range(len(messages_per_sender) - 1):
            assert messages_per_sender[i]["count"] >= messages_per_sender[i + 1]["count"]

def test_stats_messages_per_sender_limit():
    """Test messages per sender is limited to top 10"""
    response = client.get("/stats")
    assert response.status_code == 200
    
    data = response.json()
    messages_per_sender = data["messages_per_sender"]
    
    # Should have max 10 entries
    assert len(messages_per_sender) <= 10

def test_stats_timestamps():
    """Test first and last message timestamps"""
    response = client.get("/stats")
    assert response.status_code == 200
    
    data = response.json()
    
    # If there are messages, timestamps should exist
    if data["total_messages"] > 0:
        assert data["first_message_ts"] is not None
        assert data["last_message_ts"] is not None
        
        # First should be <= last
        assert data["first_message_ts"] <= data["last_message_ts"]
    else:
        # If no messages, timestamps should be null
        assert data["first_message_ts"] is None
        assert data["last_message_ts"] is None

def test_stats_consistency():
    """Test that stats data is internally consistent"""
    response = client.get("/stats")
    assert response.status_code == 200
    
    data = response.json()
    
    # If there are messages, there must be senders
    if data["total_messages"] > 0:
        assert data["senders_count"] > 0
        assert len(data["messages_per_sender"]) > 0
    
    # Sum of messages_per_sender should be <= total_messages
    # (it may be less if there are more than 10 senders)
    total_from_senders = sum(sender["count"] for sender in data["messages_per_sender"])
    assert total_from_senders <= data["total_messages"]


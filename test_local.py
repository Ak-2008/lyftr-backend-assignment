import requests
import hmac
import hashlib
import json

WEBHOOK_SECRET = "testsecret"
BASE_URL = "http://localhost:8000"

def generate_signature(body_dict):
    """Generate HMAC signature for webhook"""
    body_str = json.dumps(body_dict, separators=(',', ':'))
    signature = hmac.new(
        WEBHOOK_SECRET.encode(),
        body_str.encode(),
        hashlib.sha256
    ).hexdigest()
    return signature, body_str

def test_webhook():
    """Test webhook endpoint"""
    print("=" * 60)
    print("TESTING LYFTR WEBHOOK API")
    print("=" * 60)
    
    # Test 1: Valid message
    print("\n✓ Test 1: Sending valid message...")
    message = {
        "message_id": "m1",
        "from": "+919876543210",
        "to": "+14155550100",
        "ts": "2025-01-15T10:00:00Z",
        "text": "Hello"
    }
    
    signature, body = generate_signature(message)
    
    response = requests.post(
        f"{BASE_URL}/webhook",
        headers={
            "Content-Type": "application/json",
            "X-Signature": signature
        },
        data=body
    )
    
    print(f"  Status: {response.status_code} {'✓' if response.status_code == 200 else '✗'}")
    print(f"  Response: {response.json()}")
    
    # Test 2: Duplicate message
    print("\n✓ Test 2: Sending duplicate message (should still return 200)...")
    response = requests.post(
        f"{BASE_URL}/webhook",
        headers={
            "Content-Type": "application/json",
            "X-Signature": signature
        },
        data=body
    )
    print(f"  Status: {response.status_code} {'✓' if response.status_code == 200 else '✗'}")
    print(f"  Response: {response.json()}")
    
    # Test 3: Invalid signature
    print("\n✓ Test 3: Invalid signature (should return 401)...")
    response = requests.post(
        f"{BASE_URL}/webhook",
        headers={
            "Content-Type": "application/json",
            "X-Signature": "invalid123"
        },
        data=body
    )
    print(f"  Status: {response.status_code} {'✓' if response.status_code == 401 else '✗'}")
    print(f"  Response: {response.json()}")
    
    # Test 4: Add more messages for testing
    print("\n✓ Test 4: Adding more test messages...")
    test_messages = [
        {
            "message_id": "m2",
            "from": "+919876543210",
            "to": "+14155550100",
            "ts": "2025-01-15T09:00:00Z",
            "text": "Earlier message"
        },
        {
            "message_id": "m3",
            "from": "+911234567890",
            "to": "+14155550100",
            "ts": "2025-01-15T11:00:00Z",
            "text": "Different sender"
        },
        {
            "message_id": "m4",
            "from": "+919876543210",
            "to": "+14155550100",
            "ts": "2025-01-15T12:00:00Z",
            "text": "Latest message"
        }
    ]
    
    for msg in test_messages:
        sig, body_str = generate_signature(msg)
        response = requests.post(
            f"{BASE_URL}/webhook",
            headers={
                "Content-Type": "application/json",
                "X-Signature": sig
            },
            data=body_str
        )
        print(f"  Message {msg['message_id']}: {response.status_code} {'✓' if response.status_code == 200 else '✗'}")
    
    # Test 5: List messages
    print("\n✓ Test 5: Listing all messages...")
    response = requests.get(f"{BASE_URL}/messages")
    print(f"  Status: {response.status_code} {'✓' if response.status_code == 200 else '✗'}")
    data = response.json()
    print(f"  Total messages: {data['total']}")
    print(f"  Returned: {len(data['data'])} messages")
    
    # Test 6: Pagination
    print("\n✓ Test 6: Testing pagination (limit=2, offset=0)...")
    response = requests.get(f"{BASE_URL}/messages?limit=2&offset=0")
    print(f"  Status: {response.status_code} {'✓' if response.status_code == 200 else '✗'}")
    data = response.json()
    print(f"  Returned: {len(data['data'])} messages (expected 2)")
    print(f"  Total: {data['total']}")
    
    # Test 7: Filter by sender
    print("\n✓ Test 7: Filter by sender (+919876543210)...")
    response = requests.get(f"{BASE_URL}/messages?from=+919876543210")
    print(f"  Status: {response.status_code} {'✓' if response.status_code == 200 else '✗'}")
    data = response.json()
    print(f"  Messages from +919876543210: {data['total']}")
    
    # Test 8: Text search
    print("\n✓ Test 8: Text search (q=Hello)...")
    response = requests.get(f"{BASE_URL}/messages?q=Hello")
    print(f"  Status: {response.status_code} {'✓' if response.status_code == 200 else '✗'}")
    data = response.json()
    print(f"  Messages containing 'Hello': {data['total']}")
    
    # Test 9: Get stats
    print("\n✓ Test 9: Getting statistics...")
    response = requests.get(f"{BASE_URL}/stats")
    print(f"  Status: {response.status_code} {'✓' if response.status_code == 200 else '✗'}")
    data = response.json()
    print(f"  Total messages: {data['total_messages']}")
    print(f"  Unique senders: {data['senders_count']}")
    print(f"  First message: {data['first_message_ts']}")
    print(f"  Last message: {data['last_message_ts']}")
    print(f"  Top senders: {data['messages_per_sender']}")
    
    # Test 10: Get metrics
    print("\n✓ Test 10: Getting Prometheus metrics...")
    response = requests.get(f"{BASE_URL}/metrics")
    print(f"  Status: {response.status_code} {'✓' if response.status_code == 200 else '✗'}")
    metrics_text = response.text
    if "http_requests_total" in metrics_text and "webhook_requests_total" in metrics_text:
        print("  ✓ Required metrics found")
    else:
        print("  ✗ Required metrics missing")
    
    # Test 11: Health checks
    print("\n✓ Test 11: Health checks...")
    response = requests.get(f"{BASE_URL}/health/live")
    print(f"  Liveness: {response.status_code} {'✓' if response.status_code == 200 else '✗'}")
    
    response = requests.get(f"{BASE_URL}/health/ready")
    print(f"  Readiness: {response.status_code} {'✓' if response.status_code == 200 else '✗'}")
    
    print("\n" + "=" * 60)
    print("TESTING COMPLETE!")
    print("=" * 60)

if __name__ == "__main__":
    try:
        test_webhook()
    except requests.exceptions.ConnectionError:
        print("ERROR: Could not connect to server at http://localhost:8000")
        print("Make sure the server is running with:")
        print("  uvicorn app.main:app --reload")



# Lyftr AI - Backend Assignment

A containerized FastAPI webhook service for ingesting WhatsApp-like messages with HMAC signature validation, idempotency, and observability features.

## Features

- ✅ Webhook endpoint with HMAC-SHA256 signature validation
- ✅ Message idempotency (no duplicate insertions)
- ✅ Paginated and filterable message listing
- ✅ Message statistics endpoint
- ✅ Health probes (liveness & readiness)
- ✅ Prometheus metrics
- ✅ Structured JSON logging
- ✅ SQLite persistence with Docker volumes
- ✅ 12-factor app configuration

## Setup Used

**Tools**: Cursor AI with Claude Sonnet 4.5 for code generation and implementation guidance

## Quick Start

### Prerequisites

- Python 3.11+ (for local development)
- Docker and Docker Compose (for containerized deployment)

### Local Development Setup

1. **Create and activate virtual environment:**

```bash
# Windows PowerShell
python -m venv venv
.\venv\Scripts\Activate.ps1

# If you get execution policy error:
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

2. **Install dependencies:**

```bash
pip install -r requirements.txt
```

3. **Set environment variables:**

```bash
# Windows PowerShell
$env:WEBHOOK_SECRET = "testsecret"
$env:DATABASE_URL = "sqlite:///./app.db"
$env:LOG_LEVEL = "INFO"
```

4. **Run the application:**

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

5. **Test the application:**

Open a new terminal and run:

```bash
python test_local.py
```

### Docker Deployment

1. **Set the webhook secret:**

```bash
# Windows PowerShell
$env:WEBHOOK_SECRET = "testsecret"

# Linux/Mac
export WEBHOOK_SECRET="testsecret"
```

2. **Start the service:**

```bash
make up
# or: docker compose up -d --build
```

3. **Check logs:**

```bash
make logs
# or: docker compose logs -f api
```

4. **Test the service:**

```bash
python test_local.py
```

5. **Stop the service:**

```bash
make down
# or: docker compose down -v
```

## API Endpoints

### POST /webhook

Ingest WhatsApp-like messages with HMAC signature validation.

**Headers:**
- `Content-Type: application/json`
- `X-Signature: <HMAC-SHA256 hex of request body>`

**Body:**

```json
{
  "message_id": "m1",
  "from": "+919876543210",
  "to": "+14155550100",
  "ts": "2025-01-15T10:00:00Z",
  "text": "Hello"
}
```

**Response:** `200 {"status": "ok"}`

**Signature Calculation (Python):**

```python
import hmac
import hashlib
import json

body = json.dumps(payload, separators=(',', ':'))
signature = hmac.new(
    b"testsecret",
    body.encode(),
    hashlib.sha256
).hexdigest()
```

**Behavior:**
- Valid signature + new message → 200, inserts row
- Valid signature + duplicate message_id → 200, no insert (idempotent)
- Invalid signature → 401 with `{"detail": "invalid signature"}`
- Invalid payload → 422 with validation error details

### GET /messages

List stored messages with pagination and filters.

**Query Parameters:**
- `limit` (int, default=50, max=100): Number of messages per page
- `offset` (int, default=0): Pagination offset
- `from` (string): Filter by sender phone number (exact match)
- `since` (ISO-8601 timestamp): Filter messages after this time
- `q` (string): Search text (case-insensitive substring)

**Example:**

```bash
curl "http://localhost:8000/messages?limit=10&offset=0&from=+919876543210"
```

**Response:**

```json
{
  "data": [
    {
      "message_id": "m1",
      "from": "+919876543210",
      "to": "+14155550100",
      "ts": "2025-01-15T10:00:00Z",
      "text": "Hello"
    }
  ],
  "total": 100,
  "limit": 10,
  "offset": 0
}
```

**Ordering:** Results are ordered by `ts ASC, message_id ASC` (deterministic, oldest first)

### GET /stats

Get message statistics and analytics.

**Response:**

```json
{
  "total_messages": 123,
  "senders_count": 10,
  "messages_per_sender": [
    {"from": "+919876543210", "count": 50},
    {"from": "+911234567890", "count": 30}
  ],
  "first_message_ts": "2025-01-10T09:00:00Z",
  "last_message_ts": "2025-01-15T10:00:00Z"
}
```

**Notes:**
- `messages_per_sender` shows top 10 senders sorted by count descending
- Timestamps are null if no messages exist

### GET /health/live

Liveness probe - always returns 200 when app is running.

**Response:** `{"status": "ok"}`

### GET /health/ready

Readiness probe - returns 200 when database is ready and WEBHOOK_SECRET is set.

**Response:** `{"status": "ready"}` (200) or 503 if not ready

### GET /metrics

Prometheus-style metrics endpoint.

**Metrics exposed:**
- `http_requests_total{path, status}`: Total HTTP requests by path and status code
- `webhook_requests_total{result}`: Webhook processing outcomes (created, duplicate, invalid_signature, validation_error)
- `request_latency_ms_bucket{le}`: Request latency histogram with buckets [100, 500, 1000, 5000, 10000]

**Example output:**

```
# HELP http_requests_total Total HTTP requests
# TYPE http_requests_total counter
http_requests_total{path="/webhook",status="200"} 15.0
http_requests_total{path="/webhook",status="401"} 2.0

# HELP webhook_requests_total Total webhook requests
# TYPE webhook_requests_total counter
webhook_requests_total{result="created"} 10.0
webhook_requests_total{result="duplicate"} 5.0
webhook_requests_total{result="invalid_signature"} 2.0
```

## Design Decisions

### HMAC Verification

- Uses `hmac.compare_digest()` for timing-attack-safe comparison
- Signature computed as: `HMAC-SHA256(WEBHOOK_SECRET, raw_body_bytes).hexdigest()`
- Invalid signature returns 401 **before** any database operation
- Missing WEBHOOK_SECRET causes startup failure (app won't start)

### Pagination Contract

- **Deterministic ordering**: `ORDER BY ts ASC, message_id ASC`
- `total` reflects total matching rows (ignoring limit/offset)
- `limit` capped at 100, defaults to 50
- `offset` must be >= 0
- Filters apply before pagination

### Statistics & Metrics

- `/stats` uses SQL aggregations for efficiency
- Top 10 senders by message count
- Prometheus metrics track:
  - HTTP requests by path and status
  - Webhook outcomes (created/duplicate/invalid_signature/validation_error)
  - Request latency histogram
- Metrics survive across requests (counters increment)

### Idempotency

- Enforced via `PRIMARY KEY (message_id)` in SQLite
- Duplicate requests with same `message_id`:
  - Return 200 (success)
  - Do not insert second row
  - Logged with `"dup": true` in JSON logs
- Signature must still be valid for duplicates

### Structured Logging

- One JSON line per request (parseable with `jq`)
- Standard fields: `ts`, `level`, `message`, `request_id`, `method`, `path`, `status`, `latency_ms`
- Webhook-specific fields: `message_id`, `dup`, `result`
- All timestamps in ISO-8601 UTC format with 'Z' suffix

**Example log line:**

```json
{"ts":"2025-01-15T10:00:00.123Z","level":"INFO","message":"Request processed","request_id":"uuid-here","method":"POST","path":"/webhook","status":200,"latency_ms":12.34,"message_id":"m1","dup":false,"result":"created"}
```

## Testing with curl

### 1. Generate signature and send valid message

```bash
# Generate signature using Python
python3 -c "import hmac,hashlib,json; body='{\"message_id\":\"m1\",\"from\":\"+919876543210\",\"to\":\"+14155550100\",\"ts\":\"2025-01-15T10:00:00Z\",\"text\":\"Hello\"}'; print(hmac.new(b'testsecret', body.encode(), hashlib.sha256).hexdigest())"

# Use the signature in curl (replace YOUR_SIGNATURE with output above)
curl -X POST http://localhost:8000/webhook \
  -H "Content-Type: application/json" \
  -H "X-Signature: YOUR_SIGNATURE" \
  -d '{"message_id":"m1","from":"+919876543210","to":"+14155550100","ts":"2025-01-15T10:00:00Z","text":"Hello"}'
```

### 2. Invalid signature (should return 401)

```bash
curl -X POST http://localhost:8000/webhook \
  -H "Content-Type: application/json" \
  -H "X-Signature: invalid123" \
  -d '{"message_id":"m1","from":"+919876543210","to":"+14155550100","ts":"2025-01-15T10:00:00Z","text":"Hello"}'
```

### 3. List messages

```bash
curl "http://localhost:8000/messages"
curl "http://localhost:8000/messages?limit=2&offset=0"
curl "http://localhost:8000/messages?from=+919876543210"
curl "http://localhost:8000/messages?q=Hello"
```

### 4. Get stats

```bash
curl "http://localhost:8000/stats" | jq .
```

### 5. Check metrics

```bash
curl "http://localhost:8000/metrics"
```

### 6. Health checks

```bash
curl "http://localhost:8000/health/live"
curl "http://localhost:8000/health/ready"
```

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `WEBHOOK_SECRET` | **Yes** | - | Secret for HMAC signature verification. App won't start without it. |
| `DATABASE_URL` | No | `sqlite:////data/app.db` | SQLite database path |
| `LOG_LEVEL` | No | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR) |

## Project Structure

```
lyftr-backend-assignment/
├── app/
│   ├── __init__.py          # Package initialization
│   ├── main.py              # FastAPI app, routes, middleware
│   ├── config.py            # Environment configuration
│   ├── models.py            # Pydantic models for validation
│   ├── storage.py           # Database operations
│   ├── logging_utils.py     # JSON logging setup
│   └── metrics.py           # Prometheus metrics
├── tests/
│   └── __init__.py          # Test package
├── venv/                    # Virtual environment (local dev)
├── requirements.txt         # Python dependencies
├── Dockerfile               # Multi-stage Docker build
├── docker-compose.yml       # Docker Compose configuration
├── Makefile                 # Convenience commands
├── test_local.py            # Local testing script
├── .gitignore              # Git ignore rules
└── README.md               # This file
```

## Database Schema

```sql
CREATE TABLE messages (
    message_id TEXT PRIMARY KEY,
    from_msisdn TEXT NOT NULL,
    to_msisdn TEXT NOT NULL,
    ts TEXT NOT NULL,           -- ISO-8601 UTC string
    text TEXT,                  -- optional, max 4096 chars
    created_at TEXT NOT NULL    -- server timestamp
);

CREATE INDEX idx_from_msisdn ON messages(from_msisdn);
CREATE INDEX idx_ts ON messages(ts);
```

## Validation Rules

### Message Validation

- `message_id`: Non-empty string
- `from` / `to`: E.164 format (starts with `+`, followed by digits only)
- `ts`: ISO-8601 UTC with 'Z' suffix (e.g., `2025-01-15T10:00:00Z`)
- `text`: Optional, max 4096 characters

### Examples

**Valid:**
- `{"message_id":"m1","from":"+919876543210","to":"+14155550100","ts":"2025-01-15T10:00:00Z","text":"Hello"}`
- `{"message_id":"m2","from":"+1234567890","to":"+9876543210","ts":"2025-01-15T10:00:00Z"}` (text optional)

**Invalid:**
- `{"message_id":"","..."}` → 422 (empty message_id)
- `{"from":"919876543210",...}` → 422 (missing + prefix)
- `{"from":"+91-98765-43210",...}` → 422 (contains non-digits)
- `{"ts":"2025-01-15T10:00:00",...}` → 422 (missing Z suffix)

## Troubleshooting

### App won't start - WEBHOOK_SECRET error

**Problem:** `ERROR: WEBHOOK_SECRET environment variable is not set`

**Solution:** Set the environment variable before running:

```bash
# Windows PowerShell
$env:WEBHOOK_SECRET = "testsecret"

# Linux/Mac
export WEBHOOK_SECRET="testsecret"
```

### Database locked error

**Problem:** SQLite database is locked

**Solution:** 
- For local dev: Delete `app.db` and restart
- For Docker: `docker compose down -v` to remove volumes

### Port 8000 already in use

**Problem:** Another process is using port 8000

**Solution:**
- Kill the process: `netstat -ano | findstr :8000` (Windows)
- Or use a different port: `uvicorn app.main:app --port 8001`

### Docker build fails

**Problem:** Docker build errors

**Solution:**
- Make sure Docker Desktop is running
- Clean Docker cache: `docker system prune -a`
- Rebuild: `docker compose build --no-cache`

## Testing

### Automated Tests (pytest)

The project includes comprehensive pytest tests covering all endpoints and functionality:

**Test Suites:**
- `tests/test_webhook.py` - Webhook endpoint tests (signature validation, idempotency, validation)
- `tests/test_messages.py` - Message listing, pagination, and filtering tests
- `tests/test_stats.py` - Statistics endpoint tests
- `tests/test_health.py` - Health checks and metrics endpoint tests

**Run all tests:**
```bash
# Using make
make test

# Or directly with pytest
pytest tests/ -v

# Run specific test file
pytest tests/test_webhook.py -v
```

**Test Coverage:**
- ✅ Valid message insertion with signature verification
- ✅ Duplicate message handling (idempotency)
- ✅ Invalid signature rejection (401)
- ✅ Validation errors (422) for invalid E.164, timestamps, etc.
- ✅ Message pagination with limit/offset
- ✅ Message filtering (by sender, timestamp, text search)
- ✅ Message ordering (ts ASC, message_id ASC)
- ✅ Statistics accuracy and structure
- ✅ Health endpoints (live/ready)
- ✅ Prometheus metrics format

### Manual Testing

A comprehensive manual test script is also available:

```bash
# Make sure server is running first
python test_local.py
```

## Development Workflow

1. **Initial Setup:**
   ```bash
   python -m venv venv
   .\venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```

2. **Local Development:**
   ```bash
   $env:WEBHOOK_SECRET = "testsecret"
   $env:DATABASE_URL = "sqlite:///./app.db"
   uvicorn app.main:app --reload
   ```

3. **Run Tests:**
   ```bash
   # In another terminal
   make test
   # or: python test_local.py
   ```

4. **Docker Testing:**
   ```bash
   $env:WEBHOOK_SECRET = "testsecret"
   make up
   make logs
   make test
   make down
   ```

5. **Submission:**
   - Ensure all tests pass
   - Clean up: `make clean`
   - Push to GitHub
   - Email to careers@lyftr.ai

## License

This is an assignment submission for Lyftr AI Backend Engineer position.

## Author

Created as part of the Lyftr AI Backend Assignment using Cursor AI with Claude Sonnet 4.5.



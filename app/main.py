from fastapi import FastAPI, Request, HTTPException, Query
from fastapi.responses import Response, JSONResponse
import hmac
import hashlib
import time
import uuid
from typing import Optional

from app.config import settings
from app.models import WebhookMessage, MessagesListResponse, MessageResponse, StatsResponse
from app.storage import init_db, check_db_ready, insert_message, get_messages, get_stats
from app.logging_utils import setup_logging, get_logger, request_id_var
from app.metrics import (
    http_requests_total, webhook_requests_total, 
    request_latency_ms, get_metrics, CONTENT_TYPE_LATEST
)

# Setup logging
setup_logging(settings.LOG_LEVEL)
logger = get_logger()

# Initialize FastAPI app
app = FastAPI(title="Lyftr Webhook API")

@app.on_event("startup")
async def startup_event():
    """Initialize database on startup"""
    logger.info("Starting application...")
    init_db()
    logger.info("Database initialized")

@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Middleware to log all requests and track metrics"""
    # Generate request ID
    req_id = str(uuid.uuid4())
    request_id_var.set(req_id)
    
    start_time = time.time()
    
    # Process request
    response = await call_next(request)
    
    # Calculate latency
    latency_ms = (time.time() - start_time) * 1000
    
    # Track metrics
    http_requests_total.labels(path=request.url.path, status=response.status_code).inc()
    request_latency_ms.observe(latency_ms)
    
    # Log request
    log_extra = {
        'request_id': req_id,
        'method': request.method,
        'path': request.url.path,
        'status': response.status_code,
        'latency_ms': round(latency_ms, 2)
    }
    
    # Add webhook-specific fields if available
    if hasattr(request.state, 'message_id'):
        log_extra['message_id'] = request.state.message_id
    if hasattr(request.state, 'dup'):
        log_extra['dup'] = request.state.dup
    if hasattr(request.state, 'result'):
        log_extra['result'] = request.state.result
    
    logger.info("Request processed", extra=log_extra)
    
    return response

def verify_signature(body: bytes, signature: str) -> bool:
    """Verify HMAC-SHA256 signature"""
    expected = hmac.new(
        settings.WEBHOOK_SECRET.encode(),
        body,
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)

@app.post("/webhook")
async def webhook(request: Request):
    """Receive webhook messages with HMAC signature validation"""
    # Get raw body
    body = await request.body()
    
    # Check signature
    signature = request.headers.get('X-Signature', '')
    if not verify_signature(body, signature):
        request.state.result = "invalid_signature"
        webhook_requests_total.labels(result="invalid_signature").inc()
        logger.error("Invalid signature", extra={'result': 'invalid_signature'})
        raise HTTPException(status_code=401, detail="invalid signature")
    
    # Parse and validate message
    try:
        message = WebhookMessage.model_validate_json(body)
    except Exception as e:
        request.state.result = "validation_error"
        webhook_requests_total.labels(result="validation_error").inc()
        logger.error(f"Validation error: {e}", extra={'result': 'validation_error'})
        raise HTTPException(status_code=422, detail=str(e))
    
    # Insert into database
    success, is_duplicate = insert_message(
        message.message_id,
        message.from_,
        message.to,
        message.ts,
        message.text
    )
    
    # Track state for logging
    request.state.message_id = message.message_id
    request.state.dup = is_duplicate
    
    if is_duplicate:
        request.state.result = "duplicate"
        webhook_requests_total.labels(result="duplicate").inc()
    else:
        request.state.result = "created"
        webhook_requests_total.labels(result="created").inc()
    
    return {"status": "ok"}

@app.get("/messages", response_model=MessagesListResponse)
async def list_messages(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    from_: Optional[str] = Query(default=None, alias="from"),
    since: Optional[str] = Query(default=None),
    q: Optional[str] = Query(default=None)
):
    """List messages with pagination and filters"""
    messages, total = get_messages(
        limit=limit,
        offset=offset,
        from_filter=from_,
        since=since,
        q=q
    )
    
    return {
        "data": messages,
        "total": total,
        "limit": limit,
        "offset": offset
    }

@app.get("/stats", response_model=StatsResponse)
async def get_message_stats():
    """Get message statistics"""
    return get_stats()

@app.get("/health/live")
async def liveness():
    """Liveness probe"""
    return {"status": "ok"}

@app.get("/health/ready")
async def readiness():
    """Readiness probe"""
    if not settings.WEBHOOK_SECRET:
        raise HTTPException(status_code=503, detail="WEBHOOK_SECRET not set")
    
    if not check_db_ready():
        raise HTTPException(status_code=503, detail="Database not ready")
    
    return {"status": "ready"}

@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    return Response(content=get_metrics(), media_type=CONTENT_TYPE_LATEST)



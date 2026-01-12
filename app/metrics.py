from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from prometheus_client import REGISTRY

# HTTP requests counter
http_requests_total = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['path', 'status']
)

# Webhook processing counter
webhook_requests_total = Counter(
    'webhook_requests_total',
    'Total webhook requests',
    ['result']
)

# Request latency histogram
request_latency_ms = Histogram(
    'request_latency_ms',
    'Request latency in milliseconds',
    buckets=[100, 500, 1000, 5000, 10000]
)

def get_metrics():
    """Get Prometheus metrics in text format"""
    return generate_latest(REGISTRY)



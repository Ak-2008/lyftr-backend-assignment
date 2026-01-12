import json
import logging
import sys
import time
from datetime import datetime
from contextvars import ContextVar
import uuid

request_id_var: ContextVar[str] = ContextVar('request_id', default='')

class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_data = {
            "ts": datetime.utcnow().isoformat() + 'Z',
            "level": record.levelname,
            "message": record.getMessage(),
        }
        
        # Add request_id if available
        request_id = request_id_var.get('')
        if request_id:
            log_data["request_id"] = request_id
        
        # Add extra fields
        for key in ['method', 'path', 'status', 'latency_ms', 'message_id', 'dup', 'result']:
            if hasattr(record, key):
                log_data[key] = getattr(record, key)
        
        return json.dumps(log_data)

def setup_logging(log_level: str = "INFO"):
    """Setup JSON logging"""
    logger = logging.getLogger()
    logger.setLevel(log_level.upper())
    
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JSONFormatter())
    
    logger.handlers.clear()
    logger.addHandler(handler)
    
    return logger

def get_logger():
    return logging.getLogger()



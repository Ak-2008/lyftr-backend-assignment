from pydantic import BaseModel, Field, field_validator
from typing import Optional
import re
from datetime import datetime

class WebhookMessage(BaseModel):
    message_id: str = Field(..., min_length=1)
    from_: str = Field(..., alias="from")
    to: str = Field(..., min_length=1)
    ts: str
    text: Optional[str] = Field(None, max_length=4096)
    
    @field_validator('from_', 'to')
    @classmethod
    def validate_e164(cls, v: str) -> str:
        if not re.match(r'^\+\d+$', v):
            raise ValueError('Must be in E.164 format (start with + followed by digits)')
        return v
    
    @field_validator('ts')
    @classmethod
    def validate_iso8601(cls, v: str) -> str:
        if not v.endswith('Z'):
            raise ValueError('Timestamp must end with Z')
        try:
            datetime.fromisoformat(v.replace('Z', '+00:00'))
        except ValueError:
            raise ValueError('Invalid ISO-8601 timestamp')
        return v

class MessageResponse(BaseModel):
    message_id: str
    from_: str = Field(..., alias="from")
    to: str
    ts: str
    text: Optional[str]
    
    class Config:
        populate_by_name = True

class MessagesListResponse(BaseModel):
    data: list[MessageResponse]
    total: int
    limit: int
    offset: int

class StatsResponse(BaseModel):
    total_messages: int
    senders_count: int
    messages_per_sender: list[dict]
    first_message_ts: Optional[str]
    last_message_ts: Optional[str]



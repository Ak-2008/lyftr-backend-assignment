import sqlite3
from datetime import datetime
from typing import Optional, List, Tuple
from contextlib import contextmanager
from app.config import settings

def get_db_path() -> str:
    """Extract file path from DATABASE_URL"""
    url = settings.DATABASE_URL
    if url.startswith("sqlite:///"):
        return url.replace("sqlite:///", "")
    return "/data/app.db"

@contextmanager
def get_db_connection():
    """Context manager for database connections"""
    conn = sqlite3.connect(get_db_path())
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def init_db():
    """Initialize the database schema"""
    with get_db_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                message_id TEXT PRIMARY KEY,
                from_msisdn TEXT NOT NULL,
                to_msisdn TEXT NOT NULL,
                ts TEXT NOT NULL,
                text TEXT,
                created_at TEXT NOT NULL
            )
        """)
        # Create indexes for filtering
        conn.execute("CREATE INDEX IF NOT EXISTS idx_from_msisdn ON messages(from_msisdn)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_ts ON messages(ts)")

def check_db_ready() -> bool:
    """Check if database is accessible"""
    try:
        with get_db_connection() as conn:
            conn.execute("SELECT 1")
        return True
    except Exception:
        return False

def insert_message(message_id: str, from_msisdn: str, to_msisdn: str, 
                  ts: str, text: Optional[str]) -> Tuple[bool, bool]:
    """
    Insert a message into the database.
    Returns (success, is_duplicate)
    """
    try:
        with get_db_connection() as conn:
            created_at = datetime.utcnow().isoformat() + 'Z'
            conn.execute("""
                INSERT INTO messages (message_id, from_msisdn, to_msisdn, ts, text, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (message_id, from_msisdn, to_msisdn, ts, text, created_at))
            return True, False
    except sqlite3.IntegrityError:
        # Duplicate message_id
        return True, True

def get_messages(limit: int = 50, offset: int = 0, from_filter: Optional[str] = None,
                since: Optional[str] = None, q: Optional[str] = None) -> Tuple[List[dict], int]:
    """
    Get messages with pagination and filters.
    Returns (messages, total_count)
    """
    with get_db_connection() as conn:
        # Build WHERE clause
        where_clauses = []
        params = []
        
        if from_filter:
            where_clauses.append("from_msisdn = ?")
            params.append(from_filter)
        
        if since:
            where_clauses.append("ts >= ?")
            params.append(since)
        
        if q:
            where_clauses.append("text LIKE ?")
            params.append(f"%{q}%")
        
        where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"
        
        # Get total count
        count_query = f"SELECT COUNT(*) as total FROM messages WHERE {where_sql}"
        total = conn.execute(count_query, params).fetchone()['total']
        
        # Get messages
        query = f"""
            SELECT message_id, from_msisdn as 'from', to_msisdn as 'to', ts, text
            FROM messages
            WHERE {where_sql}
            ORDER BY ts ASC, message_id ASC
            LIMIT ? OFFSET ?
        """
        params.extend([limit, offset])
        
        rows = conn.execute(query, params).fetchall()
        messages = [dict(row) for row in rows]
        
        return messages, total

def get_stats() -> dict:
    """Get message statistics"""
    with get_db_connection() as conn:
        # Total messages
        total = conn.execute("SELECT COUNT(*) as cnt FROM messages").fetchone()['cnt']
        
        # Unique senders count
        senders = conn.execute("SELECT COUNT(DISTINCT from_msisdn) as cnt FROM messages").fetchone()['cnt']
        
        # Messages per sender (top 10)
        per_sender = conn.execute("""
            SELECT from_msisdn as 'from', COUNT(*) as count
            FROM messages
            GROUP BY from_msisdn
            ORDER BY count DESC
            LIMIT 10
        """).fetchall()
        
        messages_per_sender = [{"from": row['from'], "count": row['count']} for row in per_sender]
        
        # First and last message timestamps
        first = conn.execute("SELECT MIN(ts) as ts FROM messages").fetchone()['ts']
        last = conn.execute("SELECT MAX(ts) as ts FROM messages").fetchone()['ts']
        
        return {
            "total_messages": total,
            "senders_count": senders,
            "messages_per_sender": messages_per_sender,
            "first_message_ts": first,
            "last_message_ts": last
        }



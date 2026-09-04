# backend/app/security/audit.py
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from app.security.audit_model import AuditLog

logger = logging.getLogger(__name__)

def log_action_sync(db: AsyncSession, actor: str, action: str, target_type: str, target_id: str, details: dict = None):
    """
    Appends an audit log to the current database session.
    It does NOT commit the session; it relies on the calling business logic 
    to commit so the action and the audit record are saved atomically.
    """
    try:
        audit_entry = AuditLog(
            actor=actor,
            action=action,
            target_type=target_type,
            target_id=str(target_id),
            details=details or {}
        )
        db.add(audit_entry)
        logger.info(f"Audit: [{actor}] performed [{action}] on [{target_type}:{target_id}]")
    except Exception as e:
        logger.error(f"Failed to record audit log. Alert administrator: {e}")
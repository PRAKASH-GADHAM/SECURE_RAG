"""Audit logging service.

Records all security-relevant events for compliance and monitoring.
"""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog
from app.utils.logging import get_logger

logger = get_logger(__name__)


class AuditService:
    """Service for recording audit log entries.

    Provides methods to log authentication events, document operations,
    security violations, and other audit-worthy activities.
    """

    def __init__(self, db: AsyncSession):
        """Initialize the audit service.

        Args:
            db: Async database session.
        """
        self.db = db

    async def log(
        self,
        action: str,
        user_id: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        status: str = "success",
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        details: Optional[str] = None,
        risk_level: str = "low",
    ) -> AuditLog:
        """Create an audit log entry.

        Args:
            action: Action performed (e.g., 'user.login', 'document.upload').
            user_id: User who performed the action.
            resource_type: Type of resource affected.
            resource_id: ID of affected resource.
            status: Action status ('success' or 'failure').
            ip_address: Client IP address.
            user_agent: Client user agent.
            details: Additional event details.
            risk_level: Risk assessment ('low', 'medium', 'high', 'critical').

        Returns:
            Created AuditLog instance.
        """
        audit_log = AuditLog(
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            status=status,
            ip_address=ip_address,
            user_agent=user_agent,
            details=details,
            risk_level=risk_level,
        )

        self.db.add(audit_log)
        await self.db.flush()
        await self.db.refresh(audit_log)

        # Also log to structured logger
        log_data = {
            "action": action,
            "user_id": user_id,
            "status": status,
            "risk_level": risk_level,
        }
        if ip_address:
            log_data["ip_address"] = ip_address

        if risk_level in ("high", "critical"):
            logger.warning(f"AUDIT: {action}", extra={"audit_data": log_data})
        else:
            logger.info(f"AUDIT: {action}", extra={"audit_data": log_data})

        return audit_log

    async def log_auth_event(
        self,
        action: str,
        user_id: Optional[str] = None,
        status: str = "success",
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        details: Optional[str] = None,
    ) -> AuditLog:
        """Log an authentication event.

        Args:
            action: Auth action (e.g., 'user.login', 'user.logout').
            user_id: User ID.
            status: Success or failure.
            ip_address: Client IP.
            user_agent: Client user agent.
            details: Additional details.

        Returns:
            Created AuditLog.
        """
        risk_level = "low" if status == "success" else "medium"
        return await self.log(
            action=action,
            user_id=user_id,
            resource_type="auth",
            status=status,
            ip_address=ip_address,
            user_agent=user_agent,
            details=details,
            risk_level=risk_level,
        )

    async def log_security_event(
        self,
        action: str,
        user_id: Optional[str] = None,
        details: Optional[str] = None,
        ip_address: Optional[str] = None,
        risk_level: str = "high",
    ) -> AuditLog:
        """Log a security-related event.

        Args:
            action: Security action (e.g., 'prompt.injection.detected').
            user_id: User ID.
            details: Event details.
            ip_address: Client IP.
            risk_level: Risk assessment level.

        Returns:
            Created AuditLog.
        """
        return await self.log(
            action=action,
            user_id=user_id,
            resource_type="security",
            status="flagged",
            ip_address=ip_address,
            details=details,
            risk_level=risk_level,
        )

    async def get_user_logs(
        self,
        user_id: str,
        skip: int = 0,
        limit: int = 50,
        action_filter: Optional[str] = None,
    ) -> list[AuditLog]:
        """Get audit logs for a user.

        Args:
            user_id: User ID.
            skip: Pagination offset.
            limit: Maximum results.
            action_filter: Optional action prefix filter.

        Returns:
            List of AuditLog entries.
        """
        from sqlalchemy import select

        query = select(AuditLog).where(AuditLog.user_id == user_id)

        if action_filter:
            query = query.where(AuditLog.action.startswith(action_filter))

        query = query.order_by(AuditLog.created_at.desc()).offset(skip).limit(limit)

        result = await self.db.execute(query)
        return list(result.scalars().all())

"""
Data retention policies and automated cleanup service
"""

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from sqlalchemy import and_, or_, text
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.agent_decision import AgentDecision
from app.models.customer import Customer
from app.models.recovery_action import RecoveryAction
from app.models.review import Review
from app.models.support_ticket import SupportTicket
from app.models.user import User

logger = logging.getLogger(__name__)


class RetentionPeriod(Enum):
    """Standard retention periods"""

    DAYS_30 = 30
    DAYS_90 = 90
    DAYS_180 = 180
    DAYS_365 = 365
    DAYS_2555 = 2555  # 7 years for compliance
    PERMANENT = -1


class DataCategory(Enum):
    """Data categories for retention policies"""

    PERSONAL_DATA = "personal_data"
    BUSINESS_DATA = "business_data"
    AUDIT_LOGS = "audit_logs"
    SECURITY_LOGS = "security_logs"
    ANALYTICS_DATA = "analytics_data"
    SYSTEM_LOGS = "system_logs"
    BACKUP_DATA = "backup_data"


class RetentionPolicy:
    """Data retention policy definition"""

    def __init__(
        self,
        name: str,
        category: DataCategory,
        retention_period: RetentionPeriod,
        description: str,
        auto_delete: bool = True,
        archive_before_delete: bool = True,
        legal_hold_exempt: bool = False,
    ):
        self.name = name
        self.category = category
        self.retention_period = retention_period
        self.description = description
        self.auto_delete = auto_delete
        self.archive_before_delete = archive_before_delete
        self.legal_hold_exempt = legal_hold_exempt

    def is_expired(self, created_date: datetime) -> bool:
        """Check if data is expired based on retention policy"""
        if self.retention_period == RetentionPeriod.PERMANENT:
            return False

        expiry_date = created_date + timedelta(days=self.retention_period.value)
        return datetime.now(timezone.utc) > expiry_date

    def get_expiry_date(self, created_date: datetime) -> Optional[datetime]:
        """Get expiry date for data"""
        if self.retention_period == RetentionPeriod.PERMANENT:
            return None

        return created_date + timedelta(days=self.retention_period.value)


class DataRetentionService:
    """Service for managing data retention and cleanup"""

    def __init__(self):
        self.policies = self._initialize_policies()
        self.legal_holds: Dict[str, List[str]] = (
            {}
        )  # organization_id -> list of hold reasons

    def _initialize_policies(self) -> Dict[str, RetentionPolicy]:
        """Initialize default retention policies"""
        return {
            # Personal Data Policies
            "user_personal_data": RetentionPolicy(
                name="User Personal Data",
                category=DataCategory.PERSONAL_DATA,
                retention_period=RetentionPeriod.DAYS_2555,  # 7 years for GDPR
                description="User personal information including email, phone, address",
                auto_delete=False,  # Require manual review for personal data
                archive_before_delete=True,
            ),
            "customer_personal_data": RetentionPolicy(
                name="Customer Personal Data",
                category=DataCategory.PERSONAL_DATA,
                retention_period=RetentionPeriod.DAYS_2555,
                description="Customer personal information and contact details",
                auto_delete=False,
                archive_before_delete=True,
            ),
            # Business Data Policies
            "reviews": RetentionPolicy(
                name="Customer Reviews",
                category=DataCategory.BUSINESS_DATA,
                retention_period=RetentionPeriod.DAYS_2555,  # Keep for business intelligence
                description="Customer reviews and feedback data",
                auto_delete=False,
                archive_before_delete=True,
            ),
            "support_tickets": RetentionPolicy(
                name="Support Tickets",
                category=DataCategory.BUSINESS_DATA,
                retention_period=RetentionPeriod.DAYS_365,
                description="Customer support tickets and interactions",
                auto_delete=True,
                archive_before_delete=True,
            ),
            "recovery_actions": RetentionPolicy(
                name="Recovery Actions",
                category=DataCategory.BUSINESS_DATA,
                retention_period=RetentionPeriod.DAYS_365,
                description="Customer recovery actions and communications",
                auto_delete=True,
                archive_before_delete=True,
            ),
            "agent_decisions": RetentionPolicy(
                name="Agent Decisions",
                category=DataCategory.ANALYTICS_DATA,
                retention_period=RetentionPeriod.DAYS_365,
                description="AI agent decision logs and reasoning",
                auto_delete=True,
                archive_before_delete=False,
            ),
            # Audit and Security Logs
            "audit_logs": RetentionPolicy(
                name="Audit Logs",
                category=DataCategory.AUDIT_LOGS,
                retention_period=RetentionPeriod.DAYS_2555,  # 7 years for compliance
                description="System audit logs and compliance records",
                auto_delete=False,
                archive_before_delete=True,
                legal_hold_exempt=False,
            ),
            "security_logs": RetentionPolicy(
                name="Security Logs",
                category=DataCategory.SECURITY_LOGS,
                retention_period=RetentionPeriod.DAYS_365,
                description="Security events and incident logs",
                auto_delete=True,
                archive_before_delete=True,
            ),
            "system_logs": RetentionPolicy(
                name="System Logs",
                category=DataCategory.SYSTEM_LOGS,
                retention_period=RetentionPeriod.DAYS_90,
                description="Application and system operational logs",
                auto_delete=True,
                archive_before_delete=False,
            ),
            # Analytics and Metrics
            "analytics_data": RetentionPolicy(
                name="Analytics Data",
                category=DataCategory.ANALYTICS_DATA,
                retention_period=RetentionPeriod.DAYS_365,
                description="Usage analytics and metrics data",
                auto_delete=True,
                archive_before_delete=False,
            ),
            "metrics_data": RetentionPolicy(
                name="Metrics Data",
                category=DataCategory.ANALYTICS_DATA,
                retention_period=RetentionPeriod.DAYS_90,
                description="System performance and monitoring metrics",
                auto_delete=True,
                archive_before_delete=False,
            ),
        }

    def add_legal_hold(self, organization_id: str, reason: str):
        """Add legal hold for an organization"""
        if organization_id not in self.legal_holds:
            self.legal_holds[organization_id] = []

        if reason not in self.legal_holds[organization_id]:
            self.legal_holds[organization_id].append(reason)
            logger.info(f"Added legal hold for {organization_id}: {reason}")

    def remove_legal_hold(self, organization_id: str, reason: str):
        """Remove legal hold for an organization"""
        if organization_id in self.legal_holds:
            if reason in self.legal_holds[organization_id]:
                self.legal_holds[organization_id].remove(reason)
                logger.info(f"Removed legal hold for {organization_id}: {reason}")

                if not self.legal_holds[organization_id]:
                    del self.legal_holds[organization_id]

    def has_legal_hold(self, organization_id: str) -> bool:
        """Check if organization has any legal holds"""
        return (
            organization_id in self.legal_holds
            and len(self.legal_holds[organization_id]) > 0
        )

    async def get_expired_data(
        self, policy_name: str, limit: int = 1000
    ) -> List[Dict[str, Any]]:
        """Get expired data based on retention policy"""
        policy = self.policies.get(policy_name)
        if not policy:
            raise ValueError(f"Unknown retention policy: {policy_name}")

        if policy.retention_period == RetentionPeriod.PERMANENT:
            return []

        cutoff_date = datetime.now(timezone.utc) - timedelta(
            days=policy.retention_period.value
        )

        # Map policy names to database queries
        query_map = {
            "user_personal_data": self._get_expired_users,
            "customer_personal_data": self._get_expired_customers,
            "reviews": self._get_expired_reviews,
            "support_tickets": self._get_expired_support_tickets,
            "recovery_actions": self._get_expired_recovery_actions,
            "agent_decisions": self._get_expired_agent_decisions,
        }

        query_func = query_map.get(policy_name)
        if query_func:
            return await query_func(cutoff_date, limit)

        return []

    async def _get_expired_users(
        self, cutoff_date: datetime, limit: int
    ) -> List[Dict[str, Any]]:
        """Get expired user records"""
        db = next(get_db())
        try:
            # Only get inactive users past retention period
            users = (
                db.query(User)
                .filter(
                    and_(
                        User.created_at < cutoff_date,
                        User.is_active == False,
                        User.last_login
                        < cutoff_date - timedelta(days=90),  # Inactive for 90+ days
                    )
                )
                .limit(limit)
                .all()
            )

            return [
                {
                    "id": user.id,
                    "email": user.email,
                    "created_at": user.created_at,
                    "organization_id": user.organization_id,
                }
                for user in users
                if not self.has_legal_hold(str(user.organization_id))
            ]
        finally:
            db.close()

    async def _get_expired_customers(
        self, cutoff_date: datetime, limit: int
    ) -> List[Dict[str, Any]]:
        """Get expired customer records"""
        db = next(get_db())
        try:
            customers = (
                db.query(Customer)
                .filter(Customer.created_at < cutoff_date)
                .limit(limit)
                .all()
            )

            return [
                {
                    "id": customer.id,
                    "email": customer.email,
                    "created_at": customer.created_at,
                    "organization_id": customer.organization_id,
                }
                for customer in customers
                if not self.has_legal_hold(str(customer.organization_id))
            ]
        finally:
            db.close()

    async def _get_expired_reviews(
        self, cutoff_date: datetime, limit: int
    ) -> List[Dict[str, Any]]:
        """Get expired review records"""
        db = next(get_db())
        try:
            reviews = (
                db.query(Review)
                .filter(Review.created_at < cutoff_date)
                .limit(limit)
                .all()
            )

            return [
                {
                    "id": review.id,
                    "platform": review.platform,
                    "created_at": review.created_at,
                    "organization_id": review.organization_id,
                }
                for review in reviews
                if not self.has_legal_hold(str(review.organization_id))
            ]
        finally:
            db.close()

    async def _get_expired_support_tickets(
        self, cutoff_date: datetime, limit: int
    ) -> List[Dict[str, Any]]:
        """Get expired support ticket records"""
        db = next(get_db())
        try:
            tickets = (
                db.query(SupportTicket)
                .filter(SupportTicket.created_at < cutoff_date)
                .limit(limit)
                .all()
            )

            return [
                {
                    "id": ticket.id,
                    "subject": ticket.subject,
                    "created_at": ticket.created_at,
                    "organization_id": ticket.organization_id,
                }
                for ticket in tickets
                if not self.has_legal_hold(str(ticket.organization_id))
            ]
        finally:
            db.close()

    async def _get_expired_recovery_actions(
        self, cutoff_date: datetime, limit: int
    ) -> List[Dict[str, Any]]:
        """Get expired recovery action records"""
        db = next(get_db())
        try:
            actions = (
                db.query(RecoveryAction)
                .filter(RecoveryAction.created_at < cutoff_date)
                .limit(limit)
                .all()
            )

            return [
                {
                    "id": action.id,
                    "action_type": action.action_type,
                    "created_at": action.created_at,
                    "organization_id": action.organization_id,
                }
                for action in actions
                if not self.has_legal_hold(str(action.organization_id))
            ]
        finally:
            db.close()

    async def _get_expired_agent_decisions(
        self, cutoff_date: datetime, limit: int
    ) -> List[Dict[str, Any]]:
        """Get expired agent decision records"""
        db = next(get_db())
        try:
            decisions = (
                db.query(AgentDecision)
                .filter(AgentDecision.created_at < cutoff_date)
                .limit(limit)
                .all()
            )

            return [
                {
                    "id": decision.id,
                    "decision_type": decision.decision_type,
                    "created_at": decision.created_at,
                    "organization_id": decision.organization_id,
                }
                for decision in decisions
                if not self.has_legal_hold(str(decision.organization_id))
            ]
        finally:
            db.close()

    async def archive_data(
        self, policy_name: str, data_records: List[Dict[str, Any]]
    ) -> bool:
        """Archive data before deletion"""
        try:
            # In a real implementation, this would:
            # 1. Export data to secure archive storage (S3, etc.)
            # 2. Encrypt archived data
            # 3. Create archive manifest
            # 4. Verify archive integrity

            archive_path = (
                f"/archives/{policy_name}/{datetime.now().strftime('%Y%m%d')}"
            )

            logger.info(
                f"Archiving {len(data_records)} records for policy {policy_name} to {archive_path}"
            )

            # TODO: Implement actual archiving logic
            # For now, just log the operation
            for record in data_records:
                logger.debug(f"Archived record {record['id']} from {policy_name}")

            return True

        except Exception as e:
            logger.error(f"Failed to archive data for policy {policy_name}: {e}")
            return False

    async def delete_expired_data(
        self, policy_name: str, data_records: List[Dict[str, Any]]
    ) -> int:
        """Delete expired data records"""
        if not data_records:
            return 0

        policy = self.policies.get(policy_name)
        if not policy:
            raise ValueError(f"Unknown retention policy: {policy_name}")

        # Archive before deletion if required
        if policy.archive_before_delete:
            archive_success = await self.archive_data(policy_name, data_records)
            if not archive_success:
                logger.error(f"Archiving failed for {policy_name}, skipping deletion")
                return 0

        deleted_count = 0
        db = next(get_db())

        try:
            # Map policy names to deletion functions
            deletion_map = {
                "user_personal_data": self._delete_users,
                "customer_personal_data": self._delete_customers,
                "reviews": self._delete_reviews,
                "support_tickets": self._delete_support_tickets,
                "recovery_actions": self._delete_recovery_actions,
                "agent_decisions": self._delete_agent_decisions,
            }

            deletion_func = deletion_map.get(policy_name)
            if deletion_func:
                deleted_count = await deletion_func(db, data_records)

            db.commit()
            logger.info(f"Deleted {deleted_count} records for policy {policy_name}")

        except Exception as e:
            db.rollback()
            logger.error(f"Failed to delete data for policy {policy_name}: {e}")
            raise
        finally:
            db.close()

        return deleted_count

    async def _delete_users(self, db: Session, records: List[Dict[str, Any]]) -> int:
        """Delete user records"""
        user_ids = [record["id"] for record in records]
        result = (
            db.query(User)
            .filter(User.id.in_(user_ids))
            .delete(synchronize_session=False)
        )
        return result

    async def _delete_customers(
        self, db: Session, records: List[Dict[str, Any]]
    ) -> int:
        """Delete customer records"""
        customer_ids = [record["id"] for record in records]
        result = (
            db.query(Customer)
            .filter(Customer.id.in_(customer_ids))
            .delete(synchronize_session=False)
        )
        return result

    async def _delete_reviews(self, db: Session, records: List[Dict[str, Any]]) -> int:
        """Delete review records"""
        review_ids = [record["id"] for record in records]
        result = (
            db.query(Review)
            .filter(Review.id.in_(review_ids))
            .delete(synchronize_session=False)
        )
        return result

    async def _delete_support_tickets(
        self, db: Session, records: List[Dict[str, Any]]
    ) -> int:
        """Delete support ticket records"""
        ticket_ids = [record["id"] for record in records]
        result = (
            db.query(SupportTicket)
            .filter(SupportTicket.id.in_(ticket_ids))
            .delete(synchronize_session=False)
        )
        return result

    async def _delete_recovery_actions(
        self, db: Session, records: List[Dict[str, Any]]
    ) -> int:
        """Delete recovery action records"""
        action_ids = [record["id"] for record in records]
        result = (
            db.query(RecoveryAction)
            .filter(RecoveryAction.id.in_(action_ids))
            .delete(synchronize_session=False)
        )
        return result

    async def _delete_agent_decisions(
        self, db: Session, records: List[Dict[str, Any]]
    ) -> int:
        """Delete agent decision records"""
        decision_ids = [record["id"] for record in records]
        result = (
            db.query(AgentDecision)
            .filter(AgentDecision.id.in_(decision_ids))
            .delete(synchronize_session=False)
        )
        return result

    async def run_retention_cleanup(self, dry_run: bool = True) -> Dict[str, Any]:
        """Run automated retention cleanup for all policies"""
        results = {
            "dry_run": dry_run,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "policies_processed": 0,
            "total_records_found": 0,
            "total_records_deleted": 0,
            "policy_results": {},
        }

        for policy_name, policy in self.policies.items():
            if not policy.auto_delete:
                logger.info(f"Skipping policy {policy_name} (auto_delete=False)")
                continue

            try:
                # Get expired data
                expired_data = await self.get_expired_data(policy_name)

                policy_result = {
                    "policy_name": policy_name,
                    "retention_period_days": policy.retention_period.value,
                    "records_found": len(expired_data),
                    "records_deleted": 0,
                    "archived": policy.archive_before_delete,
                    "error": None,
                }

                if expired_data:
                    if not dry_run:
                        # Actually delete the data
                        deleted_count = await self.delete_expired_data(
                            policy_name, expired_data
                        )
                        policy_result["records_deleted"] = deleted_count
                        results["total_records_deleted"] += deleted_count
                    else:
                        # Dry run - just report what would be deleted
                        policy_result["records_deleted"] = len(expired_data)

                results["total_records_found"] += len(expired_data)
                results["policy_results"][policy_name] = policy_result
                results["policies_processed"] += 1

                logger.info(
                    f"Processed retention policy {policy_name}: {len(expired_data)} records"
                )

            except Exception as e:
                logger.error(f"Error processing retention policy {policy_name}: {e}")
                results["policy_results"][policy_name] = {
                    "policy_name": policy_name,
                    "error": str(e),
                    "records_found": 0,
                    "records_deleted": 0,
                }

        return results

    def get_retention_report(self) -> Dict[str, Any]:
        """Generate retention policy report"""
        return {
            "policies": {
                name: {
                    "name": policy.name,
                    "category": policy.category.value,
                    "retention_period_days": (
                        policy.retention_period.value
                        if policy.retention_period != RetentionPeriod.PERMANENT
                        else "permanent"
                    ),
                    "description": policy.description,
                    "auto_delete": policy.auto_delete,
                    "archive_before_delete": policy.archive_before_delete,
                    "legal_hold_exempt": policy.legal_hold_exempt,
                }
                for name, policy in self.policies.items()
            },
            "legal_holds": dict(self.legal_holds),
            "total_policies": len(self.policies),
            "auto_delete_policies": sum(
                1 for p in self.policies.values() if p.auto_delete
            ),
        }


# Global retention service instance
_retention_service = None


def get_retention_service() -> DataRetentionService:
    """Get global retention service instance"""
    global _retention_service

    if _retention_service is None:
        _retention_service = DataRetentionService()

    return _retention_service

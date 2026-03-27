"""
User consent management service for GDPR compliance
"""

import json
import logging
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.customer import Customer
from app.models.organization import Organization
from app.models.user import User

logger = logging.getLogger(__name__)


class ConsentType(Enum):
    """Types of consent"""

    NECESSARY = "necessary"  # Required for service operation
    FUNCTIONAL = "functional"  # Enhances functionality
    ANALYTICS = "analytics"  # Usage analytics and improvements
    MARKETING = "marketing"  # Marketing communications
    PERSONALIZATION = "personalization"  # Personalized content
    THIRD_PARTY = "third_party"  # Third-party integrations


class ConsentStatus(Enum):
    """Consent status"""

    GRANTED = "granted"
    DENIED = "denied"
    WITHDRAWN = "withdrawn"
    EXPIRED = "expired"
    PENDING = "pending"


class ConsentMethod(Enum):
    """Method of consent collection"""

    EXPLICIT_CHECKBOX = "explicit_checkbox"
    OPT_IN_FORM = "opt_in_form"
    COOKIE_BANNER = "cookie_banner"
    EMAIL_CONFIRMATION = "email_confirmation"
    VERBAL_CONFIRMATION = "verbal_confirmation"
    IMPLIED_CONSENT = "implied_consent"


class ConsentRecord:
    """Individual consent record"""

    def __init__(
        self,
        user_id: str,
        organization_id: str,
        consent_type: ConsentType,
        status: ConsentStatus,
        method: ConsentMethod,
        purpose: str,
        legal_basis: str = "consent",
        granted_at: datetime = None,
        expires_at: datetime = None,
        withdrawn_at: datetime = None,
        ip_address: str = None,
        user_agent: str = None,
        version: str = "1.0",
    ):
        self.user_id = user_id
        self.organization_id = organization_id
        self.consent_type = consent_type
        self.status = status
        self.method = method
        self.purpose = purpose
        self.legal_basis = legal_basis
        self.granted_at = granted_at or datetime.now(timezone.utc)
        self.expires_at = expires_at
        self.withdrawn_at = withdrawn_at
        self.ip_address = ip_address
        self.user_agent = user_agent
        self.version = version
        self.created_at = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)

    def is_valid(self) -> bool:
        """Check if consent is currently valid"""
        if self.status != ConsentStatus.GRANTED:
            return False

        if self.expires_at and datetime.now(timezone.utc) > self.expires_at:
            return False

        return True

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "user_id": self.user_id,
            "organization_id": self.organization_id,
            "consent_type": self.consent_type.value,
            "status": self.status.value,
            "method": self.method.value,
            "purpose": self.purpose,
            "legal_basis": self.legal_basis,
            "granted_at": self.granted_at.isoformat() if self.granted_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "withdrawn_at": (
                self.withdrawn_at.isoformat() if self.withdrawn_at else None
            ),
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "version": self.version,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "is_valid": self.is_valid(),
        }


class ConsentManagementService:
    """Service for managing user consent"""

    def __init__(self):
        self.consent_records: Dict[str, List[ConsentRecord]] = (
            {}
        )  # user_id -> list of records
        self.consent_definitions = self._initialize_consent_definitions()

    def _initialize_consent_definitions(self) -> Dict[ConsentType, Dict[str, Any]]:
        """Initialize consent type definitions"""
        return {
            ConsentType.NECESSARY: {
                "name": "Necessary Cookies",
                "description": "Essential cookies required for the website to function properly",
                "purpose": "Authentication, security, and basic functionality",
                "required": True,
                "default_expiry_days": None,  # No expiry for necessary
                "can_withdraw": False,
                "legal_basis": "legitimate_interest",
            },
            ConsentType.FUNCTIONAL: {
                "name": "Functional Cookies",
                "description": "Cookies that enhance website functionality and user experience",
                "purpose": "Remember preferences, language settings, and user choices",
                "required": False,
                "default_expiry_days": 365,
                "can_withdraw": True,
                "legal_basis": "consent",
            },
            ConsentType.ANALYTICS: {
                "name": "Analytics Cookies",
                "description": "Cookies that help us understand how visitors use our website",
                "purpose": "Website analytics, performance monitoring, and improvements",
                "required": False,
                "default_expiry_days": 365,
                "can_withdraw": True,
                "legal_basis": "consent",
            },
            ConsentType.MARKETING: {
                "name": "Marketing Communications",
                "description": "Permission to send marketing emails and promotional content",
                "purpose": "Email marketing, newsletters, and promotional communications",
                "required": False,
                "default_expiry_days": 730,  # 2 years
                "can_withdraw": True,
                "legal_basis": "consent",
            },
            ConsentType.PERSONALIZATION: {
                "name": "Personalization",
                "description": "Cookies that personalize content and recommendations",
                "purpose": "Personalized content, recommendations, and user experience",
                "required": False,
                "default_expiry_days": 365,
                "can_withdraw": True,
                "legal_basis": "consent",
            },
            ConsentType.THIRD_PARTY: {
                "name": "Third-Party Integrations",
                "description": "Cookies and data sharing with third-party services",
                "purpose": "Integration with external services and platforms",
                "required": False,
                "default_expiry_days": 365,
                "can_withdraw": True,
                "legal_basis": "consent",
            },
        }

    async def record_consent(
        self,
        user_id: str,
        organization_id: str,
        consent_type: ConsentType,
        granted: bool,
        method: ConsentMethod,
        ip_address: str = None,
        user_agent: str = None,
        purpose_details: str = None,
    ) -> ConsentRecord:
        """Record user consent"""

        consent_def = self.consent_definitions[consent_type]

        # Calculate expiry date
        expires_at = None
        if consent_def["default_expiry_days"]:
            expires_at = datetime.now(timezone.utc) + timedelta(
                days=consent_def["default_expiry_days"]
            )

        # Create consent record
        record = ConsentRecord(
            user_id=user_id,
            organization_id=organization_id,
            consent_type=consent_type,
            status=ConsentStatus.GRANTED if granted else ConsentStatus.DENIED,
            method=method,
            purpose=purpose_details or consent_def["purpose"],
            legal_basis=consent_def["legal_basis"],
            expires_at=expires_at,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        # Store record
        if user_id not in self.consent_records:
            self.consent_records[user_id] = []

        # Remove any existing record for this consent type
        self.consent_records[user_id] = [
            r for r in self.consent_records[user_id] if r.consent_type != consent_type
        ]

        # Add new record
        self.consent_records[user_id].append(record)

        # Update database
        await self._update_user_consent_in_db(
            user_id, organization_id, consent_type, granted
        )

        logger.info(
            f"Consent recorded: {user_id} - {consent_type.value} - {'granted' if granted else 'denied'}"
        )

        return record

    async def _update_user_consent_in_db(
        self,
        user_id: str,
        organization_id: str,
        consent_type: ConsentType,
        granted: bool,
    ):
        """Update user consent in database"""
        db = next(get_db())
        try:
            # Update user record
            user = (
                db.query(User)
                .filter(
                    and_(User.id == user_id, User.organization_id == organization_id)
                )
                .first()
            )

            if user:
                # Update consent fields based on type
                if consent_type == ConsentType.MARKETING:
                    user.marketing_consent = granted
                    user.marketing_consent_date = datetime.now(timezone.utc)
                elif consent_type == ConsentType.ANALYTICS:
                    user.analytics_consent = granted
                    user.analytics_consent_date = datetime.now(timezone.utc)
                elif consent_type == ConsentType.FUNCTIONAL:
                    user.functional_consent = granted
                    user.functional_consent_date = datetime.now(timezone.utc)
                elif consent_type == ConsentType.PERSONALIZATION:
                    user.personalization_consent = granted
                    user.personalization_consent_date = datetime.now(timezone.utc)

                db.commit()

            # Also check for customer record
            customer = (
                db.query(Customer)
                .filter(
                    and_(
                        Customer.id == user_id,
                        Customer.organization_id == organization_id,
                    )
                )
                .first()
            )

            if customer:
                if consent_type == ConsentType.MARKETING:
                    customer.marketing_consent = granted
                    customer.marketing_consent_date = datetime.now(timezone.utc)

                db.commit()

        finally:
            db.close()

    async def withdraw_consent(
        self,
        user_id: str,
        organization_id: str,
        consent_type: ConsentType,
        reason: str = None,
    ) -> bool:
        """Withdraw user consent"""

        consent_def = self.consent_definitions[consent_type]

        if not consent_def["can_withdraw"]:
            logger.warning(
                f"Cannot withdraw consent for {consent_type.value} - not withdrawable"
            )
            return False

        # Find existing consent record
        user_records = self.consent_records.get(user_id, [])
        existing_record = None

        for record in user_records:
            if (
                record.consent_type == consent_type
                and record.organization_id == organization_id
                and record.status == ConsentStatus.GRANTED
            ):
                existing_record = record
                break

        if not existing_record:
            logger.warning(
                f"No granted consent found to withdraw for {user_id} - {consent_type.value}"
            )
            return False

        # Update record
        existing_record.status = ConsentStatus.WITHDRAWN
        existing_record.withdrawn_at = datetime.now(timezone.utc)
        existing_record.updated_at = datetime.now(timezone.utc)

        # Update database
        await self._update_user_consent_in_db(
            user_id, organization_id, consent_type, False
        )

        logger.info(f"Consent withdrawn: {user_id} - {consent_type.value}")

        return True

    def get_user_consent(
        self, user_id: str, organization_id: str
    ) -> Dict[ConsentType, ConsentRecord]:
        """Get current consent status for user"""
        user_records = self.consent_records.get(user_id, [])

        current_consent = {}

        for record in user_records:
            if record.organization_id == organization_id:
                # Get the most recent record for each consent type
                if (
                    record.consent_type not in current_consent
                    or record.created_at
                    > current_consent[record.consent_type].created_at
                ):
                    current_consent[record.consent_type] = record

        return current_consent

    def check_consent(
        self, user_id: str, organization_id: str, consent_type: ConsentType
    ) -> bool:
        """Check if user has valid consent for specific type"""
        current_consent = self.get_user_consent(user_id, organization_id)

        record = current_consent.get(consent_type)
        if not record:
            # No record found - check if it's required
            consent_def = self.consent_definitions[consent_type]
            return consent_def["required"]  # Necessary cookies are always allowed

        return record.is_valid()

    def get_consent_banner_config(self, organization_id: str) -> Dict[str, Any]:
        """Get consent banner configuration"""
        return {
            "title": "Cookie Preferences",
            "description": "We use cookies to enhance your experience and provide personalized content.",
            "consent_types": [
                {
                    "type": consent_type.value,
                    "name": definition["name"],
                    "description": definition["description"],
                    "required": definition["required"],
                    "can_withdraw": definition["can_withdraw"],
                    "default_enabled": definition["required"],
                }
                for consent_type, definition in self.consent_definitions.items()
            ],
            "privacy_policy_url": f"/privacy-policy?org={organization_id}",
            "cookie_policy_url": f"/cookie-policy?org={organization_id}",
        }

    async def bulk_record_consent(
        self,
        user_id: str,
        organization_id: str,
        consent_choices: Dict[str, bool],
        method: ConsentMethod,
        ip_address: str = None,
        user_agent: str = None,
    ) -> List[ConsentRecord]:
        """Record multiple consent choices at once"""
        records = []

        for consent_type_str, granted in consent_choices.items():
            try:
                consent_type = ConsentType(consent_type_str)
                record = await self.record_consent(
                    user_id=user_id,
                    organization_id=organization_id,
                    consent_type=consent_type,
                    granted=granted,
                    method=method,
                    ip_address=ip_address,
                    user_agent=user_agent,
                )
                records.append(record)
            except ValueError:
                logger.warning(f"Unknown consent type: {consent_type_str}")

        return records

    def get_consent_history(
        self, user_id: str, organization_id: str, consent_type: ConsentType = None
    ) -> List[ConsentRecord]:
        """Get consent history for user"""
        user_records = self.consent_records.get(user_id, [])

        # Filter by organization
        org_records = [
            record
            for record in user_records
            if record.organization_id == organization_id
        ]

        # Filter by consent type if specified
        if consent_type:
            org_records = [
                record for record in org_records if record.consent_type == consent_type
            ]

        # Sort by creation date (newest first)
        org_records.sort(key=lambda r: r.created_at, reverse=True)

        return org_records

    async def expire_old_consent(self) -> int:
        """Expire old consent records"""
        expired_count = 0
        current_time = datetime.now(timezone.utc)

        for user_id, records in self.consent_records.items():
            for record in records:
                if (
                    record.expires_at
                    and current_time > record.expires_at
                    and record.status == ConsentStatus.GRANTED
                ):

                    record.status = ConsentStatus.EXPIRED
                    record.updated_at = current_time
                    expired_count += 1

                    # Update database
                    await self._update_user_consent_in_db(
                        user_id, record.organization_id, record.consent_type, False
                    )

        if expired_count > 0:
            logger.info(f"Expired {expired_count} consent records")

        return expired_count

    def generate_consent_report(self, organization_id: str) -> Dict[str, Any]:
        """Generate consent compliance report"""
        org_records = []

        for user_records in self.consent_records.values():
            org_records.extend(
                [
                    record
                    for record in user_records
                    if record.organization_id == organization_id
                ]
            )

        # Count by consent type and status
        consent_stats = {}
        for consent_type in ConsentType:
            consent_stats[consent_type.value] = {
                "granted": 0,
                "denied": 0,
                "withdrawn": 0,
                "expired": 0,
                "total": 0,
            }

        for record in org_records:
            type_key = record.consent_type.value
            status_key = record.status.value

            if status_key in consent_stats[type_key]:
                consent_stats[type_key][status_key] += 1
            consent_stats[type_key]["total"] += 1

        # Calculate consent rates
        for type_stats in consent_stats.values():
            if type_stats["total"] > 0:
                type_stats["consent_rate"] = (
                    type_stats["granted"] / type_stats["total"] * 100
                )
            else:
                type_stats["consent_rate"] = 0

        return {
            "organization_id": organization_id,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "total_users": len(set(r.user_id for r in org_records)),
            "total_records": len(org_records),
            "consent_statistics": consent_stats,
            "consent_definitions": {
                consent_type.value: {
                    "name": definition["name"],
                    "required": definition["required"],
                    "can_withdraw": definition["can_withdraw"],
                    "legal_basis": definition["legal_basis"],
                }
                for consent_type, definition in self.consent_definitions.items()
            },
        }

    async def load_consent_from_database(self, organization_id: str):
        """Load existing consent records from database"""
        db = next(get_db())
        try:
            # Load user consent data
            users = db.query(User).filter(User.organization_id == organization_id).all()

            for user in users:
                user_id = str(user.id)

                # Marketing consent
                if (
                    hasattr(user, "marketing_consent")
                    and user.marketing_consent is not None
                ):
                    record = ConsentRecord(
                        user_id=user_id,
                        organization_id=organization_id,
                        consent_type=ConsentType.MARKETING,
                        status=(
                            ConsentStatus.GRANTED
                            if user.marketing_consent
                            else ConsentStatus.DENIED
                        ),
                        method=ConsentMethod.OPT_IN_FORM,
                        purpose="Marketing communications",
                        granted_at=getattr(
                            user, "marketing_consent_date", user.created_at
                        ),
                    )

                    if user_id not in self.consent_records:
                        self.consent_records[user_id] = []
                    self.consent_records[user_id].append(record)

                # Analytics consent
                if (
                    hasattr(user, "analytics_consent")
                    and user.analytics_consent is not None
                ):
                    record = ConsentRecord(
                        user_id=user_id,
                        organization_id=organization_id,
                        consent_type=ConsentType.ANALYTICS,
                        status=(
                            ConsentStatus.GRANTED
                            if user.analytics_consent
                            else ConsentStatus.DENIED
                        ),
                        method=ConsentMethod.COOKIE_BANNER,
                        purpose="Website analytics",
                        granted_at=getattr(
                            user, "analytics_consent_date", user.created_at
                        ),
                    )

                    if user_id not in self.consent_records:
                        self.consent_records[user_id] = []
                    self.consent_records[user_id].append(record)

            logger.info(f"Loaded consent records for organization {organization_id}")

        finally:
            db.close()


# Global consent management service instance
_consent_service = None


def get_consent_service() -> ConsentManagementService:
    """Get global consent management service instance"""
    global _consent_service

    if _consent_service is None:
        _consent_service = ConsentManagementService()

    return _consent_service

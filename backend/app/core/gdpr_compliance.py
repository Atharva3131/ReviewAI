"""
GDPR compliance service for data protection and privacy rights
"""
import asyncio
import json
import zipfile
import io
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Union
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from enum import Enum
import logging

from app.core.database import get_db
from app.models.user import User
from app.models.review import Review
from app.models.customer import Customer
from app.models.support_ticket import SupportTicket
from app.models.recovery_action import RecoveryAction
from app.models.agent_decision import AgentDecision
from app.models.organization import Organization

logger = logging.getLogger(__name__)


class GDPRRights(Enum):
    """GDPR data subject rights"""
    RIGHT_TO_ACCESS = "access"  # Article 15
    RIGHT_TO_RECTIFICATION = "rectification"  # Article 16
    RIGHT_TO_ERASURE = "erasure"  # Article 17 (Right to be forgotten)
    RIGHT_TO_RESTRICT_PROCESSING = "restrict_processing"  # Article 18
    RIGHT_TO_DATA_PORTABILITY = "data_portability"  # Article 20
    RIGHT_TO_OBJECT = "object"  # Article 21
    RIGHT_TO_WITHDRAW_CONSENT = "withdraw_consent"  # Article 7


class ProcessingLawfulBasis(Enum):
    """GDPR lawful basis for processing"""
    CONSENT = "consent"  # Article 6(1)(a)
    CONTRACT = "contract"  # Article 6(1)(b)
    LEGAL_OBLIGATION = "legal_obligation"  # Article 6(1)(c)
    VITAL_INTERESTS = "vital_interests"  # Article 6(1)(d)
    PUBLIC_TASK = "public_task"  # Article 6(1)(e)
    LEGITIMATE_INTERESTS = "legitimate_interests"  # Article 6(1)(f)


class DataCategory(Enum):
    """Categories of personal data"""
    IDENTITY_DATA = "identity_data"  # Name, email, phone
    CONTACT_DATA = "contact_data"  # Address, communication preferences
    TECHNICAL_DATA = "technical_data"  # IP address, browser data
    USAGE_DATA = "usage_data"  # How services are used
    MARKETING_DATA = "marketing_data"  # Marketing preferences
    FINANCIAL_DATA = "financial_data"  # Payment information
    SPECIAL_CATEGORY = "special_category"  # Sensitive personal data


class GDPRRequest:
    """GDPR data subject request"""
    
    def __init__(
        self,
        request_id: str,
        data_subject_email: str,
        organization_id: str,
        request_type: GDPRRights,
        request_details: str = None,
        verification_method: str = "email",
        created_at: datetime = None
    ):
        self.request_id = request_id
        self.data_subject_email = data_subject_email
        self.organization_id = organization_id
        self.request_type = request_type
        self.request_details = request_details
        self.verification_method = verification_method
        self.created_at = created_at or datetime.now(timezone.utc)
        self.status = "pending_verification"
        self.verified_at = None
        self.completed_at = None
        self.response_data = None


class GDPRComplianceService:
    """Service for GDPR compliance and data subject rights"""
    
    def __init__(self):
        self.pending_requests: Dict[str, GDPRRequest] = {}
        self.data_processing_purposes = self._initialize_processing_purposes()
    
    def _initialize_processing_purposes(self) -> Dict[str, Dict[str, Any]]:
        """Initialize data processing purposes and lawful basis"""
        return {
            "user_account_management": {
                "purpose": "Managing user accounts and authentication",
                "lawful_basis": ProcessingLawfulBasis.CONTRACT,
                "data_categories": [DataCategory.IDENTITY_DATA, DataCategory.CONTACT_DATA],
                "retention_period": "7 years after account closure",
                "automated_decision_making": False
            },
            "customer_service": {
                "purpose": "Providing customer support and resolving issues",
                "lawful_basis": ProcessingLawfulBasis.LEGITIMATE_INTERESTS,
                "data_categories": [DataCategory.IDENTITY_DATA, DataCategory.CONTACT_DATA, DataCategory.USAGE_DATA],
                "retention_period": "3 years after last interaction",
                "automated_decision_making": True,
                "automated_decision_details": "AI-powered sentiment analysis and response generation"
            },
            "review_analysis": {
                "purpose": "Analyzing customer reviews for business intelligence",
                "lawful_basis": ProcessingLawfulBasis.LEGITIMATE_INTERESTS,
                "data_categories": [DataCategory.USAGE_DATA, DataCategory.IDENTITY_DATA],
                "retention_period": "7 years for business analysis",
                "automated_decision_making": True,
                "automated_decision_details": "Automated review sentiment analysis and categorization"
            },
            "marketing_communications": {
                "purpose": "Sending marketing communications and newsletters",
                "lawful_basis": ProcessingLawfulBasis.CONSENT,
                "data_categories": [DataCategory.IDENTITY_DATA, DataCategory.CONTACT_DATA, DataCategory.MARKETING_DATA],
                "retention_period": "Until consent is withdrawn",
                "automated_decision_making": False
            },
            "legal_compliance": {
                "purpose": "Compliance with legal obligations and audit requirements",
                "lawful_basis": ProcessingLawfulBasis.LEGAL_OBLIGATION,
                "data_categories": [DataCategory.IDENTITY_DATA, DataCategory.FINANCIAL_DATA],
                "retention_period": "7 years as required by law",
                "automated_decision_making": False
            },
            "security_monitoring": {
                "purpose": "Monitoring system security and preventing fraud",
                "lawful_basis": ProcessingLawfulBasis.LEGITIMATE_INTERESTS,
                "data_categories": [DataCategory.TECHNICAL_DATA, DataCategory.USAGE_DATA],
                "retention_period": "1 year for security logs",
                "automated_decision_making": True,
                "automated_decision_details": "Automated fraud detection and security monitoring"
            }
        }
    
    async def submit_gdpr_request(
        self,
        data_subject_email: str,
        organization_id: str,
        request_type: GDPRRights,
        request_details: str = None
    ) -> str:
        """Submit a GDPR data subject request"""
        
        # Generate unique request ID
        import uuid
        request_id = str(uuid.uuid4())
        
        # Create request
        request = GDPRRequest(
            request_id=request_id,
            data_subject_email=data_subject_email,
            organization_id=organization_id,
            request_type=request_type,
            request_details=request_details
        )
        
        # Store pending request
        self.pending_requests[request_id] = request
        
        # Send verification email (in real implementation)
        await self._send_verification_email(request)
        
        logger.info(f"GDPR request submitted: {request_id} for {data_subject_email}")
        
        return request_id
    
    async def _send_verification_email(self, request: GDPRRequest):
        """Send verification email to data subject"""
        # In a real implementation, this would send an email with verification link
        logger.info(f"Verification email sent for GDPR request {request.request_id}")
        
        # For demo purposes, auto-verify after a short delay
        await asyncio.sleep(1)
        await self.verify_gdpr_request(request.request_id, "auto_verified")
    
    async def verify_gdpr_request(self, request_id: str, verification_token: str) -> bool:
        """Verify GDPR request with token"""
        request = self.pending_requests.get(request_id)
        if not request:
            return False
        
        # In real implementation, verify the token
        request.status = "verified"
        request.verified_at = datetime.now(timezone.utc)
        
        # Process the request
        await self._process_gdpr_request(request)
        
        return True
    
    async def _process_gdpr_request(self, request: GDPRRequest):
        """Process verified GDPR request"""
        try:
            if request.request_type == GDPRRights.RIGHT_TO_ACCESS:
                await self._process_access_request(request)
            elif request.request_type == GDPRRights.RIGHT_TO_RECTIFICATION:
                await self._process_rectification_request(request)
            elif request.request_type == GDPRRights.RIGHT_TO_ERASURE:
                await self._process_erasure_request(request)
            elif request.request_type == GDPRRights.RIGHT_TO_DATA_PORTABILITY:
                await self._process_portability_request(request)
            elif request.request_type == GDPRRights.RIGHT_TO_RESTRICT_PROCESSING:
                await self._process_restriction_request(request)
            elif request.request_type == GDPRRights.RIGHT_TO_OBJECT:
                await self._process_objection_request(request)
            elif request.request_type == GDPRRights.RIGHT_TO_WITHDRAW_CONSENT:
                await self._process_consent_withdrawal(request)
            
            request.status = "completed"
            request.completed_at = datetime.now(timezone.utc)
            
            logger.info(f"GDPR request completed: {request.request_id}")
            
        except Exception as e:
            request.status = "failed"
            logger.error(f"GDPR request failed {request.request_id}: {e}")
            raise
    
    async def _process_access_request(self, request: GDPRRequest):
        """Process right to access request (Article 15)"""
        data_subject_data = await self._collect_personal_data(
            request.data_subject_email,
            request.organization_id
        )
        
        # Create comprehensive data export
        access_report = {
            "request_id": request.request_id,
            "data_subject": request.data_subject_email,
            "organization_id": request.organization_id,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "data_processing_purposes": self.data_processing_purposes,
            "personal_data": data_subject_data,
            "data_sources": self._get_data_sources(),
            "retention_periods": self._get_retention_periods(),
            "third_party_recipients": self._get_third_party_recipients(),
            "international_transfers": self._get_international_transfers(),
            "automated_decision_making": self._get_automated_decision_info()
        }
        
        request.response_data = access_report
        
        # In real implementation, securely deliver this data to the data subject
        logger.info(f"Access request processed for {request.data_subject_email}")
    
    async def _process_rectification_request(self, request: GDPRRequest):
        """Process right to rectification request (Article 16)"""
        # Parse rectification details from request
        rectification_data = json.loads(request.request_details or "{}")
        
        db = next(get_db())
        try:
            # Update user data
            user = db.query(User).filter(
                and_(
                    User.email == request.data_subject_email,
                    User.organization_id == request.organization_id
                )
            ).first()
            
            if user:
                for field, new_value in rectification_data.items():
                    if hasattr(user, field) and field in ['email', 'name', 'phone']:
                        setattr(user, field, new_value)
                
                db.commit()
                logger.info(f"User data rectified for {request.data_subject_email}")
            
            # Update customer data
            customer = db.query(Customer).filter(
                and_(
                    Customer.email == request.data_subject_email,
                    Customer.organization_id == request.organization_id
                )
            ).first()
            
            if customer:
                for field, new_value in rectification_data.items():
                    if hasattr(customer, field) and field in ['email', 'name', 'phone']:
                        setattr(customer, field, new_value)
                
                db.commit()
                logger.info(f"Customer data rectified for {request.data_subject_email}")
            
        finally:
            db.close()
        
        request.response_data = {"rectified_fields": list(rectification_data.keys())}
    
    async def _process_erasure_request(self, request: GDPRRequest):
        """Process right to erasure request (Article 17)"""
        deleted_records = {
            "users": 0,
            "customers": 0,
            "reviews": 0,
            "support_tickets": 0,
            "recovery_actions": 0,
            "agent_decisions": 0
        }
        
        db = next(get_db())
        try:
            # Delete user data
            user_result = db.query(User).filter(
                and_(
                    User.email == request.data_subject_email,
                    User.organization_id == request.organization_id
                )
            ).delete()
            deleted_records["users"] = user_result
            
            # Delete customer data
            customer_result = db.query(Customer).filter(
                and_(
                    Customer.email == request.data_subject_email,
                    Customer.organization_id == request.organization_id
                )
            ).delete()
            deleted_records["customers"] = customer_result
            
            # Anonymize reviews (don't delete for business purposes)
            reviews = db.query(Review).filter(
                and_(
                    Review.customer_name.contains(request.data_subject_email),
                    Review.organization_id == request.organization_id
                )
            ).all()
            
            for review in reviews:
                review.customer_name = "Anonymous"
                review.content = "[Content removed per GDPR request]"
            
            deleted_records["reviews"] = len(reviews)
            
            # Delete support tickets
            ticket_result = db.query(SupportTicket).filter(
                and_(
                    SupportTicket.customer.has(Customer.email == request.data_subject_email),
                    SupportTicket.organization_id == request.organization_id
                )
            ).delete()
            deleted_records["support_tickets"] = ticket_result
            
            # Delete recovery actions
            action_result = db.query(RecoveryAction).filter(
                and_(
                    RecoveryAction.customer.has(Customer.email == request.data_subject_email),
                    RecoveryAction.organization_id == request.organization_id
                )
            ).delete()
            deleted_records["recovery_actions"] = action_result
            
            db.commit()
            logger.info(f"Data erased for {request.data_subject_email}: {deleted_records}")
            
        except Exception as e:
            db.rollback()
            raise
        finally:
            db.close()
        
        request.response_data = deleted_records
    
    async def _process_portability_request(self, request: GDPRRequest):
        """Process right to data portability request (Article 20)"""
        portable_data = await self._collect_portable_data(
            request.data_subject_email,
            request.organization_id
        )
        
        # Create structured data export in JSON format
        export_data = {
            "data_subject": request.data_subject_email,
            "export_date": datetime.now(timezone.utc).isoformat(),
            "format": "JSON",
            "data": portable_data
        }
        
        # Create ZIP file with data
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            zip_file.writestr(
                f"personal_data_{request.data_subject_email.replace('@', '_at_')}.json",
                json.dumps(export_data, indent=2, default=str)
            )
        
        request.response_data = {
            "export_format": "JSON",
            "file_size_bytes": len(zip_buffer.getvalue()),
            "records_exported": sum(len(v) if isinstance(v, list) else 1 for v in portable_data.values())
        }
        
        logger.info(f"Data portability export created for {request.data_subject_email}")
    
    async def _process_restriction_request(self, request: GDPRRequest):
        """Process right to restrict processing request (Article 18)"""
        # Mark data for restricted processing
        db = next(get_db())
        try:
            # Add processing restriction flag to user
            user = db.query(User).filter(
                and_(
                    User.email == request.data_subject_email,
                    User.organization_id == request.organization_id
                )
            ).first()
            
            if user:
                # In real implementation, add restriction metadata
                user.processing_restricted = True
                user.restriction_reason = request.request_details
                user.restriction_date = datetime.now(timezone.utc)
            
            # Add restriction to customer records
            customer = db.query(Customer).filter(
                and_(
                    Customer.email == request.data_subject_email,
                    Customer.organization_id == request.organization_id
                )
            ).first()
            
            if customer:
                customer.processing_restricted = True
                customer.restriction_reason = request.request_details
                customer.restriction_date = datetime.now(timezone.utc)
            
            db.commit()
            logger.info(f"Processing restricted for {request.data_subject_email}")
            
        finally:
            db.close()
        
        request.response_data = {"restriction_applied": True}
    
    async def _process_objection_request(self, request: GDPRRequest):
        """Process right to object request (Article 21)"""
        objection_details = json.loads(request.request_details or "{}")
        processing_purposes = objection_details.get("processing_purposes", [])
        
        # Stop processing for specified purposes
        stopped_processing = []
        
        for purpose in processing_purposes:
            if purpose in self.data_processing_purposes:
                # Check if we can stop processing (not required by law)
                purpose_info = self.data_processing_purposes[purpose]
                if purpose_info["lawful_basis"] != ProcessingLawfulBasis.LEGAL_OBLIGATION:
                    stopped_processing.append(purpose)
                    logger.info(f"Stopped processing for purpose: {purpose}")
        
        request.response_data = {
            "objection_processed": True,
            "stopped_processing": stopped_processing,
            "continuing_processing": [
                p for p in processing_purposes 
                if p not in stopped_processing
            ]
        }
    
    async def _process_consent_withdrawal(self, request: GDPRRequest):
        """Process consent withdrawal request (Article 7)"""
        consent_types = json.loads(request.request_details or '["all"]')
        
        db = next(get_db())
        try:
            # Update consent status
            user = db.query(User).filter(
                and_(
                    User.email == request.data_subject_email,
                    User.organization_id == request.organization_id
                )
            ).first()
            
            if user:
                # In real implementation, update consent preferences
                for consent_type in consent_types:
                    if consent_type == "marketing":
                        user.marketing_consent = False
                    elif consent_type == "analytics":
                        user.analytics_consent = False
                    elif consent_type == "all":
                        user.marketing_consent = False
                        user.analytics_consent = False
                
                user.consent_withdrawn_at = datetime.now(timezone.utc)
                db.commit()
            
            logger.info(f"Consent withdrawn for {request.data_subject_email}: {consent_types}")
            
        finally:
            db.close()
        
        request.response_data = {"consent_withdrawn": consent_types}
    
    async def _collect_personal_data(self, email: str, organization_id: str) -> Dict[str, Any]:
        """Collect all personal data for a data subject"""
        personal_data = {}
        
        db = next(get_db())
        try:
            # User data
            user = db.query(User).filter(
                and_(
                    User.email == email,
                    User.organization_id == organization_id
                )
            ).first()
            
            if user:
                personal_data["user_account"] = {
                    "id": str(user.id),
                    "email": user.email,
                    "role": user.role,
                    "created_at": user.created_at.isoformat(),
                    "updated_at": user.updated_at.isoformat(),
                    "last_login": user.last_login.isoformat() if user.last_login else None
                }
            
            # Customer data
            customer = db.query(Customer).filter(
                and_(
                    Customer.email == email,
                    Customer.organization_id == organization_id
                )
            ).first()
            
            if customer:
                personal_data["customer_profile"] = {
                    "id": str(customer.id),
                    "email": customer.email,
                    "name": customer.name,
                    "phone": customer.phone,
                    "created_at": customer.created_at.isoformat(),
                    "last_interaction": customer.last_interaction.isoformat() if customer.last_interaction else None,
                    "churn_risk_score": float(customer.churn_risk_score) if customer.churn_risk_score else None
                }
            
            # Reviews
            reviews = db.query(Review).filter(
                and_(
                    Review.customer_name.contains(email),
                    Review.organization_id == organization_id
                )
            ).all()
            
            if reviews:
                personal_data["reviews"] = [
                    {
                        "id": str(review.id),
                        "platform": review.platform,
                        "rating": review.rating,
                        "content": review.content,
                        "sentiment_score": float(review.sentiment_score) if review.sentiment_score else None,
                        "created_at": review.created_at.isoformat()
                    }
                    for review in reviews
                ]
            
            # Support tickets
            if customer:
                tickets = db.query(SupportTicket).filter(
                    and_(
                        SupportTicket.customer_id == customer.id,
                        SupportTicket.organization_id == organization_id
                    )
                ).all()
                
                if tickets:
                    personal_data["support_tickets"] = [
                        {
                            "id": str(ticket.id),
                            "subject": ticket.subject,
                            "status": ticket.status,
                            "priority": ticket.priority,
                            "created_at": ticket.created_at.isoformat()
                        }
                        for ticket in tickets
                    ]
                
                # Recovery actions
                actions = db.query(RecoveryAction).filter(
                    and_(
                        RecoveryAction.customer_id == customer.id,
                        RecoveryAction.organization_id == organization_id
                    )
                ).all()
                
                if actions:
                    personal_data["recovery_actions"] = [
                        {
                            "id": str(action.id),
                            "action_type": action.action_type,
                            "status": action.status,
                            "created_at": action.created_at.isoformat(),
                            "executed_at": action.executed_at.isoformat() if action.executed_at else None
                        }
                        for action in actions
                    ]
        
        finally:
            db.close()
        
        return personal_data
    
    async def _collect_portable_data(self, email: str, organization_id: str) -> Dict[str, Any]:
        """Collect portable data (data provided by the data subject)"""
        # This is a subset of personal data that was provided by the data subject
        all_data = await self._collect_personal_data(email, organization_id)
        
        # Filter to only include data provided by the data subject
        portable_data = {}
        
        if "user_account" in all_data:
            portable_data["user_account"] = {
                k: v for k, v in all_data["user_account"].items()
                if k in ["email", "created_at"]
            }
        
        if "customer_profile" in all_data:
            portable_data["customer_profile"] = {
                k: v for k, v in all_data["customer_profile"].items()
                if k in ["email", "name", "phone", "created_at"]
            }
        
        if "reviews" in all_data:
            portable_data["reviews"] = [
                {k: v for k, v in review.items() if k in ["platform", "rating", "content", "created_at"]}
                for review in all_data["reviews"]
            ]
        
        return portable_data
    
    def _get_data_sources(self) -> List[str]:
        """Get list of data sources"""
        return [
            "User registration forms",
            "Customer support interactions",
            "Review platforms (Google, Yelp, etc.)",
            "Website analytics",
            "Email communications",
            "API integrations"
        ]
    
    def _get_retention_periods(self) -> Dict[str, str]:
        """Get data retention periods"""
        return {
            "User account data": "7 years after account closure",
            "Customer interaction data": "3 years after last interaction",
            "Review data": "7 years for business analysis",
            "Support ticket data": "3 years after resolution",
            "Marketing data": "Until consent is withdrawn",
            "Security logs": "1 year"
        }
    
    def _get_third_party_recipients(self) -> List[Dict[str, str]]:
        """Get third-party data recipients"""
        return [
            {
                "name": "Email Service Provider",
                "purpose": "Sending transactional and marketing emails",
                "safeguards": "Data Processing Agreement, EU-US Privacy Shield"
            },
            {
                "name": "Analytics Provider",
                "purpose": "Website and application analytics",
                "safeguards": "Data Processing Agreement, Anonymization"
            },
            {
                "name": "Cloud Infrastructure Provider",
                "purpose": "Data hosting and processing",
                "safeguards": "Data Processing Agreement, EU Standard Contractual Clauses"
            }
        ]
    
    def _get_international_transfers(self) -> List[Dict[str, str]]:
        """Get international data transfers"""
        return [
            {
                "country": "United States",
                "safeguards": "EU-US Privacy Shield, Standard Contractual Clauses",
                "purpose": "Cloud hosting and email services"
            }
        ]
    
    def _get_automated_decision_info(self) -> List[Dict[str, Any]]:
        """Get automated decision-making information"""
        return [
            {
                "purpose": "Review sentiment analysis",
                "logic": "Natural language processing to determine sentiment",
                "significance": "Determines response priority and type",
                "consequences": "May affect customer service response time",
                "right_to_human_review": True
            },
            {
                "purpose": "Customer churn risk assessment",
                "logic": "Machine learning model based on interaction patterns",
                "significance": "Determines proactive retention actions",
                "consequences": "May trigger automated recovery communications",
                "right_to_human_review": True
            }
        ]
    
    def get_gdpr_request_status(self, request_id: str) -> Optional[Dict[str, Any]]:
        """Get status of GDPR request"""
        request = self.pending_requests.get(request_id)
        if not request:
            return None
        
        return {
            "request_id": request.request_id,
            "data_subject_email": request.data_subject_email,
            "request_type": request.request_type.value,
            "status": request.status,
            "created_at": request.created_at.isoformat(),
            "verified_at": request.verified_at.isoformat() if request.verified_at else None,
            "completed_at": request.completed_at.isoformat() if request.completed_at else None
        }
    
    def get_processing_purposes(self) -> Dict[str, Any]:
        """Get data processing purposes for transparency"""
        return {
            purpose: {
                "purpose": info["purpose"],
                "lawful_basis": info["lawful_basis"].value,
                "data_categories": [cat.value for cat in info["data_categories"]],
                "retention_period": info["retention_period"],
                "automated_decision_making": info["automated_decision_making"],
                "automated_decision_details": info.get("automated_decision_details")
            }
            for purpose, info in self.data_processing_purposes.items()
        }


# Global GDPR service instance
_gdpr_service = None


def get_gdpr_service() -> GDPRComplianceService:
    """Get global GDPR service instance"""
    global _gdpr_service
    
    if _gdpr_service is None:
        _gdpr_service = GDPRComplianceService()
    
    return _gdpr_service

"""
Core Agent Orchestration Engine
"""
import logging
from typing import Dict, Any, List, Optional, Union
from datetime import datetime, timezone
from dataclasses import dataclass
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.review import Review
from app.models.support_ticket import SupportTicket
from app.models.agent_decision import AgentDecision, DecisionType, InputType
from app.services.sentiment_service import SentimentService
from app.services.urgency_service import UrgencyService
from app.services.categorization_service import CategorizationService
from app.services.decision_rules_engine import DecisionRulesEngine

logger = logging.getLogger(__name__)


@dataclass
class AgentDecisionResult:
    """Result of agent decision making"""
    decision_type: DecisionType
    confidence_score: float
    reasoning: str
    generated_content: Optional[str] = None
    content_type: Optional[str] = None
    context_factors: Optional[Dict[str, Any]] = None
    requires_approval: bool = False
    processing_time_ms: int = 0


class AgentEngine:
    """
    Core Agent Orchestration Engine
    
    Coordinates decision-making between different AI services and applies
    business rules to determine appropriate actions for reviews and customer interactions.
    """
    
    def __init__(self):
        self.sentiment_service = SentimentService()
        self.urgency_service = UrgencyService()
        self.categorization_service = CategorizationService()
        self.decision_rules = DecisionRulesEngine()
        self.model_version = "1.0.0"
        self.model_provider = "revive_ai_deterministic"
    
    async def process_review(
        self, 
        review: Review, 
        db: AsyncSession,
        organization_id: str,
        additional_context: Optional[Dict[str, Any]] = None
    ) -> AgentDecisionResult:
        """
        Process a review and make a decision on the appropriate action
        
        Args:
            review: Review object to process
            db: Database session
            organization_id: Organization ID for multi-tenant isolation
            additional_context: Additional context for decision making
            
        Returns:
            AgentDecisionResult with decision details
        """
        start_time = datetime.now()
        
        try:
            # Step 1: Analyze sentiment (deterministic)
            sentiment_result = await self.sentiment_service.analyze_sentiment(
                review.content or "", 
                review.rating
            )
            
            # Step 2: Classify urgency (rule-based)
            urgency_result = await self.urgency_service.classify_urgency(
                review.content or "",
                review.rating,
                sentiment_result["sentiment_score"],
                review.title
            )
            
            # Step 3: Categorize issues
            categorization_result = await self.categorization_service.categorize_issues(
                review.content or "",
                review.title,
                review.rating
            )
            
            # Step 4: Build context for decision making
            context = self._build_review_context(
                review, sentiment_result, urgency_result, 
                categorization_result, additional_context
            )
            
            # Step 5: Apply decision rules
            decision_result = await self.decision_rules.decide_review_action(
                sentiment_score=sentiment_result["sentiment_score"],
                urgency_level=urgency_result["urgency_level"],
                rating=review.rating,
                categories=categorization_result["categories"],
                context=context
            )
            
            # Step 6: Calculate processing time
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            
            # Step 7: Create result
            result = AgentDecisionResult(
                decision_type=decision_result["decision_type"],
                confidence_score=decision_result["confidence_score"],
                reasoning=decision_result["reasoning"],
                generated_content=decision_result.get("generated_content"),
                content_type=decision_result.get("content_type"),
                context_factors=context,
                requires_approval=decision_result.get("requires_approval", False),
                processing_time_ms=int(processing_time)
            )
            
            # Step 8: Log decision to database
            await self._log_agent_decision(
                db=db,
                organization_id=organization_id,
                input_type=InputType.REVIEW,
                input_id=review.id,
                result=result,
                input_data=self._serialize_review_data(review)
            )
            
            logger.info(f"Review decision completed: {review.id} -> {result.decision_type}")
            return result
            
        except Exception as e:
            logger.error(f"Agent decision failed for review {review.id}: {e}")
            # Return safe default decision
            return AgentDecisionResult(
                decision_type=DecisionType.ESCALATE,
                confidence_score=0.0,
                reasoning=f"Decision failed due to error: {str(e)}",
                requires_approval=True,
                processing_time_ms=int((datetime.now() - start_time).total_seconds() * 1000)
            )
    
    async def process_support_ticket(
        self,
        ticket: SupportTicket,
        db: AsyncSession,
        organization_id: str,
        additional_context: Optional[Dict[str, Any]] = None
    ) -> AgentDecisionResult:
        """
        Process a support ticket and make a decision on the appropriate action
        """
        start_time = datetime.now()
        
        try:
            # Step 1: Analyze sentiment
            sentiment_result = await self.sentiment_service.analyze_sentiment(
                ticket.content or "",
                None  # No rating for tickets
            )
            
            # Step 2: Classify urgency
            urgency_result = await self.urgency_service.classify_urgency(
                ticket.content or "",
                None,  # No rating
                sentiment_result["sentiment_score"],
                ticket.subject
            )
            
            # Step 3: Categorize issues
            categorization_result = await self.categorization_service.categorize_issues(
                ticket.content or "",
                ticket.subject,
                None  # No rating
            )
            
            # Step 4: Build context
            context = self._build_ticket_context(
                ticket, sentiment_result, urgency_result,
                categorization_result, additional_context
            )
            
            # Step 5: Apply decision rules
            decision_result = await self.decision_rules.decide_ticket_action(
                sentiment_score=sentiment_result["sentiment_score"],
                urgency_level=urgency_result["urgency_level"],
                priority=ticket.priority,
                categories=categorization_result["categories"],
                context=context
            )
            
            # Step 6: Calculate processing time
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            
            # Step 7: Create result
            result = AgentDecisionResult(
                decision_type=decision_result["decision_type"],
                confidence_score=decision_result["confidence_score"],
                reasoning=decision_result["reasoning"],
                generated_content=decision_result.get("generated_content"),
                content_type=decision_result.get("content_type"),
                context_factors=context,
                requires_approval=decision_result.get("requires_approval", False),
                processing_time_ms=int(processing_time)
            )
            
            # Step 8: Log decision
            await self._log_agent_decision(
                db=db,
                organization_id=organization_id,
                input_type=InputType.SUPPORT_TICKET,
                input_id=ticket.id,
                result=result,
                input_data=self._serialize_ticket_data(ticket)
            )
            
            logger.info(f"Ticket decision completed: {ticket.id} -> {result.decision_type}")
            return result
            
        except Exception as e:
            logger.error(f"Agent decision failed for ticket {ticket.id}: {e}")
            return AgentDecisionResult(
                decision_type=DecisionType.ESCALATE,
                confidence_score=0.0,
                reasoning=f"Decision failed due to error: {str(e)}",
                requires_approval=True,
                processing_time_ms=int((datetime.now() - start_time).total_seconds() * 1000)
            )
    
    async def validate_decision(
        self,
        decision_result: AgentDecisionResult,
        input_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Validate agent decision for safety and compliance
        
        Returns:
            Dict with validation results and any safety concerns
        """
        validation_result = {
            "is_valid": True,
            "safety_concerns": [],
            "compliance_issues": [],
            "recommendations": []
        }
        
        # Check confidence thresholds
        if decision_result.confidence_score < 0.3:
            validation_result["safety_concerns"].append(
                "Very low confidence score - requires human review"
            )
            validation_result["recommendations"].append("Escalate to human agent")
        
        # Check for high-risk decisions
        if decision_result.decision_type == DecisionType.RESPOND_PUBLIC:
            if decision_result.confidence_score < 0.7:
                validation_result["safety_concerns"].append(
                    "Public response with low confidence - review content"
                )
        
        # Check generated content safety
        if decision_result.generated_content:
            content_validation = await self._validate_generated_content(
                decision_result.generated_content
            )
            validation_result["safety_concerns"].extend(content_validation["concerns"])
        
        # Check for escalation triggers
        if input_data.get("rating", 5) <= 2 and decision_result.decision_type != DecisionType.ESCALATE:
            if decision_result.confidence_score < 0.8:
                validation_result["recommendations"].append(
                    "Consider escalation for low-rated review with low confidence"
                )
        
        # Overall validation
        validation_result["is_valid"] = len(validation_result["safety_concerns"]) == 0
        
        return validation_result
    
    def _build_review_context(
        self,
        review: Review,
        sentiment_result: Dict[str, Any],
        urgency_result: Dict[str, Any],
        categorization_result: Dict[str, Any],
        additional_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Build context dictionary for review decision making"""
        context = {
            "review_id": str(review.id),
            "platform": review.platform.value,
            "rating": review.rating,
            "has_content": bool(review.content and review.content.strip()),
            "content_length": len(review.content or ""),
            "sentiment_score": sentiment_result["sentiment_score"],
            "sentiment_confidence": sentiment_result["confidence"],
            "urgency_level": urgency_result["urgency_level"],
            "urgency_score": urgency_result["urgency_score"],
            "urgency_confidence": urgency_result["confidence"],
            "issue_categories": categorization_result["categories"],
            "primary_category": categorization_result.get("primary_category"),
            "category_count": len(categorization_result["categories"]),
            "is_positive": review.rating >= 4,
            "is_negative": review.rating <= 2,
            "is_neutral": review.rating == 3,
            "customer_name": review.customer_name,
            "has_customer_email": bool(review.customer_email),
            "review_age_days": review.days_since_posted,
            "analysis_timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        if additional_context:
            context.update(additional_context)
        
        return context
    
    def _build_ticket_context(
        self,
        ticket: SupportTicket,
        sentiment_result: Dict[str, Any],
        urgency_result: Dict[str, Any],
        categorization_result: Dict[str, Any],
        additional_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Build context dictionary for ticket decision making"""
        context = {
            "ticket_id": str(ticket.id),
            "status": ticket.status,
            "priority": ticket.priority,
            "has_content": bool(ticket.content and ticket.content.strip()),
            "content_length": len(ticket.content or ""),
            "sentiment_score": sentiment_result["sentiment_score"],
            "sentiment_confidence": sentiment_result["confidence"],
            "urgency_level": urgency_result["urgency_level"],
            "urgency_score": urgency_result["urgency_score"],
            "urgency_confidence": urgency_result["confidence"],
            "issue_categories": categorization_result["categories"],
            "primary_category": categorization_result.get("primary_category"),
            "category_count": len(categorization_result["categories"]),
            "customer_id": str(ticket.customer_id) if ticket.customer_id else None,
            "analysis_timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        if additional_context:
            context.update(additional_context)
        
        return context
    
    def _serialize_review_data(self, review: Review) -> Dict[str, Any]:
        """Serialize review data for logging"""
        return {
            "id": str(review.id),
            "platform": review.platform.value,
            "rating": review.rating,
            "title": review.title,
            "content": review.content,
            "customer_name": review.customer_name,
            "customer_email": review.customer_email,
            "review_date": review.review_date.isoformat() if review.review_date else None,
            "created_at": review.created_at.isoformat() if review.created_at else None
        }
    
    def _serialize_ticket_data(self, ticket: SupportTicket) -> Dict[str, Any]:
        """Serialize ticket data for logging"""
        return {
            "id": str(ticket.id),
            "subject": ticket.subject,
            "content": ticket.content,
            "status": ticket.status,
            "priority": ticket.priority,
            "customer_id": str(ticket.customer_id) if ticket.customer_id else None,
            "created_at": ticket.created_at.isoformat() if ticket.created_at else None
        }
    
    async def _log_agent_decision(
        self,
        db: AsyncSession,
        organization_id: str,
        input_type: InputType,
        input_id: Any,
        result: AgentDecisionResult,
        input_data: Dict[str, Any]
    ):
        """Log agent decision to database"""
        try:
            decision = AgentDecision(
                organization_id=organization_id,
                input_type=input_type,
                input_id=input_id,
                decision_type=result.decision_type,
                confidence_score=result.confidence_score,
                reasoning=result.reasoning,
                input_data=input_data,
                context_factors=result.context_factors,
                generated_content=result.generated_content,
                content_type=result.content_type,
                model_version=self.model_version,
                model_provider=self.model_provider,
                processing_time_ms=result.processing_time_ms
            )
            
            db.add(decision)
            await db.commit()
            
        except Exception as e:
            logger.error(f"Failed to log agent decision: {e}")
            # Don't fail the main process if logging fails
            await db.rollback()
    
    async def _validate_generated_content(self, content: str) -> Dict[str, Any]:
        """Validate generated content for safety"""
        concerns = []
        
        # Check content length
        if len(content) > 1000:
            concerns.append("Generated content is too long")
        
        # Check for potentially problematic phrases
        problematic_phrases = [
            "guarantee", "promise", "refund", "lawsuit", "legal action",
            "compensation", "money back", "free", "discount"
        ]
        
        content_lower = content.lower()
        for phrase in problematic_phrases:
            if phrase in content_lower:
                concerns.append(f"Content contains potentially problematic phrase: '{phrase}'")
        
        return {"concerns": concerns}

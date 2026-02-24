"""
Agent Decision Service for managing agent decisions and audit trails
"""
import logging
from typing import Dict, Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, desc
from datetime import datetime, timezone, timedelta
import uuid

from app.models.agent_decision import AgentDecision, DecisionType, InputType, DecisionStatus
from app.schemas.agent import AgentDecisionFilter, AgentDecisionStats

logger = logging.getLogger(__name__)


class AgentDecisionService:
    """Service for managing agent decisions and audit trails"""
    
    @staticmethod
    async def get_decisions(
        db: AsyncSession,
        organization_id: str,
        skip: int = 0,
        limit: int = 100,
        filters: Optional[AgentDecisionFilter] = None,
        sort_by: str = "created_at",
        sort_order: str = "desc"
    ) -> List[AgentDecision]:
        """Get agent decisions with filtering and sorting"""
        
        query = select(AgentDecision).where(
            AgentDecision.organization_id == organization_id
        )
        
        # Apply filters
        if filters:
            if filters.input_type:
                try:
                    input_type_enum = InputType(filters.input_type)
                    query = query.where(AgentDecision.input_type == input_type_enum)
                except ValueError:
                    pass  # Invalid input type, ignore filter
            
            if filters.decision_type:
                try:
                    decision_type_enum = DecisionType(filters.decision_type)
                    query = query.where(AgentDecision.decision_type == decision_type_enum)
                except ValueError:
                    pass  # Invalid decision type, ignore filter
            
            if filters.status:
                try:
                    status_enum = DecisionStatus(filters.status)
                    query = query.where(AgentDecision.status == status_enum)
                except ValueError:
                    pass  # Invalid status, ignore filter
            
            if filters.confidence_min is not None:
                query = query.where(AgentDecision.confidence_score >= filters.confidence_min)
            
            if filters.confidence_max is not None:
                query = query.where(AgentDecision.confidence_score <= filters.confidence_max)
            
            if filters.requires_approval is not None:
                # This would require adding a computed property or method
                pass  # Skip for now
            
            if filters.date_from:
                query = query.where(AgentDecision.created_at >= filters.date_from)
            
            if filters.date_to:
                query = query.where(AgentDecision.created_at <= filters.date_to)
            
            if filters.reviewed_by:
                query = query.where(AgentDecision.reviewed_by == filters.reviewed_by)
            
            if filters.executed_by:
                query = query.where(AgentDecision.executed_by == filters.executed_by)
        
        # Apply sorting
        if sort_order.lower() == "desc":
            query = query.order_by(desc(getattr(AgentDecision, sort_by)))
        else:
            query = query.order_by(getattr(AgentDecision, sort_by))
        
        # Apply pagination
        query = query.offset(skip).limit(limit)
        
        result = await db.execute(query)
        return result.scalars().all()
    
    @staticmethod
    async def get_decision_by_id(
        db: AsyncSession,
        decision_id: str,
        organization_id: str
    ) -> Optional[AgentDecision]:
        """Get agent decision by ID within organization"""
        try:
            decision_uuid = uuid.UUID(decision_id)
            result = await db.execute(
                select(AgentDecision).where(
                    and_(
                        AgentDecision.id == decision_uuid,
                        AgentDecision.organization_id == organization_id
                    )
                )
            )
            return result.scalar_one_or_none()
        except (ValueError, TypeError):
            return None
    
    @staticmethod
    async def get_decisions_for_input(
        db: AsyncSession,
        organization_id: str,
        input_type: InputType,
        input_id: str,
        limit: int = 10
    ) -> List[AgentDecision]:
        """Get all decisions for a specific input (review, ticket, etc.)"""
        try:
            input_uuid = uuid.UUID(input_id)
            result = await db.execute(
                select(AgentDecision)
                .where(
                    and_(
                        AgentDecision.organization_id == organization_id,
                        AgentDecision.input_type == input_type,
                        AgentDecision.input_id == input_uuid
                    )
                )
                .order_by(desc(AgentDecision.created_at))
                .limit(limit)
            )
            return result.scalars().all()
        except (ValueError, TypeError):
            return []
    
    @staticmethod
    async def get_pending_decisions(
        db: AsyncSession,
        organization_id: str,
        limit: int = 50
    ) -> List[AgentDecision]:
        """Get decisions pending human review"""
        result = await db.execute(
            select(AgentDecision)
            .where(
                and_(
                    AgentDecision.organization_id == organization_id,
                    AgentDecision.status == DecisionStatus.PENDING
                )
            )
            .order_by(desc(AgentDecision.created_at))
            .limit(limit)
        )
        return result.scalars().all()
    
    @staticmethod
    async def get_high_confidence_decisions(
        db: AsyncSession,
        organization_id: str,
        confidence_threshold: float = 0.8,
        limit: int = 50
    ) -> List[AgentDecision]:
        """Get high confidence decisions"""
        result = await db.execute(
            select(AgentDecision)
            .where(
                and_(
                    AgentDecision.organization_id == organization_id,
                    AgentDecision.confidence_score >= confidence_threshold
                )
            )
            .order_by(desc(AgentDecision.created_at))
            .limit(limit)
        )
        return result.scalars().all()
    
    @staticmethod
    async def get_decision_stats(
        db: AsyncSession,
        organization_id: str,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None
    ) -> AgentDecisionStats:
        """Get agent decision statistics"""
        
        base_query = select(AgentDecision).where(
            AgentDecision.organization_id == organization_id
        )
        
        if date_from:
            base_query = base_query.where(AgentDecision.created_at >= date_from)
        if date_to:
            base_query = base_query.where(AgentDecision.created_at <= date_to)
        
        # Total decisions
        total_result = await db.execute(
            select(func.count(AgentDecision.id)).where(
                AgentDecision.organization_id == organization_id
            )
        )
        total_decisions = total_result.scalar() or 0
        
        if total_decisions == 0:
            return AgentDecisionStats(
                total_decisions=0,
                decisions_by_type={},
                decisions_by_status={},
                avg_confidence_score=0.0,
                high_confidence_rate=0.0,
                approval_rate=0.0,
                execution_rate=0.0,
                avg_processing_time_ms=0.0,
                decisions_requiring_review=0,
                recent_decisions=0
            )
        
        # Decisions by type
        type_dist_result = await db.execute(
            select(AgentDecision.decision_type, func.count(AgentDecision.id))
            .where(AgentDecision.organization_id == organization_id)
            .group_by(AgentDecision.decision_type)
        )
        decisions_by_type = {
            decision_type.value: count 
            for decision_type, count in type_dist_result
        }
        
        # Decisions by status
        status_dist_result = await db.execute(
            select(AgentDecision.status, func.count(AgentDecision.id))
            .where(AgentDecision.organization_id == organization_id)
            .group_by(AgentDecision.status)
        )
        decisions_by_status = {
            status.value: count 
            for status, count in status_dist_result
        }
        
        # Average confidence score
        avg_confidence_result = await db.execute(
            select(func.avg(AgentDecision.confidence_score))
            .where(AgentDecision.organization_id == organization_id)
        )
        avg_confidence_score = float(avg_confidence_result.scalar() or 0.0)
        
        # High confidence rate
        high_confidence_result = await db.execute(
            select(func.count(AgentDecision.id))
            .where(
                and_(
                    AgentDecision.organization_id == organization_id,
                    AgentDecision.confidence_score >= 0.8
                )
            )
        )
        high_confidence_count = high_confidence_result.scalar() or 0
        high_confidence_rate = (high_confidence_count / total_decisions) * 100
        
        # Approval rate
        approved_count = decisions_by_status.get(DecisionStatus.APPROVED.value, 0)
        rejected_count = decisions_by_status.get(DecisionStatus.REJECTED.value, 0)
        reviewed_count = approved_count + rejected_count
        approval_rate = (approved_count / reviewed_count * 100) if reviewed_count > 0 else 0.0
        
        # Execution rate
        executed_count = decisions_by_status.get(DecisionStatus.EXECUTED.value, 0)
        execution_rate = (executed_count / total_decisions) * 100
        
        # Average processing time
        avg_processing_result = await db.execute(
            select(func.avg(AgentDecision.processing_time_ms))
            .where(
                and_(
                    AgentDecision.organization_id == organization_id,
                    AgentDecision.processing_time_ms.is_not(None)
                )
            )
        )
        avg_processing_time_ms = float(avg_processing_result.scalar() or 0.0)
        
        # Decisions requiring review
        pending_count = decisions_by_status.get(DecisionStatus.PENDING.value, 0)
        
        # Recent decisions (last 24 hours)
        yesterday = datetime.now(timezone.utc) - timedelta(days=1)
        recent_result = await db.execute(
            select(func.count(AgentDecision.id))
            .where(
                and_(
                    AgentDecision.organization_id == organization_id,
                    AgentDecision.created_at >= yesterday
                )
            )
        )
        recent_decisions = recent_result.scalar() or 0
        
        return AgentDecisionStats(
            total_decisions=total_decisions,
            decisions_by_type=decisions_by_type,
            decisions_by_status=decisions_by_status,
            avg_confidence_score=round(avg_confidence_score, 3),
            high_confidence_rate=round(high_confidence_rate, 2),
            approval_rate=round(approval_rate, 2),
            execution_rate=round(execution_rate, 2),
            avg_processing_time_ms=round(avg_processing_time_ms, 2),
            decisions_requiring_review=pending_count,
            recent_decisions=recent_decisions
        )
    
    @staticmethod
    async def approve_decision(
        db: AsyncSession,
        decision_id: str,
        organization_id: str,
        approved_by: str,
        notes: Optional[str] = None
    ) -> AgentDecision:
        """Approve an agent decision"""
        decision = await AgentDecisionService.get_decision_by_id(
            db, decision_id, organization_id
        )
        
        if not decision:
            raise ValueError("Decision not found")
        
        if decision.status != DecisionStatus.PENDING:
            raise ValueError("Decision has already been reviewed")
        
        decision.approve(approved_by, notes)
        await db.commit()
        await db.refresh(decision)
        
        logger.info(f"Decision {decision_id} approved by {approved_by}")
        return decision
    
    @staticmethod
    async def reject_decision(
        db: AsyncSession,
        decision_id: str,
        organization_id: str,
        rejected_by: str,
        reason: str
    ) -> AgentDecision:
        """Reject an agent decision"""
        decision = await AgentDecisionService.get_decision_by_id(
            db, decision_id, organization_id
        )
        
        if not decision:
            raise ValueError("Decision not found")
        
        if decision.status != DecisionStatus.PENDING:
            raise ValueError("Decision has already been reviewed")
        
        decision.reject(rejected_by, reason)
        await db.commit()
        await db.refresh(decision)
        
        logger.info(f"Decision {decision_id} rejected by {rejected_by}")
        return decision
    
    @staticmethod
    async def execute_decision(
        db: AsyncSession,
        decision_id: str,
        organization_id: str,
        executed_by: str = "system",
        execution_result: Optional[Dict[str, Any]] = None
    ) -> AgentDecision:
        """Mark decision as executed"""
        decision = await AgentDecisionService.get_decision_by_id(
            db, decision_id, organization_id
        )
        
        if not decision:
            raise ValueError("Decision not found")
        
        if decision.status != DecisionStatus.APPROVED:
            raise ValueError("Decision must be approved before execution")
        
        decision.execute(executed_by, execution_result)
        await db.commit()
        await db.refresh(decision)
        
        logger.info(f"Decision {decision_id} executed by {executed_by}")
        return decision
    
    @staticmethod
    async def mark_decision_failed(
        db: AsyncSession,
        decision_id: str,
        organization_id: str,
        error_message: str
    ) -> AgentDecision:
        """Mark decision execution as failed"""
        decision = await AgentDecisionService.get_decision_by_id(
            db, decision_id, organization_id
        )
        
        if not decision:
            raise ValueError("Decision not found")
        
        decision.mark_failed(error_message)
        await db.commit()
        await db.refresh(decision)
        
        logger.error(f"Decision {decision_id} execution failed: {error_message}")
        return decision
    
    @staticmethod
    async def set_decision_outcome(
        db: AsyncSession,
        decision_id: str,
        organization_id: str,
        success: bool,
        rating: Optional[float] = None,
        feedback: Optional[str] = None
    ) -> AgentDecision:
        """Set the outcome of a decision"""
        decision = await AgentDecisionService.get_decision_by_id(
            db, decision_id, organization_id
        )
        
        if not decision:
            raise ValueError("Decision not found")
        
        decision.set_outcome(success, rating, feedback)
        await db.commit()
        await db.refresh(decision)
        
        logger.info(f"Decision {decision_id} outcome set: success={success}")
        return decision
    
    @staticmethod
    async def get_decision_performance_metrics(
        db: AsyncSession,
        organization_id: str,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Get performance metrics for agent decisions"""
        
        base_query = select(AgentDecision).where(
            AgentDecision.organization_id == organization_id
        )
        
        if date_from:
            base_query = base_query.where(AgentDecision.created_at >= date_from)
        if date_to:
            base_query = base_query.where(AgentDecision.created_at <= date_to)
        
        # Get decisions with outcomes
        outcome_result = await db.execute(
            select(
                func.count(AgentDecision.id).label('total'),
                func.sum(func.cast(AgentDecision.outcome_success, db.Integer)).label('successful'),
                func.avg(AgentDecision.outcome_rating).label('avg_rating'),
                func.avg(AgentDecision.processing_time_ms).label('avg_processing_time')
            )
            .where(
                and_(
                    AgentDecision.organization_id == organization_id,
                    AgentDecision.outcome_success.is_not(None)
                )
            )
        )
        
        outcome_stats = outcome_result.first()
        
        # Get escalation rate
        escalation_result = await db.execute(
            select(func.count(AgentDecision.id))
            .where(
                and_(
                    AgentDecision.organization_id == organization_id,
                    AgentDecision.decision_type == DecisionType.ESCALATE
                )
            )
        )
        escalation_count = escalation_result.scalar() or 0
        
        # Get total decisions for rates
        total_result = await db.execute(
            select(func.count(AgentDecision.id))
            .where(AgentDecision.organization_id == organization_id)
        )
        total_decisions = total_result.scalar() or 0
        
        return {
            "total_decisions": total_decisions,
            "decisions_with_outcomes": outcome_stats.total or 0,
            "successful_outcomes": outcome_stats.successful or 0,
            "success_rate": (outcome_stats.successful / outcome_stats.total * 100) if outcome_stats.total else 0,
            "avg_outcome_rating": float(outcome_stats.avg_rating or 0),
            "avg_processing_time_ms": float(outcome_stats.avg_processing_time or 0),
            "escalation_count": escalation_count,
            "escalation_rate": (escalation_count / total_decisions * 100) if total_decisions else 0
        }

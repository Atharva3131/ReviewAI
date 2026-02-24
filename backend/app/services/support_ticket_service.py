"""Support ticket service for managing customer support operations"""
from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, desc
from sqlalchemy.orm import selectinload
from decimal import Decimal

from app.models.support_ticket import SupportTicket, TicketStatus, TicketPriority, TicketCategory
from app.models.customer import Customer
from app.schemas.support_ticket import (
    SupportTicketCreate,
    SupportTicketUpdate,
    TicketAnalyzeResponse,
    TicketStatsResponse
)
from app.core.exceptions import NotFoundException, ValidationException


class SupportTicketService:
    """Service for managing support tickets"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create_ticket(
        self,
        organization_id: UUID,
        ticket_data: SupportTicketCreate
    ) -> SupportTicket:
        """Create a new support ticket"""
        # Validate customer exists if provided
        if ticket_data.customer_id:
            customer = await self.session.get(Customer, ticket_data.customer_id)
            if not customer or customer.organization_id != organization_id:
                raise NotFoundException("Customer not found")
        
        # Create ticket
        ticket = SupportTicket(
            organization_id=organization_id,
            customer_id=ticket_data.customer_id,
            external_id=ticket_data.external_id,
            subject=ticket_data.subject,
            content=ticket_data.content,
            priority=ticket_data.priority,
            category=ticket_data.category,
            source=ticket_data.source,
            tags=",".join(ticket_data.tags) if ticket_data.tags else None
        )
        
        self.session.add(ticket)
        await self.session.flush()
        
        # Generate ticket number
        ticket.generate_ticket_number()
        
        await self.session.commit()
        await self.session.refresh(ticket)
        
        return ticket
    
    async def get_ticket(
        self,
        ticket_id: UUID,
        organization_id: UUID
    ) -> SupportTicket:
        """Get a support ticket by ID"""
        result = await self.session.execute(
            select(SupportTicket)
            .options(selectinload(SupportTicket.customer))
            .where(
                and_(
                    SupportTicket.id == ticket_id,
                    SupportTicket.organization_id == organization_id
                )
            )
        )
        ticket = result.scalar_one_or_none()
        
        if not ticket:
            raise NotFoundException("Support ticket not found")
        
        return ticket
    
    async def list_tickets(
        self,
        organization_id: UUID,
        status: Optional[TicketStatus] = None,
        priority: Optional[TicketPriority] = None,
        category: Optional[TicketCategory] = None,
        customer_id: Optional[UUID] = None,
        assigned_to: Optional[str] = None,
        is_overdue: Optional[bool] = None,
        search: Optional[str] = None,
        page: int = 1,
        page_size: int = 50
    ) -> tuple[List[SupportTicket], int]:
        """List support tickets with filters and pagination"""
        # Build query
        query = select(SupportTicket).where(
            SupportTicket.organization_id == organization_id
        )
        
        # Apply filters
        if status:
            query = query.where(SupportTicket.status == status)
        
        if priority:
            query = query.where(SupportTicket.priority == priority)
        
        if category:
            query = query.where(SupportTicket.category == category)
        
        if customer_id:
            query = query.where(SupportTicket.customer_id == customer_id)
        
        if assigned_to:
            query = query.where(SupportTicket.assigned_to == assigned_to)
        
        if search:
            search_pattern = f"%{search}%"
            query = query.where(
                or_(
                    SupportTicket.subject.ilike(search_pattern),
                    SupportTicket.content.ilike(search_pattern),
                    SupportTicket.ticket_number.ilike(search_pattern)
                )
            )
        
        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.session.execute(count_query)
        total = total_result.scalar()
        
        # Apply pagination and ordering
        query = query.order_by(desc(SupportTicket.created_at))
        query = query.offset((page - 1) * page_size).limit(page_size)
        
        # Execute query
        result = await self.session.execute(query)
        tickets = result.scalars().all()
        
        # Filter overdue if requested (done in Python since it's a property)
        if is_overdue is not None:
            tickets = [t for t in tickets if t.is_overdue == is_overdue]
        
        return list(tickets), total
    
    async def update_ticket(
        self,
        ticket_id: UUID,
        organization_id: UUID,
        update_data: SupportTicketUpdate
    ) -> SupportTicket:
        """Update a support ticket"""
        ticket = await self.get_ticket(ticket_id, organization_id)
        
        # Update fields
        update_dict = update_data.model_dump(exclude_unset=True)
        
        # Handle tags separately
        if 'tags' in update_dict:
            tags = update_dict.pop('tags')
            ticket.tags = ",".join(tags) if tags else None
        
        for field, value in update_dict.items():
            setattr(ticket, field, value)
        
        ticket.updated_at = datetime.now(timezone.utc)
        
        await self.session.commit()
        await self.session.refresh(ticket)
        
        return ticket
    
    async def assign_ticket(
        self,
        ticket_id: UUID,
        organization_id: UUID,
        assigned_to: str
    ) -> SupportTicket:
        """Assign a ticket to a user"""
        ticket = await self.get_ticket(ticket_id, organization_id)
        ticket.assign_to(assigned_to)
        
        await self.session.commit()
        await self.session.refresh(ticket)
        
        return ticket
    
    async def resolve_ticket(
        self,
        ticket_id: UUID,
        organization_id: UUID,
        resolution: str,
        resolved_by: str
    ) -> SupportTicket:
        """Resolve a support ticket"""
        ticket = await self.get_ticket(ticket_id, organization_id)
        
        if ticket.is_resolved:
            raise ValidationException("Ticket is already resolved")
        
        ticket.resolve(resolution, resolved_by)
        
        await self.session.commit()
        await self.session.refresh(ticket)
        
        return ticket
    
    async def close_ticket(
        self,
        ticket_id: UUID,
        organization_id: UUID
    ) -> SupportTicket:
        """Close a support ticket"""
        ticket = await self.get_ticket(ticket_id, organization_id)
        
        if not ticket.is_resolved:
            raise ValidationException("Cannot close ticket that is not resolved")
        
        ticket.close()
        
        await self.session.commit()
        await self.session.refresh(ticket)
        
        return ticket
    
    async def reopen_ticket(
        self,
        ticket_id: UUID,
        organization_id: UUID,
        reason: Optional[str] = None
    ) -> SupportTicket:
        """Reopen a support ticket"""
        ticket = await self.get_ticket(ticket_id, organization_id)
        
        if not ticket.is_resolved:
            raise ValidationException("Cannot reopen ticket that is not resolved")
        
        ticket.reopen(reason)
        
        await self.session.commit()
        await self.session.refresh(ticket)
        
        return ticket
    
    async def add_response(
        self,
        ticket_id: UUID,
        organization_id: UUID,
        content: str,
        is_internal: bool = False
    ) -> SupportTicket:
        """Add a response to a ticket"""
        ticket = await self.get_ticket(ticket_id, organization_id)
        
        if is_internal:
            # Add to internal notes
            if ticket.internal_notes:
                ticket.internal_notes += f"\n\n[{datetime.now(timezone.utc).isoformat()}]\n{content}"
            else:
                ticket.internal_notes = f"[{datetime.now(timezone.utc).isoformat()}]\n{content}"
        else:
            # Record response
            ticket.add_response()
        
        await self.session.commit()
        await self.session.refresh(ticket)
        
        return ticket
    
    async def set_satisfaction(
        self,
        ticket_id: UUID,
        organization_id: UUID,
        rating: int,
        feedback: Optional[str] = None
    ) -> SupportTicket:
        """Set customer satisfaction rating"""
        ticket = await self.get_ticket(ticket_id, organization_id)
        
        if not ticket.is_resolved:
            raise ValidationException("Cannot rate ticket that is not resolved")
        
        ticket.set_satisfaction(rating, feedback)
        
        await self.session.commit()
        await self.session.refresh(ticket)
        
        return ticket
    
    async def analyze_ticket(
        self,
        ticket_id: UUID,
        organization_id: UUID
    ) -> TicketAnalyzeResponse:
        """Analyze a ticket for sentiment, urgency, and recommendations"""
        ticket = await self.get_ticket(ticket_id, organization_id)
        
        # Simple rule-based analysis
        content_lower = ticket.content.lower()
        
        # Sentiment analysis (simple keyword-based)
        negative_keywords = ['terrible', 'awful', 'horrible', 'worst', 'angry', 'frustrated', 'disappointed']
        positive_keywords = ['great', 'excellent', 'wonderful', 'amazing', 'happy', 'satisfied']
        urgent_keywords = ['urgent', 'asap', 'immediately', 'critical', 'emergency', 'broken']
        
        negative_count = sum(1 for word in negative_keywords if word in content_lower)
        positive_count = sum(1 for word in positive_keywords if word in content_lower)
        urgent_count = sum(1 for word in urgent_keywords if word in content_lower)
        
        # Calculate sentiment score (0.0 to 1.0)
        if negative_count > positive_count:
            sentiment_score = max(0.1, 0.5 - (negative_count * 0.1))
        elif positive_count > negative_count:
            sentiment_score = min(0.9, 0.5 + (positive_count * 0.1))
        else:
            sentiment_score = 0.5
        
        # Calculate urgency score
        urgency_score = min(0.9, 0.3 + (urgent_count * 0.2))
        
        # Calculate escalation risk
        escalation_risk = (1.0 - sentiment_score) * 0.6 + urgency_score * 0.4
        
        # Recommend priority
        if escalation_risk > 0.7:
            recommended_priority = TicketPriority.CRITICAL
        elif escalation_risk > 0.5:
            recommended_priority = TicketPriority.HIGH
        elif escalation_risk > 0.3:
            recommended_priority = TicketPriority.MEDIUM
        else:
            recommended_priority = TicketPriority.LOW
        
        # Recommend category based on keywords
        category_keywords = {
            TicketCategory.BILLING: ['bill', 'charge', 'payment', 'invoice', 'refund'],
            TicketCategory.TECHNICAL: ['error', 'bug', 'broken', 'not working', 'crash'],
            TicketCategory.SHIPPING: ['delivery', 'shipping', 'package', 'tracking'],
            TicketCategory.PRODUCT: ['product', 'quality', 'defect', 'damaged'],
            TicketCategory.ACCOUNT: ['account', 'login', 'password', 'access']
        }
        
        recommended_category = None
        max_matches = 0
        for category, keywords in category_keywords.items():
            matches = sum(1 for word in keywords if word in content_lower)
            if matches > max_matches:
                max_matches = matches
                recommended_category = category
        
        # Suggest actions
        suggested_actions = []
        if escalation_risk > 0.7:
            suggested_actions.append("Escalate to senior support")
        if sentiment_score < 0.3:
            suggested_actions.append("Offer compensation or discount")
        if urgent_count > 0:
            suggested_actions.append("Respond within 2 hours")
        if not suggested_actions:
            suggested_actions.append("Respond with standard resolution")
        
        # Update ticket with analysis
        ticket.sentiment_score = Decimal(str(round(sentiment_score, 2)))
        ticket.urgency_score = Decimal(str(round(urgency_score, 2)))
        ticket.escalation_risk = Decimal(str(round(escalation_risk, 2)))
        
        await self.session.commit()
        
        return TicketAnalyzeResponse(
            ticket_id=ticket.id,
            sentiment_score=Decimal(str(round(sentiment_score, 2))),
            sentiment_label=ticket.sentiment_label,
            urgency_score=Decimal(str(round(urgency_score, 2))),
            escalation_risk=Decimal(str(round(escalation_risk, 2))),
            recommended_priority=recommended_priority,
            recommended_category=recommended_category,
            suggested_actions=suggested_actions
        )
    
    async def get_ticket_stats(
        self,
        organization_id: UUID
    ) -> TicketStatsResponse:
        """Get ticket statistics for an organization"""
        # Get all tickets for the organization
        result = await self.session.execute(
            select(SupportTicket).where(
                SupportTicket.organization_id == organization_id
            )
        )
        tickets = result.scalars().all()
        
        # Calculate statistics
        total_tickets = len(tickets)
        open_tickets = sum(1 for t in tickets if t.status == TicketStatus.OPEN)
        in_progress_tickets = sum(1 for t in tickets if t.status == TicketStatus.IN_PROGRESS)
        resolved_tickets = sum(1 for t in tickets if t.status == TicketStatus.RESOLVED)
        closed_tickets = sum(1 for t in tickets if t.status == TicketStatus.CLOSED)
        overdue_tickets = sum(1 for t in tickets if t.is_overdue)
        
        # Average times
        response_times = [t.time_to_first_response for t in tickets if t.time_to_first_response]
        resolution_times = [t.time_to_resolution for t in tickets if t.time_to_resolution]
        satisfaction_ratings = [t.satisfaction_rating for t in tickets if t.satisfaction_rating]
        
        avg_time_to_first_response = sum(response_times) / len(response_times) if response_times else None
        avg_time_to_resolution = sum(resolution_times) / len(resolution_times) if resolution_times else None
        avg_satisfaction_rating = sum(satisfaction_ratings) / len(satisfaction_ratings) if satisfaction_ratings else None
        
        # Tickets by priority
        tickets_by_priority = {}
        for priority in TicketPriority:
            tickets_by_priority[priority.value] = sum(1 for t in tickets if t.priority == priority)
        
        # Tickets by category
        tickets_by_category = {}
        for category in TicketCategory:
            tickets_by_category[category.value] = sum(1 for t in tickets if t.category == category)
        
        # Tickets by source
        tickets_by_source = {}
        for ticket in tickets:
            if ticket.source:
                tickets_by_source[ticket.source] = tickets_by_source.get(ticket.source, 0) + 1
        
        return TicketStatsResponse(
            total_tickets=total_tickets,
            open_tickets=open_tickets,
            in_progress_tickets=in_progress_tickets,
            resolved_tickets=resolved_tickets,
            closed_tickets=closed_tickets,
            overdue_tickets=overdue_tickets,
            avg_time_to_first_response=round(avg_time_to_first_response, 2) if avg_time_to_first_response else None,
            avg_time_to_resolution=round(avg_time_to_resolution, 2) if avg_time_to_resolution else None,
            avg_satisfaction_rating=round(avg_satisfaction_rating, 2) if avg_satisfaction_rating else None,
            tickets_by_priority=tickets_by_priority,
            tickets_by_category=tickets_by_category,
            tickets_by_source=tickets_by_source
        )
    
    async def delete_ticket(
        self,
        ticket_id: UUID,
        organization_id: UUID
    ) -> None:
        """Delete a support ticket"""
        ticket = await self.get_ticket(ticket_id, organization_id)
        
        await self.session.delete(ticket)
        await self.session.commit()


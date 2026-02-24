"""Tests for support ticket API endpoints"""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.organization import Organization
from app.models.user import User
from app.models.customer import Customer
from app.models.support_ticket import SupportTicket, TicketStatus, TicketPriority, TicketCategory


@pytest.mark.asyncio
class TestSupportTicketAPI:
    """Test support ticket API endpoints"""
    
    async def test_create_ticket(
        self,
        async_client: AsyncClient,
        test_organization: Organization,
        test_user: User,
        test_customer: Customer,
        auth_headers: dict
    ):
        """Test creating a support ticket"""
        ticket_data = {
            "subject": "Product not working",
            "content": "The product stopped working after the latest update. This is urgent!",
            "priority": "high",
            "category": "technical",
            "customer_id": str(test_customer.id),
            "source": "email",
            "tags": ["urgent", "bug"]
        }
        
        response = await async_client.post(
            "/api/v1/support-tickets/",
            json=ticket_data,
            headers=auth_headers
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["subject"] == ticket_data["subject"]
        assert data["content"] == ticket_data["content"]
        assert data["priority"] == ticket_data["priority"]
        assert data["category"] == ticket_data["category"]
        assert data["status"] == "open"
        assert data["ticket_number"] is not None
        assert data["is_open"] is True
        assert data["is_resolved"] is False
    
    async def test_list_tickets(
        self,
        async_client: AsyncClient,
        test_organization: Organization,
        test_user: User,
        auth_headers: dict,
        session: AsyncSession
    ):
        """Test listing support tickets"""
        # Create test tickets
        for i in range(3):
            ticket = SupportTicket(
                organization_id=test_organization.id,
                subject=f"Test ticket {i}",
                content=f"Content for ticket {i}",
                priority=TicketPriority.MEDIUM
            )
            session.add(ticket)
        
        await session.commit()
        
        response = await async_client.get(
            "/api/v1/support-tickets/",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "tickets" in data
        assert "total" in data
        assert data["total"] >= 3
        assert len(data["tickets"]) >= 3
    
    async def test_get_ticket(
        self,
        async_client: AsyncClient,
        test_organization: Organization,
        test_user: User,
        auth_headers: dict,
        session: AsyncSession
    ):
        """Test getting a specific ticket"""
        ticket = SupportTicket(
            organization_id=test_organization.id,
            subject="Test ticket",
            content="Test content",
            priority=TicketPriority.HIGH
        )
        session.add(ticket)
        await session.commit()
        await session.refresh(ticket)
        
        response = await async_client.get(
            f"/api/v1/support-tickets/{ticket.id}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(ticket.id)
        assert data["subject"] == ticket.subject
    
    async def test_update_ticket(
        self,
        async_client: AsyncClient,
        test_organization: Organization,
        test_user: User,
        auth_headers: dict,
        session: AsyncSession
    ):
        """Test updating a ticket"""
        ticket = SupportTicket(
            organization_id=test_organization.id,
            subject="Original subject",
            content="Original content",
            priority=TicketPriority.LOW
        )
        session.add(ticket)
        await session.commit()
        await session.refresh(ticket)
        
        update_data = {
            "subject": "Updated subject",
            "priority": "high"
        }
        
        response = await async_client.patch(
            f"/api/v1/support-tickets/{ticket.id}",
            json=update_data,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["subject"] == "Updated subject"
        assert data["priority"] == "high"
    
    async def test_assign_ticket(
        self,
        async_client: AsyncClient,
        test_organization: Organization,
        test_user: User,
        auth_headers: dict,
        session: AsyncSession
    ):
        """Test assigning a ticket"""
        ticket = SupportTicket(
            organization_id=test_organization.id,
            subject="Test ticket",
            content="Test content",
            status=TicketStatus.OPEN
        )
        session.add(ticket)
        await session.commit()
        await session.refresh(ticket)
        
        assign_data = {
            "assigned_to": "agent_123"
        }
        
        response = await async_client.post(
            f"/api/v1/support-tickets/{ticket.id}/assign",
            json=assign_data,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["assigned_to"] == "agent_123"
        assert data["status"] == "in_progress"
        assert data["assigned_at"] is not None
    
    async def test_resolve_ticket(
        self,
        async_client: AsyncClient,
        test_organization: Organization,
        test_user: User,
        auth_headers: dict,
        session: AsyncSession
    ):
        """Test resolving a ticket"""
        ticket = SupportTicket(
            organization_id=test_organization.id,
            subject="Test ticket",
            content="Test content",
            status=TicketStatus.IN_PROGRESS
        )
        session.add(ticket)
        await session.commit()
        await session.refresh(ticket)
        
        resolve_data = {
            "resolution": "Issue was fixed by updating the software",
            "resolved_by": "agent_123"
        }
        
        response = await async_client.post(
            f"/api/v1/support-tickets/{ticket.id}/resolve",
            json=resolve_data,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "resolved"
        assert data["resolution"] == resolve_data["resolution"]
        assert data["resolved_by"] == resolve_data["resolved_by"]
        assert data["resolved_at"] is not None
        assert data["is_resolved"] is True
    
    async def test_analyze_ticket(
        self,
        async_client: AsyncClient,
        test_organization: Organization,
        test_user: User,
        auth_headers: dict,
        session: AsyncSession
    ):
        """Test analyzing a ticket"""
        ticket = SupportTicket(
            organization_id=test_organization.id,
            subject="Urgent issue",
            content="This is terrible! The product is broken and I need help immediately. This is critical!",
            priority=TicketPriority.MEDIUM
        )
        session.add(ticket)
        await session.commit()
        await session.refresh(ticket)
        
        analyze_data = {
            "ticket_id": str(ticket.id)
        }
        
        response = await async_client.post(
            "/api/v1/support-tickets/analyze",
            json=analyze_data,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "sentiment_score" in data
        assert "urgency_score" in data
        assert "escalation_risk" in data
        assert "recommended_priority" in data
        assert "suggested_actions" in data
        assert len(data["suggested_actions"]) > 0
    
    async def test_get_ticket_stats(
        self,
        async_client: AsyncClient,
        test_organization: Organization,
        test_user: User,
        auth_headers: dict,
        session: AsyncSession
    ):
        """Test getting ticket statistics"""
        # Create tickets with different statuses
        statuses = [TicketStatus.OPEN, TicketStatus.IN_PROGRESS, TicketStatus.RESOLVED]
        for status in statuses:
            ticket = SupportTicket(
                organization_id=test_organization.id,
                subject=f"Ticket {status.value}",
                content="Test content",
                status=status,
                priority=TicketPriority.MEDIUM
            )
            session.add(ticket)
        
        await session.commit()
        
        response = await async_client.get(
            "/api/v1/support-tickets/stats",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "total_tickets" in data
        assert "open_tickets" in data
        assert "in_progress_tickets" in data
        assert "resolved_tickets" in data
        assert "tickets_by_priority" in data
        assert data["total_tickets"] >= 3

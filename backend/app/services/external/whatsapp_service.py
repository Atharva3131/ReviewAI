"""
WhatsApp Business API integration service
"""
import logging
from typing import Dict, Any, List, Optional, Union
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import uuid

from .base_service import BaseExternalService, ServiceResponse, RetryConfig
from .error_handler import error_handler, ErrorContext, with_retry_and_circuit_breaker
from app.core.config import settings

logger = logging.getLogger(__name__)


class MessageType(str, Enum):
    """WhatsApp message types"""
    TEXT = "text"
    TEMPLATE = "template"
    INTERACTIVE = "interactive"
    MEDIA = "media"


class MessageStatus(str, Enum):
    """WhatsApp message status"""
    SENT = "sent"
    DELIVERED = "delivered"
    READ = "read"
    FAILED = "failed"


@dataclass
class WhatsAppContact:
    """WhatsApp contact data structure"""
    phone_number: str
    name: Optional[str] = None
    profile_name: Optional[str] = None


@dataclass
class WhatsAppMessage:
    """WhatsApp message data structure"""
    message_id: str
    to: str
    message_type: MessageType
    content: str
    status: MessageStatus = MessageStatus.SENT
    timestamp: datetime = None
    template_name: Optional[str] = None
    template_params: Optional[List[str]] = None
    media_url: Optional[str] = None
    media_type: Optional[str] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()


class WhatsAppBusinessService(BaseExternalService):
    """
    WhatsApp Business API integration service
    
    This is a mock implementation for development and testing.
    In production, this would integrate with WhatsApp Business API.
    """
    
    def __init__(self):
        super().__init__(
            service_name="whatsapp_business",
            base_url=settings.WHATSAPP_API_URL or "https://graph.facebook.com/v18.0",
            timeout=30.0,
            retry_config=RetryConfig(
                max_retries=3,
                backoff_factor=2.0,
                retry_on_status=[429, 500, 502, 503, 504]
            )
        )
        self.access_token = settings.WHATSAPP_ACCESS_TOKEN
        self.phone_number_id = settings.WHATSAPP_PHONE_NUMBER_ID
        
    async def send_text_message(
        self, 
        to: str, 
        message: str,
        context: Optional[ErrorContext] = None
    ) -> ServiceResponse[WhatsAppMessage]:
        """Send a text message via WhatsApp"""
        
        @with_retry_and_circuit_breaker(
            service_name=self.service_name,
            operation="send_text_message",
            context=context
        )
        async def _send():
            # Mock implementation for development
            if settings.ENVIRONMENT == "development":
                return await self._mock_send_message(to, message, MessageType.TEXT)
            
            # Real implementation would call WhatsApp API
            payload = {
                "messaging_product": "whatsapp",
                "to": to,
                "type": "text",
                "text": {"body": message}
            }
            
            response = await self._make_request(
                "POST",
                f"/{self.phone_number_id}/messages",
                json=payload,
                headers={"Authorization": f"Bearer {self.access_token}"}
            )
            
            if response.success:
                message_data = response.data
                whatsapp_message = WhatsAppMessage(
                    message_id=message_data.get("messages", [{}])[0].get("id", str(uuid.uuid4())),
                    to=to,
                    message_type=MessageType.TEXT,
                    content=message,
                    status=MessageStatus.SENT
                )
                return ServiceResponse(success=True, data=whatsapp_message)
            else:
                return ServiceResponse(success=False, error=response.error)
        
        return await _send()
    
    async def send_template_message(
        self,
        to: str,
        template_name: str,
        template_params: List[str],
        context: Optional[ErrorContext] = None
    ) -> ServiceResponse[WhatsAppMessage]:
        """Send a template message via WhatsApp"""
        
        @with_retry_and_circuit_breaker(
            service_name=self.service_name,
            operation="send_template_message",
            context=context
        )
        async def _send():
            # Mock implementation for development
            if settings.ENVIRONMENT == "development":
                return await self._mock_send_template(to, template_name, template_params)
            
            # Real implementation would call WhatsApp API
            payload = {
                "messaging_product": "whatsapp",
                "to": to,
                "type": "template",
                "template": {
                    "name": template_name,
                    "language": {"code": "en_US"},
                    "components": [
                        {
                            "type": "body",
                            "parameters": [{"type": "text", "text": param} for param in template_params]
                        }
                    ]
                }
            }
            
            response = await self._make_request(
                "POST",
                f"/{self.phone_number_id}/messages",
                json=payload,
                headers={"Authorization": f"Bearer {self.access_token}"}
            )
            
            if response.success:
                message_data = response.data
                whatsapp_message = WhatsAppMessage(
                    message_id=message_data.get("messages", [{}])[0].get("id", str(uuid.uuid4())),
                    to=to,
                    message_type=MessageType.TEMPLATE,
                    content=f"Template: {template_name}",
                    template_name=template_name,
                    template_params=template_params,
                    status=MessageStatus.SENT
                )
                return ServiceResponse(success=True, data=whatsapp_message)
            else:
                return ServiceResponse(success=False, error=response.error)
        
        return await _send()
    
    async def get_message_status(
        self, 
        message_id: str,
        context: Optional[ErrorContext] = None
    ) -> ServiceResponse[MessageStatus]:
        """Get the status of a WhatsApp message"""
        
        @with_retry_and_circuit_breaker(
            service_name=self.service_name,
            operation="get_message_status",
            context=context
        )
        async def _get_status():
            # Mock implementation for development
            if settings.ENVIRONMENT == "development":
                return ServiceResponse(success=True, data=MessageStatus.DELIVERED)
            
            # Real implementation would query WhatsApp API
            # Note: WhatsApp doesn't provide a direct message status API
            # Status updates come via webhooks
            return ServiceResponse(success=True, data=MessageStatus.SENT)
        
        return await _get_status()
    
    async def _mock_send_message(
        self, 
        to: str, 
        message: str, 
        message_type: MessageType
    ) -> ServiceResponse[WhatsAppMessage]:
        """Mock message sending for development"""
        
        # Simulate API delay
        await self._simulate_delay(0.5, 1.5)
        
        # Simulate occasional failures
        if await self._should_simulate_failure(0.05):  # 5% failure rate
            return ServiceResponse(
                success=False,
                error="Mock WhatsApp API error: Rate limit exceeded"
            )
        
        whatsapp_message = WhatsAppMessage(
            message_id=f"mock_msg_{uuid.uuid4().hex[:8]}",
            to=to,
            message_type=message_type,
            content=message,
            status=MessageStatus.SENT
        )
        
        logger.info(f"Mock WhatsApp message sent to {to}: {message[:50]}...")
        
        return ServiceResponse(success=True, data=whatsapp_message)
    
    async def _mock_send_template(
        self, 
        to: str, 
        template_name: str, 
        template_params: List[str]
    ) -> ServiceResponse[WhatsAppMessage]:
        """Mock template message sending for development"""
        
        # Simulate API delay
        await self._simulate_delay(0.5, 1.5)
        
        # Simulate occasional failures
        if await self._should_simulate_failure(0.03):  # 3% failure rate
            return ServiceResponse(
                success=False,
                error="Mock WhatsApp API error: Template not approved"
            )
        
        whatsapp_message = WhatsAppMessage(
            message_id=f"mock_template_{uuid.uuid4().hex[:8]}",
            to=to,
            message_type=MessageType.TEMPLATE,
            content=f"Template: {template_name}",
            template_name=template_name,
            template_params=template_params,
            status=MessageStatus.SENT
        )
        
        logger.info(f"Mock WhatsApp template sent to {to}: {template_name}")
        
        return ServiceResponse(success=True, data=whatsapp_message)


# Factory function
def create_whatsapp_service() -> WhatsAppBusinessService:
    """Create WhatsApp Business service instance"""
    return WhatsAppBusinessService()


# Service instance for dependency injection
whatsapp_service = create_whatsapp_service()

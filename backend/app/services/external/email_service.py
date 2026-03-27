"""
Email service integration for SendGrid and AWS SES
"""

import base64
import json
import logging
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from app.core.config import settings

from .base_service import BaseExternalService, RetryConfig, ServiceResponse
from .error_handler import ErrorContext, error_handler, with_retry_and_circuit_breaker

logger = logging.getLogger(__name__)


class EmailProvider(str, Enum):
    """Supported email providers"""

    SENDGRID = "sendgrid"
    AWS_SES = "aws_ses"
    MOCK = "mock"


@dataclass
class EmailAttachment:
    """Email attachment data structure"""

    filename: str
    content: bytes
    content_type: str = "application/octet-stream"


@dataclass
class EmailRecipient:
    """Email recipient data structure"""

    email: str
    name: Optional[str] = None


@dataclass
class EmailMessage:
    """Email message data structure"""

    to: List[EmailRecipient]
    subject: str
    html_content: Optional[str] = None
    text_content: Optional[str] = None
    from_email: Optional[str] = None
    from_name: Optional[str] = None
    reply_to: Optional[str] = None
    cc: Optional[List[EmailRecipient]] = None
    bcc: Optional[List[EmailRecipient]] = None
    attachments: Optional[List[EmailAttachment]] = None
    template_id: Optional[str] = None
    template_data: Optional[Dict[str, Any]] = None
    tags: Optional[List[str]] = None
    custom_args: Optional[Dict[str, str]] = None


class SendGridEmailService(BaseExternalService):
    """SendGrid email service integration"""

    def __init__(self, api_key: Optional[str] = None):
        super().__init__(
            service_name="sendgrid",
            base_url="https://api.sendgrid.com/v3",
            api_key=api_key or settings.SENDGRID_API_KEY,
            timeout=30,
            retry_config=RetryConfig(max_retries=3, base_delay=1.0),
        )
        self.from_email = settings.SENDGRID_FROM_EMAIL
        self.from_name = settings.SENDGRID_FROM_NAME

    def _get_auth_headers(self) -> Dict[str, str]:
        """Get SendGrid authentication headers"""
        return {"Authorization": f"Bearer {self.api_key}"}

    async def test_connection(self) -> ServiceResponse:
        """Test connection to SendGrid API"""
        try:
            # Test with API key validation
            response = await self._make_request("GET", "/user/profile")

            if response.success:
                logger.info("SendGrid API connection successful")
                return ServiceResponse(
                    success=True,
                    data={"message": "Connection successful", "profile": response.data},
                )
            else:
                logger.error(f"SendGrid API connection failed: {response.error}")
                return response

        except Exception as e:
            logger.error(f"SendGrid API test connection error: {e}")
            return ServiceResponse(success=False, error=str(e))

    async def send_email(self, message: EmailMessage) -> ServiceResponse:
        """Send email via SendGrid"""
        try:
            # Build SendGrid payload
            payload = self._build_sendgrid_payload(message)

            response = await self._make_request("POST", "/mail/send", data=payload)

            if response.success:
                logger.info(
                    f"Email sent successfully via SendGrid to {len(message.to)} recipients"
                )
                return ServiceResponse(
                    success=True,
                    data={
                        "message_id": response.data.get("message_id"),
                        "recipients": len(message.to),
                        "provider": "sendgrid",
                        "sent_at": datetime.utcnow().isoformat(),
                    },
                )

            return response

        except Exception as e:
            logger.error(f"Error sending email via SendGrid: {e}")
            return ServiceResponse(success=False, error=str(e))

    async def send_template_email(
        self,
        template_id: str,
        to_emails: List[EmailRecipient],
        template_data: Dict[str, Any],
        subject: Optional[str] = None,
    ) -> ServiceResponse:
        """Send templated email via SendGrid"""
        try:
            message = EmailMessage(
                to=to_emails,
                subject=subject
                or "{{subject}}",  # Use template subject if not provided
                template_id=template_id,
                template_data=template_data,
            )

            return await self.send_email(message)

        except Exception as e:
            logger.error(f"Error sending template email via SendGrid: {e}")
            return ServiceResponse(success=False, error=str(e))

    def _build_sendgrid_payload(self, message: EmailMessage) -> Dict[str, Any]:
        """Build SendGrid API payload"""
        payload = {
            "from": {
                "email": message.from_email or self.from_email,
                "name": message.from_name or self.from_name,
            },
            "personalizations": [
                {
                    "to": [
                        {"email": recipient.email, "name": recipient.name}
                        for recipient in message.to
                    ]
                }
            ],
        }

        # Add subject
        if message.subject:
            payload["subject"] = message.subject

        # Add content
        content = []
        if message.text_content:
            content.append({"type": "text/plain", "value": message.text_content})
        if message.html_content:
            content.append({"type": "text/html", "value": message.html_content})

        if content:
            payload["content"] = content

        # Add template
        if message.template_id:
            payload["template_id"] = message.template_id
            if message.template_data:
                payload["personalizations"][0][
                    "dynamic_template_data"
                ] = message.template_data

        # Add reply-to
        if message.reply_to:
            payload["reply_to"] = {"email": message.reply_to}

        # Add CC/BCC
        if message.cc:
            payload["personalizations"][0]["cc"] = [
                {"email": recipient.email, "name": recipient.name}
                for recipient in message.cc
            ]

        if message.bcc:
            payload["personalizations"][0]["bcc"] = [
                {"email": recipient.email, "name": recipient.name}
                for recipient in message.bcc
            ]

        # Add attachments
        if message.attachments:
            payload["attachments"] = []
            for attachment in message.attachments:
                payload["attachments"].append(
                    {
                        "content": base64.b64encode(attachment.content).decode(),
                        "filename": attachment.filename,
                        "type": attachment.content_type,
                    }
                )

        # Add tracking and metadata
        if message.tags:
            payload["categories"] = message.tags

        if message.custom_args:
            payload["custom_args"] = message.custom_args

        return payload


class AWSEmailService(BaseExternalService):
    """AWS SES email service integration"""

    def __init__(
        self,
        access_key: Optional[str] = None,
        secret_key: Optional[str] = None,
        region: str = "us-east-1",
    ):
        super().__init__(
            service_name="aws_ses",
            base_url=f"https://email.{region}.amazonaws.com",
            timeout=30,
            retry_config=RetryConfig(max_retries=3, base_delay=1.0),
        )
        self.access_key = access_key or settings.AWS_ACCESS_KEY_ID
        self.secret_key = secret_key or settings.AWS_SECRET_ACCESS_KEY
        self.region = region
        self.from_email = settings.AWS_SES_FROM_EMAIL
        self.from_name = settings.AWS_SES_FROM_NAME

    def _get_auth_headers(self) -> Dict[str, str]:
        """Get AWS SES authentication headers (AWS Signature V4)"""
        # This is a simplified version - in production, use boto3 or proper AWS signing
        return {
            "Authorization": f"AWS4-HMAC-SHA256 Credential={self.access_key}/...",
            "X-Amz-Date": datetime.utcnow().strftime("%Y%m%dT%H%M%SZ"),
        }

    async def test_connection(self) -> ServiceResponse:
        """Test connection to AWS SES"""
        try:
            # Test with get send quota
            response = await self._make_request(
                "POST", "/", data={"Action": "GetSendQuota", "Version": "2010-12-01"}
            )

            if response.success:
                logger.info("AWS SES connection successful")
                return ServiceResponse(
                    success=True,
                    data={"message": "Connection successful", "quota": response.data},
                )
            else:
                logger.error(f"AWS SES connection failed: {response.error}")
                return response

        except Exception as e:
            logger.error(f"AWS SES test connection error: {e}")
            return ServiceResponse(success=False, error=str(e))

    async def send_email(self, message: EmailMessage) -> ServiceResponse:
        """Send email via AWS SES"""
        try:
            # Build AWS SES payload
            payload = self._build_aws_ses_payload(message)

            response = await self._make_request("POST", "/", data=payload)

            if response.success:
                logger.info(
                    f"Email sent successfully via AWS SES to {len(message.to)} recipients"
                )
                return ServiceResponse(
                    success=True,
                    data={
                        "message_id": response.data.get("MessageId"),
                        "recipients": len(message.to),
                        "provider": "aws_ses",
                        "sent_at": datetime.utcnow().isoformat(),
                    },
                )

            return response

        except Exception as e:
            logger.error(f"Error sending email via AWS SES: {e}")
            return ServiceResponse(success=False, error=str(e))

    def _build_aws_ses_payload(self, message: EmailMessage) -> Dict[str, Any]:
        """Build AWS SES API payload"""
        payload = {
            "Action": "SendEmail",
            "Version": "2010-12-01",
            "Source": f"{message.from_name or self.from_name} <{message.from_email or self.from_email}>",
            "Message.Subject.Data": message.subject,
            "Message.Subject.Charset": "UTF-8",
        }

        # Add destinations
        for i, recipient in enumerate(message.to):
            payload[f"Destination.ToAddresses.member.{i+1}"] = recipient.email

        # Add content
        if message.text_content:
            payload["Message.Body.Text.Data"] = message.text_content
            payload["Message.Body.Text.Charset"] = "UTF-8"

        if message.html_content:
            payload["Message.Body.Html.Data"] = message.html_content
            payload["Message.Body.Html.Charset"] = "UTF-8"

        # Add reply-to
        if message.reply_to:
            payload["ReplyToAddresses.member.1"] = message.reply_to

        return payload


class MockEmailService(BaseExternalService):
    """Mock email service for testing and development"""

    def __init__(self):
        super().__init__(
            service_name="mock_email",
            base_url="http://localhost:8080",  # Mock URL
            timeout=5,
            retry_config=RetryConfig(max_retries=1, base_delay=0.1),
        )
        self.sent_emails: List[Dict[str, Any]] = []

    def _get_auth_headers(self) -> Dict[str, str]:
        """Mock auth headers"""
        return {"Authorization": "Bearer mock_token"}

    async def test_connection(self) -> ServiceResponse:
        """Mock connection test"""
        return ServiceResponse(
            success=True, data={"message": "Mock email service connection successful"}
        )

    async def send_email(self, message: EmailMessage) -> ServiceResponse:
        """Mock email sending"""
        try:
            # Store email for testing
            email_data = {
                "message_id": f"mock_{len(self.sent_emails) + 1}",
                "to": [{"email": r.email, "name": r.name} for r in message.to],
                "subject": message.subject,
                "html_content": message.html_content,
                "text_content": message.text_content,
                "from_email": message.from_email,
                "from_name": message.from_name,
                "sent_at": datetime.utcnow().isoformat(),
                "provider": "mock",
            }

            self.sent_emails.append(email_data)

            logger.info(f"Mock email sent to {len(message.to)} recipients")

            return ServiceResponse(success=True, data=email_data)

        except Exception as e:
            logger.error(f"Mock email service error: {e}")
            return ServiceResponse(success=False, error=str(e))

    def get_sent_emails(self) -> List[Dict[str, Any]]:
        """Get all sent emails (for testing)"""
        return self.sent_emails

    def clear_sent_emails(self):
        """Clear sent emails (for testing)"""
        self.sent_emails.clear()


class EmailServiceManager:
    """Manager for email services with provider switching"""

    def __init__(self, primary_provider: EmailProvider = EmailProvider.SENDGRID):
        self.primary_provider = primary_provider
        self.services: Dict[EmailProvider, BaseExternalService] = {}
        self.fallback_order = [
            EmailProvider.SENDGRID,
            EmailProvider.AWS_SES,
            EmailProvider.MOCK,
        ]

        # Initialize services
        self._initialize_services()

    def _initialize_services(self):
        """Initialize email service providers"""
        try:
            # SendGrid
            if settings.SENDGRID_API_KEY:
                self.services[EmailProvider.SENDGRID] = SendGridEmailService()
                logger.info("SendGrid email service initialized")
        except Exception as e:
            logger.warning(f"Failed to initialize SendGrid: {e}")

        try:
            # AWS SES
            if settings.AWS_ACCESS_KEY_ID and settings.AWS_SECRET_ACCESS_KEY:
                self.services[EmailProvider.AWS_SES] = AWSEmailService()
                logger.info("AWS SES email service initialized")
        except Exception as e:
            logger.warning(f"Failed to initialize AWS SES: {e}")

        # Mock service (always available)
        self.services[EmailProvider.MOCK] = MockEmailService()
        logger.info("Mock email service initialized")

    async def send_email(
        self, message: EmailMessage, provider: Optional[EmailProvider] = None
    ) -> ServiceResponse:
        """Send email with automatic fallback"""
        providers_to_try = [provider] if provider else [self.primary_provider]
        providers_to_try.extend(
            [p for p in self.fallback_order if p not in providers_to_try]
        )

        last_error = None

        for provider_type in providers_to_try:
            service = self.services.get(provider_type)
            if not service:
                continue

            try:
                response = await service.send_email(message)
                if response.success:
                    return response
                else:
                    last_error = response.error
                    logger.warning(
                        f"Email failed via {provider_type.value}: {response.error}"
                    )

            except Exception as e:
                last_error = str(e)
                logger.error(f"Email service error with {provider_type.value}: {e}")

        return ServiceResponse(
            success=False, error=f"All email providers failed. Last error: {last_error}"
        )

    async def send_recovery_email(
        self,
        customer_email: str,
        customer_name: str,
        recovery_content: str,
        subject: str = "We'd like to make things right",
    ) -> ServiceResponse:
        """Send customer recovery email"""
        message = EmailMessage(
            to=[EmailRecipient(email=customer_email, name=customer_name)],
            subject=subject,
            html_content=recovery_content,
            text_content=self._html_to_text(recovery_content),
            tags=["recovery", "customer_service"],
            custom_args={"email_type": "recovery", "customer_email": customer_email},
        )

        return await self.send_email(message)

    async def send_review_response_notification(
        self, business_email: str, review_details: Dict[str, Any], response_content: str
    ) -> ServiceResponse:
        """Send notification about review response"""
        subject = f"Review Response Posted - {review_details.get('rating', 0)}★ Review"

        html_content = f"""
        <h2>Review Response Posted</h2>
        <p>A response has been posted to a {review_details.get('rating', 0)}-star review.</p>
        
        <h3>Original Review:</h3>
        <blockquote>{review_details.get('content', 'No content')}</blockquote>
        <p><strong>Customer:</strong> {review_details.get('customer_name', 'Anonymous')}</p>
        <p><strong>Date:</strong> {review_details.get('created_at', 'Unknown')}</p>
        
        <h3>Your Response:</h3>
        <blockquote>{response_content}</blockquote>
        
        <p>This response is now live on your review platform.</p>
        """

        message = EmailMessage(
            to=[EmailRecipient(email=business_email)],
            subject=subject,
            html_content=html_content,
            text_content=self._html_to_text(html_content),
            tags=["review_response", "notification"],
            custom_args={
                "email_type": "review_notification",
                "review_id": str(review_details.get("id", "")),
            },
        )

        return await self.send_email(message)

    async def send_alert_email(
        self,
        recipient_email: str,
        alert_title: str,
        alert_description: str,
        alert_priority: str = "medium",
    ) -> ServiceResponse:
        """Send system alert email"""
        priority_colors = {
            "low": "#28a745",
            "medium": "#ffc107",
            "high": "#fd7e14",
            "critical": "#dc3545",
        }

        color = priority_colors.get(alert_priority, "#6c757d")

        html_content = f"""
        <div style="border-left: 4px solid {color}; padding: 20px; background-color: #f8f9fa;">
            <h2 style="color: {color}; margin-top: 0;">🚨 {alert_title}</h2>
            <p>{alert_description}</p>
            <p><strong>Priority:</strong> <span style="color: {color}; text-transform: uppercase;">{alert_priority}</span></p>
            <p><strong>Time:</strong> {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC</p>
            
            <hr style="margin: 20px 0;">
            <p style="font-size: 12px; color: #6c757d;">
                This is an automated alert from your Revive AI system.
            </p>
        </div>
        """

        message = EmailMessage(
            to=[EmailRecipient(email=recipient_email)],
            subject=f"[{alert_priority.upper()}] {alert_title}",
            html_content=html_content,
            text_content=self._html_to_text(html_content),
            tags=["alert", alert_priority],
            custom_args={"email_type": "alert", "priority": alert_priority},
        )

        return await self.send_email(message)

    def _html_to_text(self, html_content: str) -> str:
        """Convert HTML to plain text (simple implementation)"""
        import re

        # Remove HTML tags
        text = re.sub(r"<[^>]+>", "", html_content)

        # Replace HTML entities
        text = text.replace("&nbsp;", " ")
        text = text.replace("&amp;", "&")
        text = text.replace("&lt;", "<")
        text = text.replace("&gt;", ">")

        # Clean up whitespace
        text = re.sub(r"\s+", " ", text)
        text = text.strip()

        return text

    async def get_service_status(self) -> Dict[str, Any]:
        """Get status of all email services"""
        status = {}

        for provider, service in self.services.items():
            try:
                service_status = await service.get_service_status()
                status[provider.value] = service_status
            except Exception as e:
                status[provider.value] = {
                    "service_name": provider.value,
                    "status": "error",
                    "error": str(e),
                }

        return {
            "primary_provider": self.primary_provider.value,
            "services": status,
            "fallback_order": [p.value for p in self.fallback_order],
        }


# Factory function to create email service manager
def create_email_service_manager(
    primary_provider: EmailProvider = EmailProvider.SENDGRID,
) -> EmailServiceManager:
    """Create and configure email service manager"""
    manager = EmailServiceManager(primary_provider)

    # Register services with the external service manager
    from .base_service import external_service_manager

    for service in manager.services.values():
        external_service_manager.register_service(service)

    return manager


# Global email service manager
email_service_manager = create_email_service_manager()

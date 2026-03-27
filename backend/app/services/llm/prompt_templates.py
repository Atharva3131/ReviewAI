"""
Prompt Template Management System

This module provides a comprehensive system for managing LLM prompt templates,
including versioning, A/B testing, and template rendering.
"""

import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union


class TemplateType(str, Enum):
    """Types of prompt templates"""

    REVIEW_RESPONSE = "review_response"
    RECOVERY_EMAIL = "recovery_email"
    APOLOGY_MESSAGE = "apology_message"
    DISCOUNT_OFFER = "discount_offer"
    FOLLOW_UP = "follow_up"
    SURVEY_REQUEST = "survey_request"
    ESCALATION_NOTICE = "escalation_notice"
    GENERIC_RESPONSE = "generic_response"


class TemplateStatus(str, Enum):
    """Template status"""

    DRAFT = "draft"
    ACTIVE = "active"
    TESTING = "testing"
    ARCHIVED = "archived"


@dataclass
class TemplateVariable:
    """Template variable definition"""

    name: str
    type: str  # "string", "number", "boolean", "object"
    required: bool = True
    default: Optional[Any] = None
    description: Optional[str] = None
    validation_pattern: Optional[str] = None


@dataclass
class PromptTemplate:
    """Prompt template definition"""

    id: str
    name: str
    type: TemplateType
    version: str
    status: TemplateStatus
    system_prompt: str
    user_prompt_template: str
    variables: List[TemplateVariable] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    created_by: Optional[str] = None
    tags: List[str] = field(default_factory=list)

    # A/B testing fields
    ab_test_group: Optional[str] = None
    ab_test_weight: float = 1.0

    # Performance metrics
    usage_count: int = 0
    success_rate: Optional[float] = None
    avg_response_time: Optional[float] = None
    customer_satisfaction: Optional[float] = None


class TemplateRenderer:
    """Template rendering engine"""

    def __init__(self):
        self.variable_pattern = re.compile(r"\{\{(\w+)\}\}")

    def render_template(
        self, template: PromptTemplate, variables: Dict[str, Any]
    ) -> Dict[str, str]:
        """
        Render a template with provided variables

        Args:
            template: Template to render
            variables: Variables to substitute

        Returns:
            Dictionary with rendered system_prompt and user_prompt

        Raises:
            ValueError: If required variables are missing or invalid
        """
        # Validate variables
        self._validate_variables(template, variables)

        # Render system prompt
        system_prompt = self._render_string(template.system_prompt, variables)

        # Render user prompt
        user_prompt = self._render_string(template.user_prompt_template, variables)

        return {"system_prompt": system_prompt, "user_prompt": user_prompt}

    def _validate_variables(self, template: PromptTemplate, variables: Dict[str, Any]):
        """Validate template variables"""
        # Check required variables
        for var in template.variables:
            if var.required and var.name not in variables:
                if var.default is not None:
                    variables[var.name] = var.default
                else:
                    raise ValueError(f"Required variable '{var.name}' is missing")

        # Validate variable types and patterns
        for var in template.variables:
            if var.name in variables:
                value = variables[var.name]

                # Type validation
                if var.type == "string" and not isinstance(value, str):
                    raise ValueError(f"Variable '{var.name}' must be a string")
                elif var.type == "number" and not isinstance(value, (int, float)):
                    raise ValueError(f"Variable '{var.name}' must be a number")
                elif var.type == "boolean" and not isinstance(value, bool):
                    raise ValueError(f"Variable '{var.name}' must be a boolean")

                # Pattern validation
                if var.validation_pattern and isinstance(value, str):
                    if not re.match(var.validation_pattern, value):
                        raise ValueError(
                            f"Variable '{var.name}' doesn't match required pattern"
                        )

    def _render_string(self, template_string: str, variables: Dict[str, Any]) -> str:
        """Render a template string with variables"""

        def replace_variable(match):
            var_name = match.group(1)
            if var_name in variables:
                return str(variables[var_name])
            else:
                return match.group(0)  # Keep original if variable not found

        return self.variable_pattern.sub(replace_variable, template_string)

    def get_template_variables(self, template_string: str) -> List[str]:
        """Extract variable names from a template string"""
        return self.variable_pattern.findall(template_string)


class TemplateManager:
    """Template management system"""

    def __init__(self):
        self.templates: Dict[str, PromptTemplate] = {}
        self.renderer = TemplateRenderer()
        self._load_default_templates()

    def _load_default_templates(self):
        """Load default prompt templates"""
        # Review response templates
        self.add_template(
            PromptTemplate(
                id="review_response_v1",
                name="Standard Review Response",
                type=TemplateType.REVIEW_RESPONSE,
                version="1.0",
                status=TemplateStatus.ACTIVE,
                system_prompt="""You are a professional customer service representative. Your task is to respond to customer reviews in a helpful, empathetic, and professional manner. Always thank the customer for their feedback and address their specific concerns when possible.""",
                user_prompt_template="""Please write a professional response to this customer review:

Review Rating: {{rating}}/5
Review Content: "{{review_content}}"
Customer Name: {{customer_name}}
Business Type: {{business_type}}

The response should be:
- Professional and empathetic
- Thank the customer for their feedback
- Address specific concerns mentioned in the review
- Encourage future business if appropriate
- Keep it concise (under 150 words)""",
                variables=[
                    TemplateVariable(
                        "rating", "number", True, description="Review rating 1-5"
                    ),
                    TemplateVariable(
                        "review_content", "string", True, description="The review text"
                    ),
                    TemplateVariable(
                        "customer_name",
                        "string",
                        False,
                        "Valued Customer",
                        "Customer's name",
                    ),
                    TemplateVariable(
                        "business_type", "string", False, "business", "Type of business"
                    ),
                ],
                tags=["review", "response", "customer_service"],
            )
        )

        # Recovery email templates
        self.add_template(
            PromptTemplate(
                id="recovery_email_v1",
                name="Customer Recovery Email",
                type=TemplateType.RECOVERY_EMAIL,
                version="1.0",
                status=TemplateStatus.ACTIVE,
                system_prompt="""You are writing a customer recovery email to address concerns and win back a potentially churning customer. The tone should be sincere, apologetic where appropriate, and focused on solutions. The goal is to rebuild trust and encourage continued business.""",
                user_prompt_template="""Write a customer recovery email with the following details:

Customer Name: {{customer_name}}
Issue Type: {{issue_type}}
Specific Concerns: {{concerns}}
Customer Value: {{customer_value}}
Proposed Solution: {{solution}}
Contact Information: {{contact_info}}

The email should:
- Have an appropriate subject line
- Acknowledge the customer's concerns specifically
- Take responsibility where appropriate
- Offer a clear solution or next steps
- Include a personal touch
- Provide easy ways to contact us
- Be professional but warm in tone
- Include a gesture of goodwill if appropriate""",
                variables=[
                    TemplateVariable(
                        "customer_name", "string", True, description="Customer's name"
                    ),
                    TemplateVariable(
                        "issue_type",
                        "string",
                        True,
                        description="Type of issue (service, product, billing, etc.)",
                    ),
                    TemplateVariable(
                        "concerns",
                        "string",
                        True,
                        description="Specific customer concerns",
                    ),
                    TemplateVariable(
                        "customer_value",
                        "string",
                        False,
                        "valued",
                        "Customer value tier",
                    ),
                    TemplateVariable(
                        "solution", "string", True, description="Proposed solution"
                    ),
                    TemplateVariable(
                        "contact_info",
                        "string",
                        True,
                        description="Contact information",
                    ),
                ],
                tags=["recovery", "email", "retention"],
            )
        )

        # Apology message template
        self.add_template(
            PromptTemplate(
                id="apology_message_v1",
                name="Sincere Apology Message",
                type=TemplateType.APOLOGY_MESSAGE,
                version="1.0",
                status=TemplateStatus.ACTIVE,
                system_prompt="""You are crafting a sincere apology message for a customer service failure. The message should take full responsibility, show genuine empathy, and focus on making things right. Avoid making excuses and focus on solutions and prevention.""",
                user_prompt_template="""Create a sincere apology message for:

Customer Name: {{customer_name}}
Issue Description: {{issue_description}}
Impact on Customer: {{impact}}
Our Responsibility: {{our_fault}}
Corrective Actions: {{corrective_actions}}
Prevention Measures: {{prevention}}

The message should:
- Take full responsibility without excuses
- Show genuine empathy for the customer's experience
- Acknowledge the specific impact on the customer
- Outline concrete steps we're taking to fix the issue
- Explain how we'll prevent similar issues
- Offer appropriate compensation if applicable
- Maintain a sincere and professional tone""",
                variables=[
                    TemplateVariable(
                        "customer_name", "string", True, description="Customer's name"
                    ),
                    TemplateVariable(
                        "issue_description",
                        "string",
                        True,
                        description="What went wrong",
                    ),
                    TemplateVariable(
                        "impact",
                        "string",
                        True,
                        description="How it affected the customer",
                    ),
                    TemplateVariable(
                        "our_fault",
                        "string",
                        True,
                        description="How we were responsible",
                    ),
                    TemplateVariable(
                        "corrective_actions",
                        "string",
                        True,
                        description="Steps to fix the issue",
                    ),
                    TemplateVariable(
                        "prevention",
                        "string",
                        False,
                        "improved processes",
                        "Prevention measures",
                    ),
                ],
                tags=["apology", "service_recovery", "responsibility"],
            )
        )

        # Discount offer template
        self.add_template(
            PromptTemplate(
                id="discount_offer_v1",
                name="Discount Offer Message",
                type=TemplateType.DISCOUNT_OFFER,
                version="1.0",
                status=TemplateStatus.ACTIVE,
                system_prompt="""You are creating a discount offer message for customer retention or recovery. The message should be enticing but not desperate, clearly explain the offer terms, and create urgency while maintaining professionalism.""",
                user_prompt_template="""Create a discount offer message with these details:

Customer Name: {{customer_name}}
Discount Percentage: {{discount_percentage}}%
Discount Code: {{discount_code}}
Valid Until: {{expiry_date}}
Minimum Purchase: {{min_purchase}}
Reason for Offer: {{offer_reason}}
Product/Service Focus: {{focus_area}}

The message should:
- Present the offer as exclusive and valuable
- Clearly state the discount percentage and code
- Explain any terms and conditions
- Create appropriate urgency
- Thank the customer for their business
- Make it easy to redeem the offer
- Include a clear call to action""",
                variables=[
                    TemplateVariable(
                        "customer_name", "string", True, description="Customer's name"
                    ),
                    TemplateVariable(
                        "discount_percentage",
                        "number",
                        True,
                        description="Discount percentage",
                    ),
                    TemplateVariable(
                        "discount_code", "string", True, description="Discount code"
                    ),
                    TemplateVariable(
                        "expiry_date", "string", True, description="Offer expiry date"
                    ),
                    TemplateVariable(
                        "min_purchase",
                        "string",
                        False,
                        "No minimum",
                        "Minimum purchase requirement",
                    ),
                    TemplateVariable(
                        "offer_reason",
                        "string",
                        False,
                        "loyalty",
                        "Reason for the offer",
                    ),
                    TemplateVariable(
                        "focus_area",
                        "string",
                        False,
                        "any purchase",
                        "Product/service focus",
                    ),
                ],
                tags=["discount", "offer", "retention", "promotion"],
            )
        )

    def add_template(self, template: PromptTemplate):
        """Add a new template"""
        self.templates[template.id] = template

    def get_template(self, template_id: str) -> Optional[PromptTemplate]:
        """Get a template by ID"""
        return self.templates.get(template_id)

    def get_templates_by_type(
        self, template_type: TemplateType
    ) -> List[PromptTemplate]:
        """Get all templates of a specific type"""
        return [
            template
            for template in self.templates.values()
            if template.type == template_type
        ]

    def get_active_templates(self) -> List[PromptTemplate]:
        """Get all active templates"""
        return [
            template
            for template in self.templates.values()
            if template.status == TemplateStatus.ACTIVE
        ]

    def render_template(
        self, template_id: str, variables: Dict[str, Any]
    ) -> Dict[str, str]:
        """Render a template with variables"""
        template = self.get_template(template_id)
        if not template:
            raise ValueError(f"Template '{template_id}' not found")

        return self.renderer.render_template(template, variables)

    def create_ab_test(
        self,
        template_type: TemplateType,
        template_ids: List[str],
        weights: Optional[List[float]] = None,
    ) -> str:
        """
        Create an A/B test for templates

        Args:
            template_type: Type of templates to test
            template_ids: List of template IDs to include in test
            weights: Optional weights for each template (default: equal)

        Returns:
            A/B test group ID
        """
        import uuid

        test_id = f"ab_test_{uuid.uuid4().hex[:8]}"

        if weights is None:
            weights = [1.0] * len(template_ids)

        if len(weights) != len(template_ids):
            raise ValueError("Number of weights must match number of templates")

        # Update templates with A/B test info
        for template_id, weight in zip(template_ids, weights):
            template = self.get_template(template_id)
            if template:
                template.ab_test_group = test_id
                template.ab_test_weight = weight
                template.status = TemplateStatus.TESTING

        return test_id

    def select_template_for_ab_test(
        self, template_type: TemplateType, ab_test_group: str
    ) -> Optional[PromptTemplate]:
        """
        Select a template for A/B testing based on weights

        Args:
            template_type: Type of template needed
            ab_test_group: A/B test group ID

        Returns:
            Selected template or None
        """
        import random

        # Get templates in the A/B test group
        test_templates = [
            template
            for template in self.templates.values()
            if (
                template.type == template_type
                and template.ab_test_group == ab_test_group
                and template.status == TemplateStatus.TESTING
            )
        ]

        if not test_templates:
            return None

        # Weighted random selection
        weights = [template.ab_test_weight for template in test_templates]
        selected = random.choices(test_templates, weights=weights, k=1)[0]

        # Update usage count
        selected.usage_count += 1

        return selected

    def update_template_metrics(
        self,
        template_id: str,
        success: bool,
        response_time: float,
        customer_satisfaction: Optional[float] = None,
    ):
        """Update template performance metrics"""
        template = self.get_template(template_id)
        if not template:
            return

        # Update success rate
        if template.success_rate is None:
            template.success_rate = 1.0 if success else 0.0
        else:
            # Running average
            total_uses = template.usage_count
            template.success_rate = (
                template.success_rate * (total_uses - 1) + (1.0 if success else 0.0)
            ) / total_uses

        # Update average response time
        if template.avg_response_time is None:
            template.avg_response_time = response_time
        else:
            total_uses = template.usage_count
            template.avg_response_time = (
                template.avg_response_time * (total_uses - 1) + response_time
            ) / total_uses

        # Update customer satisfaction if provided
        if customer_satisfaction is not None:
            if template.customer_satisfaction is None:
                template.customer_satisfaction = customer_satisfaction
            else:
                total_uses = template.usage_count
                template.customer_satisfaction = (
                    template.customer_satisfaction * (total_uses - 1)
                    + customer_satisfaction
                ) / total_uses

        template.updated_at = datetime.now(timezone.utc)

    def get_template_analytics(self, template_id: str) -> Dict[str, Any]:
        """Get analytics for a specific template"""
        template = self.get_template(template_id)
        if not template:
            return {}

        return {
            "template_id": template.id,
            "name": template.name,
            "type": template.type.value,
            "version": template.version,
            "status": template.status.value,
            "usage_count": template.usage_count,
            "success_rate": template.success_rate,
            "avg_response_time": template.avg_response_time,
            "customer_satisfaction": template.customer_satisfaction,
            "ab_test_group": template.ab_test_group,
            "created_at": template.created_at.isoformat(),
            "updated_at": template.updated_at.isoformat(),
        }

    def export_templates(
        self, template_ids: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Export templates to JSON format"""
        if template_ids is None:
            templates_to_export = self.templates
        else:
            templates_to_export = {
                tid: template
                for tid, template in self.templates.items()
                if tid in template_ids
            }

        export_data = {
            "export_timestamp": datetime.now(timezone.utc).isoformat(),
            "templates": {},
        }

        for template_id, template in templates_to_export.items():
            export_data["templates"][template_id] = {
                "id": template.id,
                "name": template.name,
                "type": template.type.value,
                "version": template.version,
                "status": template.status.value,
                "system_prompt": template.system_prompt,
                "user_prompt_template": template.user_prompt_template,
                "variables": [
                    {
                        "name": var.name,
                        "type": var.type,
                        "required": var.required,
                        "default": var.default,
                        "description": var.description,
                        "validation_pattern": var.validation_pattern,
                    }
                    for var in template.variables
                ],
                "metadata": template.metadata,
                "tags": template.tags,
                "created_at": template.created_at.isoformat(),
                "updated_at": template.updated_at.isoformat(),
            }

        return export_data


# Global template manager instance
_template_manager: Optional[TemplateManager] = None


def get_template_manager() -> TemplateManager:
    """Get the global template manager instance"""
    global _template_manager
    if _template_manager is None:
        _template_manager = TemplateManager()
    return _template_manager

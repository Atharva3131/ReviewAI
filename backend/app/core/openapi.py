"""
OpenAPI documentation customization and utilities
"""

import json
from typing import Any, Dict, Optional

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi


def custom_openapi(app: FastAPI) -> Dict[str, Any]:
    """Generate custom OpenAPI schema with enhanced documentation"""

    if app.openapi_schema:
        return app.openapi_schema

    # Generate base OpenAPI schema
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
        servers=app.servers,
    )

    # Ensure components exists
    if "components" not in openapi_schema:
        openapi_schema["components"] = {}

    # Add custom security schemes
    if "securitySchemes" not in openapi_schema["components"]:
        openapi_schema["components"]["securitySchemes"] = {}

    openapi_schema["components"]["securitySchemes"]["BearerAuth"] = {
        "type": "http",
        "scheme": "bearer",
        "bearerFormat": "JWT",
        "description": "JWT Bearer token authentication. Include the token in the Authorization header as 'Bearer <token>'",
    }

    # Cache the schema
    app.openapi_schema = openapi_schema
    return app.openapi_schema


def add_endpoint_examples(app: FastAPI):
    """Add comprehensive examples to API endpoints"""

    # This would be called after all routes are added
    # to inject examples into the OpenAPI schema

    examples = {
        "/api/v1/reviews/ingest": {
            "post": {
                "requestBody": {
                    "content": {
                        "application/json": {
                            "examples": {
                                "google_review": {
                                    "summary": "Google Review Example",
                                    "description": "Example of ingesting a Google review",
                                    "value": {
                                        "platform": "google",
                                        "external_id": "review_123456",
                                        "customer_name": "John Doe",
                                        "rating": 2,
                                        "content": "Service was terrible, waited 2 hours for my order. Very disappointed.",
                                        "created_at": "2024-01-15T10:30:00Z",
                                    },
                                },
                                "positive_review": {
                                    "summary": "Positive Review Example",
                                    "description": "Example of a positive review",
                                    "value": {
                                        "platform": "yelp",
                                        "external_id": "yelp_789",
                                        "customer_name": "Jane Smith",
                                        "rating": 5,
                                        "content": "Excellent service! The staff was friendly and the food was amazing. Highly recommend!",
                                        "created_at": "2024-01-15T14:20:00Z",
                                    },
                                },
                            }
                        }
                    }
                }
            }
        },
        "/api/v1/customers/recover": {
            "post": {
                "requestBody": {
                    "content": {
                        "application/json": {
                            "examples": {
                                "high_risk_customer": {
                                    "summary": "High Risk Customer",
                                    "description": "Recovery for a high-risk customer",
                                    "value": {
                                        "customer_id": "cust_123",
                                        "trigger_type": "support_ticket",
                                        "context": {
                                            "ticket_id": "ticket_456",
                                            "issue_summary": "Billing problem, customer frustrated with multiple failed charges",
                                        },
                                    },
                                }
                            }
                        }
                    }
                }
            }
        },
    }

    # This would be implemented to inject examples into the schema
    # For now, it's a placeholder for future enhancement
    pass


def generate_api_documentation():
    """Generate additional API documentation files"""

    # Generate markdown documentation
    markdown_docs = """
# Revive AI API Documentation

## Quick Start Guide

### 1. Authentication
```bash
# Register a new account
curl -X POST "http://localhost:8000/api/v1/auth/register" \\
  -H "Content-Type: application/json" \\
  -d '{
    "email": "user@example.com",
    "password": "securepassword",
    "organization_name": "My Company"
  }'

# Login to get access token
curl -X POST "http://localhost:8000/api/v1/auth/login" \\
  -H "Content-Type: application/json" \\
  -d '{
    "email": "user@example.com",
    "password": "securepassword"
  }'
```

### 2. Ingest a Review
```bash
curl -X POST "http://localhost:8000/api/v1/reviews/ingest" \\
  -H "Authorization: Bearer YOUR_TOKEN" \\
  -H "Content-Type: application/json" \\
  -d '{
    "platform": "google",
    "external_id": "review_123",
    "customer_name": "John Doe",
    "rating": 2,
    "content": "Service was terrible, waited 2 hours.",
    "created_at": "2024-01-15T10:30:00Z"
  }'
```

### 3. Analyze Customer Risk
```bash
curl -X POST "http://localhost:8000/api/v1/customers/recover" \\
  -H "Authorization: Bearer YOUR_TOKEN" \\
  -H "Content-Type: application/json" \\
  -d '{
    "customer_id": "cust_123",
    "trigger_type": "support_ticket",
    "context": {
      "issue_summary": "Billing problem"
    }
  }'
```

## Rate Limiting

The API implements sophisticated rate limiting with different tiers:

| User Tier | Requests/Hour | Endpoint Limits |
|-----------|---------------|-----------------|
| Anonymous | 100 | Various |
| Authenticated | 1,000 | Various |
| Premium | 5,000 | Various |
| Admin | 10,000 | Various |

Rate limit information is included in response headers:
- `X-RateLimit-Limit`: Your rate limit
- `X-RateLimit-Remaining`: Remaining requests
- `X-RateLimit-Reset`: When the limit resets

## Error Handling

All errors follow a consistent format:

```json
{
  "error": {
    "type": "validation_error",
    "message": "Request validation failed",
    "status_code": 422,
    "request_id": "123e4567-e89b-12d3-a456-426614174000",
    "timestamp": 1640995200.0,
    "path": "/api/v1/reviews",
    "details": [...]
  }
}
```

## Monitoring

The API provides comprehensive monitoring endpoints:

- `GET /metrics` - Overall system metrics
- `GET /metrics/endpoint/{path}` - Endpoint-specific metrics
- `GET /health` - Health check

## Versioning

The API supports multiple versioning strategies:

1. **URL Path** (recommended): `/api/v1/endpoint`
2. **Accept Header**: `Accept: application/vnd.revive-ai.v1+json`
3. **Query Parameter**: `/api/endpoint?version=v1`

Current stable version: **v1**
    """

    return markdown_docs


class OpenAPICustomizer:
    """Utility class for customizing OpenAPI documentation"""

    @staticmethod
    def setup_custom_openapi(app: FastAPI):
        """Set up custom OpenAPI schema generation"""
        app.openapi = lambda: custom_openapi(app)

    @staticmethod
    def add_security_schemes(openapi_schema: dict):
        """Add security schemes to OpenAPI schema"""
        if "components" not in openapi_schema:
            openapi_schema["components"] = {}

        openapi_schema["components"]["securitySchemes"] = {
            "BearerAuth": {"type": "http", "scheme": "bearer", "bearerFormat": "JWT"}
        }

    @staticmethod
    def add_common_responses(openapi_schema: dict):
        """Add common response schemas"""
        # Implementation would add common response schemas
        pass

    @staticmethod
    def enhance_endpoint_documentation(openapi_schema: dict):
        """Enhance individual endpoint documentation"""
        # Implementation would enhance endpoint docs
        pass

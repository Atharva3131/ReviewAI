# Revive AI API Documentation

Welcome to the Revive AI API documentation. This directory contains comprehensive documentation for integrating with the Revive AI platform.

## Documentation Files

### 📘 [API_DOCUMENTATION.md](./API_DOCUMENTATION.md)
Complete API reference documentation including:
- Getting started guide
- Authentication flow
- All API endpoints with request/response examples
- Rate limiting details
- Error handling
- Versioning strategies
- Best practices
- Code examples in Python, JavaScript/TypeScript

### 📝 [API_DOCUMENTATION_CURL.md](./API_DOCUMENTATION_CURL.md)
cURL command examples for:
- Quick testing
- Shell script integration
- Complete workflow examples

### 📦 [Revive_AI_Postman_Collection.json](./Revive_AI_Postman_Collection.json)
Postman collection for easy API testing:
- Pre-configured requests for all endpoints
- Environment variables setup
- Automatic token management
- Example request bodies

### 🎭 [DEMO_SCENARIOS.md](./DEMO_SCENARIOS.md)
Comprehensive demo data and testing scenarios:
- Demo organizations and login credentials
- Customer risk profiles
- Review scenarios (positive, moderate, negative)
- Support ticket scenarios
- Agent decision examples
- Recovery action workflows
- API testing scenarios
- Data validation guidelines

## Quick Start

### 1. Demo Data Setup

For testing and demonstrations, seed the database with realistic demo data:

```bash
cd backend
python scripts/seed_demo_data.py --environment development
```

**Demo Login Credentials:**
- Bella's Restaurant: `admin@bellas-restaurant.com` / `demo123`
- TechSupport Pro: `admin@techsupportpro.com` / `demo123`
- QuickShip Logistics: `admin@quickship.com` / `demo123`

See [DEMO_SCENARIOS.md](./DEMO_SCENARIOS.md) for complete demo scenarios and testing workflows.

### 2. Interactive API Documentation

When running the API in development mode, access interactive documentation at:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI Schema**: http://localhost:8000/openapi.json

### 3. Using Postman

1. Import `Revive_AI_Postman_Collection.json` into Postman
2. Set the `base_url` variable to your API endpoint
3. Run the "Login" request to automatically set the access token
4. Start making requests!

### 4. Using cURL

See [API_DOCUMENTATION_CURL.md](./API_DOCUMENTATION_CURL.md) for ready-to-use cURL commands.

### 5. Using Client Libraries

See code examples in [API_DOCUMENTATION.md](./API_DOCUMENTATION.md#code-examples) for:
- Python client implementation
- JavaScript/TypeScript client implementation

## API Overview

### Base URLs

- **Development**: `http://localhost:8000`
- **Staging**: `https://staging-api.revive-ai.com`
- **Production**: `https://api.revive-ai.com`

### Authentication

All API requests (except public endpoints) require JWT Bearer token authentication:

```bash
Authorization: Bearer <your_access_token>
```

Get your access token by:
1. Registering: `POST /api/v1/auth/register`
2. Logging in: `POST /api/v1/auth/login`

### Core Endpoints

- **Reviews**: `/api/v1/reviews/*` - Review intelligence and management
- **Customers**: `/api/v1/customers/*` - Customer recovery and risk assessment
- **Agents**: `/api/v1/agents/*` - Agent orchestration and decisions
- **Dashboard**: `/api/v1/dashboard/*` - Metrics and analytics
- **Users**: `/api/v1/users/*` - User management
- **Webhooks**: `/api/v1/webhooks/*` - Webhook management

## Rate Limits

| User Tier | Requests/Hour |
|-----------|---------------|
| Anonymous | 100 |
| Authenticated | 1,000 |
| Premium | 5,000 |
| Admin | 10,000 |

Rate limit information is included in response headers:
- `X-RateLimit-Limit`
- `X-RateLimit-Remaining`
- `X-RateLimit-Reset`

## Error Handling

All errors follow a consistent format:

```json
{
  "error": {
    "type": "error_type",
    "message": "Human-readable message",
    "status_code": 400,
    "request_id": "unique-id",
    "timestamp": 1640995200.0,
    "path": "/api/v1/endpoint"
  }
}
```

## Support

- **Documentation**: https://docs.revive-ai.com
- **Support Email**: support@revive-ai.com
- **Status Page**: https://status.revive-ai.com
- **GitHub Issues**: https://github.com/revive-ai/api/issues

## Version

Current API Version: **v1.0.0**

Last Updated: January 2024

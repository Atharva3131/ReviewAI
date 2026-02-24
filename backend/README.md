# Revive AI Backend

FastAPI-based backend for the Revive AI platform providing review intelligence, customer recovery, and agent orchestration capabilities.

## 📚 Documentation

### API Documentation

Complete API documentation is available in the `docs/` directory:

- **[API Documentation](./docs/API_DOCUMENTATION.md)** - Complete API reference with examples
- **[Quick Reference](./docs/QUICK_REFERENCE.md)** - Quick lookup for common endpoints
- **[cURL Examples](./docs/API_DOCUMENTATION_CURL.md)** - Ready-to-use cURL commands
- **[Postman Collection](./docs/Revive_AI_Postman_Collection.json)** - Import into Postman for testing
- **[OpenAPI Spec](./docs/openapi_spec.yaml)** - OpenAPI 3.0 specification

### Interactive Documentation

When running in development mode, access interactive API documentation:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL 15+ with pgvector extension
- Redis 7+

### Setup

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your configuration

# Run database migrations
alembic upgrade head

# Start the server
uvicorn main:app --reload
```

### Docker Setup

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f backend

# Run migrations
docker-compose exec backend alembic upgrade head
```

## 🏗️ Architecture

```
backend/
├── app/
│   ├── api/              # API endpoints
│   │   └── v1/
│   │       ├── endpoints/  # Route handlers
│   │       └── api.py      # API router
│   ├── core/             # Core configuration
│   │   ├── config.py       # Settings
│   │   ├── database.py     # Database setup
│   │   ├── security.py     # Auth & security
│   │   └── middleware.py   # Custom middleware
│   ├── models/           # SQLAlchemy models
│   ├── schemas/          # Pydantic schemas
│   └── services/         # Business logic
│       ├── agent_engine.py
│       ├── llm/            # LLM integration
│       └── external/       # External services
├── alembic/              # Database migrations
├── docs/                 # API documentation
├── tests/                # Test suite
└── main.py              # Application entry point
```

## 🔑 Key Features

### Review Intelligence Engine
- Automated sentiment analysis
- Urgency classification
- Issue categorization
- Response generation

### Customer Recovery Agent
- Churn risk prediction
- Bad review likelihood assessment
- Automated recovery action generation
- Multi-channel communication

### Agent Orchestration
- Rule-based decision making
- LLM-enhanced responses
- Confidence scoring
- Audit trail logging

### Multi-tenant Architecture
- Organization-based isolation
- Role-based access control
- Data privacy compliance
- GDPR support

## 🧪 Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test categories
pytest tests/unit/
pytest tests/integration/
pytest tests/property_tests/

# Run property-based tests
pytest tests/property_tests/ -v
```

## 📊 API Endpoints

### Authentication
- `POST /api/v1/auth/register` - Register new account
- `POST /api/v1/auth/login` - Login and get token
- `POST /api/v1/auth/refresh` - Refresh access token

### Reviews
- `POST /api/v1/reviews/ingest` - Ingest new review
- `GET /api/v1/reviews` - List reviews
- `GET /api/v1/reviews/{id}` - Get review details
- `POST /api/v1/reviews/analyze` - Analyze review
- `POST /api/v1/reviews/respond` - Generate response

### Customers
- `POST /api/v1/customers/recover` - Assess risk and recover
- `GET /api/v1/customers` - List customers
- `GET /api/v1/customers/{id}` - Get customer details

### Dashboard
- `GET /api/v1/dashboard/metrics` - Get KPIs and metrics

### Agents
- `POST /api/v1/agents/decide-action` - Make agent decision
- `GET /api/v1/agents/decisions` - List decisions

See [API Documentation](./docs/API_DOCUMENTATION.md) for complete details.

## 🔧 Configuration

### Environment Variables

```bash
# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/revive_ai

# Redis
REDIS_URL=redis://localhost:6379

# Security
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60

# LLM Providers
DEFAULT_LLM_PROVIDER=openai
OPENAI_API_KEY=your-openai-key
GEMINI_API_KEY=your-gemini-key

# External Services
SENDGRID_API_KEY=your-sendgrid-key
WHATSAPP_API_KEY=your-whatsapp-key

# Application
DEBUG=true
ALLOWED_HOSTS=["localhost", "127.0.0.1"]
```

## 🚀 Deployment

### Production Checklist

- [ ] Set `DEBUG=false`
- [ ] Configure production database (AWS RDS)
- [ ] Set up Redis cluster (AWS ElastiCache)
- [ ] Configure proper `SECRET_KEY`
- [ ] Set up SSL/TLS certificates
- [ ] Configure CORS for production domains
- [ ] Set up monitoring and logging
- [ ] Configure backup strategy
- [ ] Set up CI/CD pipeline

### Docker Production

```bash
# Build production image
docker build -t revive-ai-backend:latest .

# Run with production config
docker run -d \
  --name revive-ai-backend \
  -p 8000:8000 \
  --env-file .env.production \
  revive-ai-backend:latest
```

## 📈 Monitoring

### Health Check

```bash
curl http://localhost:8000/health
```

### Metrics

```bash
# System metrics
curl -H "Authorization: Bearer <token>" \
  http://localhost:8000/metrics

# Endpoint metrics
curl -H "Authorization: Bearer <token>" \
  http://localhost:8000/metrics/endpoint/api/v1/reviews/ingest
```

## 🛠️ Development

### Code Style

```bash
# Format code
black .
isort .

# Lint
flake8 .

# Type checking
mypy app/
```

### Database Migrations

```bash
# Create migration
alembic revision --autogenerate -m "Description"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1

# View history
alembic history
```

### Adding New Endpoints

1. Create endpoint in `app/api/v1/endpoints/`
2. Add route to `app/api/v1/api.py`
3. Create Pydantic schemas in `app/schemas/`
4. Implement business logic in `app/services/`
5. Add tests in `tests/`
6. Update API documentation

## 🤝 Contributing

1. Follow PEP 8 style guide
2. Add type hints to all functions
3. Write docstrings for public APIs
4. Add unit tests for new features
5. Update API documentation
6. Run tests before committing

## 📄 License

See [LICENSE](../LICENSE) file for details.

## 🆘 Support

- **Documentation**: [docs/](./docs/)
- **API Reference**: [API_DOCUMENTATION.md](./docs/API_DOCUMENTATION.md)
- **Issues**: GitHub Issues
- **Email**: support@revive-ai.com

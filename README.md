# Revive AI - AI-Powered Customer Recovery Platform

Revive AI is a comprehensive SaaS platform that helps businesses monitor public reviews, analyze customer conversations, predict churn risks, and take automated recovery actions to improve ratings, retention, and revenue.

## 🚀 Quick Start

**New to the project?** Start here: [SETUP_GUIDE.md](SETUP_GUIDE.md)

**Need a quick reference?** Check: [QUICK_REFERENCE.md](QUICK_REFERENCE.md)

## ✨ Features

- **Review Intelligence Engine**: Automated sentiment analysis, urgency classification, and issue categorization
- **Customer Recovery Agent**: Predictive churn risk assessment and automated recovery action generation
- **Agent Orchestration**: Intelligent decision-making for routing customer issues
- **LLM Integration**: Multi-provider AI integration (Mistral AI, OpenAI, Gemini) for response generation
- **Background Processing**: Scalable task queue system for asynchronous operations
- **Security**: Comprehensive security features including CSRF protection, rate limiting, and SQL injection prevention

## 🛠️ Technology Stack

### Backend
- **Framework**: FastAPI (Python 3.13)
- **Database**: PostgreSQL (via Supabase)
- **Cache**: Redis (via Upstash)
- **AI/LLM**: Mistral AI (primary), OpenAI, Google Gemini
- **Task Queue**: Celery
- **ORM**: SQLAlchemy
- **Migrations**: Alembic

### Frontend
- **Framework**: Next.js 14 (React)
- **Language**: TypeScript
- **Styling**: Tailwind CSS
- **State Management**: React Context + Hooks
- **API Client**: Axios

## 📋 Prerequisites

- Python 3.13.5 or higher
- Node.js 24.12.0 or higher
- PostgreSQL database (Supabase free tier recommended)
- Redis instance (Upstash free tier recommended)
- Mistral AI API key

## 🔧 Installation

### 1. Clone the Repository
```bash
git clone <repository-url>
cd AI_REVIEW_AGENT
```

### 2. Backend Setup
```powershell
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Generate SECRET_KEY
python generate_secret_key.py

# Configure environment variables
# Edit backend/.env with your credentials

# Run database migrations
alembic upgrade head

# Start the backend server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 3. Frontend Setup
```powershell
cd frontend

# Install dependencies
npm install

# Start the development server
npm run dev
```

## 🔑 Configuration

### Required Environment Variables

Create a `backend/.env` file with the following:

```env
# Database (Supabase)
DATABASE_URL=postgresql://postgres:password@db.xxx.supabase.co:5432/postgres

# Redis (Upstash)
REDIS_URL=redis://default:password@xxx.upstash.io:6379

# Security
SECRET_KEY=your-generated-secret-key-here

# Mistral AI
MISTRAL_API_KEY=your-mistral-api-key-here

# Background Tasks
CELERY_BROKER_URL=redis://default:password@xxx.upstash.io:6379
CELERY_RESULT_BACKEND=redis://default:password@xxx.upstash.io:6379

# Development
DEBUG=true
LOG_LEVEL=INFO
ENVIRONMENT=development
```

### Getting API Keys

1. **Mistral AI**: https://console.mistral.ai/
2. **Supabase**: https://supabase.com
3. **Upstash**: https://upstash.com

See [SETUP_GUIDE.md](SETUP_GUIDE.md) for detailed instructions.

## 🌐 Access Points

Once running:

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/api/v1/health

## 📚 Documentation

- [Setup Guide](SETUP_GUIDE.md) - Complete setup instructions
- [Quick Reference](QUICK_REFERENCE.md) - Command reference and troubleshooting
- [API Documentation](http://localhost:8000/docs) - Interactive API docs (when running)
- [Security Audit Report](SECURITY_AUDIT_REPORT.md) - Security assessment
- [Project Summary](PROJECT_SUMMARY.md) - Complete project overview

## 🧪 Testing

### Backend Tests
```powershell
cd backend
venv\Scripts\activate
pytest

# With coverage
pytest --cov=app tests/

# Security tests
pytest tests/security/
```

### Frontend Tests
```powershell
cd frontend
npm test

# With coverage
npm test -- --coverage
```

## 🏗️ Project Structure

```
AI_REVIEW_AGENT/
├── backend/              # FastAPI backend
│   ├── app/
│   │   ├── api/         # API endpoints
│   │   ├── core/        # Core configuration
│   │   ├── models/      # Database models
│   │   ├── schemas/     # Pydantic schemas
│   │   └── services/    # Business logic
│   ├── alembic/         # Database migrations
│   ├── tests/           # Backend tests
│   └── requirements.txt # Python dependencies
├── frontend/            # Next.js frontend
│   ├── src/
│   │   ├── app/        # Next.js app router
│   │   ├── components/ # React components
│   │   └── lib/        # Utilities
│   └── package.json    # Node dependencies
├── docs/               # Documentation
└── .kiro/              # Kiro specs
```

## 🔒 Security

Revive AI implements comprehensive security measures:

- JWT-based authentication
- CSRF protection
- SQL injection prevention
- XSS protection
- Rate limiting
- Input validation and sanitization
- Secure password hashing (bcrypt)
- Security headers (HSTS, CSP, etc.)

See [SECURITY_AUDIT_REPORT.md](SECURITY_AUDIT_REPORT.md) for details.

## 🚀 Deployment

### Backend Deployment
- Recommended: AWS ECS with Fargate
- Database: Supabase (managed PostgreSQL)
- Cache: Upstash (managed Redis)
- See `aws/` directory for Terraform configurations

### Frontend Deployment
- Recommended: Vercel or AWS CloudFront + S3
- Environment variables must be configured in deployment platform

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests
5. Submit a pull request

## 📝 License

Proprietary License - All rights reserved

## 🆘 Support

For issues or questions:
1. Check the [SETUP_GUIDE.md](SETUP_GUIDE.md)
2. Review [QUICK_REFERENCE.md](QUICK_REFERENCE.md)
3. Check existing documentation in `/docs`
4. Contact support team

## 🎯 Development Status

- ✅ Backend API - Complete
- ✅ Frontend UI - Complete
- ✅ Authentication - Complete
- ✅ Review Intelligence - Complete
- ✅ Customer Recovery - Complete
- ✅ LLM Integration - Complete (Mistral AI)
- ✅ Security Audit - Complete
- 🚧 Production Deployment - In Progress

## 📊 System Requirements

### Minimum
- 4GB RAM
- 2 CPU cores
- 10GB disk space

### Recommended
- 8GB RAM
- 4 CPU cores
- 20GB disk space
- SSD storage

## 🌟 Key Highlights

- **AI-Powered**: Uses Mistral AI for intelligent response generation
- **Scalable**: Built with async/await and background task processing
- **Secure**: A- security rating with comprehensive protection
- **Modern Stack**: Latest versions of FastAPI, Next.js, and Python 3.13
- **Cloud-Ready**: Designed for cloud deployment with Terraform configs
- **Well-Tested**: Comprehensive test suite with 50+ security tests

---

**Ready to get started?** Follow the [SETUP_GUIDE.md](SETUP_GUIDE.md) to set up your development environment!

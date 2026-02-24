#!/bin/bash

# Revive AI Environment Setup Script

set -e

echo "🐍 Setting up Python virtual environment..."

# Create virtual environment for backend
if [ ! -d "backend/venv" ]; then
    echo "📦 Creating Python virtual environment..."
    cd backend
    python -m venv venv
    cd ..
    echo "✅ Created Python virtual environment in backend/venv"
    echo "💡 Activate with: cd backend && source venv/bin/activate (Linux/Mac) or venv\\Scripts\\activate (Windows)"
fi

echo "🚀 Setting up Revive AI development environment..."

# Check if .env files exist, if not copy from examples
if [ ! -f .env ]; then
    echo "📝 Creating root .env file..."
    cp .env.example .env
    echo "✅ Created .env file. Please update with your actual values."
fi

if [ ! -f backend/.env ]; then
    echo "📝 Creating backend .env file..."
    cp backend/.env.example backend/.env
    echo "✅ Created backend/.env file. Please update with your actual values."
fi

if [ ! -f frontend/.env.local ]; then
    echo "📝 Creating frontend .env.local file..."
    cp frontend/.env.example frontend/.env.local
    echo "✅ Created frontend/.env.local file. Please update with your actual values."
fi

# Generate a random secret key
SECRET_KEY=$(openssl rand -hex 32)
echo "🔐 Generated SECRET_KEY: $SECRET_KEY"

# Update .env files with generated secret key
if command -v sed >/dev/null 2>&1; then
    sed -i.bak "s/your-super-secret-key-change-in-production-min-32-chars/$SECRET_KEY/g" .env
    sed -i.bak "s/your-super-secret-key-change-in-production-min-32-chars/$SECRET_KEY/g" backend/.env
    rm -f .env.bak backend/.env.bak
    echo "✅ Updated SECRET_KEY in environment files"
fi

echo ""
echo "🎯 Next steps:"
echo "1. Update .env files with your actual API keys and configuration"
echo "2. For local development:"
echo "   - Backend: cd backend && source venv/bin/activate && pip install -r requirements.txt"
echo "   - Frontend: cd frontend && npm install"
echo "3. For Docker development: docker-compose up -d"
echo "4. Run 'docker-compose exec backend alembic upgrade head' to run database migrations"
echo "5. Visit http://localhost:3000 for the frontend"
echo "6. Visit http://localhost:8000/docs for the API documentation"
echo ""
echo "📚 Important files to configure:"
echo "   - .env (root configuration)"
echo "   - backend/.env (backend-specific settings)"
echo "   - frontend/.env.local (frontend-specific settings)"
echo ""
echo "🔑 Required API keys:"
echo "   - OPENAI_API_KEY (for LLM functionality)"
echo "   - SENDGRID_API_KEY (for email notifications)"
echo ""
echo "✨ Setup complete! Happy coding!"
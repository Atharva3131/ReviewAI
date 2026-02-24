#!/bin/bash

# Revive AI Local Development Setup Script
# This script sets up a complete local development environment with venv

set -e

echo "🚀 Setting up Revive AI for local development..."

# Check Python version
python_version=$(python3 --version 2>&1 | awk '{print $2}' | cut -d. -f1,2)
required_version="3.11"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then
    echo "❌ Python 3.11+ is required. Found: $python_version"
    exit 1
fi

echo "✅ Python version check passed: $python_version"

# Check Node.js version
if ! command -v node >/dev/null 2>&1; then
    echo "❌ Node.js is required but not installed"
    exit 1
fi

node_version=$(node --version | cut -d. -f1 | sed 's/v//')
if [ "$node_version" -lt 18 ]; then
    echo "❌ Node.js 18+ is required. Found: $(node --version)"
    exit 1
fi

echo "✅ Node.js version check passed: $(node --version)"

# Setup environment files
echo "📝 Setting up environment files..."
if [ ! -f .env ]; then
    cp .env.example .env
    echo "✅ Created root .env file"
fi

if [ ! -f backend/.env ]; then
    cp backend/.env.example backend/.env
    echo "✅ Created backend .env file"
fi

if [ ! -f frontend/.env.local ]; then
    cp frontend/.env.example frontend/.env.local
    echo "✅ Created frontend .env.local file"
fi

# Generate secret key
SECRET_KEY=$(openssl rand -hex 32)
if command -v sed >/dev/null 2>&1; then
    sed -i.bak "s/your-super-secret-key-change-in-production-min-32-chars/$SECRET_KEY/g" .env
    sed -i.bak "s/your-super-secret-key-change-in-production-min-32-chars/$SECRET_KEY/g" backend/.env
    rm -f .env.bak backend/.env.bak
    echo "🔐 Generated and set SECRET_KEY"
fi

# Setup Python virtual environment
echo "🐍 Setting up Python virtual environment..."
cd backend

if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
    echo "✅ Created virtual environment"
fi

echo "📦 Activating virtual environment and installing dependencies..."
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
echo "✅ Installed Python dependencies"

cd ..

# Setup Node.js dependencies
echo "📦 Setting up Node.js dependencies..."
cd frontend
npm install
echo "✅ Installed Node.js dependencies"

cd ..

echo ""
echo "🎉 Local development setup complete!"
echo ""
echo "🚀 To start development:"
echo ""
echo "1. Start database and Redis:"
echo "   docker-compose up -d db redis"
echo ""
echo "2. Start backend (in new terminal):"
echo "   cd backend"
echo "   source venv/bin/activate"
echo "   uvicorn main:app --reload"
echo ""
echo "3. Start frontend (in new terminal):"
echo "   cd frontend"
echo "   npm run dev"
echo ""
echo "4. Initialize database:"
echo "   cd backend"
echo "   source venv/bin/activate"
echo "   alembic upgrade head"
echo ""
echo "📚 Access points:"
echo "   - Frontend: http://localhost:3000"
echo "   - Backend API: http://localhost:8000"
echo "   - API Docs: http://localhost:8000/docs"
echo ""
echo "🔧 Don't forget to:"
echo "   - Update .env files with your API keys"
echo "   - Set OPENAI_API_KEY for AI functionality"
echo ""
echo "✨ Happy coding!"
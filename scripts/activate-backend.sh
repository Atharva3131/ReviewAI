#!/bin/bash

# Quick script to activate backend virtual environment
# Usage: source scripts/activate-backend.sh

if [ -f "backend/venv/bin/activate" ]; then
    cd backend
    source venv/bin/activate
    echo "✅ Activated Python virtual environment"
    echo "📍 Current directory: $(pwd)"
    echo "🐍 Python: $(which python)"
    echo "💡 To deactivate: deactivate"
else
    echo "❌ Virtual environment not found. Run ./scripts/setup-local-dev.sh first"
fi
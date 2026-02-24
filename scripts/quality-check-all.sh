#!/bin/bash
# Comprehensive Code Quality Check Script for Revive AI
# Runs quality checks for both backend and frontend

set -e

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_header() {
    echo -e "\n${BLUE}================================================================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}================================================================================${NC}\n"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

# Track results
BACKEND_SUCCESS=0
FRONTEND_SUCCESS=0

# Parse arguments
FIX_MODE=false
if [[ "$1" == "--fix" ]]; then
    FIX_MODE=true
fi

print_header "Revive AI - Comprehensive Code Quality Checks"

# Backend quality checks
print_header "Backend Quality Checks"
cd backend

if [ "$FIX_MODE" = true ]; then
    print_warning "Running in fix mode..."
    if python scripts/quality_check.py --fix; then
        BACKEND_SUCCESS=1
        print_success "Backend formatting fixes applied"
    else
        print_error "Backend formatting fixes failed"
    fi
else
    if python scripts/quality_check.py; then
        BACKEND_SUCCESS=1
        print_success "Backend quality checks passed"
    else
        print_error "Backend quality checks failed"
    fi
fi

cd ..

# Frontend quality checks
print_header "Frontend Quality Checks"
cd frontend

if [ "$FIX_MODE" = true ]; then
    if node scripts/quality-check.js --fix; then
        FRONTEND_SUCCESS=1
        print_success "Frontend formatting fixes applied"
    else
        print_error "Frontend formatting fixes failed"
    fi
else
    if node scripts/quality-check.js; then
        FRONTEND_SUCCESS=1
        print_success "Frontend quality checks passed"
    else
        print_error "Frontend quality checks failed"
    fi
fi

cd ..

# Summary
print_header "Quality Check Summary"

if [ $BACKEND_SUCCESS -eq 1 ]; then
    print_success "Backend: PASSED"
else
    print_error "Backend: FAILED"
fi

if [ $FRONTEND_SUCCESS -eq 1 ]; then
    print_success "Frontend: PASSED"
else
    print_error "Frontend: FAILED"
fi

# Exit with appropriate code
if [ $BACKEND_SUCCESS -eq 1 ] && [ $FRONTEND_SUCCESS -eq 1 ]; then
    print_success "\n✓ All quality checks passed!"
    exit 0
else
    print_error "\n✗ Some quality checks failed"
    if [ "$FIX_MODE" = false ]; then
        print_warning "Run with --fix to auto-fix formatting issues"
    fi
    exit 1
fi

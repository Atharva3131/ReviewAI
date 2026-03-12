#!/bin/bash

# Railway Deployment Setup Script for Revive AI
# This script prepares the project for Railway deployment

set -e

echo "🚀 Setting up Revive AI for Railway deployment..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

# Check if Railway CLI is installed
check_railway_cli() {
    if ! command -v railway &> /dev/null; then
        print_warning "Railway CLI not found. Install it from: https://railway.app/cli"
        print_info "Run: npm install -g @railway/cli"
        return 1
    fi
    print_status "Railway CLI is installed"
    return 0
}

# Validate project structure
validate_project() {
    print_info "Validating project structure..."
    
    # Check required files
    required_files=(
        "backend/main.py"
        "backend/requirements.txt"
        "backend/railway.toml"
        "frontend/package.json"
        "frontend/railway.toml"
        "railway.json"
    )
    
    for file in "${required_files[@]}"; do
        if [[ -f "$file" ]]; then
            print_status "Found $file"
        else
            print_error "Missing required file: $file"
            exit 1
        fi
    done
}

# Check backend dependencies
check_backend() {
    print_info "Checking backend configuration..."
    
    cd backend
    
    # Check if requirements.txt has all necessary dependencies
    required_deps=("fastapi" "uvicorn" "sqlalchemy" "redis" "alembic")
    
    for dep in "${required_deps[@]}"; do
        if grep -q "$dep" requirements.txt; then
            print_status "Found dependency: $dep"
        else
            print_warning "Missing dependency: $dep"
        fi
    done
    
    # Check if main.py imports correctly (syntax check)
    if python -m py_compile main.py 2>/dev/null; then
        print_status "Backend main.py syntax is valid"
    else
        print_error "Backend main.py has syntax errors"
        exit 1
    fi
    
    cd ..
}

# Check frontend dependencies
check_frontend() {
    print_info "Checking frontend configuration..."
    
    cd frontend
    
    # Check if package.json exists and has required scripts
    if [[ -f "package.json" ]]; then
        if jq -e '.scripts.build' package.json > /dev/null 2>&1; then
            print_status "Frontend build script found"
        else
            print_error "Frontend build script missing in package.json"
            exit 1
        fi
        
        if jq -e '.scripts.start' package.json > /dev/null 2>&1; then
            print_status "Frontend start script found"
        else
            print_error "Frontend start script missing in package.json"
            exit 1
        fi
    else
        print_error "Frontend package.json not found"
        exit 1
    fi
    
    cd ..
}

# Create environment template
create_env_template() {
    print_info "Creating environment variable template..."
    
    cat > railway-env-template.txt << 'EOF'
# Railway Environment Variables Template
# Copy these to your Railway dashboard under Variables

# Backend Service Variables
DATABASE_URL=postgresql://user:password@host:port/database
REDIS_URL=redis://user:password@host:port
SECRET_KEY=your-32-character-secret-key-here
MASTER_ENCRYPTION_KEY=your-32-character-encryption-key
MISTRAL_API_KEY=your-mistral-api-key-here
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO
API_V1_STR=/api/v1
PROJECT_NAME=Revive AI
ALLOWED_HOSTS=https://your-frontend-url.railway.app,https://your-backend-url.railway.app

# Optional LLM Provider Keys
OPENAI_API_KEY=sk-your-openai-api-key-here
GEMINI_API_KEY=your-gemini-api-key-here

# Frontend Service Variables
NEXT_PUBLIC_API_URL=https://your-backend-url.railway.app

# Database Configuration (if using Railway PostgreSQL)
PGHOST=your-railway-postgres-host
PGPORT=5432
PGDATABASE=railway
PGUSER=postgres
PGPASSWORD=your-railway-postgres-password

# Redis Configuration (if using Railway Redis)
REDISHOST=your-railway-redis-host
REDISPORT=6379
REDISPASSWORD=your-railway-redis-password
EOF

    print_status "Created railway-env-template.txt"
    print_info "Copy these variables to your Railway dashboard"
}

# Generate secure keys
generate_keys() {
    print_info "Generating secure keys..."
    
    echo "# Generated Secure Keys for Railway Deployment" > generated-keys.txt
    echo "# Keep these secure and add them to Railway environment variables" >> generated-keys.txt
    echo "" >> generated-keys.txt
    
    # Generate SECRET_KEY
    secret_key=$(python -c "import secrets; print(secrets.token_urlsafe(32))")
    echo "SECRET_KEY=$secret_key" >> generated-keys.txt
    
    # Generate MASTER_ENCRYPTION_KEY
    encryption_key=$(python -c "import secrets; print(secrets.token_urlsafe(32))")
    echo "MASTER_ENCRYPTION_KEY=$encryption_key" >> generated-keys.txt
    
    print_status "Generated secure keys in generated-keys.txt"
    print_warning "Keep these keys secure and add them to Railway!"
}

# Create Railway deployment guide
create_deployment_guide() {
    print_info "Creating deployment guide..."
    
    cat > RAILWAY_DEPLOYMENT_GUIDE.md << 'EOF'
# Railway Deployment Guide for Revive AI

## Prerequisites

1. **Railway Account**: Sign up at https://railway.app
2. **GitHub Repository**: Push your code to GitHub
3. **Railway CLI**: Install with `npm install -g @railway/cli`

## Deployment Steps

### 1. Create Railway Project

```bash
railway login
railway new
# Choose "Deploy from GitHub repo"
# Select your repository
```

### 2. Set Up Services

Railway will automatically detect your services from the configuration files:
- **Backend**: Detected from `backend/railway.toml`
- **Frontend**: Detected from `frontend/railway.toml`

### 3. Add Environment Variables

In Railway dashboard, go to each service and add variables from `railway-env-template.txt`:

#### Backend Service Variables:
- `DATABASE_URL`: Your PostgreSQL connection string
- `REDIS_URL`: Your Redis connection string  
- `SECRET_KEY`: From generated-keys.txt
- `MASTER_ENCRYPTION_KEY`: From generated-keys.txt
- `MISTRAL_API_KEY`: Your Mistral AI API key
- `ENVIRONMENT`: production
- `DEBUG`: false

#### Frontend Service Variables:
- `NEXT_PUBLIC_API_URL`: Your backend service URL (Railway provides this)

### 4. Add Railway Databases (Optional)

If you don't have external databases:

```bash
railway add postgresql
railway add redis
```

Railway will automatically set the connection environment variables.

### 5. Deploy

```bash
railway up
```

Or push to GitHub - Railway will auto-deploy on commits.

### 6. Verify Deployment

1. Check backend health: `https://your-backend-url.railway.app/health`
2. Check frontend: `https://your-frontend-url.railway.app`
3. Monitor logs in Railway dashboard

## Troubleshooting

### Common Issues:

1. **Build Failures**: Check logs in Railway dashboard
2. **Environment Variables**: Ensure all required variables are set
3. **Database Connection**: Verify DATABASE_URL format
4. **CORS Issues**: Update ALLOWED_HOSTS with your Railway URLs

### Health Checks:

- Backend: `/health` endpoint
- Frontend: Root path `/`

### Logs:

Access logs via Railway CLI:
```bash
railway logs
```

## Production Checklist

- [ ] All environment variables set
- [ ] Database migrations run successfully
- [ ] Health checks passing
- [ ] CORS configured correctly
- [ ] SSL certificates active
- [ ] Monitoring set up
- [ ] Backup strategy in place

## Support

- Railway Docs: https://docs.railway.app
- Railway Discord: https://railway.app/discord
- Project Issues: Create GitHub issue
EOF

    print_status "Created RAILWAY_DEPLOYMENT_GUIDE.md"
}

# Main execution
main() {
    echo "🚀 Railway Setup for Revive AI"
    echo "================================"
    
    # Run checks
    validate_project
    check_backend
    check_frontend
    
    # Create deployment assets
    create_env_template
    generate_keys
    create_deployment_guide
    
    echo ""
    echo "================================"
    print_status "Railway setup complete!"
    echo ""
    print_info "Next steps:"
    echo "1. Review railway-env-template.txt"
    echo "2. Add environment variables to Railway dashboard"
    echo "3. Follow RAILWAY_DEPLOYMENT_GUIDE.md"
    echo "4. Deploy with: railway up"
    echo ""
    print_warning "Keep generated-keys.txt secure!"
    
    # Check Railway CLI
    if check_railway_cli; then
        print_info "You can now run: railway login && railway new"
    fi
}

# Run main function
main "$@"
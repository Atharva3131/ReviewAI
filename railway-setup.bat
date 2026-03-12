@echo off
setlocal enabledelayedexpansion

REM Railway Deployment Setup Script for Revive AI (Windows)
REM This script prepares the project for Railway deployment

echo 🚀 Setting up Revive AI for Railway deployment...
echo.

REM Function to print status messages
:print_status
echo ✓ %~1
goto :eof

:print_warning
echo ⚠ %~1
goto :eof

:print_error
echo ✗ %~1
goto :eof

:print_info
echo ℹ %~1
goto :eof

REM Check if Railway CLI is installed
:check_railway_cli
railway --version >nul 2>&1
if %errorlevel% neq 0 (
    call :print_warning "Railway CLI not found. Install it from: https://railway.app/cli"
    call :print_info "Run: npm install -g @railway/cli"
    goto :eof
)
call :print_status "Railway CLI is installed"
goto :eof

REM Validate project structure
:validate_project
call :print_info "Validating project structure..."

set required_files=backend\main.py backend\requirements.txt backend\railway.toml frontend\package.json frontend\railway.toml railway.json

for %%f in (%required_files%) do (
    if exist "%%f" (
        call :print_status "Found %%f"
    ) else (
        call :print_error "Missing required file: %%f"
        exit /b 1
    )
)
goto :eof

REM Check backend dependencies
:check_backend
call :print_info "Checking backend configuration..."

cd backend

REM Check if main.py compiles
python -m py_compile main.py >nul 2>&1
if %errorlevel% equ 0 (
    call :print_status "Backend main.py syntax is valid"
) else (
    call :print_error "Backend main.py has syntax errors"
    cd ..
    exit /b 1
)

cd ..
goto :eof

REM Check frontend dependencies
:check_frontend
call :print_info "Checking frontend configuration..."

cd frontend

if exist "package.json" (
    call :print_status "Frontend package.json found"
) else (
    call :print_error "Frontend package.json not found"
    cd ..
    exit /b 1
)

cd ..
goto :eof

REM Create environment template
:create_env_template
call :print_info "Creating environment variable template..."

(
echo # Railway Environment Variables Template
echo # Copy these to your Railway dashboard under Variables
echo.
echo # Backend Service Variables
echo DATABASE_URL=postgresql://user:password@host:port/database
echo REDIS_URL=redis://user:password@host:port
echo SECRET_KEY=your-32-character-secret-key-here
echo MASTER_ENCRYPTION_KEY=your-32-character-encryption-key
echo MISTRAL_API_KEY=your-mistral-api-key-here
echo ENVIRONMENT=production
echo DEBUG=false
echo LOG_LEVEL=INFO
echo API_V1_STR=/api/v1
echo PROJECT_NAME=Revive AI
echo ALLOWED_HOSTS=https://your-frontend-url.railway.app,https://your-backend-url.railway.app
echo.
echo # Optional LLM Provider Keys
echo OPENAI_API_KEY=sk-your-openai-api-key-here
echo GEMINI_API_KEY=your-gemini-api-key-here
echo.
echo # Frontend Service Variables
echo NEXT_PUBLIC_API_URL=https://your-backend-url.railway.app
echo.
echo # Database Configuration ^(if using Railway PostgreSQL^)
echo PGHOST=your-railway-postgres-host
echo PGPORT=5432
echo PGDATABASE=railway
echo PGUSER=postgres
echo PGPASSWORD=your-railway-postgres-password
echo.
echo # Redis Configuration ^(if using Railway Redis^)
echo REDISHOST=your-railway-redis-host
echo REDISPORT=6379
echo REDISPASSWORD=your-railway-redis-password
) > railway-env-template.txt

call :print_status "Created railway-env-template.txt"
call :print_info "Copy these variables to your Railway dashboard"
goto :eof

REM Generate secure keys
:generate_keys
call :print_info "Generating secure keys..."

(
echo # Generated Secure Keys for Railway Deployment
echo # Keep these secure and add them to Railway environment variables
echo.
) > generated-keys.txt

REM Generate SECRET_KEY
for /f %%i in ('python -c "import secrets; print(secrets.token_urlsafe(32))"') do set secret_key=%%i
echo SECRET_KEY=%secret_key% >> generated-keys.txt

REM Generate MASTER_ENCRYPTION_KEY
for /f %%i in ('python -c "import secrets; print(secrets.token_urlsafe(32))"') do set encryption_key=%%i
echo MASTER_ENCRYPTION_KEY=%encryption_key% >> generated-keys.txt

call :print_status "Generated secure keys in generated-keys.txt"
call :print_warning "Keep these keys secure and add them to Railway!"
goto :eof

REM Create Railway deployment guide
:create_deployment_guide
call :print_info "Creating deployment guide..."

(
echo # Railway Deployment Guide for Revive AI
echo.
echo ## Prerequisites
echo.
echo 1. **Railway Account**: Sign up at https://railway.app
echo 2. **GitHub Repository**: Push your code to GitHub
echo 3. **Railway CLI**: Install with `npm install -g @railway/cli`
echo.
echo ## Deployment Steps
echo.
echo ### 1. Create Railway Project
echo.
echo ```bash
echo railway login
echo railway new
echo # Choose "Deploy from GitHub repo"
echo # Select your repository
echo ```
echo.
echo ### 2. Set Up Services
echo.
echo Railway will automatically detect your services from the configuration files:
echo - **Backend**: Detected from `backend/railway.toml`
echo - **Frontend**: Detected from `frontend/railway.toml`
echo.
echo ### 3. Add Environment Variables
echo.
echo In Railway dashboard, go to each service and add variables from `railway-env-template.txt`:
echo.
echo #### Backend Service Variables:
echo - `DATABASE_URL`: Your PostgreSQL connection string
echo - `REDIS_URL`: Your Redis connection string  
echo - `SECRET_KEY`: From generated-keys.txt
echo - `MASTER_ENCRYPTION_KEY`: From generated-keys.txt
echo - `MISTRAL_API_KEY`: Your Mistral AI API key
echo - `ENVIRONMENT`: production
echo - `DEBUG`: false
echo.
echo #### Frontend Service Variables:
echo - `NEXT_PUBLIC_API_URL`: Your backend service URL ^(Railway provides this^)
echo.
echo ### 4. Add Railway Databases ^(Optional^)
echo.
echo If you don't have external databases:
echo.
echo ```bash
echo railway add postgresql
echo railway add redis
echo ```
echo.
echo Railway will automatically set the connection environment variables.
echo.
echo ### 5. Deploy
echo.
echo ```bash
echo railway up
echo ```
echo.
echo Or push to GitHub - Railway will auto-deploy on commits.
echo.
echo ### 6. Verify Deployment
echo.
echo 1. Check backend health: `https://your-backend-url.railway.app/health`
echo 2. Check frontend: `https://your-frontend-url.railway.app`
echo 3. Monitor logs in Railway dashboard
echo.
echo ## Troubleshooting
echo.
echo ### Common Issues:
echo.
echo 1. **Build Failures**: Check logs in Railway dashboard
echo 2. **Environment Variables**: Ensure all required variables are set
echo 3. **Database Connection**: Verify DATABASE_URL format
echo 4. **CORS Issues**: Update ALLOWED_HOSTS with your Railway URLs
echo.
echo ### Health Checks:
echo.
echo - Backend: `/health` endpoint
echo - Frontend: Root path `/`
echo.
echo ### Logs:
echo.
echo Access logs via Railway CLI:
echo ```bash
echo railway logs
echo ```
echo.
echo ## Production Checklist
echo.
echo - [ ] All environment variables set
echo - [ ] Database migrations run successfully
echo - [ ] Health checks passing
echo - [ ] CORS configured correctly
echo - [ ] SSL certificates active
echo - [ ] Monitoring set up
echo - [ ] Backup strategy in place
echo.
echo ## Support
echo.
echo - Railway Docs: https://docs.railway.app
echo - Railway Discord: https://railway.app/discord
echo - Project Issues: Create GitHub issue
) > RAILWAY_DEPLOYMENT_GUIDE.md

call :print_status "Created RAILWAY_DEPLOYMENT_GUIDE.md"
goto :eof

REM Main execution
:main
echo 🚀 Railway Setup for Revive AI
echo ================================
echo.

REM Run checks
call :validate_project
if %errorlevel% neq 0 exit /b 1

call :check_backend
if %errorlevel% neq 0 exit /b 1

call :check_frontend
if %errorlevel% neq 0 exit /b 1

REM Create deployment assets
call :create_env_template
call :generate_keys
call :create_deployment_guide

echo.
echo ================================
call :print_status "Railway setup complete!"
echo.
call :print_info "Next steps:"
echo 1. Review railway-env-template.txt
echo 2. Add environment variables to Railway dashboard
echo 3. Follow RAILWAY_DEPLOYMENT_GUIDE.md
echo 4. Deploy with: railway up
echo.
call :print_warning "Keep generated-keys.txt secure!"

REM Check Railway CLI
call :check_railway_cli
if %errorlevel% equ 0 (
    call :print_info "You can now run: railway login && railway new"
)

goto :eof

REM Run main function
call :main
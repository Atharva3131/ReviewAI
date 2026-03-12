# Railway Deployment Checklist

## Pre-Deployment Setup

### 1. Code Repository
- [ ] Code pushed to GitHub repository
- [ ] All sensitive data removed from code
- [ ] .env files added to .gitignore
- [ ] README.md updated with deployment info

### 2. Railway Account Setup
- [ ] Railway account created at https://railway.app
- [ ] Railway CLI installed: `npm install -g @railway/cli`
- [ ] Logged into Railway CLI: `railway login`

### 3. Environment Variables Prepared
- [ ] Run `railway-setup.bat` (Windows) or `railway-setup.sh` (Linux/Mac)
- [ ] Review `railway-env-template.txt`
- [ ] Secure keys generated in `generated-keys.txt`
- [ ] External service API keys obtained (Mistral AI, etc.)

## Railway Deployment Steps

### 4. Create Railway Project
- [ ] Run `railway new` and select GitHub repository
- [ ] Services automatically detected (backend + frontend)
- [ ] Project created successfully

### 5. Database Setup
- [ ] Add PostgreSQL: `railway add postgresql`
- [ ] Add Redis: `railway add redis`
- [ ] Note connection URLs from Railway dashboard

### 6. Environment Variables Configuration

#### Backend Service:
- [ ] DATABASE_URL (from Railway PostgreSQL)
- [ ] REDIS_URL (from Railway Redis)
- [ ] SECRET_KEY (from generated-keys.txt)
- [ ] MASTER_ENCRYPTION_KEY (from generated-keys.txt)
- [ ] MISTRAL_API_KEY (your API key)
- [ ] ENVIRONMENT=production
- [ ] DEBUG=false

#### Frontend Service:
- [ ] NEXT_PUBLIC_API_URL (backend Railway URL)

### 7. Deploy Services
- [ ] Deploy backend: `railway up` in backend directory
- [ ] Deploy frontend: `railway up` in frontend directory
- [ ] Monitor deployment logs for errors

## Post-Deployment Verification

### 8. Health Checks
- [ ] Backend health check: `https://backend-url.railway.app/health`
- [ ] Frontend loads: `https://frontend-url.railway.app`
- [ ] API endpoints responding correctly
- [ ] Database connection working

### 9. Functionality Testing
- [ ] User registration/login works
- [ ] API endpoints return expected responses
- [ ] Frontend-backend communication working
- [ ] Database operations successful

### 10. Production Configuration
- [ ] CORS settings updated with Railway URLs
- [ ] SSL certificates active (automatic with Railway)
- [ ] Custom domain configured (if needed)
- [ ] Monitoring and logging set up

## Troubleshooting Common Issues

### Build Failures
- Check Railway deployment logs
- Verify all dependencies in requirements.txt/package.json
- Ensure Python/Node versions are compatible

### Runtime Errors
- Check environment variables are set correctly
- Verify database connection strings
- Review application logs in Railway dashboard

### CORS Issues
- Update ALLOWED_HOSTS in backend environment
- Ensure frontend URL is whitelisted

## Success Criteria
- [ ] Both services deployed and running
- [ ] Health checks passing
- [ ] No critical errors in logs
- [ ] Basic functionality verified
- [ ] Performance acceptable

## Next Steps After Deployment
- Set up monitoring and alerts
- Configure backup strategies
- Plan scaling if needed
- Document production URLs and access
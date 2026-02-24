# Railway Deployment Guide - ReviewAI

This guide will help you deploy both the frontend and backend to Railway.app using their free tier.

## Prerequisites

1. GitHub account
2. Railway account (sign up at https://railway.app)
3. Your code pushed to a GitHub repository

## Free Tier Limits

Railway free tier includes:
- $5 free credit per month
- ~500 hours of usage
- Perfect for demos and MVPs

## Step-by-Step Deployment

### 1. Push Your Code to GitHub

```bash
# Initialize git if you haven't already
git init
git add .
git commit -m "Initial commit - ReviewAI"

# Create a new repository on GitHub, then:
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO.git
git branch -M main
git push -u origin main
```

### 2. Sign Up for Railway

1. Go to https://railway.app
2. Click "Login" and sign in with GitHub
3. Authorize Railway to access your repositories

### 3. Create a New Project

1. Click "New Project"
2. Select "Deploy from GitHub repo"
3. Choose your ReviewAI repository
4. Railway will detect your monorepo structure

### 4. Deploy Backend Service

1. Railway should auto-detect the backend
2. Click "Add Service" → "GitHub Repo" → Select your repo
3. Set the **Root Directory** to `backend`
4. Railway will use the `backend/railway.toml` configuration

#### Backend Environment Variables

Add these in the Railway dashboard (Variables tab):

```
DATABASE_URL=your_supabase_postgres_url
REDIS_URL=your_upstash_redis_url
MISTRAL_API_KEY=your_mistral_api_key
SECRET_KEY=your_secret_key_here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
ENVIRONMENT=production
ALLOWED_ORIGINS=https://your-frontend-url.railway.app
```

**Important:** After backend deploys, Railway will give you a URL like:
`https://your-backend.railway.app`

Copy this URL - you'll need it for the frontend!

### 5. Deploy Frontend Service

1. Click "New Service" in the same project
2. Select "GitHub Repo" → Choose your repo again
3. Set the **Root Directory** to `frontend`
4. Railway will use the `frontend/railway.toml` configuration

#### Frontend Environment Variables

Add these in the Railway dashboard (Variables tab):

```
NEXT_PUBLIC_API_URL=https://your-backend.railway.app
NODE_ENV=production
```

**Replace** `https://your-backend.railway.app` with your actual backend URL from step 4!

### 6. Update Backend CORS

After frontend deploys, you'll get a URL like:
`https://your-frontend.railway.app`

Go back to your **backend service** and update the `ALLOWED_ORIGINS` variable:

```
ALLOWED_ORIGINS=https://your-frontend.railway.app,https://your-custom-domain.com
```

### 7. Verify Deployment

1. Open your frontend URL: `https://your-frontend.railway.app`
2. Try logging in with demo credentials:
   - Email: `demo@restaurant.com`
   - Password: `demo123`
3. Check that the dashboard loads correctly

## Troubleshooting

### Backend Won't Start

**Check logs in Railway dashboard:**
- Click on backend service → "Deployments" → Click latest deployment → "View Logs"

**Common issues:**
- Missing environment variables
- Database connection issues (check Supabase URL)
- Port binding (Railway sets `$PORT` automatically)

### Frontend Can't Connect to Backend

**Check:**
1. `NEXT_PUBLIC_API_URL` is set correctly in frontend
2. Backend `ALLOWED_ORIGINS` includes frontend URL
3. Backend health endpoint works: `https://your-backend.railway.app/health`

### Database Connection Issues

**Supabase Connection:**
1. Go to Supabase dashboard
2. Settings → Database → Connection string
3. Use the "Connection pooling" URL for production
4. Format: `postgresql://postgres:[password]@[host]:6543/postgres?pgbouncer=true`

### Redis Connection Issues

**Upstash Connection:**
1. Go to Upstash dashboard
2. Copy the Redis URL (should start with `redis://` or `rediss://`)
3. Make sure it includes the password

## Custom Domain (Optional)

1. In Railway dashboard, click on frontend service
2. Go to "Settings" → "Domains"
3. Click "Add Domain"
4. Follow instructions to point your domain to Railway

## Monitoring & Logs

**View Logs:**
- Railway Dashboard → Select Service → "Deployments" → "View Logs"

**Monitor Usage:**
- Railway Dashboard → "Usage" tab
- Track your $5 monthly credit

**Metrics:**
- CPU usage
- Memory usage
- Network traffic

## Cost Optimization Tips

1. **Use Supabase & Upstash free tiers** (external services don't count toward Railway usage)
2. **Set sleep mode** for non-production environments
3. **Monitor your usage** regularly in the Railway dashboard
4. **Optimize build times** to reduce deployment costs

## Updating Your App

Railway auto-deploys when you push to GitHub:

```bash
# Make your changes
git add .
git commit -m "Update feature"
git push origin main
```

Railway will automatically:
1. Detect the push
2. Build both services
3. Deploy the new version
4. Zero-downtime deployment

## Rollback

If something goes wrong:
1. Go to Railway dashboard
2. Click on the service
3. "Deployments" tab
4. Click on a previous successful deployment
5. Click "Redeploy"

## Support

- Railway Docs: https://docs.railway.app
- Railway Discord: https://discord.gg/railway
- Railway Status: https://status.railway.app

## Next Steps

After successful deployment:
1. Test all features thoroughly
2. Set up custom domain
3. Configure monitoring/alerts
4. Set up backup strategy for database
5. Document your production URLs

---

**Your ReviewAI app is now live! 🚀**

Frontend: `https://your-frontend.railway.app`
Backend: `https://your-backend.railway.app`

# Zeabur Deployment Guide for Opsora

This guide will walk you through deploying Opsora to Zeabur for demo purposes.

## Prerequisites

1. **Zeabur Account**
   - Sign up at https://zeabur.com
   - You can use GitHub, Google, or email signup

2. **GitHub Repository** (Recommended)
   - Push your Opsora code to a GitHub repository
   - This enables automatic deployments on push

3. **LLM API Key**
   - Anthropic API key from https://console.anthropic.com
   - OR OpenAI API key from https://platform.openai.com
   - OR GLM API key from https://open.bigmodel.cn

## Step-by-Step Deployment

### Step 1: Prepare Your Code

```bash
# Navigate to your opsora directory
cd /data/data/com.termux/files/home/opsora

# Initialize git repository (if not already done)
git init
git add .
git commit -m "Initial commit: Opsora Business Analytics Platform"

# Create GitHub repository and push
gh repo create opsora --public --source=.
git push -u origin main
```

### Step 2: Sign Up/Login to Zeabur

1. Go to https://zeabur.com
2. Click "Sign Up" or "Login"
3. Authorize GitHub access (recommended for deployment)

### Step 3: Create a New Project

1. In Zeabur dashboard, click **"New Project"**
2. Select your GitHub repository
3. Choose the region closest to your users (default is usually fine)

### Step 4: Deploy the API Service

1. Click **"Create Service"** → **"Container"**
2. Configure the service:

   **Basic Settings:**
   - **Name**: `opsora-api`
   - **Branch**: `main`

   **Build Settings:**
   - **Dockerfile Path**: `Dockerfile`
   - **Context Path**: `/`

   **Port:**
   - **Container Port**: `8000`

   **Environment Variables:**
   ```bash
   API_HOST=0.0.0.0
   API_PORT=8000
   API_RELOAD=false
   API_WORKERS=4
   LLM_PROVIDER=glm
   GLM_API_KEY=your-glm-key-here
   ```

3. Click **"Deploy"**
4. Wait for the deployment to complete (2-3 minutes)

### Step 5: Deploy the Dashboard Service

1. Click **"Add Service"** → **"Container"**
2. Configure the service:

   **Basic Settings:**
   - **Name**: `opsora-dashboard`
   - **Branch**: `main`

   **Build Settings:**
   - **Dockerfile Path**: `Dockerfile`
   - **Context Path**: `/`

   **Port:**
   - **Container Port**: `8501`

   **Environment Variables:**
   ```bash
   API_URL=https://opsora-api.zeabur.app
   ```

3. Click **"Deploy"**
4. Wait for deployment

### Step 6: Configure Networking (Optional)

1. Go to your dashboard service
2. Click **"Networking"**
3. Add a custom domain if desired (Zeabur provides a free `.zeabur.app` domain)

### Step 7: Access Your Deployment

After both services are deployed:

- **API**: `https://opsora-api.zeabur.app`
- **Dashboard**: `https://opsora-dashboard.zeabur.app`
- **API Docs**: `https://opsora-api.zeabur.app/docs`

## Troubleshooting

### Issue: Build Fails

**Solution**: Check the build logs
- Make sure `Dockerfile` exists in repository root
- Verify `requirements.txt` includes all dependencies

### Issue: Service Crashes on Startup

**Solution**: Check environment variables
- Verify `ANTHROPIC_API_KEY` or `OPENAI_API_KEY` is set
- Check required environment variables are present

### Issue: Dashboard Can't Connect to API

**Solution**: Check API_URL
- Verify `API_URL` in dashboard service points to correct API domain
- Make sure both services are in the same project

### Issue: High Memory Usage

**Solution**: Adjust resources
- Go to service settings → Resources
- Reduce memory allocation (minimum 256MB for demo)

## Cost Estimates (Zeabur Free Tier)

Zeabur offers a generous free tier:
- **Free credits**: ~$10/month equivalent
- **After credits**: ~$5-10/month for small deployments

To minimize costs:
1. Set services to sleep when not in use
2. Use minimum resource allocations
3. Delete demo projects when done

## Alternative: Quick Deploy (Using Prebuilt Image)

If you want to skip Docker build:

1. Pull prebuilt image (if available):
   ```bash
   docker pull your-registry/opsora:latest
   ```

2. In Zeabur, select "Prebuilt Image" instead of Dockerfile

## Environment Variables Reference

### Required

| Variable | Description | Example |
|----------|-------------|---------|
| `LLM_PROVIDER` | AI provider | `anthropic`, `openai`, `glm` |
| `ANTHROPIC_API_KEY` | Claude API key | `sk-ant-xxxxx` |
| `OPENAI_API_KEY` | OpenAI API key | `sk-xxxxx` |
| `GLM_API_KEY` | GLM/Zhipu AI API key | `your-glm-key` |

### Optional

| Variable | Description | Default |
|----------|-------------|---------|
| `API_HOST` | API bind address | `0.0.0.0` |
| `API_PORT` | API port | `8000` |
| `API_WORKERS` | Number of workers | `4` |
| `GCP_PROJECT_ID` | GCP project (optional for demo) | - |
| `RECOMMENDATION_CONFIDENCE_THRESHOLD` | Min confidence | `0.7` |

## Monitoring Your Deployment

### View Logs
1. Go to your service in Zeabur
2. Click **"Logs"** tab
3. Real-time logs will appear

### Set Up Alerts (Optional)
1. Go to **"Settings"** → **"Notifications"**
2. Configure email/webhook alerts for failures

## Updating Your Deployment

### Automatic Updates (Recommended)
1. Push changes to GitHub
2. Zeabur automatically detects and redeploys

### Manual Updates
1. Go to service in Zeabur
2. Click **"Redeploy"**
3. Select commit/branch

## Security Best Practices

1. **Never commit API keys** to repository
   - Use Zeabur's environment variables instead
   - Add `.env` to `.gitignore`

2. **Use read-only API keys** when possible
   - Create dedicated keys for Zeabur deployment

3. **Enable authentication** for production
   - Add API key authentication to endpoints
   - Use Zeabur's built-in authentication

## Next Steps

1. **Test your deployment**: Access the dashboard and verify functionality
2. **Set up custom domain**: Configure your own domain for professional appearance
3. **Add monitoring**: Integrate with error tracking (e.g., Sentry)
4. **Scale resources**: Increase limits if needed for more users

## Support

- Zeabur Docs: https://zeabur.com/docs
- Zeabur Discord: https://discord.gg/zeabur
- GitHub Issues: Report issues in repository

## Quick Reference Commands

```bash
# Check deployment status
curl https://opsora-api.zeabur.app/health

# View API documentation
open https://opsora-api.zeabur.app/docs

# Access dashboard
open https://opsora-dashboard.zeabur.app

# Test API endpoint
curl https://opsora-api.zeabur.app/v1/agents/status
```

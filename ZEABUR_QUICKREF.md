# Zeabur Quick Reference Card

## One-Page Summary

### Pre-Deployment Checklist ☑️

- [ ] Zeabur account created (https://zeabur.com)
- [ ] GitHub repository with code pushed
- [ ] LLM API key ready (Anthropic, OpenAI, or GLM)
- [ ] `.env` file in `.gitignore` (never commit keys!)

### Deployment Steps (5 minutes)

#### 1. Create Project
```
Zeabur Dashboard → New Project → Select GitHub Repo
```

#### 2. Deploy API Service
```
Create Service → Container → Configure:
├── Name: opsora-api
├── Port: 8000
├── Environment Variables:
│   ├── LLM_PROVIDER=anthropic
│   └── ANTHROPIC_API_KEY=sk-ant-xxxxx
└── Deploy
```

#### 3. Deploy Dashboard Service
```
Add Service → Container → Configure:
├── Name: opsora-dashboard
├── Port: 8501
├── Environment Variables:
│   └── API_URL=https://opsora-api.zeabur.app
└── Deploy
```

### Access URLs

| Service | URL |
|---------|-----|
| Dashboard | https://opsora-dashboard.zeabur.app |
| API | https://opsora-api.zeabur.app |
| API Docs | https://opsora-api.zeabur.app/docs |

### Environment Variables Required

```bash
# API Service
LLM_PROVIDER=glm                    # or anthropic, openai
GLM_API_KEY=your-glm-key-here       # or ANTHROPIC_API_KEY

# Dashboard Service
API_URL=https://opsora-api.zeabur.app
```

### Troubleshooting

| Issue | Fix |
|-------|-----|
| Build fails | Check Dockerfile exists in repo root |
| Service crashes | Verify API key is set correctly |
| Dashboard blank | Check API_URL matches API domain |
| High costs | Enable "Sleep when inactive" |

### Cost Management

- **Free Tier**: ~$10/month credits
- **After Free**: ~$5-10/month for demo
- **Money Saving**: Enable sleep mode, use minimum resources

### Update & Redeploy

```bash
# Make changes locally
git add .
git commit -m "Update feature"
git push

# Zeabur auto-detects and redeploys
# Or click "Redeploy" in Zeabur dashboard
```

### Useful Links

- 📖 [Full Deployment Guide](DEPLOY_ZEABUR.md)
- 📚 [Zeabur Documentation](https://zeabur.com/docs)
- 💬 [Zeabur Discord](https://discord.gg/zeabur)

### Quick Test Commands

```bash
# Health check
curl https://opsora-api.zeabur.app/health

# Test API
curl https://opsora-api.zeabur.app/v1/agents/status

# Open dashboard
open https://opsora-dashboard.zeabur.app
```

---

**Estimated Time**: 5-10 minutes for first deployment
**Skill Level**: Beginner (no DevOps experience needed)

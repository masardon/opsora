# GLM / Zhipu AI Setup Guide

This guide explains how to use **GLM (Zhipu AI)** models with Opsora.

## What is GLM?

GLM is a series of large language models developed by Zhipu AI (智谱AI), including:
- **GLM-4**: Latest flagship model
- **GLM-4-Flash**: Fast, cost-effective model (recommended for Opsora)
- **GLM-3-Turbo**: Previous generation, still capable
- **ChatGLM系列**: Open-source conversational models

## Get Your API Key

1. Visit https://open.bigmodel.cn
2. Register / Login
3. Go to API Keys section
4. Create a new API key
5. Copy your key (format: `xxxxxxxx.xxxxxxx`)

## Configure Opsora for GLM

### Option 1: Using `.env` File

```bash
# Edit .env file
LLM_PROVIDER=glm
GLM_API_KEY=your-actual-api-key-here
GLM_MODEL=glm-4-flash
```

### Option 2: Environment Variables

```bash
export LLM_PROVIDER=glm
export GLM_API_KEY=your-actual-api-key-here
export GLM_MODEL=glm-4-flash
```

### Option 3: Direct in Code

```python
from agents import create_llm_adapter

adapter = create_llm_adapter(
    provider="glm",
    glm_api_key="your-api-key",
    glm_model="glm-4-flash",
)
```

## Available GLM Models

| Model | Best For | Speed | Cost |
|-------|----------|-------|------|
| `glm-4-flash` | **General use, recommended** | Fast | Low |
| `glm-4` | Complex reasoning | Medium | Medium |
| `glm-4-air` | Balanced performance | Fast | Low |
| `glm-3-turbo` | Simple tasks | Fast | Lowest |
| `chatglm3-6b` | Chinese language | Medium | Low |

## Example Configuration

```bash
# Recommended for production (best balance)
LLM_PROVIDER=glm
GLM_API_KEY=your-key
GLM_MODEL=glm-4-flash

# For complex analytics
GLM_MODEL=glm-4

# For cost optimization
GLM_MODEL=glm-3-turbo
```

## Test Your GLM Setup

```python
import asyncio
from agents import create_llm_adapter

async def test_glm():
    adapter = create_llm_adapter(
        provider="glm",
        glm_api_key="your-api-key",
        glm_model="glm-4-flash",
    )
    
    response = await adapter.generate(
        "Analyze this sales data: Revenue $50,000, Growth 15%. What does this mean?"
    )
    
    print(response)

asyncio.run(test_glm())
```

## API Pricing (Reference)

As of 2024, GLM pricing (CNY per 1K tokens):

| Model | Input | Output |
|-------|-------|--------|
| GLM-4-Flash | ¥0.0001 | ¥0.0001 |
| GLM-4 | ¥0.01 | ¥0.01 |
| GLM-4-Air | ¥0.001 | ¥0.001 |
| GLM-3-Turbo | ¥0.0005 | ¥0.0005 |

*Check https://open.bigmodel.cn/pricing for current pricing*

## Advantages of Using GLM

✅ **Cost-effective**: Significantly cheaper than Western LLMs
✅ **Fast response**: Especially GLM-4-Flash
✅ **Chinese optimized**: Excellent for Chinese language tasks
✅ **High quality**: Competitive with GPT-4/Claude for business analytics
✅ **Local support**: Chinese company, easier support for China region

## Limitations

⚠️ **Rate limits**: Check your account tier for request limits
⚠️ **Region**: May have latency outside China
⚠️ **English**: While good, English capability slightly behind Claude/GPT-4

## Troubleshooting

### Error: "Unauthorized"

**Solution**: Check your API key
- Verify key is correct
- Check key hasn't expired
- Ensure sufficient account balance

### Error: "Model not found"

**Solution**: Check model name
- Use exact model name from the list above
- Check model is available in your account tier

### Slow Response

**Solution**: Try faster model
- Switch to `glm-4-flash`
- Or use `glm-4-air`

### Poor Quality Response

**Solution**: Adjust parameters
- Increase `temperature` slightly (0.8-0.9)
- Switch to `glm-4` for complex tasks

## Quick Start Commands

```bash
# Set GLM as provider
echo "LLM_PROVIDER=glm" >> .env
echo "GLM_API_KEY=your-key" >> .env
echo "GLM_MODEL=glm-4-flash" >> .env

# Test the API
python -c "
from agents import create_llm_adapter
import asyncio

async def test():
    adapter = create_llm_adapter(
        provider='glm',
        glm_api_key='your-key',
        glm_model='glm-4-flash'
    )
    result = await adapter.generate('Say hello in JSON format')
    print(result)

asyncio.run(test())
"
```

## Migration from Other Providers

If you're switching from another provider:

```bash
# From Anthropic
# LLM_PROVIDER=anthropic
# ANTHROPIC_API_KEY=sk-ant-xxxxx

# TO
LLM_PROVIDER=glm
GLM_API_KEY=your-glm-key
GLM_MODEL=glm-4-flash

# From OpenAI
# LLM_PROVIDER=openai
# OPENAI_API_KEY=sk-xxxxx

# TO
LLM_PROVIDER=glm
GLM_API_KEY=your-glm-key
GLM_MODEL=glm-4-flash
```

## Support

- **GLM Documentation**: https://open.bigmodel.cn/dev/api
- **Pricing**: https://open.bigmodel.cn/pricing
- **Community**: https://github.com/THUDM/GLM-4
- **Issues**: Report at https://github.com/your-org/opsora/issues

## Sample .env Configuration

```bash
# =============================================================================
# Opsora Configuration with GLM
# =============================================================================

# LLM Configuration
LLM_PROVIDER=glm
GLM_API_KEY=xxxxxxxx.xxxxxxx
GLM_MODEL=glm-4-flash
GLM_BASE_URL=https://open.bigmodel.cn/api/paas/v4/

# Agent Settings
AGENT_MAX_ITERATIONS=5
AGENT_TIMEOUT=30
RECOMMENDATION_CONFIDENCE_THRESHOLD=0.7

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
```

---

**Ready to use GLM with Opsora!** 🚀

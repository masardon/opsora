claude --resume d0533c34-0bd3-4d8d-a8a4-f5d3e5fdff9d

# Opsora - Agentic AI Business Analytics & Intelligence

A cloud-native Business Analytics and Intelligence platform that leverages Agentic AI to provide live recommendations and action suggestions as data flows into a Data Warehouse.

## Architecture

```
Data Sources → PubSub → Real-time Processing → BigQuery → AI Agents → Recommendations → Dashboard
```

## Features

- **Real-time Data Ingestion**: Stream events via Google PubSub
- **Agentic AI Analysis**: Domain-specific AI agents analyze data and generate insights
- **Intelligent Recommendations**: Scored and prioritized actionable recommendations
- **Hybrid Processing**: Real-time alerts + batch deep analysis
- **Visual Dashboard**: Streamlit-based dashboard for monitoring
- **Flexible LLM Support**: Claude, GPT-4, GLM-4, Gemini, or local models

## Quick Start

### Prerequisites

- Python 3.11+
- Google Cloud Project with APIs enabled:
  - BigQuery
  - PubSub
  - Cloud Functions
  - Cloud Storage
  - Vertex AI (optional)

### Installation

```bash
# Clone repository
git clone <repo-url>
cd opsora

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp .env.example .env

# Configure your credentials
gcloud auth application-default login
```

### Configuration

Edit `.env` with your settings:

```bash
# GCP Configuration
GCP_PROJECT_ID=your-project-id
GCP_REGION=us-central1
BIGQUERY_DATASET=opsora

# PubSub Topics
PUBSUB_TOPIC_SALES=events-sales
PUBSUB_TOPIC_OPERATIONS=events-operations
PUBSUB_TOPIC_CUSTOMERS=events-customers
PUBSUB_TOPIC_REVENUE=events-revenue

# LLM Configuration
LLM_PROVIDER=anthropic  # anthropic, openai, glm, vertexai, local
ANTHROPIC_API_KEY=your-key
OPENAI_API_KEY=your-key-if-using-openai
GLM_API_KEY=your-glm-key-if-using-glm

# Agent Settings
AGENT_MAX_ITERATIONS=5
AGENT_TIMEOUT=30
RECOMMENDATION_CONFIDENCE_THRESHOLD=0.7
```

### Quick Start (Demo Mode)

To quickly test Opsora without GCP setup:

```bash
# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp .env.example .env

# Edit .env - set LLM_PROVIDER and API key at minimum
# LLM_PROVIDER=anthropic
# ANTHROPIC_API_KEY=your-key-here

# Generate sample data
python tools/generate_sample_data.py

# Start the API server
uvicorn api.main:app --reload --port 8000

# In another terminal, start the dashboard
streamlit run dashboard/streamlit_app.py --server.port 8501

# Access the dashboard at http://localhost:8501
```

### Docker Quick Start

```bash
# Build and start all services
docker-compose up -d

# Access the dashboard
open http://localhost:8501

# View API docs
open http://localhost:8000/docs
```

### Development Setup

For full local development:

```bash
# Start API server
uvicorn api.main:app --reload --port 8000

# Start dashboard (in another terminal)
streamlit run dashboard/streamlit_app.py --server.port 8501

# Generate sample data for testing (in another terminal)
python tools/generate_sample_data.py

# Run tests
pytest

# Run with coverage
pytest --cov=opsora tests/
```

## Project Structure

```
opsora/
├── agents/               # AI Agent implementations
│   ├── base/            # Base agent class and LLM adapters
│   ├── domain/          # Domain-specific agents (Sales, Operations, etc.)
│   ├── tools/           # Agent tools (Warehouse, Analyzer, Forecaster, etc.)
│   └── orchestrator.py  # Meta-agent for coordination
├── api/                 # FastAPI REST API
│   ├── routers/         # API endpoint routers
│   ├── websocket/       # WebSocket manager for real-time updates
│   └── main.py          # Main application
├── config/              # Configuration and agent prompts
├── dashboard/           # Streamlit dashboard
├── ingestion/           # Data ingestion pipelines
│   ├── event_validator.py
│   ├── stream_processor.py
│   └── batch_processor.py
├── models/              # Data models and recommendation engine
│   ├── schemas.py       # Pydantic models
│   └── recommender.py   # Recommendation scoring engine
└── tools/               # Development and demo tools
    └── generate_sample_data.py
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/v1/events` | Ingest events |
| GET | `/v1/recommendations` | Get recommendations |
| POST | `/v1/actions` | Execute action |
| GET | `/v1/analytics` | Query analytics |
| WS | `/v1/stream` | Real-time updates |

## Agent Types

- **Sales Agent**: Revenue forecasting, churn detection, upsell opportunities
- **Operations Agent**: Inventory optimization, supply chain alerts
- **Customer Agent**: Segmentation, sentiment analysis, personalization
- **Revenue Agent**: Anomaly detection, price optimization
- **Orchestrator**: Coordinates all agents and prioritizes insights

## Supported LLM Providers

| Provider | Models | How to Get API Key |
|----------|--------|-------------------|
| **Anthropic** | Claude 3 Opus, Sonnet, Haiku | https://console.anthropic.com |
| **OpenAI** | GPT-4, GPT-3.5 | https://platform.openai.com |
| **GLM (Zhipu AI)** | GLM-4, GLM-4-Flash, ChatGLM | https://open.bigmodel.cn |
| **Google Vertex AI** | Gemini Pro | https://console.cloud.google.com |
| **Local** | Ollama models | Run `ollama pull` locally |

## Deployment

### Quick Deploy to Zeabur (Recommended for Demo)

Deploy to Zeabur in minutes:
```bash
# 1. Push code to GitHub
git init
git add .
git commit -m "Initial commit"
gh repo create opsora --public --source=.
git push -u origin main

# 2. Deploy via Zeabur UI (see DEPLOY_ZEABUR.md)
# - Connect GitHub repository
# - Deploy API service (port 8000)
# - Deploy Dashboard service (port 8501)
# - Add ANTHROPIC_API_KEY environment variable
```

Full Zeabur deployment guide: [DEPLOY_ZEABUR.md](DEPLOY_ZEABUR.md)

### Google Cloud Deployment

```bash
# Deploy infrastructure
cd infrastructure/terraform
terraform init
terraform apply

# Deploy Cloud Functions
gcloud functions deploy ingest-event \
  --gen2 \
  --runtime=python311 \
  --source=ingestion/pubsub_ingestor \
  --trigger-topic=events-all

# Deploy API to Cloud Run
gcloud run deploy opsora-api \
  --source=api \
  --platform=managed
```

## Monitoring

- Check agent status in dashboard
- View PubSub message flow in GCP Console
- Monitor BigQuery query statistics
- Track API health at `/health`

## GLM / Zhipu AI Setup

Using GLM models? See [GLM_SETUP.md](GLM_SETUP.md) for detailed configuration guide.

## Contributing

1. Create a feature branch
2. Make your changes
3. Run tests: `pytest`
4. Submit a PR

## License

MIT

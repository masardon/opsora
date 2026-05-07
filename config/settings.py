"""
Opsora Configuration Module

Centralized configuration management with environment variable support.
"""

import os
from pathlib import Path
from typing import Literal, List

from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class LLMProvider(BaseModel):
    """LLM Provider Configuration"""

    provider: Literal["anthropic", "openai", "glm", "vertexai", "local"] = "anthropic"
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-3-opus-20240229"
    openai_api_key: str = ""
    openai_model: str = "gpt-4-turbo-preview"
    glm_api_key: str = ""
    glm_model: str = "glm-4-flash"
    glm_base_url: str = "https://open.bigmodel.cn/api/paas/v4/"
    vertexai_project: str = ""
    vertexai_location: str = "us-central1"
    vertexai_model: str = "gemini-pro"
    local_base_url: str = "http://localhost:11434"
    local_model: str = "llama2"


class GCPConfig(BaseModel):
    """Google Cloud Platform Configuration"""

    project_id: str = Field(default="", alias="GCP_PROJECT_ID")
    region: str = "us-central1"
    bigquery_dataset: str = "opsora"
    gcs_bucket: str = "opsora-data"


class PubSubConfig(BaseModel):
    """Google PubSub Configuration"""

    topic_sales: str = "events-sales"
    topic_operations: str = "events-operations"
    topic_customers: str = "events-customers"
    topic_revenue: str = "events-revenue"
    topic_all: str = "events-all"
    subscription_analytics: str = "analytics-sub"


class AgentConfig(BaseModel):
    """AI Agent Configuration"""

    max_iterations: int = 5
    timeout: int = 30
    debug: bool = False

    # Thresholds
    recommendation_confidence_threshold: float = 0.7
    action_confidence_threshold: float = 0.85

    # Scoring weights
    weight_confidence: float = 0.3
    weight_impact: float = 0.3
    weight_urgency: float = 0.25
    weight_effort: float = 0.15


class APIConfig(BaseModel):
    """API Server Configuration"""

    host: str = "0.0.0.0"
    port: int = 8000
    reload: bool = True
    workers: int = 4
    cors_origins: List[str] = ["http://localhost:8501", "http://localhost:3000"]


class DashboardConfig(BaseModel):
    """Dashboard Configuration"""

    host: str = "localhost"
    port: int = 8501
    theme: Literal["light", "dark"] = "light"


class Settings(BaseSettings):
    """Main Settings Class"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="allow",
    )

    # Environment
    environment: Literal["development", "staging", "production"] = "development"

    # Project paths
    base_dir: Path = Field(default_factory=lambda: Path(__file__).parent.parent)
    log_dir: Path = Field(default_factory=lambda: Path(__file__).parent.parent / "logs")

    # Sub-configurations
    gcp: GCPConfig = Field(default_factory=GCPConfig)
    pubsub: PubSubConfig = Field(default_factory=PubSubConfig)
    llm: LLMProvider = Field(default_factory=LLMProvider)
    agent: AgentConfig = Field(default_factory=AgentConfig)
    api: APIConfig = Field(default_factory=APIConfig)
    dashboard: DashboardConfig = Field(default_factory=DashboardConfig)

    # Logging
    log_level: str = "INFO"
    log_format: Literal["json", "text"] = "json"

    # Features
    feature_realtime_analytics: bool = True
    feature_batch_analytics: bool = True
    feature_auto_actions: bool = False
    feature_webhook_notifications: bool = True
    feature_slack_integration: bool = False

    @field_validator("log_dir")
    @classmethod
    def create_log_dir(cls, v: Path) -> Path:
        """Ensure log directory exists"""
        v.mkdir(parents=True, exist_ok=True)
        return v

    @property
    def is_development(self) -> bool:
        return self.environment == "development"

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def bigquery_location(self) -> str:
        """Get BigQuery dataset location (project.dataset)"""
        return f"{self.gcp.project_id}.{self.gcp.bigquery_dataset}"


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get settings instance (for dependency injection)"""
    return settings


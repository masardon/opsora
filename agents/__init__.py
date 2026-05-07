"""Agents Package

Agentic AI framework for business analytics and intelligence.
"""

from agents.base import (
    BaseAgent,
    Recommendation,
    AnalysisRequest,
    AnalysisResult,
    InsightType,
    ImpactLevel,
    UrgencyLevel,
    EffortLevel,
    create_llm_adapter,
    LLMAdapter,
    AnthropicAdapter,
    OpenAIAdapter,
    GLMAdapter,
    LocalLLMAdapter,
)

from agents.domain import (
    SalesAgent,
    OperationsAgent,
    CustomerAgent,
    RevenueAgent,
)

from agents.orchestrator import OrchestratorAgent

from agents.tools import (
    WarehouseTool,
    AnalyzerTool,
    ForecasterTool,
    AnomalyDetectorTool,
    NotifierTool,
)

__all__ = [
    # Base Agent Framework
    "BaseAgent",
    "Recommendation",
    "AnalysisRequest",
    "AnalysisResult",
    "InsightType",
    "ImpactLevel",
    "UrgencyLevel",
    "EffortLevel",
    "create_llm_adapter",
    "LLMAdapter",
    "AnthropicAdapter",
    "OpenAIAdapter",
    "GLMAdapter",
    "LocalLLMAdapter",

    # Domain Agents
    "SalesAgent",
    "OperationsAgent",
    "CustomerAgent",
    "RevenueAgent",

    # Orchestrator
    "OrchestratorAgent",

    # Tools
    "WarehouseTool",
    "AnalyzerTool",
    "ForecasterTool",
    "AnomalyDetectorTool",
    "NotifierTool",
]

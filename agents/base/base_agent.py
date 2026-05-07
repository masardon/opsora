"""
Base Agent Framework

Defines the abstract base class for all AI agents and the flexible LLM adapter.
"""

import json
from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass, field

from pydantic import BaseModel, Field


# =============================================================================
# DATA MODELS
# =============================================================================

class InsightType(str, Enum):
    """Types of insights/recommendations"""
    ALERT = "alert"           # Urgent, needs immediate attention
    SUGGESTION = "suggestion" # Actionable recommendation
    AUTOMATION = "automation" # Can be automatically executed
    INSIGHT = "insight"       # Informational finding


class ImpactLevel(str, Enum):
    """Impact level of recommendation"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class UrgencyLevel(str, Enum):
    """Urgency level of recommendation"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class EffortLevel(str, Enum):
    """Effort required to implement"""
    EASY = "easy"
    MODERATE = "moderate"
    COMPLEX = "complex"


@dataclass
class Recommendation:
    """A recommendation from an agent"""

    agent_id: str
    agent_type: str
    insight_type: InsightType
    summary: str
    description: str
    confidence: float  # 0.0 to 1.0
    impact: ImpactLevel
    urgency: UrgencyLevel
    effort: EffortLevel

    # Scoring
    composite_score: float = 0.0
    expected_impact_value: Optional[float] = None  # Quantified impact (e.g., revenue increase)

    # Additional context
    recommendation_id: Optional[str] = None
    rationale: str = ""
    stakeholders: List[str] = field(default_factory=list)
    metrics_affected: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    tags: Dict[str, str] = field(default_factory=dict)

    # Timestamps
    created_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None

    # Execution tracking
    status: str = "pending"  # pending, approved, rejected, completed, failed
    execution_result: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "recommendation_id": self.recommendation_id,
            "agent_id": self.agent_id,
            "agent_type": self.agent_type,
            "insight_type": self.insight_type.value,
            "summary": self.summary,
            "description": self.description,
            "confidence": self.confidence,
            "impact": self.impact.value,
            "urgency": self.urgency.value,
            "effort": self.effort.value,
            "composite_score": self.composite_score,
            "expected_impact_value": self.expected_impact_value,
            "rationale": self.rationale,
            "stakeholders": self.stakeholders,
            "metrics_affected": self.metrics_affected,
            "dependencies": self.dependencies,
            "tags": self.tags,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "status": self.status,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Recommendation":
        """Create from dictionary"""
        # Convert string enums back to enums
        data["insight_type"] = InsightType(data["insight_type"])
        data["impact"] = ImpactLevel(data["impact"])
        data["urgency"] = UrgencyLevel(data["urgency"])
        data["effort"] = EffortLevel(data["effort"])

        # Parse datetime
        if data.get("created_at"):
            data["created_at"] = datetime.fromisoformat(data["created_at"])
        if data.get("expires_at"):
            data["expires_at"] = datetime.fromisoformat(data["expires_at"])

        return cls(**data)


class AnalysisRequest(BaseModel):
    """Request for agent analysis"""
    query: str
    data_context: Dict[str, Any] = Field(default_factory=dict)
    time_period: str = "last 30 days"
    constraints: List[str] = Field(default_factory=list)
    include_forecasts: bool = False
    max_recommendations: int = 10


class AnalysisResult(BaseModel):
    """Result from agent analysis"""
    agent_id: str
    agent_type: str
    query: str
    summary: str
    key_findings: List[str]
    recommendations: List[Recommendation]
    confidence: float
    metrics_analyzed: List[str]
    analysis_timestamp: datetime = Field(default_factory=datetime.utcnow)
    raw_response: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


# =============================================================================
# LLM ADAPTER INTERFACE
# =============================================================================

class LLMAdapter(ABC):
    """Abstract base class for LLM adapters"""

    def __init__(self, model: str, **kwargs):
        self.model = model
        self.kwargs = kwargs

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        **kwargs
    ) -> str:
        """Generate text from prompt"""
        pass

    @abstractmethod
    async def generate_structured(
        self,
        prompt: str,
        schema: Dict[str, Any],
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        **kwargs
    ) -> Dict[str, Any]:
        """Generate structured output matching schema"""
        pass

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Name of the LLM provider"""
        pass


# =============================================================================
# ANTHROPIC CLAUDE ADAPTER
# =============================================================================

class AnthropicAdapter(LLMAdapter):
    """Adapter for Anthropic Claude API"""

    def __init__(self, api_key: str, model: str = "claude-3-opus-20240229", **kwargs):
        super().__init__(model, **kwargs)
        self.api_key = api_key
        self._client = None

    def _get_client(self):
        """Lazy load the client"""
        if self._client is None:
            try:
                import anthropic
                self._client = anthropic.AsyncAnthropic(api_key=self.api_key)
            except ImportError:
                raise ImportError("anthropic package is required. Install with: pip install anthropic")
        return self._client

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        **kwargs
    ) -> str:
        """Generate text using Claude"""
        client = self._get_client()

        messages = [{"role": "user", "content": prompt}]
        if system_prompt:
            kwargs["system"] = system_prompt

        response = await client.messages.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs
        )

        return response.content[0].text

    async def generate_structured(
        self,
        prompt: str,
        schema: Dict[str, Any],
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        **kwargs
    ) -> Dict[str, Any]:
        """Generate structured output using Claude"""
        import json

        # Add schema instructions to prompt
        schema_prompt = f"""
Respond with valid JSON matching this schema:
{json.dumps(schema, indent=2)}

Your response should be ONLY the JSON, no additional text.
"""

        full_prompt = f"{prompt}\n\n{schema_prompt}"
        response = await self.generate(
            full_prompt,
            system_prompt=system_prompt,
            temperature=temperature,
            **kwargs
        )

        # Parse JSON response
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            # Try to extract JSON from response
            import re
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                return json.loads(json_match.group(0))
            raise ValueError(f"Failed to parse JSON from response: {response[:200]}")

    @property
    def provider_name(self) -> str:
        return "anthropic"


# =============================================================================
# OPENAI ADAPTER
# =============================================================================

class OpenAIAdapter(LLMAdapter):
    """Adapter for OpenAI API"""

    def __init__(self, api_key: str, model: str = "gpt-4-turbo-preview", **kwargs):
        super().__init__(model, **kwargs)
        self.api_key = api_key
        self._client = None

    def _get_client(self):
        """Lazy load the client"""
        if self._client is None:
            try:
                import openai
                self._client = openai.AsyncOpenAI(api_key=self.api_key)
            except ImportError:
                raise ImportError("openai package is required. Install with: pip install openai")
        return self._client

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        **kwargs
    ) -> str:
        """Generate text using OpenAI"""
        client = self._get_client()

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        response = await client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs
        )

        return response.choices[0].message.content

    async def generate_structured(
        self,
        prompt: str,
        schema: Dict[str, Any],
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        **kwargs
    ) -> Dict[str, Any]:
        """Generate structured output using OpenAI with JSON mode"""
        import json

        client = self._get_client()

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        schema_prompt = f"""
Respond with valid JSON matching this schema:
{json.dumps(schema, indent=2)}
"""
        messages.append({"role": "user", "content": f"{prompt}\n\n{schema_prompt}"})

        response = await client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            response_format={"type": "json_object"},
            **kwargs
        )

        return json.loads(response.choices[0].message.content)

    @property
    def provider_name(self) -> str:
        return "openai"


# =============================================================================
# LOCAL LLM ADAPTER (Ollama)
# =============================================================================

class LocalLLMAdapter(LLMAdapter):
    """Adapter for local LLMs (e.g., Ollama)"""

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "llama2",
        **kwargs
    ):
        super().__init__(model, **kwargs)
        self.base_url = base_url
        self._client = None

    def _get_client(self):
        """Lazy load the client"""
        if self._client is None:
            try:
                import httpx
                self._client = httpx.AsyncClient(timeout=120.0)
            except ImportError:
                raise ImportError("httpx package is required. Install with: pip install httpx")
        return self._client

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        **kwargs
    ) -> str:
        """Generate text using local LLM"""
        client = self._get_client()

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        response = await client.post(
            f"{self.base_url}/api/chat",
            json={
                "model": self.model,
                "messages": messages,
                "stream": False,
                "options": {
                    "temperature": temperature,
                    "num_predict": max_tokens,
                }
            }
        )

        response.raise_for_status()
        data = response.json()
        return data.get("message", {}).get("content", "")

    async def generate_structured(
        self,
        prompt: str,
        schema: Dict[str, Any],
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        **kwargs
    ) -> Dict[str, Any]:
        """Generate structured output using local LLM"""
        import json

        schema_prompt = f"""
Respond with valid JSON matching this schema:
{json.dumps(schema, indent=2)}

Your response should be ONLY the JSON, no additional text.
"""

        full_prompt = f"{prompt}\n\n{schema_prompt}"
        response = await self.generate(
            full_prompt,
            system_prompt=system_prompt,
            temperature=temperature,
            **kwargs
        )

        try:
            return json.loads(response)
        except json.JSONDecodeError:
            import re
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                return json.loads(json_match.group(0))
            raise ValueError(f"Failed to parse JSON from response: {response[:200]}")

    @property
    def provider_name(self) -> str:
        return "local"


# =============================================================================
# GLM ADAPTER (Zhipu AI / ChatGLM)
# =============================================================================

class GLMAdapter(LLMAdapter):
    """Adapter for Zhipu AI GLM API (ChatGLM, GLM-4)"""

    def __init__(
        self,
        api_key: str,
        model: str = "glm-4-flash",
        base_url: str = "https://open.bigmodel.cn/api/paas/v4/",
        **kwargs
    ):
        super().__init__(model, **kwargs)
        self.api_key = api_key
        self.base_url = base_url
        self._client = None

    def _get_client(self):
        """Lazy load the client"""
        if self._client is None:
            try:
                import httpx
                self._client = httpx.AsyncClient(
                    base_url=self.base_url,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    timeout=120.0
                )
            except ImportError:
                raise ImportError("httpx package is required. Install with: pip install httpx")
        return self._client

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        **kwargs
    ) -> str:
        """Generate text using GLM API"""
        client = self._get_client()

        # Build messages
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        # Make request
        response = await client.post(
            f"chat/completions",
            json={
                "model": self.model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "top_p": kwargs.get("top_p", 0.7),
                "stream": False,
            }
        )

        response.raise_for_status()
        data = response.json()

        # Extract content from GLM response
        return data.get("choices", [{}])[0].get("message", {}).get("content", "")

    async def generate_structured(
        self,
        prompt: str,
        schema: Dict[str, Any],
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        **kwargs
    ) -> Dict[str, Any]:
        """Generate structured output using GLM API"""
        import json

        # Add JSON formatting instructions
        schema_prompt = f"""
IMPORTANT: You must respond with valid JSON only, no additional text.
Your response must match this schema:
{json.dumps(schema, indent=2)}

Example response format:
{{
  "field1": "value1",
  "field2": 123
}}
"""

        full_prompt = f"{prompt}\n\n{schema_prompt}"
        response = await self.generate(
            full_prompt,
            system_prompt=system_prompt,
            temperature=temperature,
            **kwargs
        )

        # Parse JSON response
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            # Try to extract JSON from response
            import re
            # Look for JSON object
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                try:
                    return json.loads(json_match.group(0))
                except:
                    pass

            # Look for JSON array
            array_match = re.search(r'\[[\s\S]*\]', response)
            if array_match:
                try:
                    return json.loads(array_match.group(0))
                except:
                    pass

            raise ValueError(f"Failed to parse JSON from GLM response: {response[:200]}")

    @property
    def provider_name(self) -> str:
        return "glm"


# =============================================================================
# ADAPTER FACTORY
# =============================================================================

def create_llm_adapter(provider: str, **config) -> LLMAdapter:
    """Factory function to create LLM adapter based on provider"""

    adapters = {
        "anthropic": lambda: AnthropicAdapter(
            api_key=config.get("anthropic_api_key", ""),
            model=config.get("anthropic_model", "claude-3-opus-20240229"),
        ),
        "openai": lambda: OpenAIAdapter(
            api_key=config.get("openai_api_key", ""),
            model=config.get("openai_model", "gpt-4-turbo-preview"),
        ),
        "glm": lambda: GLMAdapter(
            api_key=config.get("glm_api_key", ""),
            model=config.get("glm_model", "glm-4-flash"),
            base_url=config.get("glm_base_url", "https://open.bigmodel.cn/api/paas/v4/"),
        ),
        "local": lambda: LocalLLMAdapter(
            base_url=config.get("local_base_url", "http://localhost:11434"),
            model=config.get("local_model", "llama2"),
        ),
    }

    if provider not in adapters:
        raise ValueError(f"Unknown LLM provider: {provider}. Available: {list(adapters.keys())}")

    return adapters[provider]()


# =============================================================================
# BASE AGENT CLASS
# =============================================================================

class BaseAgent(ABC):
    """Abstract base class for all domain agents"""

    def __init__(
        self,
        agent_type: str,
        llm_adapter: Optional[LLMAdapter] = None,
        max_recommendations: int = 10,
        confidence_threshold: float = 0.7,
    ):
        self.agent_type = agent_type
        self.agent_id = f"{agent_type}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
        self.llm = llm_adapter
        self.max_recommendations = max_recommendations
        self.confidence_threshold = confidence_threshold

        # Scoring weights (default, can be overridden)
        self.weight_confidence = 0.3
        self.weight_impact = 0.3
        self.weight_urgency = 0.25
        self.weight_effort = 0.15

    @abstractmethod
    def get_system_prompt(self) -> str:
        """Get the system prompt for this agent"""
        pass

    @abstractmethod
    async def analyze_data(
        self,
        data: Dict[str, Any],
        query: str,
        context: Optional[Dict[str, Any]] = None
    ) -> AnalysisResult:
        """Analyze data and generate insights"""
        pass

    async def generate_recommendation(
        self,
        prompt: str,
        data_context: Dict[str, Any],
        **kwargs
    ) -> Recommendation:
        """Generate a single recommendation"""
        full_prompt = self._build_analysis_prompt(prompt, data_context)

        schema = {
            "type": "object",
            "properties": {
                "insight_type": {
                    "type": "string",
                    "enum": ["alert", "suggestion", "automation", "insight"]
                },
                "summary": {"type": "string"},
                "description": {"type": "string"},
                "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                "impact": {"type": "string", "enum": ["low", "medium", "high"]},
                "urgency": {"type": "string", "enum": ["low", "medium", "high", "critical"]},
                "effort": {"type": "string", "enum": ["easy", "moderate", "complex"]},
                "expected_impact_value": {"type": "number"},
                "rationale": {"type": "string"},
                "metrics_affected": {"type": "array", "items": {"type": "string"}},
                "stakeholders": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["insight_type", "summary", "description", "confidence", "impact", "urgency", "effort"]
        }

        response = await self.llm.generate_structured(
            full_prompt,
            schema=schema,
            system_prompt=self.get_system_prompt(),
        )

        # Calculate composite score
        response["composite_score"] = self._calculate_score(
            confidence=response["confidence"],
            impact=response["impact"],
            urgency=response["urgency"],
            effort=response["effort"],
        )

        return Recommendation(
            agent_id=self.agent_id,
            agent_type=self.agent_type,
            **response
        )

    def _calculate_score(
        self,
        confidence: float,
        impact: str,
        urgency: str,
        effort: str
    ) -> float:
        """Calculate composite score from components"""

        # Normalize impact (low=1, medium=2, high=3)
        impact_score = {"low": 1, "medium": 2, "high": 3}.get(impact, 2) / 3

        # Normalize urgency (low=1, medium=2, high=3, critical=4)
        urgency_score = {"low": 1, "medium": 2, "high": 3, "critical": 4}.get(urgency, 2) / 4

        # Normalize effort (easy=3, moderate=2, complex=1) - inverted
        effort_score = {"easy": 3, "moderate": 2, "complex": 1}.get(effort, 2) / 3

        # Calculate weighted composite
        composite = (
            confidence * self.weight_confidence +
            impact_score * self.weight_impact +
            urgency_score * self.weight_urgency +
            effort_score * self.weight_effort
        )

        return round(composite, 3)

    def _build_analysis_prompt(
        self,
        query: str,
        data_context: Dict[str, Any]
    ) -> str:
        """Build analysis prompt with context"""
        import json

        prompt = f"""
## Analysis Request

{query}

## Available Data

```json
{json.dumps(data_context, indent=2, default=str)}
```

## Analysis Requirements

1. Provide specific, actionable recommendations
2. Base insights on the provided data
3. Include confidence scores (0-1)
4. Quantify impact when possible
5. Consider the business context

Generate a response following the specified schema.
"""
        return prompt

    def filter_by_confidence(self, recommendations: List[Recommendation]) -> List[Recommendation]:
        """Filter recommendations by confidence threshold"""
        return [r for r in recommendations if r.confidence >= self.confidence_threshold]

    def sort_by_priority(self, recommendations: List[Recommendation]) -> List[Recommendation]:
        """Sort recommendations by composite score (descending)"""
        return sorted(recommendations, key=lambda r: r.composite_score, reverse=True)

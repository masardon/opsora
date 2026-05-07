"""Opsora Configuration Module"""

from config.settings import Settings, get_settings, settings
from config.agent_prompts import (
    get_agent_prompt,
    format_analysis_prompt,
    BASE_AGENT_SYSTEM,
    SALES_AGENT_SYSTEM,
    OPERATIONS_AGENT_SYSTEM,
    CUSTOMER_AGENT_SYSTEM,
    REVENUE_AGENT_SYSTEM,
    ORCHESTRATOR_SYSTEM,
)

__all__ = [
    "Settings",
    "get_settings",
    "settings",
    "get_agent_prompt",
    "format_analysis_prompt",
    "BASE_AGENT_SYSTEM",
    "SALES_AGENT_SYSTEM",
    "OPERATIONS_AGENT_SYSTEM",
    "CUSTOMER_AGENT_SYSTEM",
    "REVENUE_AGENT_SYSTEM",
    "ORCHESTRATOR_SYSTEM",
]

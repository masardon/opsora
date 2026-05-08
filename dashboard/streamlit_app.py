"""
Opsora Dashboard

Streamlit-based dashboard for visualizing analytics and recommendations.
"""

import asyncio
import json
import random
import sys
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

# Add app directory to Python path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

try:
    from config import settings
except ImportError:
    # Fallback if config import fails
    settings = None


# =============================================================================
# PAGE CONFIG
# =============================================================================

st.set_page_config(
    page_title="Opsora Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        margin-bottom: 1rem;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1rem;
        border-radius: 0.5rem;
        color: white;
        margin: 0.5rem 0;
    }
    .recommendation-card {
        border-left: 4px solid #667eea;
        padding: 1rem;
        margin: 0.5rem 0;
        background-color: #f8f9fa;
        border-radius: 0.25rem;
    }
    .critical { border-left-color: #dc3545; }
    .high { border-left-color: #fd7e14; }
    .medium { border-left-color: #ffc107; }
    .low { border-left-color: #28a745; }
</style>
""", unsafe_allow_html=True)


# =============================================================================
# SESSION STATE
# =============================================================================

if "page" not in st.session_state:
    st.session_state.page = "overview"

if "selected_domain" not in st.session_state:
    st.session_state.selected_domain = "all"

if "selected_recommendation" not in st.session_state:
    st.session_state.selected_recommendation = None

# AI Chat state
if "chat_messages" not in st.session_state:
    st.session_state.chat_messages = []

# Action tracking
if "actions_taken" not in st.session_state:
    st.session_state.actions_taken = []

# What-if scenarios
if "scenario_params" not in st.session_state:
    st.session_state.scenario_params = {
        "marketing_spend_change": 0,
        "price_adjustment": 0,
        "staffing_change": 0,
    }


# =============================================================================
# UTILITIES
# =============================================================================

def format_idr(amount: int) -> str:
    """Format amount as Indonesian Rupiah"""
    if amount >= 1_000_000_000:
        return f"Rp{amount/1_000_000_000:.1f}B"
    elif amount >= 1_000_000:
        return f"Rp{amount/1_000_000:.1f}M"
    else:
        return f"Rp{amount:,}".replace(",", ".")


# =============================================================================
# API CLIENT
# =============================================================================

class OpsoraAPI:
    """Simple API client for Opsora"""

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url

    def get_dashboard_overview(self) -> Dict[str, Any]:
        """Get dashboard overview - Indonesian QSR Data"""
        # Mock data for demo - Indonesian Fried Chicken QSR
        return {
            "metrics": {
                "sales": {"revenue": 458500000, "growth_rate": 12.8},  # ~$29K USD in IDR
                "operations": {"inventory_turnover": 4.8, "fulfillment_time": 18.5},
                "customers": {"active": 1856, "nps": 48},
                "revenue": {"mrr": 125000000, "arr": 1500000000},
            },
            "recommendations": {
                "total": 18,
                "critical": 3,
                "high": 6,
                "medium": 7,
                "low": 2,
            },
        }

    def get_recommendations(self, domain: str = None) -> List[Dict[str, Any]]:
        """Get recommendations - Indonesian QSR themed"""
        # Mock data - QSR business recommendations
        return [
            {
                "recommendation_id": "rec_001",
                "title": "Promote Paket Komplit 1 during off-peak hours",
                "description": "Bundle meal shows 23% higher conversion between 14:00-17:00 in Jakarta stores",
                "insight_type": "suggestion",
                "domain": "sales",
                "confidence": 0.88,
                "impact": "high",
                "urgency": "medium",
                "effort": "easy",
                "composite_score": 0.82,
                "status": "pending",
            },
            {
                "recommendation_id": "rec_002",
                "title": "Critical: Chicken stock depletion at STR012 (Surabaya)",
                "description": "Current inventory: 45 pieces, below safety stock of 100. Expected to run out in 3 hours",
                "insight_type": "alert",
                "domain": "operations",
                "confidence": 0.95,
                "impact": "high",
                "urgency": "critical",
                "effort": "easy",
                "composite_score": 0.92,
                "status": "pending",
            },
            {
                "recommendation_id": "rec_003",
                "title": "Customer satisfaction dip in GoFood channel",
                "description": "Average rating dropped from 4.7 to 4.2 in Bandung area. Check delivery times.",
                "insight_type": "alert",
                "domain": "customer",
                "confidence": 0.82,
                "impact": "medium",
                "urgency": "high",
                "effort": "moderate",
                "composite_score": 0.76,
                "status": "pending",
            },
            {
                "recommendation_id": "rec_004",
                "title": "New MILO Iced beverage trending well",
                "description": "32% of orders include MILO Iced. Consider promoting as add-on with chicken combos.",
                "insight_type": "insight",
                "domain": "sales",
                "confidence": 0.91,
                "impact": "medium",
                "urgency": "low",
                "effort": "easy",
                "composite_score": 0.68,
                "status": "pending",
            },
            {
                "recommendation_id": "rec_005",
                "title": "Peak hour congestion at STR001 (Jakarta Mall)",
                "description": "Average prep time: 28min vs target 15min. Consider adding staff during 11:00-13:00.",
                "insight_type": "suggestion",
                "domain": "operations",
                "confidence": 0.86,
                "impact": "high",
                "urgency": "high",
                "effort": "moderate",
                "composite_score": 0.80,
                "status": "pending",
            },
        ]

    def get_metrics(self, domain: str, time_period: str = "last_30_days") -> Dict[str, Any]:
        """Get metrics for a domain - Indonesian QSR themed"""
        # Mock data - Indonesian Fried Chicken QSR
        dates = pd.date_range(end=datetime.now(), periods=30, freq="D")

        if domain == "sales":
            # Revenue in IDR (millions)
            base = 14000000  # ~14M IDR per day
            values = [base + i * 50000 + (i % 7) * 1500000 for i in range(30)]
        elif domain == "operations":
            # Inventory turnover
            values = [4.5 + i * 0.01 + (i % 7) * 0.3 for i in range(30)]
        elif domain == "customers":
            # Daily active customers
            values = [550 + i * 2 + (i % 7) * 80 for i in range(30)]
        else:
            # Revenue in IDR
            values = [14000000 + i * 50000 + (i % 7) * 1500000 for i in range(30)]

        return {
            "dates": dates.strftime("%Y-%m-%d").tolist(),
            "values": values,
        }

    def ask_ai(self, question: str, context: Dict = None) -> Dict[str, Any]:
        """Ask AI assistant a question about the business"""

        # Simulate AI analysis based on question keywords
        question_lower = question.lower()

        # Sales questions
        if any(word in question_lower for word in ["revenue", "sales", "income", "earning"]):
            if "forecast" in question_lower or "predict" in question_lower:
                return {
                    "answer": ("Based on current trends (12.8% growth rate) and seasonal patterns, "
                             "I forecast revenue of Rp520M next month (+13% from current). "
                             "Key drivers: Ramadhan season approaching, GoFood orders up 18%."),
                    "insights": [
                        {"metric": "Revenue Forecast", "value": "Rp520M", "change": "+13%"},
                        {"metric": "Confidence", "value": "87%", "change": ""},
                        {"metric": "Key Driver", "value": "Seasonal demand", "change": ""},
                    ],
                    "recommendations": [
                        "Increase chicken inventory by 25% for Ramadhan",
                        "Prepare special combo packages for iftar",
                        "Schedule additional staff for peak hours (17:00-19:00)",
                    ],
                }
            else:
                return {
                    "answer": (f"Current revenue is Rp458.5M with a 12.8% growth rate. "
                             "Top performing stores are in Jakarta (32% of revenue) and Surabaya (18%). "
                             "GoFood channel contributes 25% of total orders."),
                    "insights": [
                        {"metric": "Current Revenue", "value": "Rp458.5M", "change": "+12.8%"},
                        {"metric": "Top Store", "value": "Jakarta Mall #1", "change": "32% share"},
                        {"metric": "Best Channel", "value": "GoFood", "change": "25% orders"},
                    ],
                    "recommendations": [
                        "Expand GoFood presence in underperforming cities",
                        "Replicate Jakarta Mall #1 practices to other locations",
                    ],
                }

        # Inventory questions
        elif any(word in question_lower for word in ["inventory", "stock", "supply", "chicken"]):
            return {
                "answer": ("3 stores are below safety stock levels. STR012 (Surabaya) is critical with 45 pieces. "
                         "Average inventory turnover is 4.8x. Recommend urgent restock for 5 locations."),
                "insights": [
                    {"metric": "Critical Stockouts", "value": "3 stores", "change": ""},
                    {"metric": "Inventory Turnover", "value": "4.8x", "change": "+0.3"},
                    {"metric": "Urgent Restock", "value": "5 locations", "change": ""},
                ],
                "recommendations": [
                    "Emergency delivery to STR012 within 3 hours",
                    "Review safety stock levels for high-traffic stores",
                    "Consider supplier diversification for Surabaya region",
                ],
            }

        # Customer questions
        elif any(word in question_lower for word in ["customer", "nps", "satisfaction", "rating"]):
            return {
                "answer": ("NPS is 48, above industry average of 42. However, GoFood ratings dropped to 4.2 in Bandung. "
                         "1,856 active customers, with 23% being heavy users (5+ orders/week)."),
                "insights": [
                    {"metric": "NPS Score", "value": "48", "change": "+6 vs industry"},
                    {"metric": "Active Customers", "value": "1,856", "change": "+12%"},
                    {"metric": "Heavy Users", "value": "23%", "change": "+3%"},
                ],
                "recommendations": [
                    "Investigate Bandung GoFood delivery delays",
                    "Launch loyalty program for heavy users",
                    "Send satisfaction survey to customers with ratings < 4",
                ],
            }

        # Performance questions
        elif any(word in question_lower for word in ["perform", "best", "worst", "top", "bottom"]):
            return {
                "answer": ("STR001 (Jakarta Mall #1) is top performer with Rp82M monthly revenue. "
                         "STR015 (Denpasar) needs attention - lowest sales at Rp12M. "
                         "Paket Komplit 1 is best-selling item (34% of orders)."),
                "insights": [
                    {"metric": "Best Store", "value": "STR001 Jakarta", "change": "Rp82M/mo"},
                    {"metric": "Worst Store", "value": "STR015 Denpasar", "change": "Rp12M/mo"},
                    {"metric": "Best Item", "value": "Paket Komplit 1", "change": "34% orders"},
                ],
                "recommendations": [
                    "Conduct store audit at STR015 - investigate low foot traffic",
                    "A/B test Jakarta Mall promotions in Denpasar",
                    "Feature Paket Komplit 1 more prominently on app",
                ],
            }

        # Default response
        return {
            "answer": ("I can help you analyze your QSR business. Try asking about: "
                     "revenue forecast, inventory levels, customer satisfaction, or store performance."),
            "insights": [],
            "recommendations": [],
        }

    def calculate_what_if(self, params: Dict[str, float]) -> Dict[str, Any]:
        """Calculate what-if scenarios"""

        base_revenue = 458500000
        base_customers = 1856
        base_orders = 8420

        # Calculate impacts
        marketing_impact = params["marketing_spend_change"] * 0.8  # 80% efficiency
        price_impact = -params["price_adjustment"] * 0.5  # Price elasticity
        volume_change = marketing_impact + price_impact + (params["staffing_change"] * 0.3)

        projected_revenue = base_revenue * (1 + volume_change)
        projected_orders = base_orders * (1 + volume_change * 0.9)
        projected_customers = base_customers * (1 + marketing_impact * 0.6)

        return {
            "base": {
                "revenue": base_revenue,
                "orders": base_orders,
                "customers": base_customers,
            },
            "projected": {
                "revenue": projected_revenue,
                "orders": projected_orders,
                "customers": projected_customers,
            },
            "change": {
                "revenue_percent": volume_change * 100,
                "orders_percent": volume_change * 90,
                "customers_percent": marketing_impact * 60,
            },
            "recommendations": self._generate_what_if_recommendations(params),
        }

    def _generate_what_if_recommendations(self, params: Dict) -> List[str]:
        """Generate recommendations based on what-if parameters"""
        recs = []

        if params["marketing_spend_change"] > 0.2:
            recs.append("Monitor ROAS closely - high marketing spend requires >3x return")
        elif params["marketing_spend_change"] < -0.1:
            recs.append("Warning: Reducing marketing may impact customer acquisition")

        if params["price_adjustment"] > 0.1:
            recs.append("Price increase >10% may reduce order frequency")
        elif params["price_adjustment"] < -0.1:
            recs.append("Promotional pricing can boost volume but monitor margins")

        if params["staffing_change"] > 0.2:
            recs.append("Additional staffing improves service speed - target peak hours")
        elif params["staffing_change"] < -0.1:
            recs.append("Reducing staff may increase prep times - monitor customer satisfaction")

        if not recs:
            recs.append("Current parameters are within optimal range")

        return recs


api = OpsoraAPI()


# =============================================================================
# SIDEBAR
# =============================================================================

def render_sidebar():
    """Render the sidebar"""

    st.sidebar.title("Opsora Dashboard")
    st.sidebar.markdown("---")

    # Page navigation
    pages = {
        "overview": "📊 Overview",
        "ai_assistant": "🤖 AI Assistant",
        "what_if": "🔮 What-If Analysis",
        "recommendations": "💡 Recommendations",
        "actions": "✅ Action Center",
        "analytics": "📈 Analytics",
        "agents": "🔧 Agents",
    }

    selected_page = st.sidebar.radio(
        "Navigation",
        list(pages.values()),
        format_func=lambda x: x,
    )

    # Map back to page key
    for key, value in pages.items():
        if value == selected_page:
            st.session_state.page = key
            break

    st.sidebar.markdown("---")

    # Domain filter
    st.sidebar.subheader("Filter by Domain")
    domains = ["all", "sales", "operations", "customer", "revenue"]
    selected_domain = st.sidebar.selectbox(
        "Domain",
        domains,
        index=domains.index(st.session_state.selected_domain),
    )
    st.session_state.selected_domain = selected_domain

    st.sidebar.markdown("---")

    # Quick stats
    st.sidebar.subheader("Quick Stats")

    overview = api.get_dashboard_overview()
    rec_counts = overview.get("recommendations", {})

    st.sidebar.metric("Total Recommendations", rec_counts.get("total", 0))
    st.sidebar.metric("Critical Alerts", rec_counts.get("critical", 0),
                     delta_color="inverse")

    # Time period
    st.sidebar.markdown("---")
    st.sidebar.subheader("Time Period")
    time_period = st.sidebar.selectbox(
        "Period",
        ["last_24h", "last_7d", "last_30d", "last_90d"],
        index=2,
    )

    return time_period


# =============================================================================
# OVERVIEW PAGE
# =============================================================================

def render_overview_page(time_period: str):
    """Render overview page"""

    st.markdown('<h1 class="main-header">Business Overview</h1>', unsafe_allow_html=True)

    # Get overview data
    overview = api.get_dashboard_overview()
    metrics = overview.get("metrics", {})

    # Key metrics
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        sales_rev = metrics["sales"]["revenue"]
        sales_growth = metrics["sales"]["growth_rate"]
        st.metric("Revenue", format_idr(sales_rev), f"+{sales_growth}%")

    with col2:
        ops_turnover = metrics["operations"]["inventory_turnover"]
        st.metric("Inventory Turnover", f"{ops_turnover:.1f}x")

    with col3:
        cust_active = metrics["customers"]["active"]
        st.metric("Active Customers", f"{cust_active:,}")

    with col4:
        rev_mrr = metrics["revenue"]["mrr"]
        st.metric("MRR", format_idr(rev_mrr))

    st.markdown("---")

    # Charts row
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Revenue Trend")
        sales_metrics = api.get_metrics("sales", time_period)
        # Convert to millions for display
        values_millions = [v / 1_000_000 for v in sales_metrics["values"]]
        fig = px.line(
            x=sales_metrics["dates"],
            y=values_millions,
            title="Revenue Over Time (IDR Millions)",
            labels={"x": "Date", "y": "Revenue (Millions IDR)"},
        )
        fig.update_layout(yaxis_tickformat=',.0f')
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("Recommendations by Urgency")
        rec_counts = overview.get("recommendations", {})
        fig = go.Figure(data=[
            go.Bar(
                x=["Critical", "High", "Medium", "Low"],
                y=[
                    rec_counts.get("critical", 0),
                    rec_counts.get("high", 0),
                    rec_counts.get("medium", 0),
                    rec_counts.get("low", 0),
                ],
                marker_color=["#dc3545", "#fd7e14", "#ffc107", "#28a745"],
            )
        ])
        fig.update_layout(title="Recommendations by Urgency")
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")

    # Recent recommendations
    st.subheader("Recent Recommendations")

    recommendations = api.get_recommendations()
    for rec in recommendations[:5]:
        urgency_class = rec["urgency"]
        icon = {
            "critical": "🚨",
            "high": "⚠️",
            "medium": "📌",
            "low": "💡",
        }.get(urgency_class, "📌")

        st.markdown(
            f'<div class="recommendation-card {urgency_class}">'
            f'{icon} **{rec["title"]}**<br>'
            f'<small>{rec["description"]}</small><br>'
            f'<small>Confidence: {rec["confidence"]:.0%} | '
            f'Domain: {rec["domain"].title()}</small>'
            f'</div>',
            unsafe_allow_html=True
        )


# =============================================================================
# RECOMMENDATIONS PAGE
# =============================================================================

def render_recommendations_page(time_period: str):
    """Render recommendations page"""

    st.markdown('<h1 class="main-header">Recommendations</h1>', unsafe_allow_html=True)

    # Filters
    col1, col2, col3 = st.columns(3)

    with col1:
        urgency_filter = st.multiselect(
            "Urgency",
            ["critical", "high", "medium", "low"],
            default=["critical", "high", "medium"],
        )

    with col2:
        domain_filter = st.multiselect(
            "Domain",
            ["sales", "operations", "customer", "revenue"],
            default=["sales", "operations", "customer", "revenue"],
        )

    with col3:
        status_filter = st.multiselect(
            "Status",
            ["pending", "approved", "in_progress", "completed"],
            default=["pending"],
        )

    st.markdown("---")

    # Get recommendations
    recommendations = api.get_recommendations()

    # Apply filters
    filtered = [
        r for r in recommendations
        if (not urgency_filter or r["urgency"] in urgency_filter) and
        (not domain_filter or r["domain"] in domain_filter) and
        (not status_filter or r["status"] in status_filter)
    ]

    # Sort by urgency
    urgency_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    filtered.sort(key=lambda x: urgency_order.get(x["urgency"], 4))

    # Display recommendations
    for rec in filtered:
        with st.expander(f"{rec['title']}", expanded=(rec["urgency"] == "critical")):
            col1, col2 = st.columns([3, 1])

            with col1:
                st.markdown(f"**{rec['description']}**")

                # Tags
                tags = f"""
                <span style='background: #e9ecef; padding: 2px 8px; border-radius: 4px; margin-right: 4px;'>
                {rec['domain'].title()}
                </span>
                <span style='background: #e9ecef; padding: 2px 8px; border-radius: 4px; margin-right: 4px;'>
                {rec['insight_type']}
                </span>
                """
                st.markdown(tags, unsafe_allow_html=True)

                st.markdown(f"*Confidence:* {rec['confidence']:.0%}")
                st.markdown(f"*Impact:* {rec['impact'].title()}")
                st.markdown(f"*Effort:* {rec['effort'].title()}")

            with col2:
                # Action buttons
                if st.button("Approve", key=f"approve_{rec['recommendation_id']}"):
                    st.success("Approved!")

                if st.button("Dismiss", key=f"dismiss_{rec['recommendation_id']}"):
                    st.info("Dismissed")


# =============================================================================
# ANALYTICS PAGE
# =============================================================================

def render_analytics_page(time_period: str):
    """Render analytics page"""

    st.markdown('<h1 class="main-header">Analytics</h1>', unsafe_allow_html=True)

    # Domain selector
    col1, col2 = st.columns([1, 3])

    with col1:
        selected_domain = st.selectbox(
            "Select Domain",
            ["sales", "operations", "customer", "revenue"],
            index=0,
        )

    with col2:
        metric_selector = st.selectbox(
            "Select Metric",
            {
                "sales": ["revenue", "average_order_value", "conversion_rate"],
                "operations": ["inventory_turnover", "fulfillment_time", "on_time_delivery"],
                "customer": ["active_customers", "nps_score", "retention_rate"],
                "revenue": ["mrr", "arr", "net_revenue_retention"],
            }.get(selected_domain, []),
        )

    st.markdown("---")

    # Get metrics
    metrics_data = api.get_metrics(selected_domain, time_period)

    # Main chart
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=metrics_data["dates"],
        y=metrics_data["values"],
        mode="lines+markers",
        name=metric_selector,
        line=dict(color="#1f77b4", width=2),
    ))

    fig.update_layout(
        title=f"{metric_selector.replace('_', ' ').title()} - {selected_domain.title()}",
        xaxis_title="Date",
        yaxis_title=metric_selector.replace('_', ' ').title(),
        hovermode="x unified",
    )

    st.plotly_chart(fig, use_container_width=True)

    # Statistics
    col1, col2, col3, col4 = st.columns(4)

    values = metrics_data["values"]

    with col1:
        st.metric("Latest", f"{values[-1]:,.2f}")

    with col2:
        st.metric("Average", f"{sum(values) / len(values):,.2f}")

    with col3:
        st.metric("Min", f"{min(values):,.2f}")

    with col4:
        st.metric("Max", f"{max(values):,.2f}")


# =============================================================================
# AGENTS PAGE
# =============================================================================

def render_agents_page(time_period: str):
    """Render agents status page"""

    st.markdown('<h1 class="main-header">AI Agents</h1>', unsafe_allow_html=True)

    # Agent status cards
    agents_info = {
        "sales": {
            "name": "Sales Agent",
            "status": "active",
            "last_analysis": "2 hours ago",
            "recommendations": 5,
            "description": "Analyzes menu item performance, combo meal conversions, and channel sales (app, GoFood, GrabFood)",
        },
        "operations": {
            "name": "Operations Agent",
            "status": "active",
            "last_analysis": "45 minutes ago",
            "recommendations": 6,
            "description": "Monitors inventory levels across 50 stores, tracks preparation times, and alerts on stockouts",
        },
        "customer": {
            "name": "Customer Agent",
            "status": "active",
            "last_analysis": "1 hour ago",
            "recommendations": 4,
            "description": "Analyzes customer satisfaction by channel, segments customers, and tracks ordering patterns",
        },
        "revenue": {
            "name": "Revenue Agent",
            "status": "active",
            "last_analysis": "30 minutes ago",
            "recommendations": 3,
            "description": "Tracks revenue across Indonesian cities, analyzes peak hour patterns, and optimizes pricing",
        },
    }

    for agent_id, info in agents_info.items():
        with st.expander(f"🤖 {info['name']}", expanded=True):
            col1, col2, col3 = st.columns(3)

            with col1:
                status_color = "🟢" if info["status"] == "active" else "🔴"
                st.markdown(f"{status_color} **Status:** {info['status'].title()}")

            with col2:
                st.markdown(f"📊 **Recommendations:** {info['recommendations']}")

            with col3:
                st.markdown(f"⏱️ **Last Analysis:** {info['last_analysis']}")

            st.markdown(f"*{info['description']}*")


# =============================================================================
# AI ASSISTANT PAGE
# =============================================================================

def render_ai_assistant_page():
    """Render AI chat assistant page"""

    st.markdown('<h1 class="main-header">🤖 AI Business Assistant</h1>', unsafe_allow_html=True)

    # Intro message
    if not st.session_state.chat_messages:
        st.info("💡 Ask me anything about your QSR business! Try questions like:\n\n"
                "• \"What's my revenue forecast?\"\n"
                "• \"Which stores are performing best?\"\n"
                "• \"Do I have any inventory issues?\"\n"
                "• \"How's customer satisfaction?\"\n"
                "• \"What are my top selling items?\"")

    # Chat container
    chat_container = st.container()

    with chat_container:
        # Display chat history
        for message in st.session_state.chat_messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

                # Show insights if available
                if message.get("insights"):
                    st.markdown("**Key Insights:**")
                    cols = st.columns(len(message["insights"]))
                    for i, insight in enumerate(message["insights"]):
                        with cols[i]:
                            st.metric(insight["metric"], insight["value"], insight.get("change", ""))

                # Show recommendations if available
                if message.get("recommendations"):
                    st.markdown("**Recommendations:**")
                    for rec in message["recommendations"]:
                        st.markdown(f"• {rec}")

    # Chat input
    if prompt := st.chat_input("Ask about your business..."):
        # Add user message
        st.session_state.chat_messages.append({"role": "user", "content": prompt})

        # Get AI response
        with st.spinner("🤖 Analyzing..."):
            response = api.ask_ai(prompt)

        # Add assistant response
        assistant_message = {
            "role": "assistant",
            "content": response["answer"],
            "insights": response.get("insights", []),
            "recommendations": response.get("recommendations", []),
        }
        st.session_state.chat_messages.append(assistant_message)

        # Rerender to show new messages
        st.rerun()

    # Clear chat button
    if st.session_state.chat_messages:
        if st.button("🗑️ Clear Chat History", key="clear_chat"):
            st.session_state.chat_messages = []
            st.rerun()


# =============================================================================
# WHAT-IF ANALYSIS PAGE
# =============================================================================

def render_what_if_page():
    """Render what-if scenario planning page"""

    st.markdown('<h1 class="main-header">🔮 What-If Analysis</h1>', unsafe_allow_html=True)

    st.markdown("""
    **Scenario Planning:** Adjust parameters to see projected impact on your business.
    The AI will calculate expected outcomes and provide recommendations.
    """)

    st.markdown("---")

    # Parameter controls
    col1, col2, col3 = st.columns(3)

    with col1:
        marketing_change = st.slider(
            "📣 Marketing Spend Change",
            min_value=-50,
            max_value=100,
            value=0,
            step=5,
            format="%d%%",
            help="Increase or decrease marketing budget"
        )

    with col2:
        price_change = st.slider(
            "💰 Price Adjustment",
            min_value=-20,
            max_value=30,
            value=0,
            step=1,
            format="%d%%",
            help="Increase or decrease menu prices"
        )

    with col3:
        staffing_change = st.slider(
            "👥 Staffing Change",
            min_value=-30,
            max_value=50,
            value=0,
            step=5,
            format="%d%%",
            help="Increase or decrease staff levels"
        )

    # Calculate scenario
    params = {
        "marketing_spend_change": marketing_change / 100,
        "price_adjustment": price_change / 100,
        "staffing_change": staffing_change / 100,
    }

    scenario = api.calculate_what_if(params)

    st.markdown("---")
    st.subheader("📊 Projected Impact")

    # Display projections
    col1, col2, col3 = st.columns(3)

    with col1:
        delta_color = "normal" if scenario["change"]["revenue_percent"] >= 0 else "inverse"
        st.metric(
            "Monthly Revenue",
            format_idr(int(scenario["projected"]["revenue"])),
            f"{scenario['change']['revenue_percent']:+.1f}%",
            delta_color=delta_color
        )
        st.caption(f"Current: {format_idr(scenario['base']['revenue'])}")

    with col2:
        delta_color = "normal" if scenario["change"]["orders_percent"] >= 0 else "inverse"
        st.metric(
            "Monthly Orders",
            f"{int(scenario['projected']['orders']):,}",
            f"{scenario['change']['orders_percent']:+.1f}%",
            delta_color=delta_color
        )
        st.caption(f"Current: {int(scenario['base']['orders']):,}")

    with col3:
        delta_color = "normal" if scenario["change"]["customers_percent"] >= 0 else "inverse"
        st.metric(
            "Active Customers",
            f"{int(scenario['projected']['customers']):,}",
            f"{scenario['change']['customers_percent']:+.1f}%",
            delta_color=delta_color
        )
        st.caption(f"Current: {int(scenario['base']['customers']):,}")

    st.markdown("---")

    # AI Recommendations
    st.subheader("🤖 AI Recommendations")
    for rec in scenario["recommendations"]:
        st.markdown(f"• {rec}")

    # Visual comparison
    st.subheader("📈 Visual Comparison")

    fig = go.Figure()

    # Add current bars
    fig.add_trace(go.Bar(
        name="Current",
        x=["Revenue (M)", "Orders (K)", "Customers (K)"],
        y=[
            scenario["base"]["revenue"] / 1_000_000,
            scenario["base"]["orders"] / 1000,
            scenario["base"]["customers"] / 1000,
        ],
        marker_color="#6c757d"
    ))

    # Add projected bars
    fig.add_trace(go.Bar(
        name="Projected",
        x=["Revenue (M)", "Orders (K)", "Customers (K)"],
        y=[
            scenario["projected"]["revenue"] / 1_000_000,
            scenario["projected"]["orders"] / 1000,
            scenario["projected"]["customers"] / 1000,
        ],
        marker_color=["#28a745" if scenario["change"]["revenue_percent"] >= 0 else "#dc3545"][0]
    ))

    fig.update_layout(
        barmode="group",
        yaxis_title="Amount",
        hovermode="x unified",
    )

    st.plotly_chart(fig, use_container_width=True)


# =============================================================================
# ACTION CENTER PAGE
# =============================================================================

def render_action_center_page():
    """Render action center page with interactive recommendations"""

    st.markdown('<h1 class="main-header">✅ Action Center</h1>', unsafe_allow_html=True)

    # Stats row
    col1, col2, col3, col4 = st.columns(4)

    recommendations = api.get_recommendations()

    pending = len([r for r in recommendations if r["status"] == "pending"])
    approved = len([r for r in recommendations if r["status"] == "approved"])
    completed = len([r for r in recommendations if r["status"] == "completed"])
    dismissed = len(st.session_state.actions_taken)

    with col1:
        st.metric("⏳ Pending", pending)

    with col2:
        st.metric("✅ Approved", approved)

    with col3:
        st.metric("🎯 Completed", completed)

    with col4:
        st.metric("❌ Dismissed", dismissed)

    st.markdown("---")

    # Tabs for different views
    tab1, tab2, tab3 = st.tabs(["📋 All Recommendations", "✅ Approved Actions", "📊 Impact Summary"])

    with tab1:
        st.subheader("AI Recommendations")

        for rec in recommendations:
            # Determine if action was taken
            action_taken = next(
                (a for a in st.session_state.actions_taken if a["id"] == rec["recommendation_id"]),
                None
            )

            if action_taken:
                if action_taken["action"] == "dismissed":
                    continue  # Skip dismissed recommendations
                rec["status"] = action_taken["action"]

            # Status badge
            status_badge = {
                "pending": "🟡",
                "approved": "🟢",
                "completed": "✅",
                "dismissed": "🔴",
            }.get(rec["status"], "🟡")

            with st.expander(f"{status_badge} {rec['title']}", expanded=(rec["urgency"] == "critical")):
                col1, col2 = st.columns([3, 1])

                with col1:
                    st.markdown(f"**{rec['description']}**")

                    # Tags
                    st.markdown(f"""
                    **Domain:** {rec['domain'].title()} |
                    **Confidence:** {rec['confidence']:.0%} |
                    **Impact:** {rec['impact'].title()} |
                    **Effort:** {rec['effort'].title()}
                    """)

                    # Show simulated impact if approved
                    if action_taken and action_taken["action"] == "approved":
                        st.success(f"✅ **Approved** - Expected impact: {action_taken.get('impact', 'Review implementation')}")

                with col2:
                    # Action buttons (only show if pending)
                    if rec["status"] == "pending":
                        col_a, col_b = st.columns(2)

                        with col_a:
                            if st.button("✅ Approve", key=f"approve_{rec['recommendation_id']}", use_container_width=True):
                                # Simulate approval with impact
                                impact = _simulate_impact(rec)

                                st.session_state.actions_taken.append({
                                    "id": rec["recommendation_id"],
                                    "action": "approved",
                                    "title": rec["title"],
                                    "impact": impact,
                                    "timestamp": datetime.now().isoformat(),
                                })

                                st.success(f"Approved! {impact}")
                                st.rerun()

                        with col_b:
                            if st.button("❌ Dismiss", key=f"dismiss_{rec['recommendation_id']}", use_container_width=True):
                                st.session_state.actions_taken.append({
                                    "id": rec["recommendation_id"],
                                    "action": "dismissed",
                                    "title": rec["title"],
                                    "timestamp": datetime.now().isoformat(),
                                })

                                st.info("Recommendation dismissed")
                                st.rerun()

    with tab2:
        st.subheader("Approved Actions Track")

        approved_actions = [a for a in st.session_state.actions_taken if a["action"] == "approved"]

        if not approved_actions:
            st.info("No actions approved yet. Go to 'All Recommendations' to approve AI suggestions.")
        else:
            for action in approved_actions:
                with st.container():
                    col1, col2, col3 = st.columns([3, 1, 1])

                    with col1:
                        st.markdown(f"**{action['title']}**")
                        st.markdown(f"*Expected Impact:* {action.get('impact', 'TBD')}")

                    with col2:
                        st.markdown(f"**Status:** In Progress")

                    with col3:
                        if st.button("✅ Complete", key=f"complete_{action['id']}", use_container_width=True):
                            action["action"] = "completed"
                            action["completed_at"] = datetime.now().isoformat()
                            st.success("Marked as complete!")
                            st.rerun()

                    st.markdown("---")

    with tab3:
        st.subheader("Impact Summary")

        if not st.session_state.actions_taken:
            st.info("No actions taken yet. Approve recommendations to see projected impact.")
        else:
            # Calculate simulated impact
            approved_count = len([a for a in st.session_state.actions_taken if a["action"] in ["approved", "completed"]])

            # Simulated metrics
            col1, col2, col3, col4 = st.columns(4)

            with col1:
                st.metric("Actions Approved", approved_count)

            with col2:
                revenue_lift = approved_count * 0.05  # 5% average impact
                st.metric("Revenue Lift", f"+{revenue_lift:.1%}")

            with col3:
                efficiency_gain = approved_count * 0.08
                st.metric("Efficiency Gain", f"+{efficiency_gain:.1%}")

            with col4:
                risk_reduction = approved_count * 2
                st.metric("Risks Addressed", f"{risk_reduction}")


def _simulate_impact(recommendation: Dict) -> str:
    """Simulate the impact of implementing a recommendation"""

    if recommendation["domain"] == "sales":
        impacts = [
            "+5-8% revenue increase in target stores",
            "3-5% conversion rate improvement",
            "Rp15-25M additional monthly revenue",
        ]
    elif recommendation["domain"] == "operations":
        impacts = [
            "15-20% reduction in prep time",
            "Eliminate stockout risks for 48 hours",
            "Rp5-10M saved in waste reduction",
        ]
    elif recommendation["domain"] == "customer":
        impacts = [
            "NPS improvement of 3-5 points",
            "10-15% reduction in complaints",
            "5-8% improvement in retention",
        ]
    else:
        impacts = [
            "Implementation in 2-3 business days",
            "Monitor for 2 weeks for full impact",
            "Review metrics after implementation",
        ]

    return random.choice(impacts)


# =============================================================================
# MAIN APP
# =============================================================================

def main():
    """Main app function"""

    # Render sidebar
    time_period = render_sidebar()

    # Render selected page
    if st.session_state.page == "overview":
        render_overview_page(time_period)
    elif st.session_state.page == "ai_assistant":
        render_ai_assistant_page()
    elif st.session_state.page == "what_if":
        render_what_if_page()
    elif st.session_state.page == "recommendations":
        render_recommendations_page(time_period)
    elif st.session_state.page == "actions":
        render_action_center_page()
    elif st.session_state.page == "analytics":
        render_analytics_page(time_period)
    elif st.session_state.page == "agents":
        render_agents_page(time_period)


if __name__ == "__main__":
    main()

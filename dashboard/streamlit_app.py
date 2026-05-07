"""
Opsora Dashboard

Streamlit-based dashboard for visualizing analytics and recommendations.
"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

from config import settings


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


# =============================================================================
# API CLIENT
# =============================================================================

class OpsoraAPI:
    """Simple API client for Opsora"""

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url

    def get_dashboard_overview(self) -> Dict[str, Any]:
        """Get dashboard overview"""
        # Mock data for demo
        return {
            "metrics": {
                "sales": {"revenue": 125000, "growth_rate": 15.3},
                "operations": {"inventory_turnover": 4.2, "fulfillment_time": 24.5},
                "customers": {"active": 2340, "nps": 42},
                "revenue": {"mrr": 85000, "arr": 1020000},
            },
            "recommendations": {
                "total": 23,
                "critical": 2,
                "high": 5,
                "medium": 12,
                "low": 4,
            },
        }

    def get_recommendations(self, domain: str = None) -> List[Dict[str, Any]]:
        """Get recommendations"""
        # Mock data
        return [
            {
                "recommendation_id": "rec_001",
                "title": "Increase marketing spend for high-value segment",
                "description": "Target the top 20% of customers by value",
                "insight_type": "suggestion",
                "domain": "sales",
                "confidence": 0.85,
                "impact": "high",
                "urgency": "medium",
                "effort": "moderate",
                "composite_score": 0.78,
                "status": "pending",
            },
            {
                "recommendation_id": "rec_002",
                "title": "Critical: Stockout risk for product SKU-1234",
                "description": "Inventory levels below safety stock",
                "insight_type": "alert",
                "domain": "operations",
                "confidence": 0.92,
                "impact": "high",
                "urgency": "critical",
                "effort": "easy",
                "composite_score": 0.88,
                "status": "pending",
            },
            {
                "recommendation_id": "rec_003",
                "title": "Customer sentiment trending negative in support channel",
                "description": "NPS dropped 8 points in last week",
                "insight_type": "alert",
                "domain": "customer",
                "confidence": 0.78,
                "impact": "medium",
                "urgency": "high",
                "effort": "moderate",
                "composite_score": 0.72,
                "status": "pending",
            },
        ]

    def get_metrics(self, domain: str, time_period: str = "last_30_days") -> Dict[str, Any]:
        """Get metrics for a domain"""
        # Mock data
        dates = pd.date_range(end=datetime.now(), periods=30, freq="D")

        if domain == "sales":
            values = [45000 + i * 500 + (i % 7) * 1000 for i in range(30)]
        elif domain == "operations":
            values = [4.0 + i * 0.01 + (i % 7) * 0.2 for i in range(30)]
        elif domain == "customers":
            values = [40 + i * 0.2 + (i % 7) * 2 for i in range(30)]
        else:
            values = [80000 + i * 500 + (i % 7) * 2000 for i in range(30)]

        return {
            "dates": dates.strftime("%Y-%m-%d").tolist(),
            "values": values,
        }


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
        "recommendations": "💡 Recommendations",
        "analytics": "📈 Analytics",
        "agents": "🤖 Agents",
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
        st.metric("Revenue", f"${sales_rev:,.0f}", f"{sales_growth}%")

    with col2:
        ops_turnover = metrics["operations"]["inventory_turnover"]
        st.metric("Inventory Turnover", f"{ops_turnover:.1f}x")

    with col3:
        cust_active = metrics["customers"]["active"]
        st.metric("Active Customers", f"{cust_active:,}")

    with col4:
        rev_mrr = metrics["revenue"]["mrr"]
        st.metric("MRR", f"${rev_mrr:,}")

    st.markdown("---")

    # Charts row
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Revenue Trend")
        sales_metrics = api.get_metrics("sales", time_period)
        fig = px.line(
            x=sales_metrics["dates"],
            y=sales_metrics["values"],
            title="Revenue Over Time",
            labels={"x": "Date", "y": "Revenue"},
        )
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
            "recommendations": 8,
            "description": "Analyzes sales performance, revenue trends, and customer behavior",
        },
        "operations": {
            "name": "Operations Agent",
            "status": "active",
            "last_analysis": "4 hours ago",
            "recommendations": 6,
            "description": "Analyzes operational efficiency, inventory, and supply chain",
        },
        "customer": {
            "name": "Customer Agent",
            "status": "active",
            "last_analysis": "1 hour ago",
            "recommendations": 5,
            "description": "Analyzes customer behavior, sentiment, and engagement",
        },
        "revenue": {
            "name": "Revenue Agent",
            "status": "active",
            "last_analysis": "3 hours ago",
            "recommendations": 4,
            "description": "Analyzes revenue streams, pricing, and financial performance",
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
# MAIN APP
# =============================================================================

def main():
    """Main app function"""

    # Render sidebar
    time_period = render_sidebar()

    # Render selected page
    if st.session_state.page == "overview":
        render_overview_page(time_period)
    elif st.session_state.page == "recommendations":
        render_recommendations_page(time_period)
    elif st.session_state.page == "analytics":
        render_analytics_page(time_period)
    elif st.session_state.page == "agents":
        render_agents_page(time_period)


if __name__ == "__main__":
    main()

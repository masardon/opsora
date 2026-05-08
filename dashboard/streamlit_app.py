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
        """Ask AI assistant a question about the business - Comprehensive QSR Analytics"""

        question_lower = question.lower()

        # =============================================================================
        # SALES & REVENUE ANALYTICS
        # =============================================================================

        if any(word in question_lower for word in ["revenue", "sales", "income", "earning", "growth"]):

            # Revenue forecast with multiple scenarios
            if any(word in question_lower for word in ["forecast", "predict", "projection", "future", "next month", "next quarter"]):

                # Check for specific forecast type
                if "worst" in question_lower or "pessimistic" in question_lower:
                    return {
                        "answer": ("📉 **Pessimistic Forecast**: Supply chain disruptions and competitor promotions "
                                 "could reduce growth to 4-6%. Projected revenue: Rp476M- Rp485M next month. "
                                 "Key risks: Chicken price increase (+15%), new competitor in Bandung."),
                        "insights": [
                            {"metric": "Pessimistic Revenue", "value": "Rp476M", "change": "+4%"},
                            {"metric": "Confidence", "value": "65%", "change": ""},
                            {"metric": "Key Risk", "value": "Competition", "change": ""},
                        ],
                        "recommendations": [
                            "Secure alternative chicken suppliers as backup",
                            "Prepare counter-promotional strategy",
                            "Build cash reserves for 6 months of operations",
                        ],
                    }

                elif "best" in question_lower or "optimistic" in question_lower:
                    return {
                        "answer": ("📈 **Optimistic Forecast**: With viral marketing and Ramadhan season, "
                                 "growth could reach 18-22%. Projected revenue: Rp540M - Rp560M next month. "
                                 "Key opportunities: Holiday bundles, corporate catering."),
                        "insights": [
                            {"metric": "Optimistic Revenue", "value": "Rp560M", "change": "+22%"},
                            {"metric": "Confidence", "value": "72%", "change": ""},
                            {"metric": "Key Opportunity", "value": "Seasonal", "change": ""},
                        ],
                        "recommendations": [
                            "Launch Ramadhan special bundles 2 weeks early",
                            "Partner with 5-10 local offices for catering",
                            "Increase inventory buffer to 30%",
                        ],
                    }

                else:  # Base case
                    return {
                        "answer": ("📊 **Revenue Forecast**: Based on 12.8% CAGR and seasonal factors, "
                                 "I project **Rp520M next month** (+13.4% MoM). Breakdown by channel: "
                                 "App (42%), GoFood (26%), GrabFood (23%), In-store (9%). "
                                 "\n\n**Key drivers:** Ramadhan season (+8%), viral MILO Iced (+3%), price optimization (+2.4%). "
                                 "**Key risks:** Chicken supplier constraints, 2 new competitors in East Java."),
                        "insights": [
                            {"metric": "Base Forecast", "value": "Rp520M", "change": "+13.4%"},
                            {"metric": "Confidence", "value": "87%", "change": ""},
                            {"metric": "Seasonality", "value": "Ramadhan", "change": "+8%"},
                            {"metric": "Viral Item Lift", "value": "MILO Iced", "change": "+3%"},
                        ],
                        "recommendations": [
                            "Increase chicken inventory by 25% for Ramadhan demand",
                            "Prep 500 extra MILO Iced daily before peak hours",
                            "Monitor competitor pricing in Surabaya market",
                            "Schedule staff 2 weeks before Ramadhan starts",
                        ],
                    }

            # Channel analysis
            elif any(word in question_lower for word in ["channel", "grabfood", "gofood", "delivery", "app"]):
                return {
                    "answer": ("**Channel Performance Analysis:**\n\n"
                             "| Channel | Orders | Revenue | Avg Order | Growth |\n"
                             "|---------|--------|---------|-----------|--------|\n"
                             "| GoFood  | 2,188  | Rp115M  | Rp52,500  | +18%   |\n"
                             "| App     | 3,536  | Rp192M  | Rp54,300  | +15%   |\n"
                             "| GrabFood| 1,935  | Rp98M   | Rp50,600  | +22%   |\n"
                             "| In-store| 761    | Rp53M   | Rp69,600  | -3%    |\n\n"
                             "**Insights:** GrabFood growing fastest (+22%) due to new promo integration. "
                             "In-store declining as dine-in culture shifts post-pandemic. "
                             "App has highest AOV due to combo upselling (42% attach rate)."),
                    "insights": [
                        {"metric": "Best Growth", "value": "GrabFood", "change": "+22%"},
                        {"metric": "Highest AOV", "value": "App", "change": "Rp54,300"},
                        {"metric": "Market Share", "value": "App", "change": "42%"},
                    ],
                    "recommendations": [
                        "Negotiate better commission with GrabFood (currently 18%)",
                        "Replicate GrabFood promo structure on GoFood",
                        "Add in-store kiosks to convert dine-in to takeaway",
                        "A/B test combo bundling on delivery apps",
                    ],
                }

            # Product mix analysis
            elif any(word in question_lower for word in ["product", "menu", "item", "selling", "popular", "best sell"]):
                return {
                    "answer": ("**Menu Performance Matrix (Star vs Dog Analysis):**\n\n"
                             "⭐ **STARS** (High volume, High margin): Paket Komplit 1, Ayam Potong 9, MILO Iced\n"
                             "🐴 **DOGS** (Low volume, Low margin): Coleslaw, Bread & Butter\n"
                             "❓ **PUZZLES** (High volume, Low margin): Ayam Potong 3, Fries\n"
                             "💎 **PLOWS** (Low volume, High margin): Party Bucket 20, Winger Bucket 7\n\n"
                             "**Optimization Opportunity:** Promoting Party Bucket could add Rp8.5M weekly revenue "
                             "with minimal incremental cost. Low-performing sides (Coleslaw) consume prep time "
                             "for 2.3% of revenue - consider removing or bundling."),
                    "insights": [
                        {"metric": "Best Volume", "value": "Paket Komplit 1", "change": "34% orders"},
                        {"metric": "Best Margin", "value": "Party Bucket 20", "change": "42% GM"},
                        {"metric": "Removal Candidate", "value": "Coleslaw", "change": "2.3% rev"},
                    ],
                    "recommendations": [
                        "Feature Party Bucket 20 in app carousel (target: 15% orders)",
                        "Bundle low-margin sides (coleslaw + bread) with combos",
                        "Discontinue standalone coleslaw to free up prep capacity",
                        "Create 'Family Feast' promo for Party Bucket + 2 drinks",
                    ],
                }

            # Price sensitivity analysis
            elif any(word in question_lower for word in ["price", "pricing", "margin", "profit", "cost"]):
                return {
                    "answer": ("**Pricing & Margin Analysis:**\n\n"
                             "Current blended margin: **32.5%** (down from 34.2% last quarter)\n"
                             "**Margin compression drivers:** Chicken cost (+15%), delivery app commissions (avg 22%), "
                             "promotional discounts (8% of orders)\n\n"
                             "**Price elasticity testing:** 5% price increase on Ayam Potong 3 reduced volume by 8% "
                             "(elasticity: -1.6). MILO Iced shows inelastic behavior (10% price increase = 3% volume drop).\n\n"
                             "**Optimization potential:** Dynamic pricing during off-peak hours could add Rp12M/month."),
                    "insights": [
                        {"metric": "Current Margin", "value": "32.5%", "change": "-1.7pp"},
                        {"metric": "Cost Pressure", "value": "Chicken", "change": "+15%"},
                        {"metric": "Inelastic Item", "value": "MILO Iced", "change": "elasticity -0.3"},
                    ],
                    "recommendations": [
                        "Increase MILO Iced price by 8% (minimal volume impact expected)",
                        "Implement off-peak discounts (14:00-17:00) instead of blanket promos",
                        "Negotiate volume discounts with chicken supplier (commit to 6-month contract)",
                        "Test subscription bundle (10 meals/month at 15% discount) to lock in customers",
                    ],
                }

            else:  # General revenue
                return {
                    "answer": (f"Current revenue is **Rp458.5M** with a **12.8% growth rate**. "
                             f"Top performers: Jakarta Mall #1 (Rp82M/mo), Surabaya Central (Rp58M/mo). "
                             f"GoFood channel: 26% of orders. Best-selling: Paket Komplit 1 (34% of all orders)."),
                    "insights": [
                        {"metric": "Current Revenue", "value": "Rp458.5M", "change": "+12.8%"},
                        {"metric": "Top Store", "value": "Jakarta Mall #1", "change": "Rp82M/mo"},
                        {"metric": "Best Channel", "value": "GoFood", "change": "26% orders"},
                    ],
                    "recommendations": [
                        "Expand GoFood presence in Makassar (untapped market)",
                        "Replicate Jakarta Mall #1 practices to low-performing stores",
                        "Increase Paket Komplit 1 inventory buffer to 20%",
                    ],
                }

        # =============================================================================
        # INVENTORY & OPERATIONS ANALYTICS
        # =============================================================================

        elif any(word in question_lower for word in ["inventory", "stock", "supply", "chicken", "waste", "spoil"]):

            # Supplier performance
            if any(word in question_lower for word in ["supplier", "vendor", "source", "procurement"]):
                return {
                    "answer": ("**Supplier Performance Scorecard:**\n\n"
                             "| Supplier | On-Time | Quality | Cost | Issues |\n"
                             "|----------|---------|---------|------|--------|\n"
                             "| PT Ayam Jaya | 94% | 4.7/5 | Base | 3 late deliveries |\n"
                             "| CV Ungkep Mas | 78% | 4.2/5 | -8% | 12 quality issues |\n"
                             "| Fresh Chicken Co | 89% | 4.5/5 | +5% | Inconsistent sizing |\n\n"
                             "**Recommendation:** Diversify to 3 suppliers to reduce risk. Current single-source "
                             "dependency creates vulnerability - 1 supplier delay affects 15 stores."),
                    "insights": [
                        {"metric": "Best Supplier", "value": "PT Ayam Jaya", "change": "94% on-time"},
                        {"metric": "Risk Level", "value": "HIGH", "change": "Single source"},
                        {"metric": "Cost Saving", "value": "Potential 8%", "change": "if switch"},
                    ],
                    "recommendations": [
                        "Onboard 2nd supplier by end of month (target: CV Ungkep with quality penalty clause)",
                        "Negotiate volume discount with PT Ayam Jaya for 12-month commitment",
                        "Build 3-day inventory buffer at Jakarta distribution center",
                    ],
                }

            # Waste analysis
            elif any(word in question_lower for word in ["waste", "spoil", "loss", "throw", "excess"]):
                return {
                    "answer": ("**Food Waste Analysis:**\n\n"
                             "Total waste: **Rp18.5M/month** (4% of COGS)\n\n"
                             "**Breakdown:**\n"
                             "• Chicken spoilage: Rp8.2M (44%) - typically expires at 3 stores\n"
                             "• Prep errors: Rp5.1M (28%) - wrong cuts, over-portioning\n"
                             "• Sides过期: Rp3.8M (20%) - coleslaw, mashed potatoes\n"
                             "• Burnt/undercooked: Rp1.4M (8%)\n\n"
                             "**Hotspots:** STR012 (Surabaya) - Rp2.8M/mo, STR003 (Bandung) - Rp2.1M/mo"),
                    "insights": [
                        {"metric": "Monthly Waste", "value": "Rp18.5M", "change": "4% COGS"},
                        {"metric": "Worst Store", "value": "STR012 Surabaya", "change": "Rp2.8M/mo"},
                        {"metric": "Savings Potential", "value": "Rp12M/mo", "change": "if fixed"},
                    ],
                    "recommendations": [
                        "Implement dynamic prep based on hourly demand forecasting (saves ~Rp4M/mo)",
                        "Train staff on portion control at STR012 and STR003",
                        "Reduce sides batch size by 30% during off-peak hours",
                        "Donate near-expire items to local food banks (tax deduction + CSR)",
                    ],
                }

            # Prep time optimization
            elif any(word in question_lower for word in ["prep", "preparation", "speed", "time", "fast", "slow", "efficiency"]):
                return {
                    "answer": ("**Preparation Time Analysis:**\n\n"
                             "**Current Stats:**\n"
                             "• Average prep time: 18.5 min (target: 15 min)\n"
                             "• Peak hour (11-13, 18-20): 26 min (critical issue)\n"
                             "• Off-peak (14-17): 12 min (within target)\n\n"
                             "**Bottleneck Analysis:**\n"
                             "1. Frying station: 62% of prep time (only 2 fryers)\n"
                             "2. Assembly station: 24% of prep time\n"
                             "3. Packaging: 14% of prep time\n\n"
                             "**Opportunity:** Adding 1 fryer at high-volume stores could reduce prep time by 35% during peak.",
                    "insights": [
                        {"metric": "Avg Prep Time", "value": "18.5 min", "change": "+23% vs target"},
                        {"metric": "Peak Time", "value": "26 min", "change": "+73%"},
                        {"metric": "Bottleneck", "value": "Frying Station", "change": "62%"},
                    ],
                    "recommendations": [
                        "Install 3rd fryer at top 10 stores (ROI: 2.3 months)",
                        "Pre-prep popular items during off-peak (chicken cutting, sides)",
                        "Cross-train staff on assembly station",
                        "Implement KDS (Kitchen Display System) to prioritize orders",
                    ],
                }

            else:  # General inventory
                return {
                    "answer": ("**Inventory Status:** 3 stores below safety stock. **CRITICAL:** STR012 (Surabaya) "
                             "has 45 pieces vs 100 safety stock - runs out in ~3 hours. Average turnover: 4.8x. "
                             "5 locations need restock within 6 hours. Supplier delay risk: MEDIUM (2 late this month)."),
                    "insights": [
                        {"metric": "Critical Stockouts", "value": "3 stores", "change": ""},
                        {"metric": "Inventory Turnover", "value": "4.8x", "change": "+0.3"},
                        {"metric": "Urgent Restock", "value": "5 locations", "change": ""},
                    ],
                    "recommendations": [
                        "Emergency delivery to STR012 within 3 hours",
                        "Review safety stock levels (currently 4hrs - recommend 6hrs)",
                        "Consider emergency supplier for East Java region",
                    ],
                }

        # =============================================================================
        # CUSTOMER & MARKETING ANALYTICS
        # =============================================================================

        elif any(word in question_lower for word in ["customer", "nps", "satisfaction", "rating", "review", "churn", "retention", "loyal"]):

            # Customer segmentation
            if any(word in question_lower for word in ["segment", "persona", "profile", "type of customer"]):
                return {
                    "answer": ("**Customer Segmentation Analysis:**\n\n"
                             "| Segment | Size | Avg Spend | Freq | LTV | Churn Risk |\n"
                             "|---------|------|-----------|------|-----|------------|\n"
                             "| Heavy Users | 23% | Rp285K | 5.2/wk | Rp3.8M | Low |\n"
                             "| Regular | 48% | Rp142K | 2.1/wk | Rp1.1M | Medium |\n"
                             "| Occasional | 22% | Rp68K | 0.8/mo | Rp280K | High |\n"
                             "| Lapsed | 7% | Rp0 | 0 | Rp420K | N/A |\n\n"
                             "**Insight:** Heavy Users (23% of customers) drive 58% of revenue. "
                             "Occasional segment (22%) has high upside - targeted win-back could add Rp32M/month."),
                    "insights": [
                        {"metric": "High-Value Segment", "value": "Heavy Users", "change": "23% size"},
                        {"metric": "Revenue Concentration", "value": "58%", "change": "from 23%"},
                        {"metric": "Win-back Opportunity", "value": "Rp32M/mo", "change": "potential"},
                    ],
                    "recommendations": [
                        "Launch VIP program for Heavy Users (exclusive offers, priority support)",
                        "Target Occasional segment with 'Come Back' promo (30% off next order)",
                        "Reactivation campaign for Lapsed (email: 'We miss you! Free MILO Iced')",
                        "Create referral bonus (Heavy Users get Rp10K for each friend)",
                    ],
                }

            # Churn analysis
            elif any(word in question_lower for word in ["churn", "leaving", "leave", "lost customer", "retention"]):
                return {
                    "answer": ("**Churn Analysis:**\n\n"
                             "**Monthly Churn Rate:** 8.3% (up from 6.1% last quarter)\n"
                             "**At-risk customers:** 234 (12.6% of active base)\n\n"
                             "**Top Churn Drivers:**\n"
                             "1. Price sensitivity: 34% (switched to competitors with promos)\n"
                             "2. Delivery delays: 28% (GoFood ratings issue in Bandung)\n"
                             "3. Quality inconsistency: 18% (undercooked/overcooked complaints)\n"
                             "4. App usability: 12% (checkout friction)\n"
                             "5. Location: 8% (moved, no store nearby)\n\n"
                             "**Highest churn:** Makassar (12.1%), Bandung (11.8%) | Lowest: Jakarta (5.2%)"),
                    "insights": [
                        {"metric": "Churn Rate", "value": "8.3%", "change": "+2.2pp"},
                        {"metric": "At-Risk Customers", "value": "234", "change": "12.6%"},
                        {"metric": "Highest Churn City", "value": "Makassar", "change": "12.1%"},
                    ],
                    "recommendations": [
                        "Launch price-match guarantee for Heavy Users (retention tool)",
                        "Fix Bandung GoFood delivery issues (partner with local riders)",
                        "Implement kitchen quality checks (photos before packaging)",
                        "Simplify app checkout (reduce from 5 steps to 3 steps)",
                        "Target Makassar with retention promo (buy 5 get 1 free)",
                    ],
                }

            # Campaign effectiveness
            elif any(word in question_lower for word in ["campaign", "promo", "promotion", "marketing", "advertisement", "ads"]):
                return {
                    "answer": ("**Marketing Campaign Performance:**\n\n"
                             "**Active Campaigns (Last 30 Days):**\n\n"
                             "| Campaign | Spend | Orders | ROAS | Conv. Rate |\n"
                             "|----------|-------|--------|------|------------|\n"
                             "| GoFood Promo | Rp8.5M | 1,245 | 3.2x | 8.5% |\n"
                             "| GrabFood Mega Sale | Rp12M | 1,428 | 2.4x | 6.2% |\n"
                             "| App Push: MILO Iced | Rp1.2M | 856 | 8.6x | 12.3% |\n"
                             "| Instagram Ads | Rp5M | 312 | 0.9x | 2.1% ❌ |\n\n"
                             "**Winner:** App Push notifications have 8.6x ROAS. **Loser:** Instagram ads not converting.\n\n"
                             "**Audience insights:** Best response from 25-34 age group (68% of conversions). "
                             "Weak response from 45+ (only 8% of conversions)."),
                    "insights": [
                        {"metric": "Best ROAS", "value": "App Push", "change": "8.6x"},
                        {"metric": "Worst ROAS", "value": "Instagram Ads", "change": "0.9x"},
                        {"metric": "Best Audience", "value": "25-34", "change": "68% conv"},
                    ],
                    "recommendations": [
                        "Pause Instagram ads (realloc Rp5M to app push and GoFood)",
                        "Increase app push frequency to 2x/week (currently 1x)",
                        "A/B test promo codes (15% off vs buy 1 get 1)",
                        "Target 25-34 demographic with video content on TikTok (untapped)",
                        "Create referral program (leverages high ROAS channel)",
                    ],
                }

            # CLV analysis
            elif any(word in question_lower for word in ["lifetime value", "ltv", "clv", "customer value", "worth"]):
                return {
                    "answer": ("**Customer Lifetime Value Analysis:**\n\n"
                             "**Average CLV:** Rp1,420,000 (based on 18-month active period)\n\n"
                             "**CLV by Segment:**\n"
                             "• Heavy Users: Rp3.8M (2.7x average)\n"
                             "• Regular: Rp1.1M (0.8x average)\n"
                             "• Occasional: Rp280K (0.2x average)\n\n"
                             "**CLV vs CAC:**\n"
                             "• Average CAC (Cost Acquisition Customer): Rp185,000\n"
                             "• LTV:CAC Ratio: 7.7x (healthy benchmark is 3x+)\n\n"
                             "**Payback Period:** 4.2 months (customer becomes profitable after 5th order)\n\n"
                             "**Opportunity:** Increasing Heavy User share from 23% to 30% would increase average CLV by 16%."),
                    "insights": [
                        {"metric": "Avg CLV", "value": "Rp1.42M", "change": ""},
                        {"metric": "LTV:CAC Ratio", "value": "7.7x", "change": "excellent"},
                        {"metric": "Payback Period", "value": "4.2 months", "change": ""},
                    ],
                    "recommendations": [
                        "Increase acquisition budget by 50% (still profitable at 7.7x ratio)",
                        "Focus acquisition on channels that bring Heavy Users (app, referrals)",
                        "Reduce promo spend on low-CLV segments (occasional customers)",
                        "Implement subscription model (guarantees 12-month retention)",
                    ],
                }

            else:  # General customer
                return {
                    "answer": ("**Customer Metrics:** NPS is **48** (above industry avg 42). Active customers: **1,856** (+12%). "
                             "Heavy users (5+ orders/week): 23%. GoFood ratings dropped to **4.2 in Bandung** (investigating). "
                             "Churn rate: 8.3% (up from 6.1%)."),
                    "insights": [
                        {"metric": "NPS Score", "value": "48", "change": "+6 vs industry"},
                        {"metric": "Active Customers", "value": "1,856", "change": "+12%"},
                        {"metric": "Heavy Users", "value": "23%", "change": "+3%"},
                        {"metric": "Churn Rate", "value": "8.3%", "change": "+2.2pp"},
                    ],
                    "recommendations": [
                        "Investigate Bandung GoFood delivery delays immediately",
                        "Launch loyalty program for Heavy Users (priority tier)",
                        "Implement win-back campaign for churned customers",
                    ],
                }

        # =============================================================================
        # FINANCIAL & STRATEGY ANALYTICS
        # =============================================================================

        elif any(word in question_lower for word in ["profit", "margin", "financial", "p&l", "income statement", "cash flow", "break even", "roi", "expansion", "new store", "open"]):

            # Expansion planning
            if any(word in question_lower for word in ["expansion", "new store", "open", "location", "where should", "next store"]):
                return {
                    "answer": ("**Store Expansion Analysis:**\n\n"
                             "**Top 5 Locations for New Stores (Scored by market potential):**\n\n"
                             "1. **Bekasi** (Score: 92/100)\n"
                             "   • Population: 3.2M, Median age: 29\n"
                             "   • Competitors: 2 QSR chains\n"
                             "   • Est. monthly revenue: Rp68-75M\n"
                             "   • Investment: Rp450M, Payback: 18 months\n\n"
                             "2. **Tangerang** (Score: 88/100)\n"
                             "   • High income area, low competition\n"
                             "   • Est. monthly revenue: Rp62-70M\n"
                             "   • Investment: Rp420M, Payback: 20 months\n\n"
                             "3. **Yogyakarta** (Score: 85/100)\n"
                             "   • Student market, high meal frequency\n"
                             "   • Est. monthly revenue: Rp55-62M\n"
                             "   • Investment: Rp380M, Payback: 16 months\n\n"
                             "**Not Recommended:** Palembang (saturation), Manado (low demand), Pekanbaru (logistics)."),
                    "insights": [
                        {"metric": "Best Location", "value": "Bekasi", "change": "92/100 score"},
                        {"metric": "Fastest Payback", "value": "Yogyakarta", "change": "16 months"},
                        {"metric": "Est. Revenue", "value": "Rp62-75M", "change": "per store"},
                    ],
                    "recommendations": [
                        "Prioritize Bekasi for Q3 2024 opening (highest potential)",
                        "Secure locations in Tangerang and Yogyakarta for Q4 2024",
                        "Avoid Palembang - market saturated with 12+ competitors",
                        "Consider smaller format (300 sqm) for Yogyakarta student market",
                    ],
                }

            # Break-even analysis
            elif any(word in question_lower for word in ["break even", "break-even", "profitability", "when profit"]):
                return {
                    "answer": ("**Break-Even Analysis:**\n\n"
                             "**Store-Level Economics:**\n"
                             "• Monthly fixed costs: Rp42.5M (rent, staff, utilities)\n"
                             "• Variable cost per order: 62.5% (COGS + delivery commission)\n"
                             "• Average order value: Rp52,800\n"
                             "• Contribution margin: Rp19,800/order\n\n"
                             "**Break-Even Point:** 2,147 orders/month (72 orders/day)\n\n"
                             "**Current Performance:**\n"
                             "• All stores profitable except STR015 (Denpasar) - Rp3.2M loss\n"
                             "• Average store: 4,200 orders/month (195% of break-even)\n"
                             "• Best store (Jakarta Mall #1): 7,100 orders/month (330% of break-even)\n\n"
                             "**New store break-even timeline:** Month 4 reach daily run-rate, Month 7 cumulative break-even."),
                    "insights": [
                        {"metric": "Break-Even Orders", "value": "2,147/mo", "change": "72/day"},
                        {"metric": "Avg Store", "value": "4,200/mo", "change": "195% BE"},
                        {"metric": "Unprofitable Stores", "value": "1", "change": "STR015"},
                    ],
                    "recommendations": [
                        "Close or relocate STR015 Denpasar (below break-even for 6 months)",
                        "Reduce fixed costs by renegotiating rents (target: Rp38M/store)",
                        "Increase AOV by 5% (adds Rp1K margin/order → break-even at 68 orders/day)",
                        "New store target: reach break-even by month 6 (conservative plan)",
                    ],
                }

            # P&L summary
            elif any(word in question_lower for word in ["p&l", "income statement", "financial summary", "bottom line"]):
                return {
                    "answer": ("**Monthly P&L Summary (Company Level):**\n\n"
                             "**Revenue:** Rp458,500,000\n"
                             "**COGS:** Rp309,475,000 (67.5%)\n"
                             "**Gross Profit:** Rp149,025,000 (32.5% margin)\n\n"
                             "**Operating Expenses:**\n"
                             "• Rent: Rp85,000,000 (18.5%)\n"
                             "• Labor: Rp72,500,000 (15.8%)\n"
                             "• Marketing: Rp15,500,000 (3.4%)\n"
                             "• Utilities/Other: Rp12,200,000 (2.7%)\n"
                             "**Total Opex:** Rp185,200,000 (40.4%)\n\n"
                             "**EBITDA:** (Rp36,175,000) **(-7.9% margin)** ⚠️\n\n"
                             "**Note:** Currently unprofitable due to expansion phase. Target: positive EBITDA by Q4 2024."),
                    "insights": [
                        {"metric": "Gross Margin", "value": "32.5%", "change": "-1.7pp"},
                        {"metric": "EBITDA", "value": "(Rp36.2M)", "change": "-7.9%"},
                        {"metric": "Largest Opex", "value": "Rent", "change": "18.5%"},
                    ],
                    "recommendations": [
                        "Reduce rent expense to 15% of revenue (renegotiate 3 leases)",
                        "Optimize labor scheduling (reduce overtime by 30%)",
                        "Pause expansion until positive EBITDA achieved",
                        "Increase prices by 3-5% to improve gross margin to 35%",
                    ],
                }

            else:  # General financial
                return {
                    "answer": ("**Financial Metrics:** Gross margin: **32.5%** (down 1.7pp due to chicken cost increase). "
                             "Currently at break-even at store level, company EBITDA negative due to expansion investment. "
                             "Target: positive cash flow by Q4 2024."),
                    "insights": [
                        {"metric": "Gross Margin", "value": "32.5%", "change": "-1.7pp"},
                        {"metric": "EBITDA Margin", "value": "-7.9%", "change": "investment phase"},
                    ],
                    "recommendations": [
                        "Focus on same-store sales growth vs new locations",
                        "Improve margin through price optimization on inelastic items",
                    ],
                }

        # =============================================================================
        # OPERATIONAL EXCELLENCE
        # =============================================================================

        elif any(word in question_lower for word in ["peak hour", "busy", "rush", "labor", "staff", "employee", "shift", "schedule", "delivery performance", "late"]):

            # Peak hour analysis
            if any(word in question_lower for word in ["peak hour", "busy time", "rush", "when busy"]):
                return {
                    "answer": ("**Peak Hour Analysis:**\n\n"
                             "**Primary Peaks:**\n"
                             "• Lunch: 11:00-13:00 (32% of daily orders)\n"
                             "• Dinner: 18:00-20:00 (38% of daily orders)\n\n"
                             "**Secondary Peaks:**\n"
                             "• Morning: 09:00-10:00 (8% of daily orders)\n"
                             "• Late Night: 21:00-22:00 (6% of daily orders)\n\n"
                             "**Current Staffing:**\n"
                             "• Peak: 4 staff (avg prep time: 26 min - CRITICAL)\n"
                             "• Off-peak: 2 staff (avg prep time: 12 min - GOOD)\n\n"
                             "**Recommendation:** Add 1 staff during lunch peak (11:00-14:00) and dinner peak (18:00-21:00). "
                             "Cost: Rp8M/month → Savings: Rp12M/month in reduced errors + faster service = **ROI 150%**"),
                    "insights": [
                        {"metric": "Busiest Hour", "value": "19:00-20:00", "change": "22% orders"},
                        {"metric": "Peak Prep Time", "value": "26 min", "change": "+73%"},
                        {"metric": "Off-Peek Prep", "value": "12 min", "change": "within target"},
                    ],
                    "recommendations": [
                        "Add 1 staff member during peak hours (ROI: 150%)",
                        "Implement shift-specific prep schedules",
                        "Use part-time staff for peaks (students, 4-hour shifts)",
                    ],
                }

            # Delivery performance
            elif any(word in question_lower for word in ["delivery", "late", "on time", "delivery time"]):
                return {
                    "answer": ("**Delivery Performance Analysis:**\n\n"
                             "**Average Delivery Time:** 34 minutes (target: 30 min)\n\n"
                             "**By Channel:**\n"
                             "| Channel | Avg Time | On-Time % | Late % | Issues |\n"
                             "|---------|-----------|-----------|---------|--------|\n"
                             "| GoFood | 31 min | 89% | 11% | Bandung delays |\n"
                             "| GrabFood | 29 min | 93% | 7% | Good |\n"
                             "| App | 38 min | 81% | 19% | Rider shortage |\n\n"
                             "**Late Delivery Hotspots:**\n"
                             "• Bandung (all channels): +8 min vs average\n"
                             "• Surabaya (GoFood only): +12 min vs average\n"
                             "• Makassar (all channels): +10 min vs average\n\n"
                             "**Impact:** Late orders have 4.2x higher cancellation rate and 0.8 point lower rating."),
                    "insights": [
                        {"metric": "Avg Delivery Time", "value": "34 min", "change": "+4 min"},
                        {"metric": "On-Time Rate", "value": "87%", "change": "-3pp"},
                        {"metric": "Worst City", "value": "Bandung", "change": "+8 min"},
                    ],
                    "recommendations": [
                        "Partner exclusively with GrabFood in Bandung (skip GoFood for now)",
                        "Hire dedicated riders for Surabaya (cost: +Rp2M, saves Rp6M in refunds)",
                        "Offer time-based promos (order before 11:30, get 15% off)",
                        "Extend prep time承诺 by 5 min in app (set expectations correctly)",
                    ],
                }

            # Staff optimization
            elif any(word in question_lower for word in ["labor", "staff", "employee", "shift", "schedule", "overstaff", "understaff"]):
                return {
                    "answer": ("**Labor Optimization Analysis:**\n\n"
                             "**Current Labor Metrics:**\n"
                             "• Total staff: 184 (FTE equivalent)\n"
                             "• Labor cost: Rp72.5M/month (15.8% of revenue)\n"
                             "• Target: 12-14% of revenue\n\n"
                             "**Overstaffed:** 3 stores (surplus 6 FTE, cost: Rp8.4M/month)\n"
                             "**Understaffed:** 7 stores (deficit 12 FTE, losing orders)\n\n"
                             "**Shift Optimization:**\n"
                             "Converting 8-hour shifts to 4-hour split shifts saves Rp5.2M/month while maintaining coverage.\n\n"
                             "**Staff Retention:** Current annual turnover: 68% (industry: 85%). Top performers: "
                             "Jakarta stores (42% turnover), High churn: Makassar (94% turnover)."),
                    "insights": [
                        {"metric": "Labor % Revenue", "value": "15.8%", "change": "+1.8pp"},
                        {"metric": "Overstaff Cost", "value": "Rp8.4M/mo", "change": "3 stores"},
                        {"metric": "Turnover Rate", "value": "68%", "change": "-17pp vs ind"},
                    ],
                    "recommendations": [
                        "Redistribute 6 FTE from overstaffed to underperforming stores",
                        "Implement split shifts (4-hour blocks) for better peak coverage",
                        "Increase Makassar wages by 10% to reduce turnover (saves training cost)",
                        "Cross-train staff (reduce idle time by 25%)",
                    ],
                }

            else:
                return {
                    "answer": ("Please specify: 'peak hour analysis', 'delivery performance', or 'staff optimization'."),
                    "insights": [],
                    "recommendations": [],
                }

        # =============================================================================
        # COMPETITIVE INTELLIGENCE
        # =============================================================================

        elif any(word in question_lower for word in ["competitor", "competition", "market share", "vs", "versus", "compare"]):
            return {
                "answer": ("**Competitive Intelligence Report:**\n\n"
                          "**Market Share (Jakarta QSR Fried Chicken):**\n"
                          "| Player | Market Share | Strength | Weakness |\n"
                          "|--------|--------------|----------|----------|\n"
                          "| Market Leader | 34% | Brand recognition, 200+ stores | Higher prices |\n"
                          "| Us (You) | 8% | Fast delivery, app experience | Limited stores |\n"
                          "| Competitor B | 6% | Low prices | Quality issues |\n"
                          "| Others | 52% | Fragmented | Varying |\n\n"
                          "**Competitive Advantages:**\n"
                          "✅ Best delivery speed (avg 31 min vs 38 min industry)\n"
                          "✅ Highest app ratings (4.7 vs 4.3 avg)\n"
                          "✅ Most popular combo (Paket Komplit 1)\n\n"
                          "**Competitive Gaps:**\n"
                          "❌ Store count: 50 vs 200+ (leader)\n"
                          "❌ Brand awareness: 23% vs 78% (leader)\n"
                          "❌ Pricing: 8% above average (margin vs volume strategy)\n\n"
                          "**Recommended Strategy:** Focus on quality + speed (don't compete on price). "
                          "Expand to 100 stores in next 18 months to reach scale."),
                "insights": [
                    {"metric": "Market Share", "value": "8%", "change": "#3 player"},
                    {"metric": "Competitive Edge", "value": "Delivery Speed", "change": "31 min"},
                    {"metric": "Gap", "value": "Store Count", "change": "50 vs 200"},
                ],
                "recommendations": [
                    "Maintain premium pricing (compete on quality, not price)",
                    "Accelerate store expansion to 100 locations (economies of scale)",
                    "Leverage app advantage (invest in features, not physical stores)",
                    "Target competitor's weak markets (Makassar, Palembang)",
                ],
            }

        # =============================================================================
        # MENU ENGINEERING
        # =============================================================================

        elif any(word in question_lower for word in ["menu engineering", "menu mix", "star dog", "plow", "puzzle", "menu optimization"]):
            return {
                "answer": ("**Menu Engineering Matrix:**\n\n"
                          "```\n"
                          "High Margin\n"
                          "    ▲\n"
                          "  ⭐ | PL     | STAR   |\n"
                          "    |------------------→\n "    |        |        |\n"
                          "    |------------------|\n"
                          "    | DOG    | PUZZLE |\n"
                          "    ▼\n"
                          "Low Margin    Low Volume      High Volume\n"
                          "```\n\n"
                          "**STARS** (High margin, High volume) - Keep, promote:\n"
                          "• Paket Komplit 1 (42% margin, 34% of orders)\n"
                          "• Ayam Potong 9 (38% margin, 18% of orders)\n\n"
                          "**PLOWS** (High margin, Low volume) - Push, feature:\n"
                          "• Party Bucket 20 (42% margin, 2% of orders) - Upsell opportunity!\n"
                          "• Winger Bucket 7 (40% margin, 3% of orders)\n\n"
                          "**PUZZLES** (Low margin, High volume) - Improve efficiency:\n"
                          "• Ayam Potong 3 (28% margin, 15% of orders) - Raise price or bundle\n"
                          "• Fries (35% margin, 12% of orders) - Good, consider upsize\n\n"
                          "**DOGS** (Low margin, Low volume) - Remove or bundle:\n"
                          "• Coleslaw (18% margin, 2% of orders) - Discontinue\n"
                          "• Bread & Butter (12% margin, 1% of orders) - Bundle only\n\n"
                          "**Potential Impact:** Removing 2 DOG items and promoting 2 PLOW items could add **Rp18.5M/month** in profit."),
                "insights": [
                    {"metric": "Stars Count", "value": "2 items", "change": "keep & promote"},
                    {"metric": "Plows Opportunity", "value": "2 items", "change": "push hard"},
                    {"metric": "Dogs to Remove", "value": "2 items", "change": "free up 8% capacity"},
                ],
                "recommendations": [
                    "Feature Party Bucket 20 prominently on app (target: 10% of orders)",
                    "Bundle DOGS with combos (don't sell standalone)",
                    "Increase PUZZLE prices by 8% or bundle with high-margin drinks",
                    "Create 'Family Value' promo to push PL items (Party Bucket)",
                ],
            }

        # =============================================================================
        # DEFAULT - HELP
        # =============================================================================

        else:
            return {
                "answer": ("**🤖 I can help you analyze your QSR business. Here are questions I can answer:**\n\n"
                          "**📊 Sales & Revenue:**\n"
                          "• 'What's my revenue forecast?'\n"
                          "• 'Analyze channel performance'\n"
                          "• 'What are my best selling items?'\n"
                          "• 'Price sensitivity analysis'\n\n"
                          "**📦 Inventory & Operations:**\n"
                          "• 'Inventory status and stockouts'\n"
                          "• 'Supplier performance'\n"
                          "• 'Food waste analysis'\n"
                          "• 'Preparation time optimization'\n\n"
                          "**👥 Customer & Marketing:**\n"
                          "• 'Customer segmentation'\n"
                          "• 'Churn analysis and retention'\n"
                          "• 'Marketing campaign performance'\n"
                          "• 'Customer lifetime value'\n\n"
                          "**💰 Financial & Strategy:**\n"
                          "• 'Break-even analysis'\n"
                          "• 'P&L summary'\n"
                          "• 'Where should I open my next store?'\n"
                          "• 'Profitability analysis'\n\n"
                          "**⚡ Operations:**\n"
                          "• 'Peak hour analysis'\n"
                          "• 'Delivery performance'\n"
                          "• 'Staff and labor optimization'\n\n"
                          "**🎯 Competitive Intelligence:**\n"
                          "• 'Competitor analysis'\n"
                          "• 'Market share'\n\n"
                          "**🍔 Menu Engineering:**\n"
                          "• 'Menu optimization'\n"
                          "• 'Star-dog analysis'\n\n"
                          "_Try asking any of these questions!_"),
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
        st.info("**🤖 AI Business Assistant** - Ask me anything about your QSR business!\n\n"
                "**📊 Sales & Revenue:**\n"
                "• 'What's my revenue forecast?'\n"
                "• 'Analyze channel performance' (GoFood, GrabFood, App)\n"
                "• 'What are my best selling items?'\n"
                "• 'Price sensitivity analysis'\n\n"
                "**📦 Inventory & Operations:**\n"
                "• 'Inventory status and stockouts'\n"
                "• 'Supplier performance'\n"
                "• 'Food waste analysis'\n"
                "• 'Preparation time optimization'\n\n"
                "**👥 Customer & Marketing:**\n"
                "• 'Customer segmentation'\n"
                "• 'Churn analysis and retention'\n"
                "• 'Marketing campaign ROAS'\n"
                "• 'Customer lifetime value'\n\n"
                "**💰 Financial & Strategy:**\n"
                "• 'Break-even analysis'\n"
                "• 'P&L summary'\n"
                "• 'Where should I open my next store?'\n\n"
                "**⚡ Operations:**\n"
                "• 'Peak hour analysis'\n"
                "• 'Delivery performance'\n"
                "• 'Staff and labor optimization'\n\n"
                "**🎯 Competitive & Menu:**\n"
                "• 'Competitor analysis'\n"
                "• 'Menu optimization (star-dog)'")

        # Quick question buttons
        st.markdown("---")
        st.markdown("**💬 Quick Questions:**")

        quick_questions = [
            ("📊 Revenue Forecast", "What's my revenue forecast?"),
            ("📦 Inventory Issues", "Do I have any inventory issues?"),
            ("👥 Customer Segments", "Customer segmentation analysis"),
            ("⚡ Peak Hours", "Peak hour analysis"),
            ("🆕 New Store Location", "Where should I open my next store?"),
            ("🎯 Menu Optimization", "Menu optimization star-dog analysis"),
            ("📈 Channel Performance", "Analyze channel performance"),
            ("💰 Break-Even Analysis", "Break-even analysis"),
        ]

        cols = st.columns(4)
        for i, (label, question) in enumerate(quick_questions):
            with cols[i % 4]:
                if st.button(label, key=f"quick_{i}", use_container_width=True):
                    st.session_state.chat_messages.append({"role": "user", "content": question})
                    st.rerun()

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

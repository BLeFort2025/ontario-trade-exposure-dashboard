"""
🍁 Ontario–U.S. Trade Exposure & Import Substitution Dashboard
=============================================================
Main Streamlit application entry point.

Developed for the Ontario Federation of Agriculture (OFA) to monitor
bilateral Ontario–U.S. merchandise trade flows, identify import substitution
opportunities, and assess tariff vulnerability across all 50 states + D.C.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from lib.data_loader import get_available_years, get_trade_summary
from lib.chapter_labels import AGRI_FOOD_CHAPTERS, chapter_label

# ── 1. Page Configuration ─────────────────────────────────────────────

st.set_page_config(
    page_title="Ontario Agri-Food Trade Exposure Dashboard",
    page_icon="🍁",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Helper Functions & Caching ────────────────────────────────────────

def format_currency(val: float) -> str:
    """Format CAD value as $X.XXB for billions, $X.XXM for millions, or $X.XXK."""
    abs_val = abs(val)
    sign = "-" if val < 0 else ""
    if abs_val >= 1_000_000_000:
        return f"{sign}${abs_val / 1_000_000_000:.2f}B"
    elif abs_val >= 1_000_000:
        return f"{sign}${abs_val / 1_000_000:.2f}M"
    elif abs_val >= 1_000:
        return f"{sign}${abs_val / 1_000:.2f}K"
    else:
        return f"{sign}${abs_val:.2f}"


@st.cache_data(ttl=3600)
def compute_headline_metrics(year: str) -> tuple[float, float, float]:
    """Compute total agri-food exports, imports, and net trade balance.

    Filters for HS Chapters 01–23 only (excluding industrial goods and 87-AUTO).
    """
    summary = get_trade_summary(year)
    agri_df = summary[summary["hs2_chapter"].isin(AGRI_FOOD_CHAPTERS)]

    exports_val = float(
        agri_df[agri_df["trade_type"] == "Domestic exports"]["value_cad"].sum()
    )
    imports_val = float(
        agri_df[agri_df["trade_type"] == "Imports"]["value_cad"].sum()
    )
    net_balance = exports_val - imports_val

    return exports_val, imports_val, net_balance


@st.cache_data(ttl=3600)
def get_chapter_level_comparison(year: str) -> pd.DataFrame:
    """Prepare chapter-level agri-food summary pivoted for chart display."""
    summary = get_trade_summary(year)
    agri_df = summary[summary["hs2_chapter"].isin(AGRI_FOOD_CHAPTERS)].copy()
    
    pivot = agri_df.pivot_table(
        index="hs2_chapter",
        columns="trade_type",
        values="value_cad",
        aggfunc="sum",
        fill_value=0.0,
    ).reset_index()

    # Normalize column names
    col_map = {}
    for col in pivot.columns:
        cl = str(col).lower()
        if "export" in cl:
            col_map[col] = "Exports"
        elif "import" in cl:
            col_map[col] = "Imports"
    pivot = pivot.rename(columns=col_map)
    if "Exports" not in pivot.columns:
        pivot["Exports"] = 0.0
    if "Imports" not in pivot.columns:
        pivot["Imports"] = 0.0

    pivot["Net Balance"] = pivot["Exports"] - pivot["Imports"]
    pivot["Total Trade"] = pivot["Exports"] + pivot["Imports"]
    pivot["Chapter Name"] = pivot["hs2_chapter"].apply(chapter_label)
    return pivot.sort_values("Total Trade", ascending=True)


# ── 2. Sidebar Navigation & State Management ──────────────────────────

available_years = get_available_years()

# Set default to most recent full calendar year (2025 or 2024) rather than partial 2026 YTD
default_year = "2025" if "2025" in available_years else ("2024" if "2024" in available_years else available_years[-1])

# Initialize session state for selected_year
if "selected_year" not in st.session_state or st.session_state["selected_year"] not in available_years:
    st.session_state["selected_year"] = default_year

st.sidebar.markdown("### ⚙️ Dashboard Controls")

# Format display labels in sidebar dropdown to clearly mark partial-year 2026
def format_year_label(yr: str) -> str:
    if yr == "2026":
        return "2026 (YTD Partial Year)"
    return f"{yr} (Full Year)"

selected_year_index = (
    available_years.index(st.session_state["selected_year"])
    if st.session_state["selected_year"] in available_years
    else available_years.index(default_year)
)

selected_year = st.sidebar.selectbox(
    "Select Reporting Year",
    options=available_years,
    index=selected_year_index,
    format_func=format_year_label,
    help="Select the reference year for trade flow analysis and headline metrics.",
)

# Keep session state updated for multi-page tabs
st.session_state["selected_year"] = selected_year

st.sidebar.markdown("---")
st.sidebar.markdown(
    """
    **📌 Methodology & Scope**
    - **Geographic Scope**: **Ontario ↔ U.S. 50 States + D.C.**
      *(Captures ~80% of Ontario's total global exports. Ontario's total agri-food exports to the **World** is ~$28B–$30B CAD).*
    - **Currency**: Canadian Dollars (CAD)
    - **HS Chapter 06**: Classified as *Primary Agriculture* per OFA convention
    - **HS Chapter 87**: Ag vehicles/trailers (8701/8716) separated from automotive
    """
)

# ── 3. Main Header ───────────────────────────────────────────────────

st.title("🍁 Ontario–U.S. Trade Exposure Dashboard")
st.markdown(
    "<h4 style='color: #2E7D32; margin-top: -12px; font-weight: 500;'>"
    "Ontario Federation of Agriculture | Bilateral Trade Intelligence"
    "</h4>",
    unsafe_allow_html=True,
)

if selected_year == "2026":
    st.info(
        "ℹ️ **Note on 2026 Data:** Statistics Canada data for 2026 is **Year-to-Date (YTD, ~6 months)**. "
        "The $10.52B in agri-food exports represents a half-year of trade, pacing on track for **~$21B+ annualized**. "
        "For complete annual baselines, select **2024** or **2025**."
    )

# ── 4. Brief Description ─────────────────────────────────────────────

st.markdown(
    """
    Welcome to the **Ontario–U.S. Trade Exposure & Import Substitution Intelligence Platform**. 
    This interactive tool provides farm leaders, policy analysts, and agribusinesses with granular 
    bilateral merchandise trade data across all 50 U.S. states. It is designed to identify top export 
    destinations, evaluate cross-border tariff exposure (including Canada's retaliatory counter-tariffs 
    and U.S. Section 338 measures), and pinpoint high-value domestic import substitution opportunities 
    where Ontario producers can expand domestic market share.
    """
)

# ── 5. Headline Metrics ──────────────────────────────────────────────

total_exports, total_imports, net_balance = compute_headline_metrics(selected_year)

st.markdown(f"### 📊 Key Agri-Food Trade Indicators ({selected_year})")

col1, col2, col3 = st.columns(3)

with col1:
    st.metric(
        label="Total Agri-Food Exports",
        value=format_currency(total_exports),
        help=f"Total bilateral merchandise exports from Ontario to the U.S. in {selected_year} across HS Chapters 01–23.",
    )

with col2:
    st.metric(
        label="Total Agri-Food Imports",
        value=format_currency(total_imports),
        help=f"Total bilateral merchandise imports into Ontario from the U.S. in {selected_year} across HS Chapters 01–23.",
    )

with col3:
    delta_text = f"+{format_currency(net_balance)}" if net_balance > 0 else format_currency(net_balance)
    st.metric(
        label="Net Trade Balance",
        value=format_currency(net_balance),
        delta=delta_text,
        delta_color="normal",
        help=f"Net trade balance (Exports minus Imports) for HS Chapters 01–23 in {selected_year}. A negative balance indicates a trade deficit.",
    )

st.markdown("---")

# ── 6. Interactive Overview Visualizations ────────────────────────────

col_chart, col_info = st.columns([3, 2])

with col_chart:
    st.subheader(f"📈 Agri-Food Trade by HS Chapter ({selected_year})")
    df_chapters = get_chapter_level_comparison(selected_year)
    
    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            y=df_chapters["Chapter Name"],
            x=df_chapters["Exports"],
            name="Domestic Exports",
            orientation="h",
            marker_color="#2E7D32",
            hovertemplate="%{y}<br>Exports: $%{x:,.0f} CAD<extra></extra>",
        )
    )
    fig.add_trace(
        go.Bar(
            y=df_chapters["Chapter Name"],
            x=df_chapters["Imports"],
            name="Imports",
            orientation="h",
            marker_color="#D32F2F",
            hovertemplate="%{y}<br>Imports: $%{x:,.0f} CAD<extra></extra>",
        )
    )
    fig.update_layout(
        barmode="group",
        height=520,
        margin=dict(l=10, r=20, t=20, b=30),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        xaxis=dict(title="Trade Value (CAD)", tickprefix="$"),
        yaxis=dict(title="", tickfont=dict(size=11)),
    )
    st.plotly_chart(fig, use_container_width=True)

with col_info:
    st.subheader("🧭 Platform Navigation & Modules")
    st.markdown(
        """
        Use the sidebar navigation to explore the dedicated analysis modules:

        - 🗺️ **Trade Map**: Interactive U.S. state choropleth map tracking Ontario's export destinations and import origins by state and commodity chapter.
        - 🔄 **Import Substitution**: Systematic ranking of commodities with significant trade deficits to highlight Ontario production expansion opportunities.
        - 🛡️ **Tariff Tracker**: Detailed exposure models evaluating Canada's Sept 8 counter-tariffs and U.S. Section 338 tariff impacts.
        - 🔍 **Commodity Explorer**: Search and filter 1,300+ HS-6 subheadings with full time-series charts and export capabilities (CSV / Excel).
        """
    )
    
    with st.expander("ℹ️ About the Data & Classification Conventions", expanded=False):
        st.markdown(
            """
            - **Primary Agriculture**: Per OFA guidelines, **HS Chapter 06** (*Live trees, cut flowers, floriculture and nursery products*) is explicitly categorized as Primary Agriculture alongside field crops, livestock, vegetables, and fruits.
            - **Agricultural Machinery & Vehicles**: **HS Chapter 87** is divided to separate farm equipment (HS 8701 tractors, HS 8716 trailers) from passenger automotive flows.
            - **Time Horizon**: Covers annual trade from **2021 through 2026**.
            """
        )

# ── 7. Footer ─────────────────────────────────────────────────────────

st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: #666666; font-size: 0.85rem; padding: 10px 0;'>
        <strong>Data Sources:</strong> Statistics Canada (CIMT Table 71-607-X) &bull; U.S. Census Bureau International Trade API &bull; Department of Finance Canada &bull; Office of the United States Trade Representative (USTR)<br>
        <em>Ontario Federation of Agriculture (OFA) &copy; 2026 &bull; Developed for Bilateral Trade & Market Intelligence</em>
    </div>
    """,
    unsafe_allow_html=True,
)

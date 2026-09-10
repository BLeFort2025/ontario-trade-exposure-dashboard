"""
Global Market Diversification Matrix (Track 4)
==============================================
Maps alternative export destinations, tariff preferences (CUSMA, CETA, CPTPP),
and models trade diversion potential away from the increasingly hostile U.S. market.
Ground-truthed with Statistics Canada CIMT data and Gemini Deep Research baselines.
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from io import BytesIO

from lib.data_loader import (
    get_available_years,
    get_global_market_summary,
    get_global_agreement_summary,
    get_global_chapter_trade,
    get_preferential_tariffs,
    get_diversion_matrix,
    _get_global_conn,
)
from lib.chapter_labels import (
    CHAPTER_LABELS,
    chapter_label,
    chapter_short,
    AGRI_FOOD_CHAPTERS,
    FARM_INPUT_CHAPTERS,
    PRIMARY_AG_CHAPTERS,
)

st.set_page_config(
    page_title="Global Market Diversification | OFA Trade",
    page_icon="🌐",
    layout="wide",
)

# ── Title & Header ───────────────────────────────────────────────────

st.title("🌐 Global Market Diversification Matrix")
st.caption("Ontario Federation of Agriculture | International Trade & Tariff Mitigation Engine")

# Year selection from session state or fallback
selected_year = st.session_state.get("selected_year", "2025")

# ── Top Overview Banner ──────────────────────────────────────────────

st.info(
    "**Strategic Context (Deep Research Ground-Truthed):** Ontario's agri-food export economy exhibits a critical "
    "structural divergence. **Primary Agriculture (NAPCS C11)**—strictly including NAICS 1114 greenhouse and nursery "
    "growers—is already **~35% diversified** into non-U.S. global corridors ($3.44B to Japan, EU, Mexico, and Asia). "
    "Conversely, **Processed Food & Beverages (HS 16–22)** exceed **90% dependency on the U.S.** market, leaving them "
    "critically exposed to U.S. Section 338 import bans effective September 29, 2026."
)

# ── Controls Row ─────────────────────────────────────────────────────

col_ctrl1, col_ctrl2, col_ctrl3 = st.columns([1, 1, 2])

with col_ctrl1:
    years = get_available_years()
    year = st.selectbox(
        "Reference Year",
        years,
        index=years.index(selected_year) if selected_year in years else len(years) - 2,
        key="global_year_select",
    )

with col_ctrl2:
    trade_type = st.radio(
        "Trade Direction",
        ["Domestic exports", "Imports"],
        horizontal=True,
        key="global_trade_type",
    )

with col_ctrl3:
    chapter_options = ["All Agri-Food (Chapters 01–24)"] + [
        f"Chapter {ch} — {chapter_short(ch)}"
        for ch in sorted(list(AGRI_FOOD_CHAPTERS))
        if ch in CHAPTER_LABELS and not ch.endswith("-AG") and not ch.endswith("-AUTO")
    ]
    selected_ch_label = st.selectbox("Commodity Filter", chapter_options, key="global_chapter_filter")
    selected_ch = selected_ch_label.split(" ")[1] if "Chapter" in selected_ch_label else None

st.divider()

# ── 4-Tab Analytical Architecture ────────────────────────────────────

tabs = st.tabs([
    "🌍 Market Concentration",
    "🏛️ Trade Agreement Corridors",
    "🎯 Diversion Opportunity Matrix",
    "📈 Strategic Benchmarks & Non-Tariff Barriers",
])

# =====================================================================
# TAB 1: Market Concentration & Destination Mix
# =====================================================================

with tabs[0]:
    st.subheader("Global Destination Mix & Market Exposure")
    st.markdown(
        "Analyze Ontario's global trading partners, contrast U.S. border dependency against non-U.S. corridors, "
        "and track international market penetration across 50+ countries."
    )

    df_market = get_global_market_summary(year, trade_type)

    if not df_market.empty:
        total_trade = df_market["value_cad"].sum()
        us_row = df_market[df_market["country"] == "United States"]
        us_val = us_row["value_cad"].iloc[0] if not us_row.empty else 0.0
        non_us_val = total_trade - us_val
        us_share = (us_val / total_trade * 100.0) if total_trade > 0 else 0.0
        non_us_share = 100.0 - us_share

        top_non_us = df_market[df_market["country"] != "United States"].iloc[0] if len(df_market) > 1 else None
        active_partners = len(df_market[df_market["value_cad"] >= 1e6])

        # KPI Scorecard
        kpi1, kpi2, kpi3, kpi4 = st.columns(4)
        kpi1.metric(
            f"Total Global {trade_type}",
            f"${total_trade / 1e9:.2f}B CAD",
            f"{year} Calendar Year",
        )
        kpi2.metric(
            "U.S. Market Share",
            f"{us_share:.1f}%",
            f"${us_val / 1e9:.2f}B CAD",
            delta_color="inverse",
        )
        kpi3.metric(
            "Non-U.S. Diversified Share",
            f"{non_us_share:.1f}%",
            f"${non_us_val / 1e9:.2f}B CAD",
        )
        kpi4.metric(
            "Top Global Partner",
            f"{top_non_us['country']}" if top_non_us is not None else "N/A",
            f"${top_non_us['value_cad'] / 1e6:.1f}M CAD ({top_non_us['trade_agreement']})" if top_non_us is not None else "",
        )

        st.markdown("<br>", unsafe_allow_html=True)

        # Choropleth World Map
        st.markdown("#### 🗺️ Global Geographic Distribution")
        
        # Color scale toggle
        map_col1, map_col2 = st.columns([3, 1])
        with map_col2:
            exclude_us_map = st.checkbox(
                "Exclude U.S. from Color Scale",
                value=True,
                help="Excludes the United States from color scaling so non-U.S. diversification markets stand out visually.",
            )

        map_df = df_market.copy()
        if exclude_us_map:
            # Cap U.S. for coloring to maximum non-US value
            max_non_us = map_df[map_df["country"] != "United States"]["value_cad"].max()
            map_df["color_val"] = np.where(map_df["country"] == "United States", max_non_us, map_df["value_cad"])
        else:
            map_df["color_val"] = map_df["value_cad"]

        colorscale = "Greens" if trade_type == "Domestic exports" else "Reds"

        fig_world = px.choropleth(
            map_df,
            locations="country_iso3",
            color="color_val",
            hover_name="country",
            hover_data={
                "color_val": False,
                "country_iso3": False,
                "value_cad": ":$,.0f",
                "share_pct": ":.2f",
                "trade_agreement": True,
            },
            labels={
                "value_cad": f"{trade_type} (CAD)",
                "share_pct": "Share of Total (%)",
                "trade_agreement": "Trade Framework",
            },
            color_continuous_scale=colorscale,
            projection="natural earth",
        )
        fig_world.update_layout(
            height=520,
            margin=dict(l=0, r=0, t=10, b=10),
            coloraxis_colorbar=dict(title=f"{trade_type}<br>(CAD)", tickprefix="$"),
        )
        st.plotly_chart(fig_world, use_container_width=True)

        # Top 15 Non-US Partners Bar Chart
        st.markdown("#### 🏆 Top 15 Non-U.S. Trading Partners")
        top15_non_us = df_market[df_market["country"] != "United States"].head(15).copy()

        agreement_colors = {
            "CPTPP": "#E65100",  # Amber/Orange
            "CETA": "#0D47A1",   # Deep Blue
            "CUSMA": "#2E7D32",  # Green
            "CUKTA": "#6A1B9A",  # Purple
            "CKFTA": "#00838F",  # Cyan/Teal
            "MFN": "#757575",    # Gray
        }

        fig_bar = px.bar(
            top15_non_us,
            x="value_cad",
            y="country",
            orientation="h",
            color="trade_agreement",
            color_discrete_map=agreement_colors,
            text=top15_non_us["value_cad"].apply(lambda v: f"${v / 1e6:,.1f}M"),
            hover_data={"value_cad": ":$,.0f", "share_pct": ":.2f", "trade_agreement": True},
            labels={
                "value_cad": f"{trade_type} (CAD)",
                "country": "Partner Country",
                "trade_agreement": "Trade Agreement",
            },
        )
        fig_bar.update_layout(
            yaxis=dict(autorange="reversed"),
            height=480,
            margin=dict(l=10, r=20, t=20, b=10),
            xaxis_tickprefix="$",
        )
        st.plotly_chart(fig_bar, use_container_width=True)

        # Data Table Expander
        with st.expander(f"📋 View Full Country League Table ({len(df_market)} Countries)"):
            display_df = df_market.copy()
            display_df["Value (CAD)"] = display_df["value_cad"].apply(lambda v: f"${v:,.0f}")
            display_df["Share (%)"] = display_df["share_pct"].apply(lambda v: f"{v:.2f}%")
            display_df = display_df.rename(columns={
                "rank": "Rank",
                "country": "Country",
                "country_iso3": "ISO3",
                "trade_agreement": "Trade Agreement",
            })[["Rank", "Country", "ISO3", "Trade Agreement", "Value (CAD)", "Share (%)"]]

            st.dataframe(display_df, use_container_width=True, hide_index=True)

            csv_data = df_market.to_csv(index=False).encode("utf-8")
            st.download_button(
                f"📥 Download {trade_type} League Table (CSV)",
                data=csv_data,
                file_name=f"ontario_global_{trade_type.lower().replace(' ', '_')}_{year}.csv",
                mime="text/csv",
            )
    else:
        st.warning(f"No global trade data found for {year}.")


# =====================================================================
# TAB 2: Trade Agreement Corridors
# =====================================================================

with tabs[1]:
    st.subheader("Bilateral Trade Agreement Corridors")
    st.markdown(
        "Evaluate Ontario's trade performance and expansion potential across Canada's key free trade frameworks: "
        "**CUSMA (Mexico)**, **CETA (European Union)**, **CPTPP (Trans-Pacific & Japan)**, and **CUKTA (United Kingdom)**."
    )

    df_agreements = get_global_agreement_summary(year, trade_type)

    col_ag1, col_ag2 = st.columns([1, 2])

    with col_ag1:
        st.markdown("#### Corridor Distribution")
        fig_donut = px.pie(
            df_agreements,
            names="trade_agreement",
            values="value_cad",
            hole=0.45,
            color="trade_agreement",
            color_discrete_map=agreement_colors,
        )
        fig_donut.update_traces(textposition="inside", textinfo="percent+label")
        fig_donut.update_layout(height=380, margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(fig_donut, use_container_width=True)

    with col_ag2:
        st.markdown("#### Strategic Corridor Profiles")
        st.markdown(
            """
            - **🇯🇵 CPTPP Corridor (Japan, Vietnam, Australia, Malaysia):**
              *Ontario's premier premium value destination.* Duty-free access for non-GMO food soybeans (**HS 1201**).
              Reformed Japanese pork gate-price (specific duty capped at 50 yen/kg) enables massive chilled loin shipments.
            - **🇪🇺 CETA Corridor (EU-27: Germany, Italy, Netherlands, Spain):**
              *Over $1.05B in annual primary ag flows.* 0% tariff on Ontario soybeans, dry edible beans, and distilled spirits.
              Constrained by stringent non-tariff barriers: ractopamine bans in pork, glyphosate MRL differences, and EUDR GPS polygon rules.
            - **🇲🇽 CUSMA Corridor (Mexico):**
              *Duty-free North American diversification.* 0% applied tariff on Ontario grain corn, winter wheat, dry edible beans,
              and specialized pork cuts.
            - **🇬🇧 CUKTA Corridor (United Kingdom):**
              *Trade continuity following Brexit.* 0% preferential duty on Canadian rye whiskies, processed confectionery, and food preparations.
            """
        )

    # Detailed Commodity Query by Corridor
    st.divider()
    st.markdown("#### 🔍 Corridor Commodity Deep Dive")

    corridor_choice = st.selectbox(
        "Select Trade Corridor",
        ["CPTPP", "CETA", "CUSMA", "CUKTA", "MFN"],
        key="corridor_select",
    )

    conn_gl = _get_global_conn()
    df_corridor_commodities = pd.read_sql(
        """
        SELECT hs6_clean, hs2_chapter, commodity_desc, sum(value_cad) as value_cad, count(DISTINCT country) as market_count
        FROM global_hs_trade
        WHERE trade_type = ? AND ref_date LIKE ? AND trade_agreement = ?
          AND hs2_chapter BETWEEN '01' AND '24'
        GROUP BY hs6_clean, hs2_chapter, commodity_desc
        ORDER BY value_cad DESC
        LIMIT 15
        """,
        conn_gl,
        params=[trade_type, f"{year}%", corridor_choice],
    )

    if not df_corridor_commodities.empty:
        fig_corr_bar = px.bar(
            df_corridor_commodities,
            x="value_cad",
            y="commodity_desc",
            orientation="h",
            text=df_corridor_commodities["value_cad"].apply(lambda v: f"${v / 1e6:,.1f}M"),
            labels={"value_cad": f"{trade_type} (CAD)", "commodity_desc": "Commodity"},
            title=f"Top 15 Commodities Traded with {corridor_choice} Partners ({year})",
            color_discrete_sequence=[agreement_colors.get(corridor_choice, "#1565C0")],
        )
        fig_corr_bar.update_layout(
            yaxis=dict(autorange="reversed"),
            height=450,
            margin=dict(l=10, r=20, t=40, b=10),
            xaxis_tickprefix="$",
        )
        st.plotly_chart(fig_corr_bar, use_container_width=True)

        with st.expander(f"📋 View All {corridor_choice} Traded Commodities"):
            disp_corr = df_corridor_commodities.copy()
            disp_corr["Value (CAD)"] = disp_corr["value_cad"].apply(lambda v: f"${v:,.0f}")
            disp_corr = disp_corr.rename(columns={
                "hs6_clean": "HS-6 Code",
                "hs2_chapter": "Chapter",
                "commodity_desc": "Commodity Description",
                "market_count": "Active Countries",
            })[["HS-6 Code", "Chapter", "Commodity Description", "Active Countries", "Value (CAD)"]]
            st.dataframe(disp_corr, use_container_width=True, hide_index=True)
    else:
        st.info(f"No commodities found for corridor {corridor_choice} in {year}.")


# =====================================================================
# TAB 3: Diversion Opportunity Matrix (Section 338 Mitigation)
# =====================================================================

with tabs[2]:
    st.subheader("Section 338 Trade Diversion & Mitigation Engine")
    st.markdown(
        "Identify export commodities vulnerable to U.S. tariff escalation or outright import bans, "
        "and quantify the feasibility of redirecting trade into secondary non-U.S. markets."
    )

    # Section 338 Callout Box
    st.error(
        "🚨 **September 29, 2026 U.S. Import Bans (Section 338):** Presidential Proclamations 11046, 11047, and 11048 "
        "ban the importation of Canadian **Alcoholic Beverages ($794M)**, **Dairy, Whey & Mixes ($530M)**, and "
        "**Floriculture & Honey ($438M — Primary Ag)**. Below is the empirical diversion feasibility model."
    )

    df_diversion = get_diversion_matrix(year)

    if not df_diversion.empty:
        # Filter for commodities with significant export volume (> $1M)
        df_div_plot = df_diversion[df_diversion["total_exports"] >= 1e6].copy()

        # Scatter Opportunity Quadrants
        st.markdown("#### 🎯 Export Diversion Quadrant")
        st.caption(
            "Bubble size represents total Ontario export volume. "
            "Top-Right = High U.S. vulnerability, but established global buyer pipeline already exists."
        )

        tier_colors = {
            "Immediate Pivot (Primary Commodity)": "#2E7D32",   # Green
            "Immediate Pivot (Shelf-Stable)": "#1565C0",        # Blue
            "Immediate Pivot (Shelf-Stable Powder)": "#00838F", # Cyan
            "Feasible with Shelf Life / Cold Chain": "#F57C00", # Orange
            "Supply Managed Domestic Replacement": "#D32F2F",  # Red
            "Immediate Pivot (Manufactured)": "#7B1FA2",        # Purple
            "Immediate Pivot (Commodity)": "#388E3C",           # Light Green
        }

        fig_scatter = px.scatter(
            df_div_plot,
            x="us_concentration_pct",
            y="non_us_exports",
            size="total_exports",
            color="diversion_tier",
            color_discrete_map=tier_colors,
            hover_name="commodity_desc",
            hover_data={
                "hs6_clean": True,
                "us_exports": ":$,.0f",
                "non_us_exports": ":$,.0f",
                "us_concentration_pct": ":.1f",
                "active_markets": True,
                "total_exports": False,
            },
            labels={
                "us_concentration_pct": "U.S. Export Concentration (%)",
                "non_us_exports": "Non-U.S. Established Trade (CAD)",
                "diversion_tier": "Diversion Feasibility Tier",
                "hs6_clean": "HS-6 Code",
                "active_markets": "Active Global Buyers",
            },
            log_y=True,
        )
        fig_scatter.add_vline(x=75.0, line_dash="dash", line_color="gray", annotation_text="75% U.S. Dependency Threshold")
        fig_scatter.update_layout(
            height=540,
            margin=dict(l=10, r=10, t=30, b=10),
            yaxis_tickprefix="$",
        )
        st.plotly_chart(fig_scatter, use_container_width=True)

        # Strategic Table for Targeted Lines
        st.markdown("#### 🛡️ Section 338 Targeted Commodities Diversion Matrix")

        df_targeted = df_diversion[df_diversion["proclamation"].notna() | df_diversion["diversion_tier"].notna()].copy()

        if not df_targeted.empty:
            df_targeted["U.S. Exposure (CAD)"] = df_targeted["us_exports"].apply(lambda v: f"${v:,.0f}")
            df_targeted["Non-U.S. Trade (CAD)"] = df_targeted["non_us_exports"].apply(lambda v: f"${v:,.0f}")
            df_targeted["U.S. Share (%)"] = df_targeted["us_concentration_pct"].apply(lambda v: f"{v:.1f}%")
            df_targeted["Armington Elasticity"] = df_targeted["armington_elasticity"].apply(
                lambda v: f"{v:.1f}x" if pd.notna(v) else "N/A"
            )

            cols_show = [
                "hs6_clean", "commodity_desc", "U.S. Exposure (CAD)",
                "Non-U.S. Trade (CAD)", "U.S. Share (%)", "Armington Elasticity",
                "diversion_tier", "active_markets"
            ]
            disp_target = df_targeted[cols_show].rename(columns={
                "hs6_clean": "HS-6 Code",
                "commodity_desc": "Commodity Description",
                "diversion_tier": "Feasibility Tier",
                "active_markets": "Established Alternative Markets",
            })
            st.dataframe(disp_target, use_container_width=True, hide_index=True)


# =====================================================================
# TAB 4: Strategic Benchmarks & Non-Tariff Barriers
# =====================================================================

with tabs[3]:
    st.subheader("Preferential Tariff Architecture & Non-Tariff Regulatory Barriers")
    st.markdown(
        "Ground-truthed tariff rates, quota regimes, and critical non-tariff regulatory blockers (MRLs, EUDR, "
        "soil prohibitions) governing trade diversion feasibility for Ontario's core agricultural outputs."
    )

    df_benchmarks = get_preferential_tariffs()

    for idx, row in df_benchmarks.iterrows():
        with st.container():
            col_b1, col_b2 = st.columns([2, 3])

            with col_b1:
                st.markdown(f"### {row['commodity_desc']}")
                st.caption(f"HS-6 Code: **{row['hs6_code']}** | Chapter {row['hs2_chapter']}")

                b_m1, b_m2, b_m3 = st.columns(3)
                b_m1.metric("CUSMA (Mexico)", f"{row['cusma_rate_pct']:.1f}%")
                b_m2.metric("CETA (EU)", f"{row['ceta_rate_pct']:.1f}%")
                b_m3.metric("CPTPP (Japan)", f"{row['cptpp_rate_pct']:.1f}%")

                st.markdown(f"**Feasibility Tier:** `{row['diversion_tier']}`")
                st.markdown(f"**Armington Elasticity:** `{row['armington_elasticity']}x` (Empirical redirection speed)")

            with col_b2:
                st.markdown("**Critical Non-Tariff Barriers & Trade Rules:**")
                if pd.notna(row["ceta_sps_blocker"]) and row["ceta_sps_blocker"]:
                    st.warning(f"🇪🇺 **CETA Non-Tariff Blocker:** {row['ceta_sps_blocker']}")
                if pd.notna(row["cptpp_sps_blocker"]) and row["cptpp_sps_blocker"]:
                    st.error(f"🇯🇵 **CPTPP Regulatory Blocker:** {row['cptpp_sps_blocker']}")
                st.info(f"💡 **Strategic Action:** {row['strategic_notes']}")

            st.divider()

st.caption("Ontario Trade Exposure Dashboard | Built for Ontario Federation of Agriculture (OFA)")

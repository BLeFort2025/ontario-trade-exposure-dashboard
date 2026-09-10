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
    get_india_cepa_matrix,
    get_india_headline_metrics,
    calculate_india_landed_duty,
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

# ── 5-Tab Analytical Architecture ────────────────────────────────────

tabs = st.tabs([
    "🌍 Market Concentration",
    "🏛️ Trade Agreement Corridors",
    "🎯 Diversion Opportunity Matrix",
    "📈 Strategic Benchmarks & Non-Tariff Barriers",
    "🇮🇳 India CEPA Frontier",
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

        # Clip to $1,000 for safe log-scale visualization without mathematical singularity
        df_div_plot["non_us_plot"] = df_div_plot["non_us_exports"].clip(lower=1000.0)

        fig_scatter = px.scatter(
            df_div_plot,
            x="us_concentration_pct",
            y="non_us_plot",
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
                "non_us_plot": False,
            },
            labels={
                "us_concentration_pct": "U.S. Export Concentration (%)",
                "non_us_plot": "Non-U.S. Established Trade (CAD)",
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


# =====================================================================
# TAB 5: India CEPA Frontier (2026 Negotiations)
# =====================================================================

with tabs[4]:
    st.subheader("🇮🇳 Canada–India CEPA: Ontario Agri-Food Export Opportunities")
    st.markdown(
        "Empirical trade opportunities, landed tariff compounding, competitor concession benchmarks (Australia AI-ECTA), "
        "and non-tariff regulatory arbitrage for Ontario producers under the prospective **Canada–India Comprehensive "
        "Economic Partnership Agreement (CEPA)**."
    )

    st.info(
        "💡 **Key Strategic Takeaway (Deep Research Verified):** India represents a **$37.8B USD ($51.7B CAD)** annual agricultural "
        "import market. While Western Canada trades heavily in bulk red lentils, Ontario's competitive edge lies in **high-margin, "
        "Identity-Preserved (IP) non-GMO food crops, premium spirits, genetics, and specialized equipment**. "
        "Most crucially, India's **FSSAI 1% Adventitious Presence (AP) non-GMO mandate** structurally blocks U.S. bulk commodity GMO soybeans, "
        "handing Ontario's **Canadian Identity Preserved Recognition System (CIPRS)** a near-monopolistic quality arbitrage advantage."
    )

    # 1. Headline Metrics
    metrics_in = get_india_headline_metrics()
    m_col1, m_col2, m_col3, m_col4 = st.columns(4)
    m_col1.metric("India World Agri-Imports", f"${metrics_in['total_india_import_cad'] / 1e9:.1f}B CAD", "Target Commodities")
    m_col2.metric("Ontario Exportable Surplus", f"${metrics_in['total_ontario_surplus'] / 1e9:.2f}B CAD", "Across 13 Strategic Lines")
    m_col3.metric("Current Average MFN Duty", f"{metrics_in['avg_mfn_duty']:.1f}%", "Compound Landed Tariff")
    m_col4.metric("Negotiated CEPA Target", "5.0% TRQ / 0% Phased", "Parity with Australia ECTA")

    st.divider()

    # 2. Interactive Landed Duty & Tariff Stack Simulator
    st.markdown("### 🧮 Interactive Landed Cost & Tariff Stack Simulator")
    st.markdown(
        "Simulate the complete statutory landed duty stack (**Basic Customs Duty + AIDC + Social Welfare Surcharge + IGST**) "
        "for a commercial consignment entering India under current MFN rates versus competitor benchmarks and proposed CEPA concessions."
    )

    df_india = get_india_cepa_matrix()
    comm_options = {
        f"{r['hs6_code']} — {r['commodity_desc']} ({r['sector']})": r['hs6_code']
        for _, r in df_india.iterrows()
    }

    sim_col1, sim_col2 = st.columns([1, 1])

    with sim_col1:
        selected_comm_label = st.selectbox("Select Target Commodity", list(comm_options.keys()), index=0)
        selected_hs6 = comm_options[selected_comm_label]
        cif_val = st.number_input("Consignment CIF Value (CAD)", min_value=10000.0, max_value=10000000.0, value=100000.0, step=25000.0, format="%.2f")

    sim_mfn = calculate_india_landed_duty(selected_hs6, cif_val, "Applied MFN")
    sim_ecta = calculate_india_landed_duty(selected_hs6, cif_val, "AI-ECTA Benchmark")
    sim_cepa = calculate_india_landed_duty(selected_hs6, cif_val, "Proposed CEPA Target")

    with sim_col2:
        st.markdown(f"**Duty Comparison for ${cif_val:,.0f} CAD Consignment:**")
        comp_data = [
            {"Scenario": "1. Current Applied MFN", "Total Duty (CAD)": sim_mfn["total_duty"], "Effective Tax (%)": f"{sim_mfn['effective_rate_pct']:.1f}%", "Landed Total": sim_mfn["total_landed"]},
            {"Scenario": "2. Australia AI-ECTA Parity", "Total Duty (CAD)": sim_ecta["total_duty"], "Effective Tax (%)": f"{sim_ecta['effective_rate_pct']:.1f}%", "Landed Total": sim_ecta["total_landed"]},
            {"Scenario": "3. Proposed CEPA Target", "Total Duty (CAD)": sim_cepa["total_duty"], "Effective Tax (%)": f"{sim_cepa['effective_rate_pct']:.1f}%", "Landed Total": sim_cepa["total_landed"]},
        ]
        st.dataframe(pd.DataFrame(comp_data), use_container_width=True, hide_index=True)
        savings = sim_mfn["total_duty"] - sim_cepa["total_duty"]
        st.success(f"🎉 **Potential Duty Savings under CEPA:** **${savings:,.2f} CAD** per consignment ({sim_mfn['effective_rate_pct'] - sim_cepa['effective_rate_pct']:.1f}% margin expansion).")

    # Bar chart of duty components
    duty_breakdown = pd.DataFrame([
        {"Scenario": "Applied MFN", "Component": "Basic Customs Duty (BCD)", "Amount": sim_mfn["bcd_amt"]},
        {"Scenario": "Applied MFN", "Component": "Agriculture Infra Cess (AIDC)", "Amount": sim_mfn["aidc_amt"]},
        {"Scenario": "Applied MFN", "Component": "Social Welfare Surcharge (SWS)", "Amount": sim_mfn["sws_amt"]},
        {"Scenario": "Applied MFN", "Component": "Integrated GST (IGST)", "Amount": sim_mfn["igst_amt"]},
        {"Scenario": "AI-ECTA Benchmark", "Component": "Basic Customs Duty (BCD)", "Amount": sim_ecta["bcd_amt"]},
        {"Scenario": "AI-ECTA Benchmark", "Component": "Agriculture Infra Cess (AIDC)", "Amount": sim_ecta["aidc_amt"]},
        {"Scenario": "AI-ECTA Benchmark", "Component": "Social Welfare Surcharge (SWS)", "Amount": sim_ecta["sws_amt"]},
        {"Scenario": "AI-ECTA Benchmark", "Component": "Integrated GST (IGST)", "Amount": sim_ecta["igst_amt"]},
        {"Scenario": "Proposed CEPA Target", "Component": "Basic Customs Duty (BCD)", "Amount": sim_cepa["bcd_amt"]},
        {"Scenario": "Proposed CEPA Target", "Component": "Agriculture Infra Cess (AIDC)", "Amount": sim_cepa["aidc_amt"]},
        {"Scenario": "Proposed CEPA Target", "Component": "Social Welfare Surcharge (SWS)", "Amount": sim_cepa["sws_amt"]},
        {"Scenario": "Proposed CEPA Target", "Component": "Integrated GST (IGST)", "Amount": sim_cepa["igst_amt"]},
    ])

    fig_sim = px.bar(
        duty_breakdown,
        x="Scenario",
        y="Amount",
        color="Component",
        title=f"Landed Duty Stack Breakdown: {sim_mfn['commodity_desc']} (${cif_val:,.0f} CAD)",
        labels={"Amount": "Tax Burden (CAD)"},
        color_discrete_sequence=["#003366", "#D9534F", "#F0AD4E", "#5CB85C"],
        height=380,
    )
    fig_sim.update_layout(barmode="stack", margin=dict(l=20, r=20, t=40, b=20))
    st.plotly_chart(fig_sim, use_container_width=True)

    st.divider()

    # 3. High-Potential Commodity Opportunity Matrix
    st.markdown("### 📋 Ontario–India High-Potential Commodity Matrix")
    st.markdown(
        "Ranked opportunities matching Ontario's verified production surplus against India's global import demand, "
        "highlighting competitor benchmarks and negotiating targets."
    )

    mat_col1, mat_col2 = st.columns([1, 1])
    with mat_col1:
        sectors = ["All Sectors"] + sorted(list(df_india["sector"].unique()))
        sel_sector = st.selectbox("Filter by Sector", sectors, key="india_sector_filter")
    with mat_col2:
        tiers = ["All Strategic Tiers"] + sorted(list(df_india["tci_tier"].unique()))
        sel_tier = st.selectbox("Filter by TCI Strategic Tier", tiers, key="india_tier_filter")

    df_disp_mat = df_india.copy()
    if sel_sector != "All Sectors":
        df_disp_mat = df_disp_mat[df_disp_mat["sector"] == sel_sector]
    if sel_tier != "All Strategic Tiers":
        df_disp_mat = df_disp_mat[df_disp_mat["tci_tier"] == sel_tier]

    df_disp_mat["Ontario Surplus (CAD)"] = df_disp_mat["ontario_surplus_cad"].apply(lambda v: f"${v / 1e6:.1f}M")
    df_disp_mat["India World Demand (CAD)"] = df_disp_mat["india_world_import_cad"].apply(lambda v: f"${v / 1e6:.1f}M")
    df_disp_mat["Effective MFN Duty"] = df_disp_mat["effective_mfn_duty_pct"].apply(lambda v: f"{v:.1f}%")

    cols_show_in = [
        "hs6_code", "commodity_desc", "sector", "Ontario Surplus (CAD)",
        "India World Demand (CAD)", "Effective MFN Duty", "cepa_negotiating_target",
        "tci_tier", "ontario_arbitrage_advantage"
    ]
    df_show_in = df_disp_mat[cols_show_in].rename(columns={
        "hs6_code": "HS-6",
        "commodity_desc": "Commodity Description",
        "sector": "Sector",
        "cepa_negotiating_target": "Proposed CEPA Target",
        "tci_tier": "Strategic Tier",
        "ontario_arbitrage_advantage": "Ontario Strategic Advantage",
    })
    st.dataframe(df_show_in, use_container_width=True, hide_index=True)

    # 4. Non-Tariff & SPS Protocol Clearance Tracker
    st.markdown("### 🛡️ Non-Tariff Measures (NTMs) & Regulatory Clearance Tracker")
    st.markdown(
        "Tariff reductions are meaningless if consignments are blocked at Indian ports. Below are the four essential "
        "non-tariff protocols that must be resolved in the CEPA Sanitary and Phytosanitary (SPS) chapter."
    )

    ntm1, ntm2 = st.columns(2)

    with ntm1:
        with st.expander("🌱 1. FSSAI Non-GM Mandate & The Ontario CIPRS Arbitrage", expanded=True):
            st.markdown(
                "**The Regulatory Hurdle:** The Food Safety and Standards Authority of India (FSSAI) enforces a mandatory "
                "**Non-GM Origin cum GM-Free Certificate** on 24 imported food crops (effective March 1, 2021) with a strict "
                "**1% Adventitious Presence (AP)** threshold.\n\n"
                "**Why Competitors Fail:** Bulk commodity soy from the United States and South America is nearly 100% GMO, "
                "rendering them incapable of meeting the 1% AP limit without costly segregated containerization.\n\n"
                "**Ontario's Advantage:** Ontario produces **3.6 MMT of soybeans (52% of Canada's crop)** and is a world leader in "
                "Identity-Preserved (IP) non-GMO food soy. The Canadian Grain Commission's (CGC) **Canadian Identity Preserved "
                "Recognition System (CIPRS)** provides certified varietal purity from seed to port.\n\n"
                "**CEPA Mandate:** Codify explicit mutual recognition of CGC CIPRS certificates by FSSAI."
            )

        with ntm2:
            with st.expander("🧪 2. PQO 2003 Methyl Bromide & The Systems Approach", expanded=True):
                st.markdown(
                    "**The Dispute:** Clause 3 of India's *Plant Quarantine Order (PQO) 2003* mandates offshore fumigation with "
                    "methyl bromide (48 g/m³ at 21°C). Canada phased out agricultural methyl bromide under the Montreal Protocol.\n\n"
                    "**The Asymmetric Penalty:** While India grants import derogations, consignments arriving without offshore "
                    "methyl bromide face **punitive inspection fees 4 to 5 times the standard rate**.\n\n"
                    "**The Systems Approach:** CEPA must formally recognize Canada's integrated pest risk management—including "
                    "winter cold-weather storage, mechanical purity grading, and phosphine fumigation (1.1 g/m³)—as fully equivalent, "
                    "permanently eliminating the 4x–5x penal fees."
                )

    ntm3, ntm4 = st.columns(2)

    with ntm3:
        with st.expander("🧬 3. DAHD Veterinary Protocols for Bovine Genetics (HS 0511.10)", expanded=True):
            st.markdown(
                "**The Demand Driver:** India has over 300 million cattle and water buffalo, but low average milk yield per animal. "
                "The National Dairy Development Board (NDDB) is actively seeking elite global genetics.\n\n"
                "**Zero Cultural Sensitivity:** Because this involves artificial insemination and embryo transfer rather than live slaughter "
                "cattle, it faces zero religious or cultural opposition in India.\n\n"
                "**Regulatory Requirement:** Importers must obtain Department of Animal Husbandry and Dairying (DAHD) Sanitary Permits "
                "certifying freedom from Foot and Mouth Disease (FMD), Contagious Bovine Pleuropneumonia (CBPP), and Lumpy Skin Disease (LSD). "
                "Ontario's CFIA-inspected facilities already comply with International Embryo Transfer Society (IETS) standards; CEPA must "
                "pre-clear bilateral veterinary certificates."
            )

    with ntm4:
        with st.expander("🌸 4. Primary Floriculture: PQO 2003 Tissue Culture Exemption (NAICS 1114)", expanded=True):
            st.markdown(
                "**Primary Agriculture Classification:** Nursery, floriculture, and greenhouse operators are classified strictly as "
                "**Primary Agriculture** under NAICS 1114 and Ontario's *Farm Registration and Farm Organizations Funding Act, 1993*.\n\n"
                "**The Breakthrough Exemption:** While living potted plants cannot enter India due to blanket soil prohibitions under PQO 2003, "
                "**Sub-clause 3(3) of PQO 2003 explicitly exempts tissue-cultured plants** grown in sterile agar media in sealed flasks. "
                "Unrooted cuttings (HS 0602.10) without soil are also permitted under Schedule VI.\n\n"
                "**The Commercial Frontier:** Ontario's high-tech greenhouses can export elite plant genetics, virus-free propagation stock, "
                "and unrooted ornamental cuttings directly into India's expanding commercial horticultural market at 0%–10% tariffs."
            )

    st.divider()

    # 5. Download Section
    st.markdown("### 📥 Export Opportunity Matrix")
    csv_india = df_india.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="Download Full India CEPA Opportunity Matrix (CSV)",
        data=csv_india,
        file_name="Ontario_India_CEPA_AgriFood_Opportunities.csv",
        mime="text/csv",
    )

st.caption("Ontario Trade Exposure Dashboard | Built for Ontario Federation of Agriculture (OFA)")

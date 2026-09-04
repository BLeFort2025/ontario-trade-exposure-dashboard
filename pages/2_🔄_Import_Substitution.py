import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from lib.data_loader import (
    get_net_balance, 
    get_import_substitution_matrix, 
    calculate_substitution_impact
)
from lib.chapter_labels import (
    chapter_label, 
    chapter_short, 
    AGRI_FOOD_CHAPTERS, 
    VALUE_ADD_COMPLEXES
)

st.set_page_config(page_title="Import Substitution Engine", page_icon="🔄", layout="wide")

def format_currency(value):
    if pd.isna(value) or value is None:
        return "$0"
    if abs(value) >= 1e9:
        return f"${value/1e9:,.2f}B"
    elif abs(value) >= 1e6:
        return f"${value/1e6:,.1f}M"
    else:
        return f"${value:,.0f}"

st.title("🔄 Import Substitution & Domestic Processing Engine")
st.caption("Identifying high-feasibility opportunities to displace U.S. imports, expand domestic processing, and simulate provincial GDP and job gains.")

# Global Year Selector
selected_year = st.session_state.get('selected_year', '2025')
st.write(f"**Analyzing Trade Year:** {selected_year}")

# Load master substitution matrix
try:
    sub_matrix = get_import_substitution_matrix(selected_year)
except Exception as e:
    st.error(f"Error loading substitution matrix: {e}")
    sub_matrix = pd.DataFrame()

# ── 4-TAB NAVIGATION ────────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs([
    "🎯 Low-Hanging Fruit & Deficit Explorer",
    "🏭 Raw vs. Processed Value-Add Engine",
    "📈 Economic Impact & Job Simulator",
    "🍁 Inter-Provincial & National Replacement"
])

# ====================================================================
# TAB 1: LOW-HANGING FRUIT & DEFICIT EXPLORER
# ====================================================================
with tab1:
    st.header("🎯 Domestic Substitution Feasibility Explorer")
    st.markdown(
        """
        Not all import deficits can be displaced. Canada’s climate limits commercial production of tropical crops 
        (e.g., bananas, citrus, cocoa beans, coffee). This engine isolates **high-feasibility domestic commodities**—where 
        Ontario already possesses proven primary agricultural or food processing capacity.
        """
    )
    
    if not sub_matrix.empty:
        # Deficit filter: imports > exports
        deficits_all = sub_matrix[sub_matrix['net_balance'] < 0].copy()
        
        # Headline KPI row
        tot_all_deficit = deficits_all['net_deficit_cad'].sum()
        high_feas_df = deficits_all[deficits_all['feasibility_tier'] == '🟢 High Domestic Feasibility']
        tot_high_feas_deficit = high_feas_df['net_deficit_cad'].sum()
        
        tariff_amp_df = deficits_all[deficits_all['faces_counter_tariff'] == True]
        tot_tariff_amp_deficit = tariff_amp_df['net_deficit_cad'].sum()
        
        kpi1, kpi2, kpi3, kpi4 = st.columns(4)
        kpi1.metric("Total Net Import Deficit", format_currency(tot_all_deficit), help="All negative trade balances across all imported HS-6 codes.")
        kpi2.metric("High Domestic Feasibility Deficit", format_currency(tot_high_feas_deficit), delta=f"{(tot_high_feas_deficit/tot_all_deficit)*100:.1f}% of total", delta_color="normal", help="Commodities Ontario actively produces at scale.")
        kpi3.metric("Counter-Tariff Amplified", format_currency(tot_tariff_amp_deficit), delta="15-50% Price Advantage", delta_color="normal", help="Deficit goods facing Canada retaliatory tariffs.")
        kpi4.metric("High-Feasibility Lines", f"{len(high_feas_df):,} HS-6 codes")
        
        st.markdown("---")
        
        # Interactive Controls
        ctrl_col1, ctrl_col2, ctrl_col3 = st.columns([2, 2, 1])
        with ctrl_col1:
            tier_options = list(sub_matrix['feasibility_tier'].unique())
            selected_tiers = st.multiselect(
                "Filter by Substitution Feasibility:",
                options=tier_options,
                default=['🟢 High Domestic Feasibility']
            )
        with ctrl_col2:
            all_chapters = sorted(list(sub_matrix['hs2_chapter'].unique()))
            selected_chaps = st.multiselect(
                "Filter by HS-2 Chapter (Optional):",
                options=all_chapters,
                format_func=lambda c: f"{c} - {chapter_short(c)}"
            )
        with ctrl_col3:
            show_tariffs_only = st.checkbox("Only Counter-Tariff Affected", value=False)
            
        # Filtered DataFrame
        filtered_sub = deficits_all[deficits_all['feasibility_tier'].isin(selected_tiers)].copy()
        if selected_chaps:
            filtered_sub = filtered_sub[filtered_sub['hs2_chapter'].isin(selected_chaps)]
        if show_tariffs_only:
            filtered_sub = filtered_sub[filtered_sub['faces_counter_tariff'] == True]
            
        st.subheader("Opportunity Quadrant: Trade Volume vs. Deficit Size")
        st.caption("Larger bubble = greater net deficit. Top-left quadrant represents high imports with low domestic exports.")
        
        if not filtered_sub.empty:
            scatter_df = filtered_sub.head(100).copy()
            scatter_df['Exports (M)'] = scatter_df['exports'] / 1e6
            scatter_df['Imports (M)'] = scatter_df['imports'] / 1e6
            scatter_df['Deficit (M)'] = scatter_df['net_deficit_cad'] / 1e6
            scatter_df['Short Desc'] = scatter_df['commodity_desc'].astype(str).str[:40]
            
            fig_scatter = px.scatter(
                scatter_df,
                x='Exports (M)',
                y='Imports (M)',
                size='Deficit (M)',
                color='feasibility_tier',
                hover_name='Short Desc',
                hover_data={'hs6_code': True, 'Exports (M)': ':.1f', 'Imports (M)': ':.1f', 'Deficit (M)': ':.1f'},
                labels={'Exports (M)': 'Ontario Exports to U.S. ($M CAD)', 'Imports (M)': 'Ontario Imports from U.S. ($M CAD)'},
                color_discrete_map={
                    '🟢 High Domestic Feasibility': '#2ca02c',
                    '🟡 Moderate / Seasonal': '#ff7f0e',
                    '⚪ Low / Non-Substitutable (Tropical/Exotic)': '#7f7f7f',
                    '⚙️ Industrial / Non-Ag': '#1f77b4'
                },
                height=500
            )
            st.plotly_chart(fig_scatter, use_container_width=True)
        
        # Top Ranked Table
        st.subheader("📋 Top 50 Ranked Import Substitution Opportunities")
        table_df = filtered_sub.head(50).copy()
        
        table_df['Chapter'] = table_df['hs2_chapter'].apply(chapter_short)
        table_df['Description'] = table_df['commodity_desc'].astype(str).str[:55] + '...'
        table_df['Exports (CAD)'] = table_df['exports'].apply(format_currency)
        table_df['Imports (CAD)'] = table_df['imports'].apply(format_currency)
        table_df['Net Deficit (CAD)'] = table_df['net_deficit_cad'].apply(lambda x: f"-{format_currency(x)}")
        table_df['Counter-Tariff'] = table_df['counter_tariff_pct'].apply(lambda x: f"Yes ({x:.0f}%)" if pd.notna(x) and x > 0 else "No")
        table_df['Top U.S. Sources'] = table_df['top_import_states'].fillna('U.S. General')
        
        disp_cols = [
            'hs6_code', 'Description', 'Chapter', 'feasibility_tier',
            'Exports (CAD)', 'Imports (CAD)', 'Net Deficit (CAD)', 'Counter-Tariff', 'Top U.S. Sources'
        ]
        st.dataframe(
            table_df[disp_cols].rename(columns={
                'hs6_code': 'HS-6 Code',
                'feasibility_tier': 'Feasibility Tier'
            }), 
            use_container_width=True, 
            hide_index=True
        )
        
        # Download Button
        csv_sub = filtered_sub.to_csv(index=False).encode('utf-8')
        st.download_button(
            "📥 Download Filtered Substitution Matrix (CSV)",
            data=csv_sub,
            file_name=f"ontario_import_substitution_opportunities_{selected_year}.csv",
            mime="text/csv"
        )
    else:
        st.info("No substitution matrix data available.")

# ====================================================================
# TAB 2: RAW VS. PROCESSED VALUE-ADD ENGINE
# ====================================================================
with tab2:
    st.header("🏭 Upstream vs. Downstream: The Value-Add Disconnect")
    st.markdown(
        """
        A fundamental structural vulnerability of Ontario agriculture is the **"Upstream/Downstream Disconnect"**: 
        we frequently export raw, unprocessed agricultural commodities in bulk south of the border, only to import higher-value 
        processed foods, ingredients, and animal feeds back from the United States.
        
        Expanding domestic processing captures the value-added margin, insulates farmers from cross-border tariff risk, 
        and creates stable, year-round domestic buyer demand.
        """
    )
    
    if not sub_matrix.empty:
        complex_names = list(VALUE_ADD_COMPLEXES.keys())
        selected_complex = st.radio(
            "**Select Agricultural Complex to Analyze:**",
            options=complex_names,
            horizontal=True
        )
        
        complex_data = VALUE_ADD_COMPLEXES[selected_complex]
        st.info(f"{complex_data['icon']} **{selected_complex}:** {complex_data['description']}")
        
        cdf = sub_matrix[sub_matrix['value_add_complex'] == selected_complex].copy()
        
        raw_df = cdf[cdf['complex_role'] == 'Raw / Primary Commodity']
        proc_df = cdf[cdf['complex_role'] == 'Value-Added Processed']
        
        raw_exp = raw_df['exports'].sum()
        raw_imp = raw_df['imports'].sum()
        raw_net = raw_exp - raw_imp
        
        proc_exp = proc_df['exports'].sum()
        proc_imp = proc_df['imports'].sum()
        proc_net = proc_exp - proc_imp
        
        # Scorecard Row
        sc1, sc2, sc3 = st.columns(3)
        sc1.metric(
            "Raw Primary Commodity Balance", 
            format_currency(raw_net), 
            delta=f"Exports: {format_currency(raw_exp)} | Imports: {format_currency(raw_imp)}",
            delta_color="normal" if raw_net >= 0 else "inverse"
        )
        sc2.metric(
            "Processed Value-Add Balance", 
            format_currency(proc_net), 
            delta=f"Imports: {format_currency(proc_imp)} | Exports: {format_currency(proc_exp)}",
            delta_color="normal" if proc_net >= 0 else "inverse"
        )
        sc3.metric(
            "Domestic Value-Add Opportunity", 
            format_currency(abs(proc_net)) if proc_net < 0 else "$0 (Surplus)",
            delta="Potential Processing Replacement",
            delta_color="normal"
        )
        
        st.markdown("---")
        
        # Comparison Bar Chart
        comp_chart_df = pd.DataFrame([
            {"Stage": "1. Raw Primary Commodity", "Flow": "Ontario Exports", "Value (M CAD)": raw_exp / 1e6},
            {"Stage": "1. Raw Primary Commodity", "Flow": "Ontario Imports", "Value (M CAD)": raw_imp / 1e6},
            {"Stage": "2. Value-Added Processed", "Flow": "Ontario Exports", "Value (M CAD)": proc_exp / 1e6},
            {"Stage": "2. Value-Added Processed", "Flow": "Ontario Imports", "Value (M CAD)": proc_imp / 1e6},
        ])
        
        fig_comp = px.bar(
            comp_chart_df,
            x="Stage",
            y="Value (M CAD)",
            color="Flow",
            barmode="group",
            title=f"{selected_complex}: Raw vs. Processed Trade Balance (2025)",
            color_discrete_map={"Ontario Exports": "#2ca02c", "Ontario Imports": "#d62728"},
            height=400
        )
        st.plotly_chart(fig_comp, use_container_width=True)
        
        # Breakdown Table
        st.subheader(f"Commodities within {selected_complex}")
        cdf_disp = cdf[['hs6_code', 'commodity_desc', 'complex_role', 'exports', 'imports', 'net_balance']].copy()
        cdf_disp['Exports'] = cdf_disp['exports'].apply(format_currency)
        cdf_disp['Imports'] = cdf_disp['imports'].apply(format_currency)
        cdf_disp['Net Balance'] = cdf_disp['net_balance'].apply(format_currency)
        
        st.dataframe(
            cdf_disp[['hs6_code', 'commodity_desc', 'complex_role', 'Exports', 'Imports', 'Net Balance']].rename(columns={
                'hs6_code': 'HS-6 Code',
                'commodity_desc': 'Description',
                'complex_role': 'Value Chain Role'
            }).sort_values(by='Value Chain Role', ascending=False),
            use_container_width=True,
            hide_index=True
        )

# ====================================================================
# TAB 3: ECONOMIC IMPACT & JOB CREATION SIMULATOR
# ====================================================================
with tab3:
    st.header("📈 Macroeconomic Impact & Job Creation Simulator")
    st.markdown(
        """
        Simulate the macroeconomic return to Ontario's economy if domestic producers and food processors 
        displace a portion of current U.S. agricultural imports.
        
        **Methodological Baseline:** Calculations use Statistics Canada's validated provincial Input-Output multipliers 
        (Table 36-10-0595-01 / Ontario SUT Multiplier Engine), quantifying direct, indirect supply-chain, and induced consumer spending effects.
        """
    )
    
    if not sub_matrix.empty:
        sim_col1, sim_col2 = st.columns([1, 1])
        
        with sim_col1:
            st.subheader("⚙️ Simulation Parameters")
            
            sim_target_scope = st.selectbox(
                "Select Substitution Target Pool:",
                options=[
                    "All High-Feasibility Agri-Food ($9.47B pool)",
                    "Counter-Tariff Amplified Goods ($2.46B pool)",
                    "Red Meat & Livestock Processing Deficit ($450.6M)",
                    "Corn & Grain Processing Deficit ($918.4M)",
                    "Dairy Value-Add Processing Deficit ($370.2M)",
                    "Soybean Value-Add Processing Deficit ($281.9M)",
                    "Greenhouse & Processing Veg Deficit ($128.0M)",
                ]
            )
            
            # Map target pool to dollars
            if "All High-Feasibility" in sim_target_scope:
                pool_dollars = tot_high_feas_deficit
                sector_type = "food_manufacturing"
            elif "Counter-Tariff" in sim_target_scope:
                pool_dollars = tot_tariff_amp_deficit
                sector_type = "food_manufacturing"
            elif "Red Meat" in sim_target_scope:
                pool_dollars = 450.6e6
                sector_type = "food_manufacturing"
            elif "Corn & Grain" in sim_target_scope:
                pool_dollars = 918.4e6
                sector_type = "food_manufacturing"
            elif "Dairy" in sim_target_scope:
                pool_dollars = 370.2e6
                sector_type = "food_manufacturing"
            elif "Soybean" in sim_target_scope:
                pool_dollars = 281.9e6
                sector_type = "food_manufacturing"
            else:
                pool_dollars = 128.0e6
                sector_type = "food_manufacturing"
                
            disp_rate_pct = st.slider(
                "Target Import Displacement Rate (%):",
                min_value=5,
                max_value=50,
                value=15,
                step=5,
                help="The percentage of currently imported U.S. goods displaced by Ontario production."
            )
            
            displaced_cad = pool_dollars * (disp_rate_pct / 100.0)
            st.metric("Total Domestic Output Generated", format_currency(displaced_cad), help="Dollar value of new domestic manufacturing/farm production.")
            
        with sim_col2:
            st.subheader("📊 Projected Economic Returns")
            
            impact = calculate_substitution_impact(displaced_cad, sector=sector_type)
            
            res1, res2 = st.columns(2)
            res1.metric("Total Provincial GDP Generated", format_currency(impact['gdp_total']), delta=f"Direct: {format_currency(impact['gdp_direct'])}")
            res2.metric("Total FTE Jobs Created", f"{impact['jobs_total']:,} Jobs", delta=f"Direct: {impact['jobs_direct']:,} FTE")
            
            res3, res4 = st.columns(2)
            res3.metric("Total Labour Income / Payroll", format_currency(impact['labour_income_total']))
            res4.metric("Farm-Gate Revenue Upside", format_currency(impact['farm_gate_revenue']), delta="Direct to Farmers", delta_color="normal")
            
        st.markdown("---")
        
        # Economic Ripple Breakdown Chart
        st.subheader("Economic Multiplier Breakdown (Direct vs. Indirect & Induced)")
        
        breakdown_df = pd.DataFrame([
            {"Metric": "GDP ($M CAD)", "Direct": impact['gdp_direct'] / 1e6, "Indirect & Induced": impact['gdp_indirect_induced'] / 1e6},
            {"Metric": "Labour Income ($M CAD)", "Direct": (impact['labour_income_total'] * 0.47) / 1e6, "Indirect & Induced": (impact['labour_income_total'] * 0.53) / 1e6},
            {"Metric": "FTE Jobs (Units)", "Direct": impact['jobs_direct'], "Indirect & Induced": impact['jobs_indirect_induced']},
        ])
        
        fig_breakdown = px.bar(
            breakdown_df,
            x="Metric",
            y=["Direct", "Indirect & Induced"],
            barmode="stack",
            title=f"Economic Ripple Effects of Displacing {disp_rate_pct}% ({format_currency(displaced_cad)}) of U.S. Imports",
            color_discrete_sequence=["#2ca02c", "#1f77b4"],
            height=400
        )
        st.plotly_chart(fig_breakdown, use_container_width=True)
        
        # Methodology Callout
        with st.expander("ℹ️ Multiplier Methodology & Multiplier Sources"):
            st.markdown(
                """
                * **Data Source:** Statistics Canada Table 36-10-0595-01 (Input-Output Multipliers, provincial and territorial, Supply-Use Tables).
                * **Model Structure:** Open Type II provincial input-output multiplier model capturing backward supply-chain linkages (indirect) and consumer wage respending (induced).
                * **Food & Beverage Processing (NAICS 311/312):**
                  * Total GDP Multiplier: **0.72** (for every \$1.00 of food manufacturing output, \$0.72 in provincial value-added GDP is created).
                  * Total Employment Multiplier: **5.8 FTE jobs** per \$1 Million in output.
                  * Farm-Gate Share: **35%** of gross processing output directly translates into farm-gate agricultural commodity purchases from Ontario producers.
                """
            )

# ====================================================================
# TAB 4: INTER-PROVINCIAL & NATIONAL REPLACEMENT
# ====================================================================
with tab4:
    st.header("🍁 Inter-Provincial Trade & National Food Autonomy")
    st.markdown(
        """
        Import replacement does not stop at Ontario’s borders. Canada as a whole imports over **$25 Billion** in agricultural 
        and food products from the United States that could be produced domestically. 
        
        Ontario possesses the manufacturing scale, greenhouse infrastructure, and logistics network to supply neighboring 
        provinces (Quebec, Atlantic Canada, the Prairies, and BC), replacing foreign imports on a national scale.
        """
    )
    
    col_nat1, col_nat2 = st.columns(2)
    
    with col_nat1:
        st.subheader("Top Ontario Candidates for Inter-Provincial Expansion")
        st.markdown(
            """
            Based on Ontario's domestic scale and production surpluses, these 5 sectors represent the highest-potential 
            candidates to displace foreign food imports across other Canadian provinces:
            
            1. **🍅 Greenhouse Vegetables (Tomatoes, Peppers, Cucumbers):**
               * *Ontario Surplus:* **+$1.4 Billion CAD**.
               * *National Opportunity:* Replacing Mexican and California field produce in Quebec and Atlantic Canada year-round through Ontario's Kingsville/Leamington cluster.
            2. **🍞 Bakery & Cereal Preparations:**
               * *Ontario Scale:* Canada's largest bakery manufacturing hub (industrial bread, pasta, tortillas, snack foods).
               * *National Opportunity:* Displacing Midwest U.S. bakery shipments into Western and Eastern Canada.
            3. **🥩 Value-Added Pork & Deli Meats:**
               * *Ontario Strength:* High provincial hog production and federally inspected processing capacity (Sofina, Conestoga).
               * *National Opportunity:* Supplying pre-packaged deli and sausages to Maritime and Prairie retail chains.
            4. **🐕 Pet Food & Animal Feed Preparations:**
               * *The Deficit Reality:* Canada imports over **$1.5B in pet food**, mostly from the U.S.
               * *Ontario Opportunity:* Utilizing local livestock by-products and grain to manufacture domestic pet food for all provinces.
            5. **🍎 Craft Cider, Wine & Specialty Beverages:**
               * *Ontario Clusters:* Niagara, Prince Edward County, and Georgian Bay apple/grape production.
               * *National Opportunity:* Displacing imported U.S. hard seltzers, ciders, and table wines in provincial liquor board channels.
            """
        )
        
    with col_nat2:
        st.subheader("Key Policy Levers to Unlock Inter-Provincial Markets")
        st.info(
            """
            **What OFA & Industry Must Advocate For:**
            * 🚛 **Internal Trade Barrier Reduction:** Harmonizing inter-provincial trucking weight restrictions, axle configurations, and road regulations along the 401/Trans-Canada corridor.
            * 🏷️ **Bilingual Packaging & Standardized Labeling:** Streamlining federal and provincial packaging regulations so Ontario processors can sell seamlessly into Quebec without redundant SKUs.
            * 🏛️ **Public Sector & Institutional Procurement:** Establishing "Buy Canadian / Buy Local" procurement benchmarks for hospitals, schools, and correctional facilities across all 10 provinces.
            * ⚡ **Processing Infrastructure Capital Grants:** Matching provincial and federal agri-food capital funds to expand cold-storage, freezing capacity, and high-speed processing lines.
            """
        )

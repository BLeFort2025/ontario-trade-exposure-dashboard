import streamlit as st
import pandas as pd
import plotly.express as px
from lib.data_loader import (
    get_tariff_matched_imports, 
    get_tariff_matched_exports, 
    get_canada_counter_tariffs, 
    get_us_section338_tariffs,
    get_us_section338_oct23_reshuffle,
    evaluate_aafc_remission_ruling,
    get_oct23_naics_packaging_context
)
from lib.chapter_labels import chapter_label
from lib.geo_utils import get_valid_state_names

st.set_page_config(page_title="Tariff Impact Tracker", layout="wide")

st.title("🛡️ Tariff Impact Tracker")
st.subheader("Canada's Counter-Tariffs & Remissions vs. U.S. Section 338 Tariffs (Updated for Oct 23, 2026 Reshuffle)")

selected_year = st.session_state.get('selected_year', '2025')
st.write(f"**Analyzing Trade Year:** {selected_year}")

tab1, tab2 = st.tabs(['🇨🇦 Canada Counter-Tariffs (Imports & Remissions)', '🇺🇸 U.S. Section 338 (Exports)'])

def format_currency(val):
    if abs(val) >= 1e9:
        return f"${val/1e9:,.2f}B"
    elif abs(val) >= 1e6:
        return f"${val/1e6:,.1f}M"
    else:
        return f"${val:,.0f}"

with tab1:
    st.header("Canada Counter-Tariffs & Remission Framework")
    
    # Official Remission Regulatory Banner
    st.info(
        """
        ℹ️ **Federal Remission & Counter-Tariff Framework (CBSA Customs Notice 26-23 & AAFC Oct 2026 Guidance):**  
        Following Order in Council P.C. 2026-0785, Canada matches U.S. tariffs dollar-for-dollar across 3 statutory surtax tiers entered in **Field 85 (Surtax Code)** of the Commercial Accounting Declaration (CAD):
        * **CARM Code `26186A` (15% Surtax):** Schedule 1 goods (headline rate for combine parts and industrial machinery).
        * **CARM Code `26186B` (25% Surtax):** Schedule 2 goods (including farm and livestock trailers under `HS 8716.39`).
        * **CARM Code `26186C` (50% Surtax):** Schedule 3 goods (targeted consumer ag/food: dairy `HS 0402/0404`, honey `0409`, bakery mixes `1901.20`).
        * **Special Authorization Remission Code `25-0466C` (0% Net Duty Through June 30, 2027):** Pursuant to the *United States Surtax Remission Order*, "steel goods" are strictly limited to **Chapters 72 and 73**. All goods made of steel classified outside Chapters 72 and 73—including agricultural equipment and combine parts under **Chapter 84 (`HS 8433.90`, `8433.20`)**—are legally classified as **"non-steel goods"** and qualify for **0% net duty horizontal remission** when imported for **agriculture, agri-food, and food & beverage processing or packaging (NAICS 11 & 31–33)** for imports up to **June 30, 2027**.
        """
    )

    # --- INTERACTIVE AAFC HORIZONTAL REMISSION & CHAPTER 72/73 RULING TOOL ---
    with st.expander("🧭 **Interactive AAFC Horizontal Remission & Chapter 72/73 'Steel vs. Non-Steel' Boundary Ruling Tool**", expanded=True):
        st.caption(
            "Verify whether any imported tariff line qualifies for 0% horizontal remission under AAFC's October 2026 "
            "guidance, CBSA Customs Notice 26-23, and the *United States Surtax Remission Order (SOR/2025-122)*."
        )
        rul_col1, rul_col2 = st.columns([1.2, 1.8])
        with rul_col1:
            hs_query_input = st.text_input(
                "Enter 4, 6, or 8-Digit HS Tariff Code (e.g., `8433.90`, `7308.90`, `8716.39`, `1901.20`):",
                value="8433.90",
                key="remission_hs_input"
            )
        with rul_col2:
            end_use_input = st.selectbox(
                "Select Importer End-Use / NAICS Classification:",
                options=[
                    "🌾 Primary Agriculture (NAICS 111 / 112 — incl. NAICS 1114 Greenhouse, Nursery & Floriculture)",
                    "🏭 Food, Beverage & Feed Processing (NAICS 311 / 312)",
                    "📦 Food, Beverage & Agricultural Produce Packaging",
                    "🏢 General Commercial / Non-Manufacturing / Retail Distribution",
                ],
                index=0,
                key="remission_end_use_input"
            )

        ruling = evaluate_aafc_remission_ruling(hs_query_input, end_use_input)
        if ruling.get("valid"):
            rc1, rc2, rc3, rc4 = st.columns(4)
            rc1.metric(
                "Chapter 72/73 Steel Status",
                "Ch. 72/73 Steel Good" if ruling["is_steel_ch72_73"] else "Non-Steel Good (Outside 72/73)",
                delta=f"Chapter {ruling['hs2_chapter']}",
                delta_color="inverse" if ruling["is_steel_ch72_73"] else "normal"
            )
            rc2.metric(
                "Headline Counter-Tariff",
                f"{ruling['headline_rate_pct']:.0f}%" if ruling["in_counter_tariff_schedule"] else "0% (Not Listed)",
                delta=ruling["carm_surtax_code"],
                delta_color="off"
            )
            rc3.metric(
                "Effective Net Duty Rate",
                f"{ruling['net_rate_pct']:.0f}%",
                delta="Waived via Code 25-0466C" if (ruling["in_counter_tariff_schedule"] and ruling["net_rate_pct"] == 0) else ruling["ruling_badge"],
                delta_color="normal" if ruling["net_rate_pct"] == 0 else "inverse"
            )
            rc4.metric(
                "Remission Sunset Date",
                ruling["sunset_date"],
                delta="CBSA Field 84: 25-0466C" if "25-0466C" in ruling["special_auth_code"] else "No Ag Horizontal Waiver",
                delta_color="normal" if "25-0466C" in ruling["special_auth_code"] else "off"
            )
            if ruling["net_rate_pct"] == 0 and ruling["in_counter_tariff_schedule"]:
                st.success(f"**{ruling['ruling_badge']}** — **{ruling['matched_desc']}**: {ruling['statutory_explanation']}")
            elif not ruling["in_counter_tariff_schedule"]:
                st.info(f"**{ruling['ruling_badge']}**: {ruling['statutory_explanation']}")
            else:
                st.error(f"**{ruling['ruling_badge']}** — **{ruling['matched_desc']}**: {ruling['statutory_explanation']}")
        else:
            st.warning(ruling.get("error", "Please enter a valid HS code."))
    
    try:
        imports_df = get_tariff_matched_imports(year=selected_year)
    except Exception as e:
        st.error(f"Error loading import data: {e}")
        imports_df = pd.DataFrame()

    if not imports_df.empty:
        matched_imports = imports_df[imports_df['has_tariff'] == True].copy()

        if not matched_imports.empty:
            # Remission View Toggle
            view_mode = st.radio(
                "**Tariff Accounting Mode:**",
                ["🟢 Net Exposure (After CBSA Code 25-0466C Remission)", "🔴 Gross Exposure (Headline Counter-Tariffs)"],
                horizontal=True
            )
            is_net_view = "Net Exposure" in view_mode

            total_gross_imports = matched_imports['value_cad'].sum()
            total_gross_tariffs = matched_imports['tariff_dollars_gross'].sum()
            total_net_tariffs = matched_imports['tariff_dollars_net'].sum()
            total_tariffs_saved = matched_imports['tariff_dollars_saved'].sum()
            
            lines_matched = matched_imports['hs6_code'].nunique()
            
            # Metric Columns
            col1, col2, col3, col4 = st.columns(4)
            if is_net_view:
                col1.metric("Total Affected Imports", format_currency(total_gross_imports))
                col2.metric("Net Tariff Duties Payable", format_currency(total_net_tariffs), delta=f"-{format_currency(total_tariffs_saved)} waived", delta_color="normal")
                col3.metric("Duties Waived (Code 25-0466C)", format_currency(total_tariffs_saved), delta="Zero Cash Drag", delta_color="normal")
                col4.metric("Combine Parts (`8433.90`)", "0.0% Net", delta="Waived via 25-0466C", delta_color="normal")
            else:
                col1.metric("Total Affected Imports", format_currency(total_gross_imports))
                col2.metric("Gross Surtax Assessed", format_currency(total_gross_tariffs))
                col3.metric("Tariff Lines Matched", f"{lines_matched} HS-6 codes")
                col4.metric("Combine Parts (`8433.90`)", "15.0% Headline", delta="Without Remission", delta_color="inverse")
            
            st.markdown("---")
            
            # --- AG & FOOD PROCESSING SPOTLIGHT ---
            st.subheader("🚜 Agricultural Machinery & Food Processing Spotlight")
            st.caption("Status of key agricultural and food manufacturing lines under the Sept 8 counter-tariffs and remission rules:")
            
            ag_spotlight_codes = ['843390', '843320', '190120', '871639', '843311']
            spotlight_df = matched_imports[matched_imports['hs6_code'].isin(ag_spotlight_codes)].copy()
            
            if not spotlight_df.empty:
                spotlight_agg = spotlight_df.groupby(
                    ['hs6_code', 'commodity_desc', 'tariff_rate_pct', 'remission_status', 'net_tariff_pct'], as_index=False
                ).agg({
                    'value_cad': 'sum',
                    'tariff_dollars_gross': 'sum',
                    'tariff_dollars_saved': 'sum',
                    'tariff_dollars_net': 'sum'
                }).sort_values(by='value_cad', ascending=False)
                
                spotlight_agg['Import Value'] = spotlight_agg['value_cad'].apply(format_currency)
                spotlight_agg['Headline Tariff'] = spotlight_agg['tariff_rate_pct'].apply(lambda x: f"{x:.0f}%")
                spotlight_agg['Net Tariff'] = spotlight_agg['net_tariff_pct'].apply(lambda x: f"{x:.0f}%" if x > 0 else "0% (Waived)")
                spotlight_agg['Duties Saved'] = spotlight_agg['tariff_dollars_saved'].apply(format_currency)
                spotlight_agg['Net Duty Cost'] = spotlight_agg['tariff_dollars_net'].apply(format_currency)
                
                spotlight_disp = spotlight_agg[[
                    'hs6_code', 'commodity_desc', 'Headline Tariff', 'remission_status', 'Net Tariff', 
                    'Import Value', 'Duties Saved', 'Net Duty Cost'
                ]].rename(columns={
                    'hs6_code': 'HS-6 Code',
                    'commodity_desc': 'Commodity Description',
                    'remission_status': 'Remission Eligibility'
                })
                
                st.dataframe(spotlight_disp, use_container_width=True, hide_index=True)
            
            st.markdown("---")
            
            # --- CHARTS ROW ---
            col_chart1, col_chart2 = st.columns(2)
            
            with col_chart1:
                st.subheader("Remission & Duty Status Breakdown")
                status_df = matched_imports.groupby('remission_status')['value_cad'].sum().reset_index()
                status_df['Formatted_Val'] = status_df['value_cad'].apply(format_currency)
                fig_pie = px.pie(
                    status_df, 
                    values='value_cad', 
                    names='remission_status', 
                    hole=0.4,
                    color_discrete_sequence=['#2ca02c', '#1f77b4', '#d62728', '#ff7f0e', '#9467bd']
                )
                fig_pie.update_traces(textposition='inside', textinfo='percent+label')
                st.plotly_chart(fig_pie, use_container_width=True)
            
            with col_chart2:
                st.subheader("Affected Imports by HS Chapter")
                matched_imports['chapter_name'] = matched_imports['hs2_chapter'].apply(
                    lambda x: f"{str(x).zfill(2)} - {chapter_label(str(x).zfill(2))}"
                )
                chap_df = matched_imports.groupby(['chapter_name', 'remission_status'])['value_cad'].sum().reset_index()
                
                fig_bar = px.bar(
                    chap_df, 
                    x='value_cad', 
                    y='chapter_name', 
                    color='remission_status', 
                    orientation='h', 
                    labels={'value_cad': 'Import Value (CAD)', 'chapter_name': 'HS-2 Chapter', 'remission_status': 'Status'},
                    color_discrete_sequence=['#2ca02c', '#1f77b4', '#d62728', '#ff7f0e', '#9467bd']
                )
                fig_bar.update_layout(yaxis={'categoryorder':'total ascending'})
                st.plotly_chart(fig_bar, use_container_width=True)
            
            # --- DETAILED DATA TABLE ---
            st.subheader("📋 Comprehensive Tariff-Matched Import Lines")
            
            filter_col1, filter_col2 = st.columns([2, 1])
            with filter_col1:
                status_filter = st.multiselect(
                    "Filter by Remission Status:",
                    options=matched_imports['remission_status'].unique(),
                    default=matched_imports['remission_status'].unique()
                )
            with filter_col2:
                search_kw = st.text_input("Search description / HS-6:", "")

            filtered_df = matched_imports[matched_imports['remission_status'].isin(status_filter)].copy()
            if search_kw:
                filtered_df = filtered_df[
                    filtered_df['commodity_desc'].str.contains(search_kw, case=False, na=False) |
                    filtered_df['hs6_code'].str.contains(search_kw, na=False)
                ]

            # Aggregation for display
            table_agg = filtered_df.groupby(
                ['hs6_code', 'commodity_desc', 'hs2_chapter', 'tariff_rate_pct', 'remission_status', 'net_tariff_pct'], as_index=False
            ).agg({
                'value_cad': 'sum',
                'tariff_dollars_gross': 'sum',
                'tariff_dollars_saved': 'sum',
                'tariff_dollars_net': 'sum'
            }).sort_values(by='value_cad', ascending=False)
            
            table_agg['Import Value (CAD)'] = table_agg['value_cad'].apply(format_currency)
            table_agg['Gross Tariff Cost'] = table_agg['tariff_dollars_gross'].apply(format_currency)
            table_agg['Duties Saved'] = table_agg['tariff_dollars_saved'].apply(format_currency)
            table_agg['Net Tariff Cost'] = table_agg['tariff_dollars_net'].apply(format_currency)
            table_agg['Headline Rate'] = table_agg['tariff_rate_pct'].apply(lambda x: f"{x:.0f}%")
            table_agg['Net Rate'] = table_agg['net_tariff_pct'].apply(lambda x: f"{x:.0f}%")
            
            disp_table = table_agg[[
                'hs6_code', 'commodity_desc', 'Headline Rate', 'remission_status', 'Net Rate',
                'Import Value (CAD)', 'Duties Saved', 'Net Tariff Cost'
            ]].rename(columns={
                'hs6_code': 'HS-6 Code',
                'commodity_desc': 'Commodity Description',
                'remission_status': 'Remission Status'
            })

            st.dataframe(disp_table, use_container_width=True, hide_index=True)
            
            csv = filtered_df.to_csv(index=False).encode('utf-8')
            st.download_button(
                "📥 Download Tariff & Remission Dataset as CSV", 
                data=csv, 
                file_name=f"canada_counter_tariffs_remissions_{selected_year}.csv", 
                mime="text/csv"
            )
        else:
            st.info("No tariff matched imports found for the selected year.")
    else:
        st.info("No import data available for the selected year.")


with tab2:
    st.header("U.S. Section 338 Tariffs, Import Bans & October 23, 2026 Reshuffle (Ontario Exports)")
    st.caption("Tracking Proclamations 11046–11048 (Aug 22), Proclamations 11061–11065 (Sept 15/29), and the October 23, 2026 Reshuffle (Effective Oct 30, 2026):")
    
    st.warning(
        """
        🔄 **NEW — October 23, 2026 White House Proclamation (Effective Oct 30, 2026 at 12:01 a.m. EDT):**  
        The U.S. further modified Proclamation 11048 (`HTSUS 9903.03.14` — 50% Section 338 duty, applicable **regardless of USMCA/CUSMA preference** and **stacked on top of Section 232**):
        * **🟢 22 Tariff Lines REMOVED (Tariff Relief for Ag/Food Machinery & Packaging):** Removes the 50% duty from **egg, fruit & produce grading machines (`8433.60.00`, `$12.66M` ON exports)**, **food/beverage packaging, bottling, thermal processing & cold-chain refrigeration equipment (`8422.40.91`, `8422.30.91`, `8419.89.95`, `8418.69.01` — `$505.6M` in 6-digit ON exports)**, **9 food & produce packaging lines** (molded pulp egg/berry trays `4823.70.00`, corrugated boxes `4819.10.00`, aseptic dairy carton stock `4811.51.20/.40`, plastic produce crates `3923.10.90`, polyethylene bags `3923.21.00`, BOPP food film `3920.20.00`), **edible seaweed (`1212.21.00`, `$233.5K`)**, and **7 thin hardwood plywood lines (`4412.33/.34`)**.
        * **🔴 100 Tariff Lines ADDED (New 50% Duty Effective Oct 30):** Imposes a new 50% duty on **all 13 tariff lines of sweetened cocoa powder (`1806.10.05`–`1806.10.75`)** to block sugar-cocoa arbitrage (note: bulk chocolate `1806.20` and chocolate bars `1806.31/.32/.90` remain **exempt**), **heavy-duty multi-wall paper sacks >=40cm (`4819.30.00`, used for 20–25 kg seed/feed/flour/milk powder)**, **solid-sided wooden packing boxes (`4415.10.30`)**, **wooden food skewers/ice cream sticks (`4421.99.60`)**, **unprinted pressure-sensitive labels (`4821.90.20`)**, **orchard grafting putty (`3214.10.00`)**, **diagnostic lab reagents (`3822.19/.90`)**, **chest freezers <=800L (`8418.30.00`)**, **hand-operated steel valves (`8481.80.30`)**, and **43 wool, fine animal hair, coconut coir & textile carpet lines (`5701`–`5705`)**.
        * **🚨 Retained Primary Agriculture & Sept 8 Escalations:** **Primary Floriculture & Nursery (`0601`–`0604`, NAICS 1114)** and **Natural Honey (`0409.00.00`)** were **not removed** and remain subject to the 50% Section 338 tariff (`$438M` CAD exposed). Meanwhile, the Sept 8 Proclamations (`11061`–`11065`) enforced **import bans** on retail Canadian alcohol (`<=4L`) and whey/molasses (while exempting bulk whisky/spirits `>4L`), and added 50% tariffs on **22 cheese lines (`0406`, `$117.5M`)**, **modified animal/vegetable fats & oils (`1518.00.40`, `$217.4M`)**, and **raw bovine hides (`4101.50/.90`, `$28.4M`)**.
        """
    )

    # --- OCT 23, 2026 RESHUFFLE INTERACTIVE EXPLORER ---
    with st.expander("🔍 **Explore All 122 Tariff Lines in the October 23, 2026 Section 338 Reshuffle (22 Removed vs. 100 Added)**", expanded=True):
        try:
            oct23_df = get_us_section338_oct23_reshuffle()
        except Exception as e:
            st.error(f"Error loading Oct 23 reshuffle table: {e}")
            oct23_df = pd.DataFrame()

        if not oct23_df.empty:
            r_col1, r_col2, r_col3, r_col4 = st.columns(4)
            r_col1.metric("Lines Removed (Part A Relief)", "22 HTS Lines", delta="Ag/Food Machinery & Packaging", delta_color="normal")
            r_col2.metric("ON Machinery Exports Relieved", "$518.3M CAD", delta="8433.60 + 8422 + 8419 + 8418", delta_color="normal")
            r_col3.metric("Lines Added (Part B 50% Duty)", "100 HTS Lines", delta="13 Cocoa + 43 Wool/Carpet + 44 Ind/Pkg", delta_color="inverse")
            r_col4.metric("Effective Date & Time", "Oct 30, 2026", delta="12:01 a.m. EDT", delta_color="off")

            f_col1, f_col2, f_col3 = st.columns([1.3, 1.7, 1.2])
            with f_col1:
                act_filter = st.multiselect(
                    "Filter by Oct 23 Action:",
                    options=oct23_df["action"].unique().tolist(),
                    default=oct23_df["action"].unique().tolist(),
                    key="oct23_act"
                )
            with f_col2:
                cat_filter = st.multiselect(
                    "Filter by Sector Category:",
                    options=oct23_df["sector_category"].unique().tolist(),
                    default=oct23_df["sector_category"].unique().tolist(),
                    key="oct23_cat"
                )
            with f_col3:
                oct23_kw = st.text_input("Search HTS code or description:", "", key="oct23_kw")

            oct23_filt = oct23_df[
                oct23_df["action"].isin(act_filter) &
                oct23_df["sector_category"].isin(cat_filter)
            ].copy()
            if oct23_kw:
                oct23_filt = oct23_filt[
                    oct23_filt["htsus_code"].str.contains(oct23_kw, case=False, na=False) |
                    oct23_filt["description"].str.contains(oct23_kw, case=False, na=False) |
                    oct23_filt["ontario_ag_relevance"].str.contains(oct23_kw, case=False, na=False)
                ]

            oct23_disp = oct23_filt.copy()
            oct23_disp["ON->US 2024 (HS-6)"] = oct23_disp["on_us_exports_2024_cad"].apply(lambda v: format_currency(v) if v > 0 else "— (Non-Ag DB / $0)")
            oct23_disp["ON->US 2025 (HS-6)"] = oct23_disp["on_us_exports_2025_cad"].apply(lambda v: format_currency(v) if v > 0 else "— (Non-Ag DB / $0)")
            oct23_disp["ON->US 2026 YTD (HS-6)"] = oct23_disp["on_us_exports_2026_ytd_cad"].apply(lambda v: format_currency(v) if v > 0 else "— (Non-Ag DB / $0)")

            st.dataframe(
                oct23_disp[[
                    "action_short", "htsus_code", "sector_category", "description",
                    "ontario_ag_relevance", "ON->US 2024 (HS-6)", "ON->US 2025 (HS-6)", "ON->US 2026 YTD (HS-6)"
                ]].rename(columns={
                    "action_short": "Oct 30 Action",
                    "htsus_code": "HTSUS 8-Digit",
                    "sector_category": "Sector Category",
                    "description": "Official HTSUS Description",
                    "ontario_ag_relevance": "Ontario Agri-Food & Supply Chain Impact"
                }),
                use_container_width=True,
                hide_index=True
            )

            oct23_csv = oct23_filt.to_csv(index=False).encode("utf-8")
            st.download_button(
                "📥 Download Full Oct 23, 2026 Section 338 Reshuffle (122 HTS Lines) as CSV",
                data=oct23_csv,
                file_name="us_section338_oct23_2026_reshuffle_122_lines.csv",
                mime="text/csv",
                key="oct23_dl"
            )

    # --- PHASE 5: U.S. CENSUS 4-DIGIT NAICS PACKAGING, WOOD, PAPER & MACHINERY CONTEXT ---
    with st.expander("📦 **Empirical Bilateral Trade Context for Non-Agri-Food Packaging, Wood, Paper, Plastics & Machinery Sectors (`census_us_state_exports_to_canada`)**", expanded=False):
        st.markdown(
            """
            Because `state_hs_trade` is scoped specifically to **HS Chapters 01–24 (Agri-Food)** and **Chapters 31, 38, 84, 87 (Farm Inputs & Machinery)**, 
            non-agricultural industrial packaging, wood, paper, plastics, coatings, and textile lines in **HS Chapters 32, 39, 44, 48, and 57** display `— (Non-Ag DB / $0)` at the 6-digit HS level above.
            
            To provide an **evidence-based macroeconomic baseline** without using synthetic placeholders, the table below links the October 23, 2026 Section 338 reshuffle sectors to **official U.S. Census Bureau 4-digit NAICS bilateral trade (`census_us_state_exports_to_canada`, 2024 USD)**. *(For exact 8-digit HTSUS / 6-digit HS bilateral flows for Chapters 32, 39, 44, 48, and 57, query USITC DataWeb or Statistics Canada CIMT Table 12-10-0119-01).*
            """
        )
        try:
            pkg_ctx_df = get_oct23_naics_packaging_context(year="2024")
        except Exception as e:
            st.error(f"Error loading NAICS packaging context: {e}")
            pkg_ctx_df = pd.DataFrame()

        if not pkg_ctx_df.empty:
            pkg_disp = pkg_ctx_df.copy()
            pkg_disp["US->Canada Exports (2024 USD)"] = pkg_disp["us_to_canada_exports_usd"].apply(format_currency)
            st.dataframe(
                pkg_disp[[
                    "naics4", "naics_desc", "oct23_relevance",
                    "US->Canada Exports (2024 USD)", "top_us_origin_states"
                ]].rename(columns={
                    "naics4": "4-Digit NAICS",
                    "naics_desc": "NAICS Industry Group",
                    "oct23_relevance": "Oct 23, 2026 Section 338 Tariff Lines & Ag Supply-Chain Role",
                    "top_us_origin_states": "Top U.S. Exporting States to Canada (2024 USD)"
                }),
                use_container_width=True,
                hide_index=True
            )

    st.markdown("---")
    st.subheader(f"📊 Active U.S. Section 338 Export Exposure Overlay ({selected_year})")
    
    try:
        exports_df = get_tariff_matched_exports(year=selected_year)
    except Exception as e:
        st.error(f"Error loading export data: {e}")
        exports_df = pd.DataFrame()

    if not exports_df.empty:
        matched_exports = exports_df[exports_df['has_tariff'] == True].copy()
            
        if not matched_exports.empty:
            total_exports = matched_exports['value_cad'].sum()
            exposed_exports = matched_exports['exposed_value_cad'].sum() if 'exposed_value_cad' in matched_exports.columns else total_exports
            lines_affected = matched_exports['hs6_code'].nunique()
            
            col1, col2, col3 = st.columns(3)
            col1.metric("Gross Exports in Targeted HS-6 Lines", format_currency(total_exports))
            col2.metric("Midpoint Tariff/Ban Exposed Value", format_currency(exposed_exports))
            col3.metric("Active HS-6 Subheadings Affected", f"{lines_affected} HS-6 codes")
            
            st.markdown("---")
            
            col_chart1, col_chart2 = st.columns(2)
            
            with col_chart1:
                st.subheader("Exports by Commodity Group")
                if 'commodity_group' in matched_exports.columns:
                    comm_df = matched_exports.groupby('commodity_group', as_index=False)['value_cad'].sum().sort_values('value_cad', ascending=True)
                    fig_comm = px.bar(
                        comm_df, x='value_cad', y='commodity_group', orientation='h',
                        labels={'value_cad': 'Export Value (CAD)', 'commodity_group': 'Commodity Group'},
                        color='value_cad', color_continuous_scale='Reds'
                    )
                    fig_comm.update_layout(coloraxis_showscale=False)
                    st.plotly_chart(fig_comm, use_container_width=True)
                else:
                    st.info("Commodity group data not available.")
            
            with col_chart2:
                st.subheader("Top U.S. State Destinations")
                if 'state' in matched_exports.columns:
                    state_df = matched_exports.groupby('state', as_index=False)['value_cad'].sum()
                    top_states = state_df.sort_values(by='value_cad', ascending=False).head(15)
                    fig_states = px.bar(
                        top_states, x='value_cad', y='state', orientation='h',
                        labels={'value_cad': 'Export Value (CAD)', 'state': 'State'},
                        color='value_cad', color_continuous_scale='Blues'
                    )
                    fig_states.update_layout(yaxis={'categoryorder':'total ascending'}, coloraxis_showscale=False)
                    st.plotly_chart(fig_states, use_container_width=True)
                else:
                    st.info("State level data not available.")
            
            st.subheader("📋 Detailed U.S. Section 338 Export Exposure Lines")
            group_cols = ['hs6_code', 'commodity_desc', 'commodity_group']
            if 'measure_status' in matched_exports.columns:
                group_cols.append('measure_status')
            exp_table = matched_exports.groupby(group_cols, as_index=False).agg({
                'value_cad': 'sum',
                'exposed_value_cad': 'sum'
            }).sort_values(by='value_cad', ascending=False)
            exp_table['Gross Export Value (CAD)'] = exp_table['value_cad'].apply(format_currency)
            exp_table['Midpoint Exposed Value (CAD)'] = exp_table['exposed_value_cad'].apply(format_currency)
            
            disp_cols = ['hs6_code', 'commodity_desc', 'commodity_group']
            if 'measure_status' in exp_table.columns:
                disp_cols.append('measure_status')
            disp_cols.extend(['Gross Export Value (CAD)', 'Midpoint Exposed Value (CAD)'])
            
            st.dataframe(
                exp_table[disp_cols].rename(columns={
                    'hs6_code': 'HS-6 Code',
                    'commodity_desc': 'Commodity Description',
                    'commodity_group': 'Commodity Group',
                    'measure_status': 'Statutory Status (Aug / Sept / Oct 2026)'
                }), 
                use_container_width=True, 
                hide_index=True
            )
            
            csv_exp = matched_exports.to_csv(index=False).encode('utf-8')
            st.download_button(
                "📥 Download U.S. Section 338 Export Exposure as CSV", 
                data=csv_exp, 
                file_name=f"us_sec338_exports_{selected_year}.csv", 
                mime="text/csv", 
                key='export_dl'
            )
        else:
            st.info("No tariff matched exports found for the selected year.")
    else:
        st.info("No export data available for the selected year.")

import streamlit as st
import pandas as pd
import plotly.express as px
from lib.data_loader import (
    get_tariff_matched_imports, 
    get_tariff_matched_exports, 
    get_canada_counter_tariffs, 
    get_us_section338_tariffs
)
from lib.chapter_labels import chapter_label
from lib.geo_utils import get_valid_state_names

st.set_page_config(page_title="Tariff Impact Tracker", layout="wide")

st.title("🛡️ Tariff Impact Tracker")
st.subheader("Canada's Counter-Tariffs (Sept 8, 2026) & U.S. Section 338 Tariffs")

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
        ℹ️ **Federal Remission Framework (*United States Surtax Remission Order*):**  
        Pursuant to Sections 3 and 5 of the Remission Order and **CBSA Customs Notice 25-19 (Paragraph 41)**, 
        goods imported for **Primary Agriculture (NAICS 11)** and **Food & Beverage Manufacturing (NAICS 31-33)** 
        are granted **automatic point-of-import remission** using Special Authorization Code **`25-0466C`**.  
        * **Field Machinery & Parts:** Direct agricultural machinery parts (`HS 8433.90` combine parts, `HS 8433.20` mower bars) enter duty-free.  
        * **Transportation & Storage Exclusion:** Goods used for hauling and storage (such as farm/livestock trailers under `HS 8716.39`) remain subject to the **25% active surtax**.
        """
    )
    
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
    st.header("U.S. Section 338 Tariffs (Ontario Exports)")
    st.caption("Overlay of proposed or enacted U.S. retaliatory tariffs against Ontario export flows:")
    
    try:
        exports_df = get_tariff_matched_exports(year=selected_year)
    except Exception as e:
        st.error(f"Error loading export data: {e}")
        exports_df = pd.DataFrame()

    if not exports_df.empty:
        matched_exports = exports_df[exports_df['has_tariff'] == True].copy()
            
        if not matched_exports.empty:
            total_exports = matched_exports['value_cad'].sum()
            lines_affected = matched_exports['hs6_code'].nunique()
            
            col1, col2, col3 = st.columns(3)
            col1.metric("Total Exports Facing U.S. Tariffs", format_currency(total_exports))
            col2.metric("HS-6 Codes Affected", f"{lines_affected}")
            col3.metric("Total Exposed Export Value", format_currency(total_exports))
            
            st.markdown("---")
            
            col_chart1, col_chart2 = st.columns(2)
            
            with col_chart1:
                st.subheader("Exports by Commodity Group")
                if 'commodity_group' in matched_exports.columns:
                    comm_df = matched_exports.groupby('commodity_group')['value_cad'].sum().reset_index()
                    fig_comm = px.bar(comm_df, x='commodity_group', y='value_cad', labels={'value_cad': 'Export Value (CAD)', 'commodity_group': 'Commodity Group'})
                    st.plotly_chart(fig_comm, use_container_width=True)
                else:
                    st.info("Commodity group data not available.")
            
            with col_chart2:
                st.subheader("Top U.S. State Destinations")
                if 'state' in matched_exports.columns:
                    state_df = matched_exports.groupby('state')['value_cad'].sum().reset_index()
                    top_states = state_df.sort_values(by='value_cad', ascending=False).head(15)
                    fig_states = px.bar(top_states, x='value_cad', y='state', orientation='h', labels={'value_cad': 'Export Value (CAD)', 'state': 'State'})
                    fig_states.update_layout(yaxis={'categoryorder':'total ascending'})
                    st.plotly_chart(fig_states, use_container_width=True)
                else:
                    st.info("State level data not available.")
            
            st.subheader("📋 Detailed U.S. Tariff Exposure Lines")
            exp_table = matched_exports.groupby(['hs6_code', 'commodity_desc', 'commodity_group'], as_index=False)['value_cad'].sum().sort_values(by='value_cad', ascending=False)
            exp_table['Export Value (CAD)'] = exp_table['value_cad'].apply(format_currency)
            st.dataframe(
                exp_table[['hs6_code', 'commodity_desc', 'commodity_group', 'Export Value (CAD)']].rename(columns={
                    'hs6_code': 'HS-6 Code',
                    'commodity_desc': 'Commodity Description',
                    'commodity_group': 'Commodity Group'
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

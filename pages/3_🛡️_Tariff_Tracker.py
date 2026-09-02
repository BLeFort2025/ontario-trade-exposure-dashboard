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

selected_year = st.session_state.get('selected_year', '2024')
st.write(f"**Analyzing Year:** {selected_year}")

tab1, tab2 = st.tabs(['🇨🇦 Canada Counter-Tariffs (Imports)', '🇺🇸 U.S. Section 338 (Exports)'])

def format_currency(val):
    return f"${val:,.0f}"

with tab1:
    st.header("Canada Counter-Tariffs (Imports)")
    
    try:
        imports_df = get_tariff_matched_imports(year=selected_year)
    except Exception as e:
        st.error(f"Error loading import data: {e}")
        imports_df = pd.DataFrame()

    if not imports_df.empty:
        # Filter for matched tariffs
        if 'has_tariff' in imports_df.columns:
            matched_imports = imports_df[imports_df['has_tariff'] == True].copy()
        elif 'tariff_rate_pct' in imports_df.columns:
            matched_imports = imports_df[imports_df['tariff_rate_pct'] > 0].copy()
        else:
            matched_imports = pd.DataFrame()

        if not matched_imports.empty:
            total_imports = matched_imports['value_cad'].sum()
            lines_matched = matched_imports['hs6_code'].nunique() if 'hs6_code' in matched_imports.columns else len(matched_imports)
            
            # Calculate weighted average tariff rate
            if 'tariff_rate_pct' in matched_imports.columns and total_imports > 0:
                weighted_avg = (matched_imports['value_cad'] * matched_imports['tariff_rate_pct']).sum() / total_imports
            else:
                weighted_avg = 0
            
            col1, col2, col3 = st.columns(3)
            col1.metric("Total Affected Imports", format_currency(total_imports))
            col2.metric("Tariff Lines Matched", f"{lines_matched}")
            col3.metric("Avg Tariff Rate", f"{weighted_avg:.1f}%")
            
            st.markdown("---")
            
            col_chart1, col_chart2 = st.columns(2)
            
            with col_chart1:
                st.subheader("Tariff Tier Breakdown")
                if 'tariff_rate_pct' in matched_imports.columns:
                    tier_df = matched_imports.groupby('tariff_rate_pct')['value_cad'].sum().reset_index()
                    tier_df['tariff_tier'] = tier_df['tariff_rate_pct'].astype(str) + '%'
                    fig_pie = px.pie(tier_df, values='value_cad', names='tariff_tier', hole=0.4)
                    st.plotly_chart(fig_pie, use_container_width=True)
            
            with col_chart2:
                st.subheader("Affected Imports by HS Chapter")
                if 'hs2_chapter' in matched_imports.columns:
                    # Assign chapter label for y-axis
                    matched_imports['chapter_name'] = matched_imports['hs2_chapter'].apply(
                        lambda x: f"{str(x).zfill(2)} - {chapter_label(str(x).zfill(2))}"
                    )
                    chap_df = matched_imports.groupby(['chapter_name', 'tariff_rate_pct'])['value_cad'].sum().reset_index()
                    
                    fig_bar = px.bar(chap_df, x='value_cad', y='chapter_name', color='tariff_rate_pct', 
                                     orientation='h', labels={'value_cad': 'Import Value (CAD)', 'chapter_name': 'HS-2 Chapter'})
                    fig_bar.update_layout(yaxis={'categoryorder':'total ascending'})
                    st.plotly_chart(fig_bar, use_container_width=True)
            
            st.subheader("Detailed Data")
            display_cols = [c for c in ['hs6_code', 'description', 'tariff_rate_pct', 'value_cad', 'top_states'] if c in matched_imports.columns]
            # Make sure it's sortable and looks good
            st.dataframe(matched_imports[display_cols].sort_values(by='value_cad', ascending=False), use_container_width=True)
            
            csv = matched_imports.to_csv(index=False).encode('utf-8')
            st.download_button("Download Data as CSV", data=csv, file_name=f"canada_counter_tariffs_imports_{selected_year}.csv", mime="text/csv")
        else:
            st.info("No tariff matched imports found for the selected year.")
    else:
        st.info("No import data available for the selected year.")


with tab2:
    st.header("U.S. Section 338 (Exports)")
    
    try:
        exports_df = get_tariff_matched_exports(year=selected_year)
    except Exception as e:
        st.error(f"Error loading export data: {e}")
        exports_df = pd.DataFrame()

    if not exports_df.empty:
        # Filter for matched tariffs
        if 'has_tariff' in exports_df.columns:
            matched_exports = exports_df[exports_df['has_tariff'] == True].copy()
        else:
            matched_exports = exports_df.copy() # fallback
            
        if not matched_exports.empty:
            total_exports = matched_exports['value_cad'].sum()
            lines_affected = matched_exports['hs6_code'].nunique() if 'hs6_code' in matched_exports.columns else len(matched_exports)
            
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
            
            st.subheader("Detailed Data")
            st.dataframe(matched_exports.sort_values(by='value_cad', ascending=False), use_container_width=True)
            
            csv_exp = matched_exports.to_csv(index=False).encode('utf-8')
            st.download_button("Download Data as CSV", data=csv_exp, file_name=f"us_sec338_exports_{selected_year}.csv", mime="text/csv", key='export_dl')
        else:
            st.info("No tariff matched exports found for the selected year.")
    else:
        st.info("No export data available for the selected year.")

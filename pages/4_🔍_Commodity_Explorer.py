import streamlit as st
import pandas as pd
import plotly.express as px
from io import BytesIO

from lib.data_loader import get_commodity_search, get_time_series, get_hs6_detail, get_canada_counter_tariffs
from lib.chapter_labels import chapter_label
from lib.geo_utils import get_valid_state_names

def main():
    st.set_page_config(page_title="Commodity Explorer", page_icon="🔍", layout="wide")

    st.title("🔍 Commodity Explorer")
    st.markdown("Search, analyze, and export Ontario–U.S. trade data at the HS-6 commodity level")

    if 'search_term' not in st.session_state:
        st.session_state['search_term'] = ''

    col1, col2 = st.columns([3, 1])

    with col1:
        search_input = st.text_input(
            "Search commodities (e.g., tomato, combine, maple, soybean, fertilizer)",
            value=st.session_state['search_term'],
            placeholder="Search commodities (e.g., tomato, combine, maple, soybean, fertilizer)"
        )
        if search_input != st.session_state['search_term']:
            st.session_state['search_term'] = search_input
            st.rerun()

    with col2:
        selected_year = st.session_state.get('selected_year', '2024')
        year_options = [str(y) for y in range(2021, 2027)]
        if selected_year not in year_options:
            selected_year = '2024'
        year = st.selectbox("Select Year", options=year_options, index=year_options.index(selected_year))
        st.session_state['selected_year'] = year

    search_term = st.session_state['search_term']

    if len(search_term) >= 3:
        st.markdown("---")
        
        with st.spinner("Searching commodities..."):
            # Call data loader
            results_df = get_commodity_search(search_term, int(year))
            
        if results_df.empty:
            st.warning(f"No commodities found matching '{search_term}' in {year}.")
        else:
            # Number of unique HS-6 codes
            unique_hs6 = results_df['hs6_code'].nunique()
            st.metric(f"Matching commodities found for '{search_term}'", unique_hs6)
            
            # Aggregate results
            pivot_df = results_df.pivot_table(
                index=['hs6_code', 'commodity_desc', 'hs2_chapter'],
                columns='trade_type',
                values='value_cad',
                aggfunc='sum',
                fill_value=0
            ).reset_index()
            
            # Ensure Export and Import columns exist
            if 'Export' not in pivot_df.columns:
                pivot_df['Export'] = 0
            if 'Import' not in pivot_df.columns:
                pivot_df['Import'] = 0
                
            pivot_df['Export Value'] = pivot_df['Export']
            pivot_df['Import Value'] = pivot_df['Import']
            pivot_df['Net Balance'] = pivot_df['Export Value'] - pivot_df['Import Value']
            pivot_df['Total Volume'] = pivot_df['Export Value'] + pivot_df['Import Value']
            
            # Add chapter label
            pivot_df['Chapter Label'] = pivot_df['hs2_chapter'].apply(chapter_label)
            
            # Sort by total trade volume descending
            pivot_df = pivot_df.sort_values(by='Total Volume', ascending=False)
            
            # Format for display
            display_cols = ['hs6_code', 'commodity_desc', 'Chapter Label', 'Export Value', 'Import Value', 'Net Balance']
            display_df = pivot_df[display_cols].copy()
            
            st.dataframe(
                display_df,
                column_config={
                    "hs6_code": st.column_config.TextColumn("HS-6 Code", width="small"),
                    "commodity_desc": st.column_config.TextColumn("Description", width="large"),
                    "Chapter Label": st.column_config.TextColumn("Chapter", width="medium"),
                    "Export Value": st.column_config.NumberColumn("Export Value", format="$%.2f", width="medium"),
                    "Import Value": st.column_config.NumberColumn("Import Value", format="$%.2f", width="medium"),
                    "Net Balance": st.column_config.NumberColumn("Net Balance", format="$%.2f", width="medium")
                },
                hide_index=True,
                use_container_width=True
            )
            
            st.markdown("### Commodity Detail")
            
            # Selectbox for specific HS-6 code
            hs6_options = pivot_df.apply(lambda x: f"{x['hs6_code']} - {x['commodity_desc']}", axis=1).tolist()
            selected_option = st.selectbox("Select a commodity to view details", options=hs6_options)
            
            if selected_option:
                selected_code = selected_option.split(" - ")[0]
                
                with st.expander(f"Details for {selected_option}", expanded=True):
                    col_ts, col_st = st.columns(2)
                    
                    with col_ts:
                        st.markdown("**Trade Trend (2021-2026)**")
                        ts_df = get_time_series(hs6_code=selected_code)
                        if not ts_df.empty:
                            fig = px.line(
                                ts_df, 
                                x='year', 
                                y='value_cad', 
                                color='trade_type', 
                                markers=True,
                                title=f"Trade Trend for {selected_code}",
                                labels={'value_cad': 'Value (CAD)', 'year': 'Year', 'trade_type': 'Trade Type'}
                            )
                            fig.update_layout(xaxis=dict(tickmode='linear', dtick=1))
                            st.plotly_chart(fig, use_container_width=True)
                        else:
                            st.info("No time series data available for this commodity.")
                            
                    with col_st:
                        st.markdown(f"**State Breakdown ({year})**")
                        detail_df = get_hs6_detail(int(year), state=None)
                        if not detail_df.empty:
                            state_df = detail_df[detail_df['hs6_code'] == selected_code]
                            if not state_df.empty:
                                state_agg = state_df.groupby(['state', 'trade_type'])['value_cad'].sum().reset_index()
                                state_pivot = state_agg.pivot_table(
                                    index='state', 
                                    columns='trade_type', 
                                    values='value_cad', 
                                    aggfunc='sum', 
                                    fill_value=0
                                ).reset_index()
                                
                                if 'Export' not in state_pivot.columns:
                                    state_pivot['Export'] = 0
                                if 'Import' not in state_pivot.columns:
                                    state_pivot['Import'] = 0
                                    
                                state_pivot['Total'] = state_pivot['Export'] + state_pivot['Import']
                                state_pivot = state_pivot.sort_values(by='Total', ascending=False).head(10)
                                
                                st.dataframe(
                                    state_pivot[['state', 'Export', 'Import']],
                                    column_config={
                                        "state": "State",
                                        "Export": st.column_config.NumberColumn("Export", format="$%.2f"),
                                        "Import": st.column_config.NumberColumn("Import", format="$%.2f")
                                    },
                                    hide_index=True,
                                    use_container_width=True
                                )
                            else:
                                st.info("No state breakdown data available.")
                        else:
                            st.info("No state breakdown data available.")
                            
                    st.markdown("**Tariff Status**")
                    tariffs_df = get_canada_counter_tariffs()
                    if not tariffs_df.empty and selected_code in tariffs_df['hs6_code'].values:
                        st.error(f"⚠️ HS-6 code {selected_code} is subject to Canadian counter-tariffs.")
                    else:
                        st.success(f"✅ HS-6 code {selected_code} is not currently flagged in the counter-tariff schedule.")

            st.markdown("### Export Results")
            
            # Download section
            csv = pivot_df.to_csv(index=False).encode('utf-8')
            
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                pivot_df.to_excel(writer, index=False, sheet_name='Search Results')
            excel_data = output.getvalue()
            
            dl_col1, dl_col2, _ = st.columns([1, 1, 3])
            with dl_col1:
                st.download_button(
                    label="Download CSV",
                    data=csv,
                    file_name=f"commodity_search_{search_term}_{year}.csv",
                    mime="text/csv",
                )
            with dl_col2:
                st.download_button(
                    label="Download Excel",
                    data=excel_data,
                    file_name=f"commodity_search_{search_term}_{year}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

    else:
        st.markdown("---")
        st.markdown("### Getting Started")
        st.write("Not sure what to search for? Try one of these common agricultural commodities:")
        
        suggested = {
            'tomato': 'Greenhouse vegetables',
            'combine': 'Agricultural machinery parts',
            'maple': 'Maple syrup & sugar',
            'soybean': 'Oilseeds & feed',
            'whey': 'Dairy protein concentrates & albumins',
            'starch': 'Modified corn & wheat starches',
            'fertilizer': 'Farm input costs',
            'wine': 'Beverages & spirits',
        }
        
        for term, desc in suggested.items():
            if st.button(f"🔍 **{term}** — {desc}"):
                st.session_state['search_term'] = term
                st.rerun()

if __name__ == "__main__":
    main()

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from lib.data_loader import get_net_balance, get_import_substitution_matrix
from lib.chapter_labels import chapter_label, chapter_short, AGRI_FOOD_CHAPTERS

def format_currency(value):
    if pd.isna(value):
        return "$0"
    if abs(value) >= 1e9:
        return f"${value/1e9:,.1f}B"
    elif abs(value) >= 1e6:
        return f"${value/1e6:,.1f}M"
    else:
        return f"${value:,.0f}"

# Page configuration shouldn't be called if it was already called in a multi-page app, but it can be.
# Typically st.set_page_config is called in the main page or at the very top.
# st.set_page_config(page_title="Import Substitution Engine", page_icon="🔄", layout="wide")

st.title("🔄 Import Substitution Engine")
st.markdown("### Identifying opportunities where Ontario producers can displace U.S. imports")

# Year selector
selected_year = st.session_state.get('selected_year', '2024')

# SECTION 1: Chapter-Level Net Trade Balance
st.header(f"Ontario–U.S. Net Trade Balance by Sector ({selected_year})")

net_balance_df = get_net_balance(selected_year)
if not net_balance_df.empty:
    net_balance_df['Chapter Label'] = net_balance_df['hs2_chapter'].apply(chapter_label)
    net_balance_df = net_balance_df.sort_values(by='net_balance', ascending=True)
    net_balance_df['Color'] = net_balance_df['net_balance'].apply(lambda x: 'green' if x >= 0 else 'red')

    fig = px.bar(
        net_balance_df,
        y='Chapter Label',
        x='net_balance',
        orientation='h',
        color='Color',
        color_discrete_map={'green': 'green', 'red': 'red'},
        labels={'net_balance': 'Net Balance (CAD)', 'Chapter Label': 'Sector'}
    )
    
    # Format hover values as currency
    fig.update_traces(hovertemplate='%{y}<br>Net Balance: $%{x:,.0f}<extra></extra>')
    fig.update_layout(height=800, showlegend=False)
    
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("No net balance data available for the selected year.")

# SECTION 2: Top Import Substitution Opportunities
st.header("Top Import Substitution Opportunities")

sub_matrix = get_import_substitution_matrix(selected_year)
if not sub_matrix.empty:
    # Filter to rows where imports > 0 and net_balance < 0
    opp_df = sub_matrix[(sub_matrix['imports'] > 0) & (sub_matrix['net_balance'] < 0)].copy()
    
    # Sort by largest deficit (most negative net_balance) -> smallest net balance
    opp_df = opp_df.sort_values(by='net_balance', ascending=True)
    
    top_50 = opp_df.head(50).copy()
    
    # Format dataframe for display
    display_df = top_50.copy()
    display_df['Chapter'] = display_df['hs2_chapter'].apply(chapter_label)
    display_df['Description'] = display_df['description'].astype(str).str[:60] + '...'
    display_df['Net Deficit (CAD)'] = display_df['net_balance']
    
    # Ensure all required columns are there
    cols_to_show = ['hs6_code', 'Description', 'Chapter', 'exports', 'imports', 'Net Deficit (CAD)']
    
    if 'faces_counter_tariff' in display_df.columns:
        display_df['Counter-Tariff?'] = display_df.apply(
            lambda row: f"Yes ({row.get('tariff_rate', 'N/A')})" if row['faces_counter_tariff'] else "No", axis=1
        )
        cols_to_show.append('Counter-Tariff?')
        
    if 'top_sources' in display_df.columns:
        display_df['Top Import Sources'] = display_df['top_sources']
        cols_to_show.append('Top Import Sources')
        
    # Keep only the columns we want to show and rename them
    display_df = display_df[[c for c in cols_to_show if c in display_df.columns]]
    display_df = display_df.rename(columns={
        'hs6_code': 'HS-6 Code',
        'exports': 'Exports (CAD)',
        'imports': 'Imports (CAD)',
    })
    
    # Styling method compatibility
    style_func = getattr(display_df.style, 'map', getattr(display_df.style, 'applymap', None))
    styled_df = display_df.style.format({
        'Exports (CAD)': '${:,.0f}',
        'Imports (CAD)': '${:,.0f}',
        'Net Deficit (CAD)': '${:,.0f}'
    })
    if style_func:
        styled_df = style_func(lambda x: 'color: red' if isinstance(x, (int, float)) and x < 0 else '', subset=['Net Deficit (CAD)'])
        
    st.dataframe(styled_df, use_container_width=True, hide_index=True)
    
    # Download button
    csv = opp_df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="Download Full Import Substitution Matrix (CSV)",
        data=csv,
        file_name=f'import_substitution_matrix_{selected_year}.csv',
        mime='text/csv',
    )
else:
    st.info("No import substitution data available for the selected year.")
    opp_df = pd.DataFrame()


# SECTION 3: Counter-Tariff Amplifier
st.header("Counter-Tariff Amplifier")
st.info("Products facing Canadian counter-tariffs will see import costs rise 15-50%, creating immediate market openings for domestic producers.")

if not sub_matrix.empty and 'faces_counter_tariff' in sub_matrix.columns:
    tariff_df = sub_matrix[sub_matrix['faces_counter_tariff'] == True].copy()
    if not tariff_df.empty:
        total_tariff_imports = tariff_df['imports'].sum()
        st.metric("Total Value of Tariff-Affected Imports", format_currency(total_tariff_imports))
        
        tariff_display = tariff_df.copy()
        tariff_display['Chapter'] = tariff_display['hs2_chapter'].apply(chapter_label)
        tariff_display['Description'] = tariff_display['description'].astype(str).str[:60] + '...'
        
        cols = ['hs6_code', 'Description', 'Chapter', 'imports', 'net_balance', 'tariff_rate']
        tariff_display = tariff_display[[c for c in cols if c in tariff_display.columns]]
        tariff_display = tariff_display.rename(columns={
            'hs6_code': 'HS-6 Code',
            'imports': 'Imports (CAD)',
            'net_balance': 'Net Balance (CAD)',
            'tariff_rate': 'Tariff Rate'
        })
        
        st.dataframe(
            tariff_display.style.format({
                'Imports (CAD)': '${:,.0f}',
                'Net Balance (CAD)': '${:,.0f}'
            }),
            use_container_width=True,
            hide_index=True
        )
    else:
        st.write("No counter-tariff affected products found.")

# SECTION 4: Chapter-Level Summary Metrics
st.header("Chapter-Level Summary Metrics")
if not opp_df.empty:
    col1, col2, col3 = st.columns(3)
    
    num_net_importer_codes = len(opp_df)
    total_deficit = opp_df['net_balance'].sum()
    
    col1.metric("HS-6 Codes w/ Net Deficit", num_net_importer_codes)
    col2.metric("Total Net Import Deficit", format_currency(total_deficit))
    
    if 'faces_counter_tariff' in opp_df.columns:
        num_tariff_deficit = len(opp_df[opp_df['faces_counter_tariff'] == True])
        col3.metric("Deficit Commodities w/ Counter-Tariffs", num_tariff_deficit)
    else:
        col3.metric("Deficit Commodities w/ Counter-Tariffs", "N/A")

import streamlit as st
import pandas as pd
import plotly.express as px

from lib.data_loader import get_state_summary_for_map, get_available_years
from lib.chapter_labels import CHAPTER_LABELS, chapter_label, AGRI_FOOD_CHAPTERS, FARM_INPUT_CHAPTERS
from lib.geo_utils import state_name_to_abbrev, get_valid_state_names

st.set_page_config(page_title="Trade Map", page_icon="🗺️", layout="wide")

st.title("🗺️ Bilateral Trade Map")

# Build chapter options
chapter_options = list(AGRI_FOOD_CHAPTERS | FARM_INPUT_CHAPTERS)
if "87" in chapter_options:
    chapter_options.remove("87")
chapter_options.extend(["87-AG", "87-AUTO"])
chapter_options.sort()

# Add 'All Agri-Food Chapters'
all_chapters_opt = "All Agri-Food Chapters"
display_options = [all_chapters_opt] + chapter_options

col1, col2, col3 = st.columns(3)

with col1:
    trade_type = st.radio("Trade Type", ["Exports", "Imports", "Net Balance"])

with col2:
    selected_chapter_display = st.selectbox(
        "Chapter filter", 
        display_options,
        format_func=lambda x: x if x == all_chapters_opt else chapter_label(x)
    )

with col3:
    available_years = get_available_years()
    default_year = st.session_state.get('selected_year', '2024')
    if default_year not in available_years:
        default_year = available_years[-1] if available_years else '2024'
    
    selected_year = st.selectbox(
        "Year",
        available_years,
        index=available_years.index(default_year) if default_year in available_years else 0
    )

# Get data
chapter_param = None if selected_chapter_display == all_chapters_opt else selected_chapter_display

if trade_type == "Net Balance":
    df_exp = get_state_summary_for_map(selected_year, "Domestic exports", chapter_param)
    df_imp = get_state_summary_for_map(selected_year, "Imports", chapter_param)
    df_exp = df_exp.rename(columns={"value_cad": "exports"})
    df_imp = df_imp.rename(columns={"value_cad": "imports"})
    df = pd.merge(df_exp, df_imp, on=["state", "state_abbrev"], how="outer").fillna(0)
    df["value_cad"] = df["exports"] - df["imports"]
    
    # Diverging color scale
    color_scale = "RdYlGn"
    color_mid = 0
else:
    db_trade_type = "Domestic exports" if trade_type == "Exports" else "Imports"
    df = get_state_summary_for_map(selected_year, db_trade_type, chapter_param)
    
    # Sequential color scales
    color_scale = "Greens" if trade_type == "Exports" else "Reds"
    color_mid = None

# Filter out NaNs if any and sort
df = df[df["value_cad"].notna()]
df = df.sort_values("value_cad", ascending=False)

if not df.empty:
    fig = px.choropleth(
        df,
        locationmode="USA-states",
        locations="state_abbrev",
        color="value_cad",
        hover_name="state",
        hover_data={"state_abbrev": False, "value_cad": ":$,.0f"},
        color_continuous_scale=color_scale,
        color_continuous_midpoint=color_mid
    )
    
    fig.update_layout(
        geo=dict(scope="usa"),
        height=550,
        margin=dict(l=0, r=0, t=30, b=0),
        coloraxis_colorbar_title="CAD"
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    st.markdown("### Data Table")
    # Rename columns for display
    display_df = df[["state", "state_abbrev", "value_cad"]].rename(columns={
        "state": "State",
        "state_abbrev": "State Code",
        "value_cad": "Trade Value (CAD)"
    })
    
    st.dataframe(
        display_df,
        column_config={
            "Trade Value (CAD)": st.column_config.NumberColumn(format="$ %d")
        },
        hide_index=True,
        use_container_width=True
    )
    
    if selected_chapter_display != all_chapters_opt:
        st.markdown("### Top 15 States")
        top15 = df.head(15).copy()
        
        # Determine bar color based on trade type
        if trade_type == "Exports":
            marker_color = "#2ca02c"  # Green
        elif trade_type == "Imports":
            marker_color = "#d62728"  # Red
        else:
            marker_color = ["#2ca02c" if val >= 0 else "#d62728" for val in top15["value_cad"]]
            
        fig_bar = px.bar(
            top15,
            x="state",
            y="value_cad",
            text="value_cad",
            labels={"state": "State", "value_cad": "Trade Value (CAD)"}
        )
        
        fig_bar.update_traces(
            texttemplate='%{text:$,.0s}', 
            textposition='outside',
            marker_color=marker_color
        )
        
        # Extend y-axis limits slightly to fit text outside
        max_val = top15["value_cad"].max()
        min_val = top15["value_cad"].min()
        y_max = max_val * 1.15 if max_val > 0 else 0
        y_min = min_val * 1.15 if min_val < 0 else 0
        
        fig_bar.update_layout(
            height=400,
            yaxis_range=[y_min, y_max]
        )
        st.plotly_chart(fig_bar, use_container_width=True)

else:
    st.info("No data available for the selected filters.")

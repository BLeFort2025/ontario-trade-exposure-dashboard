"""
Data Loader — Cached SQLite Queries for Trade Exposure Dashboard
=================================================================
Central data access layer. All database reads flow through this module.
Uses @st.cache_data to avoid redundant reads on Streamlit re-runs.

Tables in trade_exposure.db:
  - state_hs_trade          (251,405 rows) — Ontario bilateral HS-6 trade
  - canada_counter_tariffs   (629 rows)    — Canada's Sept 8 counter-tariffs
  - us_section338_tariffs    (66 rows)     — U.S. Section 338 tariffs
  - census_us_state_exports  (29,920 rows) — U.S. Census NAICS state exports
  - provincial_napcs_trade   (67,860 rows) — StatCan provincial NAPCS
  - national_naics_trade     (74,880 rows) — StatCan national NAICS
"""

import sqlite3
from pathlib import Path

import pandas as pd
import streamlit as st

from lib.chapter_labels import is_ag_vehicle
from lib.geo_utils import state_name_to_abbrev, get_valid_state_names

# ── Database Path ────────────────────────────────────────────────────

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "trade_exposure.db"


def _get_conn() -> sqlite3.Connection:
    """Return a SQLite connection (one per Streamlit session)."""
    return sqlite3.connect(str(DB_PATH), check_same_thread=False)


# ── Core Trade Queries ───────────────────────────────────────────────

@st.cache_data(ttl=3600)
def get_available_years() -> list[str]:
    """Return sorted list of available years in the dataset."""
    conn = _get_conn()
    df = pd.read_sql(
        "SELECT DISTINCT substr(ref_date, 1, 4) as yr FROM state_hs_trade ORDER BY yr",
        conn,
    )
    return df["yr"].tolist()


@st.cache_data(ttl=3600)
def get_trade_summary(year: str) -> pd.DataFrame:
    """Chapter-level trade summary for a given year.

    Returns one row per (hs2_chapter, trade_type) with total value.
    Splits Chapter 87 into AG and AUTO sub-chapters.
    """
    conn = _get_conn()
    df = pd.read_sql(
        """
        SELECT hs2_chapter, hs6_code, trade_type,
               sum(value_cad) as value_cad
        FROM state_hs_trade
        WHERE substr(ref_date, 1, 4) = ?
        GROUP BY hs2_chapter, hs6_code, trade_type
        """,
        conn,
        params=[year],
    )

    # Split Chapter 87 into AG vs AUTO
    mask_87 = df["hs2_chapter"] == "87"
    df.loc[mask_87, "hs2_chapter"] = df.loc[mask_87, "hs6_code"].apply(
        lambda x: "87-AG" if is_ag_vehicle(x) else "87-AUTO"
    )

    # Aggregate to chapter level
    summary = (
        df.groupby(["hs2_chapter", "trade_type"], as_index=False)["value_cad"]
        .sum()
    )
    return summary


@st.cache_data(ttl=3600)
def get_net_balance(year: str) -> pd.DataFrame:
    """Net trade balance (exports - imports) by chapter for a given year.

    Returns columns: hs2_chapter, exports, imports, net_balance.
    Chapter 87 is split into AG/AUTO.
    """
    summary = get_trade_summary(year)
    pivot = summary.pivot_table(
        index="hs2_chapter",
        columns="trade_type",
        values="value_cad",
        aggfunc="sum",
        fill_value=0,
    ).reset_index()

    # Normalize column names
    pivot.columns.name = None
    col_map = {}
    for c in pivot.columns:
        cl = c.lower()
        if "export" in cl:
            col_map[c] = "exports"
        elif "import" in cl:
            col_map[c] = "imports"
    pivot = pivot.rename(columns=col_map)

    if "exports" not in pivot.columns:
        pivot["exports"] = 0
    if "imports" not in pivot.columns:
        pivot["imports"] = 0

    pivot["net_balance"] = pivot["exports"] - pivot["imports"]
    return pivot.sort_values("net_balance")


@st.cache_data(ttl=3600)
def get_state_trade(year: str, trade_type: str = None, chapter: str = None) -> pd.DataFrame:
    """State-level trade data, optionally filtered by trade type and chapter.

    For Chapter 87, if chapter is '87-AG' or '87-AUTO', filters accordingly.
    Returns columns: state, state_abbrev, hs2_chapter, trade_type, value_cad.
    """
    conn = _get_conn()
    valid_states = get_valid_state_names()

    query = """
        SELECT state, hs2_chapter, hs6_code, trade_type,
               sum(value_cad) as value_cad
        FROM state_hs_trade
        WHERE substr(ref_date, 1, 4) = ?
    """
    params = [year]

    if trade_type:
        query += " AND trade_type = ?"
        params.append(trade_type)

    # Handle virtual 87-AG / 87-AUTO chapters
    real_chapter = chapter
    if chapter in ("87-AG", "87-AUTO"):
        real_chapter = "87"

    if real_chapter:
        query += " AND hs2_chapter = ?"
        params.append(real_chapter)

    query += " GROUP BY state, hs2_chapter, hs6_code, trade_type"

    df = pd.read_sql(query, conn, params=params)

    # Apply Ch 87 split
    if chapter in ("87-AG", "87-AUTO") or (chapter is None):
        mask_87 = df["hs2_chapter"] == "87"
        df.loc[mask_87, "hs2_chapter"] = df.loc[mask_87, "hs6_code"].apply(
            lambda x: "87-AG" if is_ag_vehicle(x) else "87-AUTO"
        )
        if chapter in ("87-AG", "87-AUTO"):
            df = df[df["hs2_chapter"] == chapter]

    # Aggregate after split
    df = (
        df.groupby(["state", "hs2_chapter", "trade_type"], as_index=False)["value_cad"]
        .sum()
    )

    # Filter to valid US states and add abbreviation
    df = df[df["state"].isin(valid_states)].copy()
    df["state_abbrev"] = df["state"].apply(state_name_to_abbrev)

    return df


@st.cache_data(ttl=3600)
def get_state_summary_for_map(year: str, trade_type: str, chapter: str = None) -> pd.DataFrame:
    """Aggregate trade by state for choropleth map.

    Returns one row per state with: state, state_abbrev, value_cad.
    """
    df = get_state_trade(year, trade_type, chapter)
    agg = df.groupby(["state", "state_abbrev"], as_index=False)["value_cad"].sum()
    return agg.sort_values("value_cad", ascending=False)


@st.cache_data(ttl=3600)
def get_hs6_detail(year: str, chapter: str = None, state: str = None,
                   trade_type: str = None) -> pd.DataFrame:
    """HS-6 level commodity detail, optionally filtered.

    Returns: hs6_code, commodity_desc, hs2_chapter, trade_type, state,
             value_cad, quantity, uom.
    """
    conn = _get_conn()
    query = """
        SELECT hs6_code, commodity_desc, hs2_chapter, trade_type, state,
               value_cad, quantity, uom
        FROM state_hs_trade
        WHERE substr(ref_date, 1, 4) = ?
    """
    params = [year]

    real_chapter = chapter
    if chapter in ("87-AG", "87-AUTO"):
        real_chapter = "87"

    if real_chapter:
        query += " AND hs2_chapter = ?"
        params.append(real_chapter)
    if state:
        query += " AND state = ?"
        params.append(state)
    if trade_type:
        query += " AND trade_type = ?"
        params.append(trade_type)

    df = pd.read_sql(query, conn, params=params)

    # Apply Ch 87 split
    mask_87 = df["hs2_chapter"] == "87"
    if mask_87.any():
        df.loc[mask_87, "hs2_chapter"] = df.loc[mask_87, "hs6_code"].apply(
            lambda x: "87-AG" if is_ag_vehicle(x) else "87-AUTO"
        )
        if chapter in ("87-AG", "87-AUTO"):
            df = df[df["hs2_chapter"] == chapter]

    return df


@st.cache_data(ttl=3600)
def get_commodity_search(search_term: str, year: str = None) -> pd.DataFrame:
    """Search commodity descriptions by keyword. Returns aggregated results."""
    conn = _get_conn()
    query = """
        SELECT hs6_code, commodity_desc, hs2_chapter, trade_type, state,
               ref_date, value_cad, quantity, uom
        FROM state_hs_trade
        WHERE commodity_desc LIKE ?
    """
    params = [f"%{search_term}%"]

    if year:
        query += " AND substr(ref_date, 1, 4) = ?"
        params.append(year)

    df = pd.read_sql(query, conn, params=params)

    # Apply Ch 87 split
    mask_87 = df["hs2_chapter"] == "87"
    if mask_87.any():
        df.loc[mask_87, "hs2_chapter"] = df.loc[mask_87, "hs6_code"].apply(
            lambda x: "87-AG" if is_ag_vehicle(x) else "87-AUTO"
        )

    return df


@st.cache_data(ttl=3600)
def get_time_series(hs6_code: str = None, chapter: str = None,
                    state: str = None) -> pd.DataFrame:
    """Annual time series of trade values, optionally filtered.

    Returns: year, trade_type, value_cad.
    """
    conn = _get_conn()
    query = """
        SELECT substr(ref_date, 1, 4) as year, trade_type, hs2_chapter, hs6_code,
               sum(value_cad) as value_cad
        FROM state_hs_trade
        WHERE 1=1
    """
    params = []

    real_chapter = chapter
    if chapter in ("87-AG", "87-AUTO"):
        real_chapter = "87"

    if hs6_code:
        query += " AND hs6_code = ?"
        params.append(hs6_code)
    if real_chapter:
        query += " AND hs2_chapter = ?"
        params.append(real_chapter)
    if state:
        query += " AND state = ?"
        params.append(state)

    query += " GROUP BY year, trade_type, hs2_chapter, hs6_code"

    df = pd.read_sql(query, conn, params=params)

    # Apply Ch 87 split
    mask_87 = df["hs2_chapter"] == "87"
    if mask_87.any():
        df.loc[mask_87, "hs2_chapter"] = df.loc[mask_87, "hs6_code"].apply(
            lambda x: "87-AG" if is_ag_vehicle(x) else "87-AUTO"
        )
        if chapter in ("87-AG", "87-AUTO"):
            df = df[df["hs2_chapter"] == chapter]

    # Aggregate after split
    agg = df.groupby(["year", "trade_type"], as_index=False)["value_cad"].sum()
    return agg.sort_values("year")


# ── Tariff Queries ───────────────────────────────────────────────────

@st.cache_data(ttl=3600)
def get_canada_counter_tariffs() -> pd.DataFrame:
    """Load Canada's counter-tariff schedule."""
    conn = _get_conn()
    return pd.read_sql("SELECT * FROM canada_counter_tariffs", conn)


@st.cache_data(ttl=3600)
def get_us_section338_tariffs() -> pd.DataFrame:
    """Load U.S. Section 338 tariff concordance."""
    conn = _get_conn()
    return pd.read_sql("SELECT * FROM us_section338_tariffs", conn)


@st.cache_data(ttl=3600)
def get_tariff_matched_imports(year: str) -> pd.DataFrame:
    """Join Ontario imports against Canada's counter-tariff schedule.

    Matches on HS-6 subheading to identify which imported goods face
    retaliatory tariffs. Returns trade rows augmented with tariff rate.
    """
    conn = _get_conn()
    query = """
        SELECT t.hs6_code, t.commodity_desc, t.hs2_chapter, t.state,
               sum(t.value_cad) as value_cad,
               ct.tariff_rate_pct, ct.indicative_description as tariff_desc
        FROM state_hs_trade t
        LEFT JOIN canada_counter_tariffs ct
            ON t.hs6_code = ct.hs6_subheading
        WHERE t.trade_type = 'Imports'
          AND substr(t.ref_date, 1, 4) = ?
        GROUP BY t.hs6_code, t.commodity_desc, t.hs2_chapter, t.state,
                 ct.tariff_rate_pct, ct.indicative_description
    """
    df = pd.read_sql(query, conn, params=[year])
    df["has_tariff"] = df["tariff_rate_pct"].notna()
    return df


@st.cache_data(ttl=3600)
def get_tariff_matched_exports(year: str) -> pd.DataFrame:
    """Join Ontario exports against U.S. Section 338 tariff concordance.

    Matches on HS-6 code to identify which exports face U.S. tariffs.
    """
    conn = _get_conn()
    query = """
        SELECT t.hs6_code, t.commodity_desc, t.hs2_chapter, t.state,
               sum(t.value_cad) as value_cad,
               s.commodity_group, s.description as tariff_desc,
               s.midpoint_fraction
        FROM state_hs_trade t
        LEFT JOIN us_section338_tariffs s
            ON t.hs6_code = s.hs6_code
        WHERE t.trade_type = 'Domestic exports'
          AND substr(t.ref_date, 1, 4) = ?
        GROUP BY t.hs6_code, t.commodity_desc, t.hs2_chapter, t.state,
                 s.commodity_group, s.description, s.midpoint_fraction
    """
    df = pd.read_sql(query, conn, params=[year])
    df["has_tariff"] = df["midpoint_fraction"].notna()
    return df


@st.cache_data(ttl=3600)
def get_import_substitution_matrix(year: str) -> pd.DataFrame:
    """Ranked import substitution opportunities.

    For each HS-6 code, calculates:
      - Total Ontario exports to U.S. (that code)
      - Total Ontario imports from U.S. (that code)
      - Net balance (exports - imports)
      - Top source states for imports
      - Whether the import faces a Canadian counter-tariff

    Sorted by largest net deficit (biggest substitution opportunities first).
    """
    conn = _get_conn()

    # Get trade data pivoted by HS-6
    query = """
        SELECT hs6_code,
               max(commodity_desc) as commodity_desc,
               hs2_chapter,
               sum(case when trade_type = 'Domestic exports' then value_cad else 0 end) as exports,
               sum(case when trade_type = 'Imports' then value_cad else 0 end) as imports
        FROM state_hs_trade
        WHERE substr(ref_date, 1, 4) = ?
        GROUP BY hs6_code, hs2_chapter
    """
    df = pd.read_sql(query, conn, params=[year])
    df["net_balance"] = df["exports"] - df["imports"]

    # Apply Ch 87 split
    mask_87 = df["hs2_chapter"] == "87"
    if mask_87.any():
        df.loc[mask_87, "hs2_chapter"] = df.loc[mask_87, "hs6_code"].apply(
            lambda x: "87-AG" if is_ag_vehicle(x) else "87-AUTO"
        )

    # Join counter-tariff info
    tariffs = get_canada_counter_tariffs()
    tariff_map = tariffs.set_index("hs6_subheading")["tariff_rate_pct"].to_dict()
    df["counter_tariff_pct"] = df["hs6_code"].map(tariff_map)
    df["faces_counter_tariff"] = df["counter_tariff_pct"].notna()

    # Get top import source states for each HS-6
    state_query = """
        SELECT hs6_code, state, sum(value_cad) as value_cad
        FROM state_hs_trade
        WHERE trade_type = 'Imports' AND substr(ref_date, 1, 4) = ?
        GROUP BY hs6_code, state
    """
    state_df = pd.read_sql(state_query, conn, params=[year])
    valid = get_valid_state_names()
    state_df = state_df[state_df["state"].isin(valid)]

    # Top 3 source states per HS-6
    top_states = (
        state_df.sort_values("value_cad", ascending=False)
        .groupby("hs6_code")
        .head(3)
        .groupby("hs6_code")["state"]
        .apply(lambda x: ", ".join(x))
        .reset_index()
        .rename(columns={"state": "top_import_states"})
    )

    df = df.merge(top_states, on="hs6_code", how="left")
    return df.sort_values("net_balance")

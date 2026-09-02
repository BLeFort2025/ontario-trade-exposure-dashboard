"""
U.S. State Geographic Utilities
================================
FIPS codes, 2-letter abbreviations, and name mappings for all 50 states + DC.
Used for Plotly choropleth compatibility (locationmode="USA-states").

StatCan CIMT exports state names as full names (e.g., "New York"), while
Plotly needs 2-letter codes (e.g., "NY"). This module bridges the two.
"""

# Full state name → 2-letter abbreviation
STATE_ABBREV = {
    "Alabama": "AL", "Alaska": "AK", "Arizona": "AZ", "Arkansas": "AR",
    "California": "CA", "Colorado": "CO", "Connecticut": "CT",
    "Delaware": "DE", "District of Columbia": "DC", "Florida": "FL",
    "Georgia": "GA", "Hawaii": "HI", "Idaho": "ID", "Illinois": "IL",
    "Indiana": "IN", "Iowa": "IA", "Kansas": "KS", "Kentucky": "KY",
    "Louisiana": "LA", "Maine": "ME", "Maryland": "MD",
    "Massachusetts": "MA", "Michigan": "MI", "Minnesota": "MN",
    "Mississippi": "MS", "Missouri": "MO", "Montana": "MT",
    "Nebraska": "NE", "Nevada": "NV", "New Hampshire": "NH",
    "New Jersey": "NJ", "New Mexico": "NM", "New York": "NY",
    "North Carolina": "NC", "North Dakota": "ND", "Ohio": "OH",
    "Oklahoma": "OK", "Oregon": "OR", "Pennsylvania": "PA",
    "Rhode Island": "RI", "South Carolina": "SC", "South Dakota": "SD",
    "Tennessee": "TN", "Texas": "TX", "Utah": "UT", "Vermont": "VT",
    "Virginia": "VA", "Washington": "WA", "West Virginia": "WV",
    "Wisconsin": "WI", "Wyoming": "WY",
    # StatCan also uses these variants
    "Puerto Rico": "PR", "Virgin Islands": "VI", "Guam": "GU",
}

# Reverse: abbreviation → full name
ABBREV_TO_STATE = {v: k for k, v in STATE_ABBREV.items()}

# Census API state FIPS codes (2-digit string)
STATE_FIPS = {
    "AL": "01", "AK": "02", "AZ": "04", "AR": "05", "CA": "06",
    "CO": "08", "CT": "09", "DE": "10", "DC": "11", "FL": "12",
    "GA": "13", "HI": "15", "ID": "16", "IL": "17", "IN": "18",
    "IA": "19", "KS": "20", "KY": "21", "LA": "22", "ME": "23",
    "MD": "24", "MA": "25", "MI": "26", "MN": "27", "MS": "28",
    "MO": "29", "MT": "30", "NE": "31", "NV": "32", "NH": "33",
    "NJ": "34", "NM": "35", "NY": "36", "NC": "37", "ND": "38",
    "OH": "39", "OK": "40", "OR": "41", "PA": "42", "PR": "72",
    "RI": "44", "SC": "45", "SD": "46", "TN": "47", "TX": "48",
    "UT": "49", "VT": "50", "VA": "51", "VI": "78", "WA": "53",
    "WV": "54", "WI": "55", "WY": "56",
}

# Ontario's border / key trading partner states (for highlighting)
BORDER_STATES = {"MI", "NY", "MN", "OH", "PA", "WI", "IN", "VT"}


def state_name_to_abbrev(name: str) -> str:
    """Convert a full state name to its 2-letter abbreviation.

    Returns the original string if no match found (handles edge cases
    like 'State not specified' or 'Other territories').
    """
    return STATE_ABBREV.get(name.strip(), "")


def abbrev_to_state_name(abbrev: str) -> str:
    """Convert a 2-letter abbreviation to the full state name."""
    return ABBREV_TO_STATE.get(abbrev.strip().upper(), abbrev)


def get_valid_state_names() -> set:
    """Return the set of valid U.S. state names (for filtering out
    aggregate rows like 'State not specified')."""
    return set(STATE_ABBREV.keys())

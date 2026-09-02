"""
HS Chapter Labels, Icons, and Agricultural Vehicle Filtering
=============================================================
Maps HS-2 chapter codes to human-readable names and emoji icons.
Provides utilities for separating agricultural vehicles/trailers
from automotive within Chapter 87.

Note: HS Chapter 06 (Floriculture, Nursery & Greenhouse) is always
classified as **Primary Agriculture** per OFA convention (NAICS 1114).
"""

# ── HS-2 Chapter Labels ─────────────────────────────────────────────

CHAPTER_LABELS = {
    "01": "🐄 Live Animals",
    "02": "🥩 Meat (Beef, Pork, Poultry)",
    "03": "🐟 Fish & Seafood",
    "04": "🧀 Dairy, Eggs & Honey",
    "05": "🦴 Animal Products (NES)",
    "06": "🌸 Floriculture & Nursery (Primary Ag)",
    "07": "🥬 Vegetables (Greenhouse & Field)",
    "08": "🍎 Fruit & Berries",
    "09": "☕ Coffee, Tea & Spices",
    "10": "🌾 Cereals (Grain, Corn, Wheat)",
    "11": "🏭 Milling Products (Flour, Malt)",
    "12": "🫘 Oilseeds & Forage",
    "13": "🌿 Lac, Gums & Resins",
    "14": "🧺 Vegetable Plaiting Materials",
    "15": "🫒 Fats & Oils",
    "16": "🌭 Prepared Meats & Seafood",
    "17": "🍁 Sugar & Confectionery",
    "18": "🍫 Cocoa & Chocolate",
    "19": "🍞 Bakery, Pasta & Cereal Prep",
    "20": "🥫 Preserved Vegetables & Fruit",
    "21": "🧂 Misc Edible Preparations",
    "22": "🍷 Beverages, Wine & Spirits",
    "23": "🐕 Animal Feed & Residues",
    "24": "🚬 Tobacco & Substitutes",
    "31": "🧪 Fertilizers",
    "84": "⚙️ Machinery & Parts",
    "87": "🚗 Vehicles & Trailers",
    # Virtual sub-chapters for Chapter 87 split
    "87-AG": "🚜 Ag Vehicles & Farm Trailers",
    "87-AUTO": "🚗 Automotive (Non-Farm)",
}

# Short labels for charts (no emoji)
CHAPTER_SHORT = {
    "01": "Live Animals",
    "02": "Meat",
    "03": "Fish/Seafood",
    "04": "Dairy/Eggs",
    "05": "Animal Products",
    "06": "Floriculture/Nursery",
    "07": "Vegetables",
    "08": "Fruit/Berries",
    "09": "Coffee/Tea/Spices",
    "10": "Cereals",
    "11": "Milling",
    "12": "Oilseeds",
    "13": "Gums/Resins",
    "14": "Plaiting Materials",
    "15": "Fats/Oils",
    "16": "Prepared Meats",
    "17": "Sugar/Confectionery",
    "18": "Cocoa/Chocolate",
    "19": "Bakery/Pasta",
    "20": "Preserved Veg/Fruit",
    "21": "Edible Preparations",
    "22": "Beverages/Spirits",
    "23": "Animal Feed",
    "24": "Tobacco",
    "31": "Fertilizers",
    "84": "Machinery/Parts",
    "87": "Vehicles/Trailers",
    "87-AG": "Ag Vehicles/Trailers",
    "87-AUTO": "Automotive",
}


def chapter_label(code: str) -> str:
    """Return the emoji + label for a chapter code, or the raw code if unknown."""
    return CHAPTER_LABELS.get(code, f"Chapter {code}")


def chapter_short(code: str) -> str:
    """Return the short label for a chapter code."""
    return CHAPTER_SHORT.get(code, f"Ch {code}")


# ── Chapter 87: Agricultural vs Automotive Split ─────────────────────
# HS-4 headings that are agricultural vehicles & trailers:
#   8701 = Tractors (agricultural, road, industrial)
#   8716 = Trailers & semi-trailers (includes livestock & farm trailers)
# Everything else in Ch 87 = automotive (passenger cars, trucks, buses,
#   motorcycles, parts)

AG_VEHICLE_HS4_PREFIXES = ("8701", "8716")


def is_ag_vehicle(hs6_code: str) -> bool:
    """Return True if hs6_code falls under agricultural vehicles/trailers."""
    code = str(hs6_code).strip()
    return any(code.startswith(prefix) for prefix in AG_VEHICLE_HS4_PREFIXES)


# ── Agri-Food vs Industrial Classification ──────────────────────────
# All 24 Harmonized System chapters covering Primary Agriculture & Food/Agri-Food
AGRI_FOOD_CHAPTERS = {
    "01", "02", "03", "04", "05", "06", "07", "08", "09", "10",
    "11", "12", "13", "14", "15", "16", "17", "18", "19", "20",
    "21", "22", "23", "24",
}

# Chapters that are farm inputs / equipment
FARM_INPUT_CHAPTERS = {"31", "84", "87"}

# Chapters where Ontario is classified as Primary Agriculture
PRIMARY_AG_CHAPTERS = {"01", "03", "06", "07", "08", "10", "12", "24"}


def is_agri_food(chapter: str) -> bool:
    """Return True if chapter is core agri-food."""
    return chapter in AGRI_FOOD_CHAPTERS


def is_farm_input(chapter: str) -> bool:
    """Return True if chapter is a farm input / equipment chapter."""
    return chapter in FARM_INPUT_CHAPTERS


def is_primary_ag(chapter: str) -> bool:
    """Return True if chapter is primary agriculture."""
    return chapter in PRIMARY_AG_CHAPTERS

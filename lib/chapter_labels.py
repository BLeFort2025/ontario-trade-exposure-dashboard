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


# ── Domestic Substitution Feasibility Classification ────────────────
# Tier 1: High Domestic Feasibility (Immediate/Low-Hanging Fruit)
# Tier 2: Moderate / Seasonal / Capital-Intensive
# Tier 3: Low / Non-Substitutable (Tropical & Exotic / Climate-Limited)

# Specific non-substitutable HS-4 prefixes (tropical/climate-limited)
TROPICAL_HS4_PREFIXES = {
    "0801",  # Coconuts, Brazil nuts, cashews
    "0803",  # Bananas & plantains
    "0804",  # Dates, figs, pineapples, avocados, guavas, mangoes
    "0805",  # Citrus fruit (oranges, lemons, limes, grapefruit)
    "0807",  # Melons, watermelons, papayas
    "0901",  # Coffee
    "0902",  # Tea
    "0904",  # Pepper
    "0905",  # Vanilla
    "0906",  # Cinnamon
    "0907",  # Cloves
    "0908",  # Nutmeg, mace, cardamoms
    "0909",  # Anise, badian, fennel, coriander, cumin
    "0910",  # Ginger, saffron, turmeric, thyme, bay leaves, curry
    "1006",  # Rice (paddy, husked, semi-milled)
    "1509",  # Olive oil
    "1510",  # Other olive oils
    "1511",  # Palm oil
    "1513",  # Coconut, palm kernel or babassu oil
    "1801",  # Cocoa beans, whole or broken, raw or roasted
    "1802",  # Cocoa shells, husks, skins
    "1803",  # Cocoa paste
    "1804",  # Cocoa butter, fat and oil
    "1805",  # Cocoa powder, not sweetened
}

# High-feasibility Ontario domestic chapters
HIGH_FEASIBILITY_CHAPTERS = {
    "01",  # Live animals (cattle, swine, sheep, poultry)
    "02",  # Meat (pork, beef, poultry)
    "04",  # Dairy, eggs, natural honey
    "06",  # Floriculture, nursery, greenhouse plants
    "07",  # Vegetables (field & greenhouse tomatoes, peppers, cucumbers)
    "10",  # Cereals (corn, wheat, barley, oats)
    "11",  # Milling products, malt, starches
    "12",  # Oilseeds (soybeans, canola, forage seeds)
    "15",  # Animal & vegetable fats and oils (canola oil, lard, tallow)
    "16",  # Prepared meats, sausages, preserved meats
    "19",  # Bakery, pastry, pasta, cereal preparations
    "20",  # Preserved vegetables, fruits, juices, jams
    "22",  # Beverages, spirits, wine, cider, beer
    "23",  # Animal feed, oilcake, food industry residues
}

# High-feasibility fruit lines in Chapter 08
ONTARIO_FRUIT_HS4_PREFIXES = {
    "0808",  # Apples, pears and quinces
    "0809",  # Apricots, cherries, peaches, plums
    "0810",  # Strawberries, raspberries, blackberries, cranberries, blueberries
    "0811",  # Fruit and nuts, uncooked or cooked by steaming, frozen
    "0812",  # Fruit and nuts, provisionally preserved
    "0813",  # Fruit, dried (apples, prunes, etc.)
}


def get_feasibility_tier(hs6_code: str, hs2_chapter: str = None, commodity_desc: str = "") -> str:
    """Classify an HS commodity into one of three substitution feasibility tiers.
    
    Returns:
      '🟢 High Domestic Feasibility'
      '🟡 Moderate / Seasonal'
      '⚪ Low / Non-Substitutable (Tropical/Exotic)'
      '⚙️ Industrial / Non-Ag'
    """
    code = str(hs6_code).strip()
    ch2 = str(hs2_chapter).strip().zfill(2) if hs2_chapter else code[:2]
    
    # Check if not in Agri-Food
    if ch2 not in AGRI_FOOD_CHAPTERS:
        return "⚙️ Industrial / Non-Ag"
        
    # Check Tropical / Non-Substitutable
    hs4 = code[:4]
    if hs4 in TROPICAL_HS4_PREFIXES:
        return "⚪ Low / Non-Substitutable (Tropical/Exotic)"
        
    # Cane sugar check
    if code.startswith("17011") or code.startswith("170112"):
        return "⚪ Low / Non-Substitutable (Tropical/Exotic)"
        
    # High-Feasibility Domestic Chapters
    if ch2 in HIGH_FEASIBILITY_CHAPTERS:
        return "🟢 High Domestic Feasibility"
        
    # Fruit Chapter 08: check if Ontario-grown
    if ch2 == "08":
        if hs4 in ONTARIO_FRUIT_HS4_PREFIXES:
            return "🟢 High Domestic Feasibility"
        return "🟡 Moderate / Seasonal"
        
    # Chocolate products (HS 1806) - high feasibility in Ontario (Ferrero, Mondelez, Mars)
    if code.startswith("1806"):
        return "🟢 High Domestic Feasibility"
        
    # Sugar confectionery & maple/glucose (HS 1702, 1704)
    if ch2 == "17":
        if code.startswith("1702") or code.startswith("1704"):
            return "🟢 High Domestic Feasibility"
        return "🟡 Moderate / Seasonal"
        
    # Default for remaining agri-food lines
    return "🟡 Moderate / Seasonal"


# ── Agricultural Value-Add Complexes (Raw vs. Processed) ─────────────
# Links raw agricultural export commodities to downstream processed imports

VALUE_ADD_COMPLEXES = {
    "Soybean Complex": {
        "icon": "🫘",
        "description": "Raw soybeans exported in bulk vs. processed meal, oil, and protein imported.",
        "raw_prefixes": ("1201",),  # Raw soybeans
        "processed_prefixes": ("2304", "1507", "210610"),  # Soybean oilcake/meal, soybean oil, soy protein
    },
    "Corn & Grain Complex": {
        "icon": "🌽",
        "description": "Feed grains exported vs. value-added animal feed, starch, sweeteners, and mixes imported.",
        "raw_prefixes": ("1005", "1001"),  # Corn, wheat
        "processed_prefixes": ("2309", "170230", "170240", "190120", "110812", "1101", "1102"),
    },
    "Red Meat & Livestock Complex": {
        "icon": "🥩",
        "description": "Live slaughter animals & primals exported vs. processed deli, sausages, and prepared meats imported.",
        "raw_prefixes": ("0102", "0103", "0201", "0202", "0203"),  # Live cattle/swine, fresh beef/pork
        "processed_prefixes": ("1601", "1602", "1501", "1502"),  # Sausages, prepared meats, fats
    },
    "Dairy Value Chain": {
        "icon": "🧀",
        "description": "Raw milk/cream production vs. specialty cheeses, whey powders, and dairy proteins imported.",
        "raw_prefixes": ("0401", "0402"),  # Milk, cream
        "processed_prefixes": ("0406", "0404", "0405", "350220"),  # Cheeses, whey, butter, milk protein
    },
    "Greenhouse & Horticultural Complex": {
        "icon": "🍅",
        "description": "Fresh field/greenhouse produce exported vs. canned, preserved, frozen, and sauces imported.",
        "raw_prefixes": ("0702", "0707", "070960", "0705"),  # Fresh tomatoes, cucumbers, peppers, lettuce
        "processed_prefixes": ("2002", "2005", "210320", "0710"),  # Canned tomatoes, sauces, frozen veg
    },
}


def get_value_add_complex(hs6_code: str) -> str:
    """Return the name of the agricultural value-add complex, or None."""
    code = str(hs6_code).strip()
    for name, data in VALUE_ADD_COMPLEXES.items():
        if any(code.startswith(p) for p in data["raw_prefixes"]):
            return name
        if any(code.startswith(p) for p in data["processed_prefixes"]):
            return name
    return None


def get_complex_role(hs6_code: str, complex_name: str) -> str:
    """Return 'Raw / Primary Commodity' or 'Value-Added Processed' within a complex."""
    code = str(hs6_code).strip()
    if complex_name not in VALUE_ADD_COMPLEXES:
        return "Other"
    data = VALUE_ADD_COMPLEXES[complex_name]
    if any(code.startswith(p) for p in data["raw_prefixes"]):
        return "Raw / Primary Commodity"
    if any(code.startswith(p) for p in data["processed_prefixes"]):
        return "Value-Added Processed"
    return "Other"

# Ontario–U.S. Trade Exposure & Import Substitution Dashboard

Interactive Streamlit web application for the Ontario Federation of Agriculture (OFA) that visualizes bilateral Ontario–U.S. agricultural trade flows, identifies import substitution opportunities, and tracks tariff impacts at the state and HS-6 commodity level.

## 🔗 Live App

[**Launch Dashboard →**](https://ontario-trade-exposure-dashboard.streamlit.app)

## Features

| Tab | Description |
| :--- | :--- |
| 🗺️ **Trade Map** | Interactive U.S. choropleth showing Ontario's export destinations and import sources by state |
| 🔄 **Import Substitution** | Ranks commodities by net trade deficit — pinpoints where Ontario producers can displace U.S. imports |
| 🛡️ **Tariff Tracker** | Overlays Canada's Sept 8 counter-tariffs and U.S. Section 338 tariffs on actual trade flows |
| 🔍 **Commodity Explorer** | Free-text search across 1,300+ HS-6 codes with one-click CSV/Excel export |

## Data Sources

- **Statistics Canada CIMT** (Catalogue 71-607-X): State-level bilateral merchandise trade (2021–2026)
- **U.S. Census Bureau International Trade API**: State-level NAICS exports to Canada
- **Department of Finance Canada**: Counter-tariff schedule (September 8, 2026)
- **U.S. Trade Representative**: Section 338 tariff proclamations

## Local Development

```bash
# Clone the repository
git clone https://github.com/BLeFort2025/ontario-trade-exposure-dashboard.git
cd ontario-trade-exposure-dashboard

# Install dependencies
pip install -r requirements.txt

# Run locally
streamlit run app.py
```

## Data Notes

- **HS Chapter 06** (Floriculture, Nursery & Greenhouse) is classified as **Primary Agriculture** throughout this application
- **HS Chapter 87** (Vehicles) is split into **Agricultural Vehicles & Trailers** (HS 8701 tractors, 8716 trailers) and **Automotive** to isolate farm economy exposure
- All dollar values are in **Canadian Dollars (CAD)** unless otherwise noted
- Trade data covers Ontario ↔ all 50 U.S. states + DC (2021–2026, annual)

## License

Data is sourced from public government statistical agencies. Analysis and application code © 2026 Ontario Federation of Agriculture.

# UI Spec

## Theme
Professional police dashboard: blue/white color scheme, modern cards, and clear typography.

## Screens

1. **Dashboard / Upload View (Initial State)**
   - Drag-and-drop zone for CSV files.
   - List of uploaded files showing row counts and parsed columns.
   - "Analyze Data" section with a text input area for natural language queries.

2. **Results View (Active State)**
   - Structured dashboard appears below the query input.
   - **Executive Summary Card:** High-level AI response.
   - **Key Findings Card:** Bulleted list of insights.
   - **Charts Area:** Time-series line chart or bar chart (using a charting library like Chart.js or Recharts).
   - **Recommendations Card:** Actionable advice based on the data.

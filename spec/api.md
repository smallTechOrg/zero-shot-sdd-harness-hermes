# API Contract

## POST /upload
**Request:** `multipart/form-data` with multiple `file` fields (CSVs).
**Response:**
```json
{
  "session_id": "uuid",
  "files_processed": 2,
  "schemas": {
    "file1.csv": ["Date", "Crime_Type", "District"],
    "file2.csv": ["District", "Officer_Count"]
  }
}
```

## POST /analyze
**Request:**
```json
{
  "session_id": "uuid",
  "query": "Which district has the highest crime rate?"
}
```
**Response:**
```json
{
  "summary": "District 9 has the highest crime rate, primarily driven by property crimes.",
  "findings": ["District 9 accounts for 24% of all incidents.", "Theft is up 12% YoY."],
  "charts": [
    {
      "type": "bar",
      "title": "Crime by District",
      "labels": ["Dist 9", "Dist 2"],
      "datasets": [{"label": "Total Incidents", "data": [1400, 800]}]
    }
  ],
  "recommendations": ["Reallocate patrol units to District 9 between 8 PM and 2 AM."]
}
```

## GET /health
**Response:**
```json
{
  "status": "ok"
}
```

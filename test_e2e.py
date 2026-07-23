import requests
import json
import time
import os

API_URL = "http://localhost:8001"

# 1. Create a dummy CSV
csv_content = """district,date,type
A,2023-01-01,theft
A,2023-01-02,assault
B,2023-01-01,theft
"""
with open("test_data.csv", "w") as f:
    f.write(csv_content)

# 2. Upload
print("Uploading...")
with open("test_data.csv", "rb") as f:
    res = requests.post(f"{API_URL}/api/upload", files={"files": ("test_data.csv", f, "text/csv")})
    
if res.status_code != 200:
    print("Upload failed:", res.text)
    exit(1)
    
data = res.json()
session_id = data["session_id"]
print("Session ID:", session_id)

# 3. Analyze
print("Analyzing...")
query_payload = {
    "session_id": session_id,
    "query": "Which district has the most crimes?"
}
res2 = requests.post(f"{API_URL}/api/analyze", json=query_payload)

if res2.status_code != 200:
    print("Analyze failed:", res2.text)
    exit(1)
    
print("Result:", json.dumps(res2.json(), indent=2))
print("SUCCESS!")

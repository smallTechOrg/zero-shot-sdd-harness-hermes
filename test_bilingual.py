import requests
import json
import time

API_URL = "http://localhost:8001"

# 1. Create a dummy CSV
csv_content = """district,date,type,crime_count
A,2023-01-01,theft,10
A,2023-01-02,assault,5
B,2023-01-01,theft,15
B,2023-01-02,burglary,20
C,2023-01-01,murder,1
"""
with open("test_hindi.csv", "w") as f:
    f.write(csv_content)

print("Uploading...")
with open("test_hindi.csv", "rb") as f:
    res = requests.post(f"{API_URL}/api/upload", files={"files": ("test_hindi.csv", f, "text/csv")})
    
data = res.json()
session_id = data["session_id"]
print("Session ID:", session_id)

queries = [
    "kis district me sabse jyada crime count hai? Mujhe number bhi batao.",
    "Which district has the lowest crime count?",
    "saare districts ka total crime batao bar chart ke format me",
]

for q in queries:
    print(f"\nAnalyzing Query: {q}")
    query_payload = {
        "session_id": session_id,
        "query": q
    }
    res2 = requests.post(f"{API_URL}/api/analyze", json=query_payload)
    if res2.status_code != 200:
        print("Analyze failed:", res2.text)
    else:
        print("Result:", json.dumps(res2.json(), indent=2))

print("SUCCESS!")

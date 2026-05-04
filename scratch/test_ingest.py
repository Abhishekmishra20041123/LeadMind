import requests
import json
import time

API_URL = "http://127.0.0.1:8000/api/ingest/event"
API_KEY = "lm_live_U3gJ-qz0GyrEKwRMswQiXS2xArTKJpJd"

payload = {
    "api_key": API_KEY,
    "visitor_id": "test_visitor_manual",
    "event_type": "page_view",
    "url": "http://localhost:3001/test-page",
    "title": "Test Page",
    "session_id": "test_session_manual",
    "device_type": "Desktop",
    "browser": "Chrome",
    "os": "Windows"
}

try:
    response = requests.post(API_URL, json=payload)
    print(f"Status Code: {response.status_code}")
    print(f"Response Body: {response.text}")
except Exception as e:
    print(f"Error: {e}")

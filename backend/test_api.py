import requests
import json

API = "http://localhost:8000/api"

def test_tasks():
    try:
        print(f"Testing {API}/tasks/my-tasks...")
        r = requests.get(f"{API}/tasks/my-tasks", timeout=5)
        print(f"Status Code: {r.status_code}")
        print(f"Response: {r.text}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_tasks()

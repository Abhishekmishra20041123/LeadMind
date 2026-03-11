import urllib.request
import json
import os

url = 'http://localhost:8000/api/leads/L003/preview-template'
data = json.dumps({"template_id": "", "content": "hello body"}).encode('utf-8')
req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})

try:
    res = urllib.request.urlopen(req)
    print("STATUS", res.status)
    print(res.read().decode('utf-8'))
except urllib.error.HTTPError as e:
    print("HTTP ERROR", e.code)
    print(e.read().decode('utf-8'))
except Exception as e:
    print("ERROR", str(e))

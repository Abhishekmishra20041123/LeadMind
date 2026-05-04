import json
import urllib.request
import urllib.error
import socket
import ssl

def fetch_microlink(url):
    print(f"--- Fetching Microlink for URL: {url} ---")
    _microlink_url = f'https://api.microlink.io/?url={urllib.request.quote(url, safe="/:?=&")}'
    print(f"DEBUG: Microlink API URL: {_microlink_url}")
    
    req = urllib.request.Request(
        _microlink_url,
        headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
    )
    
    try:
        with urllib.request.urlopen(req, timeout=10) as _resp:
            _raw = _resp.read(65536)
            _data = json.loads(_raw.decode('utf-8', errors='replace'))
            return _data
    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {str(e)}")
        return None

if __name__ == "__main__":
    test_url = "https://www.bookswagon.com/book/atomic-habits-james-clear/9781847941831"
    data = fetch_microlink(test_url)
    
    if data:
        print("\n[RESULT] Data received:")
        # print(json.dumps(data, indent=2))
        
        extracted_img = (
            data.get('data', {}).get('image', {}).get('url') or
            data.get('data', {}).get('logo',  {}).get('url')
        )
        print(f"\nExtracted Image: {extracted_img}")
        
        if extracted_img:
            print("✅ SUCCESS!")
        else:
            print("❌ FAILURE: No image in response.")
    else:
        print("\n❌ FAILURE: No data received from Microlink.")

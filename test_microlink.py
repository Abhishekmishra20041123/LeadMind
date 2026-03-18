
import json
import urllib.request

def test_microlink(url):
    try:
        req = urllib.request.Request(f'https://api.microlink.io/?url={url}', headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode('utf-8'))
            print(json.dumps(data, indent=2))
            extracted_img = data.get('data', {}).get('image', {}).get('url')
            print(f"\nExtracted Image: {extracted_img}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_microlink("https://theobroma.in/products/blueberry-cheesecake-cup")

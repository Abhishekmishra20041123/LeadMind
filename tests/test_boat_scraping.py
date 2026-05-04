import re
import urllib.request
import urllib.error
from urllib.parse import urljoin

def direct_fetch_og_image(url: str, timeout=10) -> str:
    print(f"--- Attempting Direct OG Fetch for: {url} ---")
    try:
        req = urllib.request.Request(
            url,
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            content = resp.read(256000).decode('utf-8', errors='replace')
            match = re.search(r'<meta.*?property=["\']og:image["\'].*?content=["\'](.*?)["\']', content)
            if not match:
                match = re.search(r'<meta.*?content=["\'](.*?)["\'].*?property=["\']og:image["\']', content)
            
            if match:
                img_url = match.group(1)
                if img_url.startswith('//'):
                    img_url = 'https:' + img_url
                elif not img_url.startswith('http'):
                    img_url = urljoin(url, img_url)
                return img_url
    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {str(e)}")
    return None

if __name__ == "__main__":
    # Test with a boAt product
    test_url = "https://www.boat-lifestyle.com/products/airdopes-161"
    img = direct_fetch_og_image(test_url)
    if img:
        print(f"\n[boAt SUCCESS] URL: {img}")
    else:
        print("\n[boAt FAIL] Could not extract image directly.")

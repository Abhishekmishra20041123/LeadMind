import re
import urllib.request
import urllib.error
from urllib.parse import urljoin

def direct_fetch_og_image(url: str, timeout=10) -> str:
    """Fallback scraper that tries to fetch OpenGraph image directly if Microlink fails"""
    print(f"--- Attempting Direct OG Fetch for: {url} ---")
    try:
        req = urllib.request.Request(
            url,
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            content = resp.read(256000).decode('utf-8', errors='replace') # Read 256KB for better chance
            
            # Look for og:image
            match = re.search(r'<meta.*?property=["\']og:image["\'].*?content=["\'](.*?)["\']', content)
            if not match:
                match = re.search(r'<meta.*?content=["\'](.*?)["\'].*?property=["\']og:image["\']', content)
            
            # Look for twitter:image
            if not match:
                match = re.search(r'<meta.*?name=["\']twitter:image["\'].*?content=["\'](.*?)["\']', content)

            if match:
                img_url = match.group(1)
                print(f"DEBUG: Found raw match: {img_url}")
                if img_url.startswith('//'):
                    img_url = 'https:' + img_url
                elif not img_url.startswith('http'):
                    img_url = urljoin(url, img_url)
                return img_url
            else:
                print("DEBUG: No OG or Twitter image tags found in the first 256KB.")
    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {str(e)}")
    return None

if __name__ == "__main__":
    test_url = "https://www.bookswagon.com/book/atomic-habits-james-clear/9781847941831"
    img = direct_fetch_og_image(test_url)
    
    if img:
        print(f"\n✅ SUCCESS! Extracted Image URL: {img}")
    else:
        print("\n❌ FAILURE: Could not extract image directly.")

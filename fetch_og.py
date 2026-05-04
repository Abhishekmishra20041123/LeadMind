import asyncio
from playwright.async_api import async_playwright
import json

async def fetch_og_image(url):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        
        try:
            # Wait until domcontentloaded to quickly grab the meta tag without waiting for full page load
            await page.goto(url, wait_until="domcontentloaded", timeout=15000)
            
            # Extract og:image
            og_image = await page.evaluate('''() => {
                const meta = document.querySelector('meta[property="og:image"]');
                return meta ? meta.content : null;
            }''')
            
            return og_image
        except Exception as e:
            print(f"Error fetching {url}: {e}")
            return None
        finally:
            await browser.close()

async def main():
    urls = [
        "https://www.tiffany.com/engagement-rings/1711",
        "https://www.tiffany.com/necklaces/1364184611",
        "https://www.tiffany.com/earrings/1361328805"
    ]
    
    results = {}
    for url in urls:
        print(f"Fetching {url}...")
        img = await fetch_og_image(url)
        results[url] = img
        print(f"Found: {img}")
        
    with open("tiffany_images.json", "w") as f:
        json.dump(results, f, indent=2)

if __name__ == "__main__":
    asyncio.run(main())

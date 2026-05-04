"""
sdk_page_crawler.py — Intelligent Page Understanding for SDK Leads

Upgraded to use Playwright for robust, headless crawling.
Features:
1. Page Type Detection (Product, Listing, Home, etc.)
2. Product Block Extraction (Containers)
3. Smart Image Filtering (Size, Aspect Ratio, Content)
4. AI-Powered Segmentation & Refinement

Isolated from CSV lead pipeline.
"""

import re
import json
import time
from typing import List, Dict, Optional
from urllib.parse import urljoin, urlparse
from playwright.sync_api import sync_playwright

# ── Constants ─────────────────────────────────────────────────────────────────

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

TIMEOUT = 15000  # 15 seconds
MAX_PAGES = 5
MIN_IMAGE_SIZE = 200  # Minimum width/height for a product image

# ── Console Helper ────────────────────────────────────────────────────────────

def _safe_print(msg: str):
    """Print message to console, sanitizing non-ASCII characters for Windows."""
    try:
        print(msg)
    except UnicodeEncodeError:
        print(msg.encode('ascii', 'ignore').decode('ascii'))

# ── Smart Crawler Core ────────────────────────────────────────────────────────

class SmartCrawler:
    def __init__(self, llm=None):
        self.llm = llm

    def detect_page_type(self, page) -> str:
        """
        Detects if the page is a Product page, Listing/Category page, Checkout, or general.
        """
        url = page.url.lower()
        
        # 0. Check checkout/booking pages first
        checkout_keywords = ["/checkout", "/booking", "/pay", "/cart", "/order"]
        if any(x in url for x in checkout_keywords):
            return "checkout"

        content = page.content().lower()

        # 1. Check Meta Tags
        og_type = page.query_selector('meta[property="og:type"]')
        if og_type:
            content_val = og_type.get_attribute("content") or ""
            if "product" in content_val.lower():
                return "product"

        # 2. Check JSON-LD
        scripts = page.query_selector_all('script[type="application/ld+json"]')
        for script in scripts:
            try:
                data = json.loads(script.inner_text())
                if isinstance(data, dict):
                    if data.get("@type") == "Product": return "product"
                    if data.get("@type") == "ItemList": return "listing"
                elif isinstance(data, list):
                    for item in data:
                        if item.get("@type") == "Product": return "product"
            except:
                pass

        # 3. Heuristics
        # Many product pages have "add to cart" or "reserve"
        add_to_cart = page.query_selector_all('button:has-text("Add to Cart"), button:has-text("Buy Now"), button:has-text("Reserve")')
        if len(add_to_cart) == 1:
            return "product"
        elif len(add_to_cart) > 1:
            return "listing"

        # URL hints
        url_path = urlparse(url).path
        path_parts = [p for p in url_path.split('/') if p]
        
        if path_parts:
            last_part = path_parts[-1]
            # If the last part looks like an ID (long alphanumeric, or numbers) 
            is_id = len(last_part) >= 6 and any(c.isdigit() for c in last_part)
            
            if any(x in url_path for x in ["/p/", "/product/", "/item/"]): 
                return "product"
                
            # Handle categories and listings
            if any(x in url_path for x in ["/c/", "/category/", "/shop/", "/collections/", "/listings"]):
                if is_id:
                    return "product" # /listings/12345
                else:
                    return "listing" # /listings

        return "general"

    def extract_product_blocks(self, page) -> List[Dict]:
        """
        Extracts product-like containers from the page.
        """
        blocks = []
        
        # Selectors commonly used for product items
        selectors = [
            '[itemtype*="Product"]', 
            '.product-item', '.product-card', '.product',
            '.item', '.grid-item', '.card'
        ]
        
        for selector in selectors:
            elements = page.query_selector_all(selector)
            if len(elements) > 2: # Significant number of products
                for el in elements[:10]: # Cap at 10 per page
                    text = el.inner_text().strip()
                    if len(text) < 20: continue # Too short to be a product
                    
                    img = el.query_selector('img')
                    img_url = img.get_attribute('src') if img else None
                    if img_url:
                        img_url = urljoin(page.url, img_url)
                    
                    blocks.append({
                        "text": text,
                        "image": img_url,
                        "html": el.inner_html()[:500] # Snippet for AI
                    })
                break # Found a good set
        
        return blocks

    def filter_images(self, page) -> List[Dict]:
        """
        Finds images on the page and extracts their properties for AI segmentation.
        """
        images = []
        img_elements = page.query_selector_all('img')
        
        for img in img_elements:
            try:
                src = img.get_attribute('src')
                if not src: continue
                
                src = urljoin(page.url, src)
                alt = (img.get_attribute('alt') or "").strip()
                
                size = page.evaluate('''(img) => {
                    return { w: img.naturalWidth, h: img.naturalHeight };
                }''', img)
                
                w, h = size['w'], size['h']
                
                # Exclude tiny tracking pixels
                if w < 20 or h < 20: continue
                
                images.append({
                    "src": src,
                    "alt": alt,
                    "width": w,
                    "height": h
                })
            except:
                continue
                
        # Deduplicate by src
        seen = set()
        unique_images = []
        for img in images:
            if img["src"] not in seen:
                seen.add(img["src"])
                unique_images.append(img)
                
        # Sort by area (largest first)
        unique_images.sort(key=lambda x: x["width"] * x["height"], reverse=True)
        return unique_images[:15] # Top 15 largest

    def understand_page_with_ai(self, url: str, page_type: str, blocks: List[Dict], images: List[Dict], meta: Dict) -> Dict:
        """
        Uses LLM to refine the extracted data and segment images.
        """
        if not self.llm:
            return {
                "product_name": meta.get("title", "Unknown Product"),
                "category": "product",
                "price": meta.get("price"),
                "short_description": meta.get("description", ""),
                "key_features": [],
                "why_buy": None,
                "images": {}
            }

        prompt = f"""You are a product and page data specialist. Analyze these signals from a webpage ({url}).
Page Type Detected: {page_type}
Meta Title: {meta.get('title')}
Meta Description: {meta.get('description')}
Visible Price (Regex matched): {meta.get('price', 'None found')}

Sample Product Blocks found:
{json.dumps(blocks[:3], indent=2)}

Images found on page (sorted by size, largest first):
{json.dumps(images[:10], indent=2)}

Based on the URL, text content, and image metadata (alt text, size), segment the data properly.
Return a JSON object:
{{
  "product_name": "Main product/service/property name",
  "category": "e.g., electronics, clothing, saas, real estate, booking, etc.",
  "price": "Price if found",
  "short_description": "1-2 sentence summary",
  "key_features": ["feature 1", "feature 2"],
  "why_buy": "Compelling sales hook or unique value proposition",
  "images": {{
     "main_product_image": "Best URL for the actual product/property/service itself (the main offering)",
     "host_or_seller_image": "URL of the seller, brand avatar, or host if present",
     "logo": "URL of the site logo if present",
     "ad_images": ["URLs of banners/ads"]
  }}
}}
Return ONLY JSON."""

        try:
            resp = self.llm.generate_content(prompt)
            text = resp.text.strip()
            if "```" in text:
                text = re.search(r'\{.*\}', text, re.DOTALL).group(0)
            return json.loads(text)
        except Exception as e:
            _safe_print(f"  [SmartCrawler] AI refinement failed: {e}")
            return {
                "product_name": meta.get("title", "Unknown"),
                "category": "product",
                "price": meta.get("price"),
                "short_description": meta.get("description", ""),
                "key_features": [],
                "why_buy": None,
                "images": {}
            }

    def crawl(self, urls: List[str]) -> List[Dict]:
        results = []
        seen_names = set()

        # Smart URL selection: Prioritize most recent, non-utility pages
        recent_urls = list(dict.fromkeys(reversed(urls)))  # Deduplicate while keeping most recent first
        ignored_patterns = ["/login", "/signup", "/register", "/profile", "/account", "/cart", "/checkout"]
        filtered_urls = [u for u in recent_urls if not any(p in u for p in ignored_patterns)]
        target_urls = filtered_urls if filtered_urls else recent_urls
        urls_to_crawl = target_urls[:MAX_PAGES]

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(user_agent=USER_AGENT)
            
            for url in urls_to_crawl:
                try:
                    _safe_print(f"  [SmartCrawler] Visiting: {url}")
                    page = context.new_page()
                    page.goto(url, timeout=TIMEOUT, wait_until="domcontentloaded")
                    
                    # Scroll to trigger lazy loaded images
                    page.evaluate("window.scrollBy(0, document.body.scrollHeight/2)")
                    time.sleep(1)
                    page.evaluate("window.scrollBy(0, -document.body.scrollHeight/2)")
                    time.sleep(1)

                    page_type = self.detect_page_type(page)
                    blocks = self.extract_product_blocks(page)
                    images = self.filter_images(page)
                    
                    # Extract basic meta for context
                    meta = {
                        "title": page.title(),
                        "description": page.query_selector('meta[name="description"]').get_attribute('content') if page.query_selector('meta[name="description"]') else "",
                        "price": None, # Fallback
                        "og_image": page.query_selector('meta[property="og:image"]').get_attribute('content') if page.query_selector('meta[property="og:image"]') else None
                    }
                    
                    # Try to find price in visible text if not in meta
                    try:
                        visible_text = page.inner_text()
                        price_match = re.search(r'(?:₹|Rs\.?|INR|USD|\$|£|€)\s?[0-9]+(?:[,.][0-9]+)*', visible_text)
                        if price_match:
                            meta["price"] = price_match.group(0).strip()
                    except:
                        pass

                    # AI refinement
                    understood = self.understand_page_with_ai(url, page_type, blocks, images, meta)
                    
                    product_name = understood.get("product_name") or meta["title"]
                    name_key = product_name.lower()[:40]
                    
                    if name_key in seen_names:
                        continue
                    seen_names.add(name_key)

                    # Choose best image
                    segmented_images = understood.get("images", {})
                    best_image = segmented_images.get("main_product_image") or meta.get("og_image")
                    
                    if not best_image and images:
                        # Fallback to the largest image if none selected
                        best_image = images[0]["src"]
                        
                    if best_image and not best_image.startswith("http"):
                        best_image = urljoin(url, best_image)

                    card = {
                        "url": url,
                        "name": product_name,
                        "category": understood.get("category", "product"),
                        "price": understood.get("price") or meta["price"],
                        "short_description": understood.get("short_description") or meta["description"],
                        "key_features": understood.get("key_features") or [],
                        "why_buy": understood.get("why_buy"),
                        "image": best_image,
                        "has_image": bool(best_image),
                        "page_type": page_type,
                        "image_segmentation": segmented_images,
                        "all_images": [img["src"] for img in images[:5]] # Keep URLs for selection later
                    }
                    results.append(card)
                    _safe_print(f"  [SmartCrawler] SUCCESS: {card['name']} ({page_type})")

                except Exception as e:
                    _safe_print(f"  [SmartCrawler] Error crawling {url}: {e}")
                finally:
                    page.close()

            browser.close()

        # If we have actual product pages, filter out general listings or checkouts
        product_results = [r for r in results if r.get("page_type") == "product"]
        if product_results:
            return product_results

        return results

# ── Main Entry Point ──────────────────────────────────────────────────────────

def crawl_sdk_product_pages(urls: List[str], llm=None) -> List[Dict]:
    crawler = SmartCrawler(llm=llm)
    return crawler.crawl(urls)

if __name__ == "__main__":
    # Test
    test_urls = ["https://www.apple.com/iphone-15/"]
    # print(crawl_sdk_product_pages(test_urls))

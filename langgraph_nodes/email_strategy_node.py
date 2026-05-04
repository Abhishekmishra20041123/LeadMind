import json
import re
import urllib.request
import urllib.error
import socket
import ssl
import time
import random
from typing import Dict, Any
from langgraph.graph import StateGraph, END

def _safe_print(msg: str):
    """Print message to console, sanitizing non-ASCII characters for Windows."""
    try:
        print(msg)
    except UnicodeEncodeError:
        # Fallback for Windows CP1252 / charmap
        print(msg.encode('ascii', 'ignore').decode('ascii'))

def direct_fetch_og_image(url: str, timeout=5) -> str:
    """Fallback scraper that tries to fetch OpenGraph image directly if Microlink fails"""
    try:
        req = urllib.request.Request(
            url,
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            content = resp.read(128000).decode('utf-8', errors='replace') # Read first 128KB
            # Look for og:image or twitter:image
            match = re.search(r'<meta.*?property=["\']og:image["\'].*?content=["\'](.*?)["\']', content)
            if not match:
                match = re.search(r'<meta.*?content=["\'](.*?)["\'].*?property=["\']og:image["\']', content)
            if not match:
                match = re.search(r'<meta.*?name=["\']twitter:image["\'].*?content=["\'](.*?)["\']', content)
            
            if match:
                img_url = match.group(1)
                if img_url.startswith('//'):
                    img_url = 'https:' + img_url
                elif not img_url.startswith('http'):
                    # Handle relative paths (basic)
                    from urllib.parse import urljoin
                    img_url = urljoin(url, img_url)
                return img_url
    except:
        pass
    return None

def create_email_strategy_graph(llm, prompt_templates):
    """Create email strategy workflow"""
    workflow = StateGraph(Dict[str, Any])
    
    workflow.add_node("prepare_data", prepare_data)
    workflow.add_node("generate_email", lambda x: generate_email(x, llm, prompt_templates))
    
    workflow.add_edge("prepare_data", "generate_email")
    workflow.add_edge("generate_email", END)
    
    workflow.set_entry_point("prepare_data")
    return workflow.compile()

def prepare_data(state):
    """Clean and validate data for single lead"""
    print("\n=== prepare_data Step (Email Strategy) ===")
    
    lead = state.get("lead", {})
    if not lead:
        return {**state, "status": "error", "error": "No lead data provided"}
    
    intent_score = state.get("intent_score", 0.0)
    
    return {
        **state,
        "status": "data_prepared"
    }

def generate_email(state, llm=None, prompt_templates=None):
    """Generate email using LLM for single lead"""
    print("\n=== generate_email Step ===")
    
    if not llm or not prompt_templates:
        return {**state, "status": "error", "error": "Missing LLM or prompts"}
    
    lead_json = json.dumps(state.get("lead", {}), indent=2)
    intent_signals = json.dumps(state.get("key_signals", []), indent=2)
    company_info = json.dumps(state.get("company_info", {}), indent=2)
    operator_info = json.dumps(state.get("operator_info", {}), indent=2)
    
    
    try:
        # Dynamically fetch the official OpenGraph product image from the exact URL
        import urllib.request
        from urllib.error import URLError
        
        # The "lead" in state can be either:
        # (a) the raw CSV row dict directly (which contains page_link at the top level), or
        # (b) a nested MongoDB doc with a raw_data sub-key.
        lead_data = state.get("lead_data", state.get("lead", {}))
        raw_data = lead_data.get("raw_data", lead_data)
        schema_mapping = state.get("schema_mapping", {})

        is_sdk_lead = lead_data.get("source") == "sdk"

        # ══════════════════════════════════════════════════════════════════════
        # PATH A — SDK Lead: Intelligent Page Crawler (context-aware)
        # Understands what each page is ABOUT and extracts product/service data.
        # Works for electronics, food, hotel, books, courses, bakery — any type.
        # ══════════════════════════════════════════════════════════════════════
        if is_sdk_lead:
            import sys, os
            sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
            from services.sdk_page_crawler import crawl_sdk_product_pages

            # Prefer confirmed product page URLs, fall back to all visited URLs
            product_urls = (
                lead_data.get("sdk_activity", {}).get("product_page_urls") or
                lead_data.get("sdk_activity", {}).get("urls") or
                []
            )

            print(f"  [EmailNode/SDK] Crawling {len(product_urls)} product pages intelligently...")
            product_cards = crawl_sdk_product_pages(product_urls, llm=llm)

            # Build product context summary for the LLM email prompt
            product_context_lines = []
            product_cards_html   = ""
            scraped_media        = []

            for card in product_cards:
                # Build a text summary for the LLM
                line = f"- {card['name']}"
                if card.get("category"):       line += f" [{card['category']}]"
                if card.get("price"):          line += f" — {card['price']}"
                if card.get("short_description"): line += f": {card['short_description']}"
                if card.get("key_features"):   line += f" | Features: {', '.join(card['key_features'][:3])}"
                if card.get("location"):       line += f" | Location: {card['location']}"
                if card.get("why_buy"):        line += f" | Why buy: {card['why_buy']}"
                product_context_lines.append(line)

                # Build HTML product card (only if we have an image)
                if card.get("image"):
                    price_html = f'<p style="font-size:14px;font-weight:700;color:#1a73e8;margin:4px 0;">{card["price"]}</p>' if card.get("price") else ""
                    desc_html  = f'<p style="font-size:12px;color:#555;margin:4px 0;line-height:1.4;">{card["short_description"][:120]}...</p>' if card.get("short_description") else ""
                    product_cards_html += f'''
                    <div style="flex:1;min-width:200px;max-width:280px;border:1px solid #eef2f7;border-radius:12px;
                                padding:14px;background:#fff;box-shadow:0 4px 6px rgba(0,0,0,0.05);
                                margin:8px;display:inline-block;vertical-align:top;text-align:center;">
                        <img src="{card['image']}" alt="{card['name']}"
                             style="width:100%;height:160px;object-fit:cover;border-radius:8px;margin-bottom:10px;background:#f8fafc;" />
                        <h4 style="margin:0 0 6px;color:#1a1f36;font-size:15px;line-height:1.3;">{card['name']}</h4>
                        {price_html}
                        {desc_html}
                        <a href="{card['url']}" style="display:block;width:80%;margin:10px auto 0;padding:9px 0;
                           background:#1a73e8;color:#fff;text-decoration:none;border-radius:6px;
                           font-weight:600;font-size:13px;">View Details</a>
                    </div>'''

                # Always add to scraped_media for UI display
                scraped_media.append({
                    "url":              card["url"],
                    "name":             card["name"],
                    "image":            card.get("image"),
                    "price":            card.get("price"),
                    "category":         card.get("category"),
                    "short_description":card.get("short_description"),
                    "has_image":        card.get("has_image", False),
                })

            product_context_str = "\n".join(product_context_lines) if product_context_lines else "No specific products identified — write a general engagement email."
            _safe_print(f"  [EmailNode/SDK] Product context built for {len(product_cards)} items.")

            # ── Build SDK-specific email prompt ──────────────────────────────
            sdk_email_prompt = f"""You are an expert sales copywriter drafting a personalized outreach email for a web visitor.

VISITOR INFO:
{lead_json}

BEHAVIORAL SIGNALS:
{intent_signals}

COMPANY/SENDER INFO:
{company_info}

PRODUCTS/PAGES THE VISITOR VIEWED:
{product_context_str}

INSTRUCTIONS:
- Write a warm, personalized HTML email that references the specific products/services the visitor viewed
- Mention product names, prices (if available), and key features naturally in the body text
- Keep it conversational and compelling — not generic
- Do NOT mention you tracked them; frame it as "based on your interest in..."
- If products have a location (hotel/restaurant), mention the area naturally
- End with a clear call to action
- Return a JSON object: {{"subject": "...", "email_preview": "<html email body here>", "personalization_factors": ["...", "..."]}}

Return ONLY valid JSON."""

            response = llm.generate_content(sdk_email_prompt)
            response_text = response.text.strip()

        # ══════════════════════════════════════════════════════════════════════
        # PATH B — CSV Lead: Original image-scraping logic (UNCHANGED)
        # ══════════════════════════════════════════════════════════════════════
        else:
            collected_links = []

            # Step 1: page_link field
            print(f"  [EmailNode] DEBUG: raw_data keys found: {list(raw_data.keys())}")
            page_links_raw = raw_data.get("page_link", lead_data.get("page_link", []))
            if page_links_raw:
                items_to_scan = page_links_raw if isinstance(page_links_raw, list) else [page_links_raw]
                for item in items_to_scan:
                    urls = re.findall(r'https?://[^\s,|;<>\"\'[\](){}]+', str(item))
                    for u in urls:
                        clean_u = re.sub(r'[,;\"\')\]\s\.]+$', '', u)
                        if clean_u and clean_u not in collected_links:
                            collected_links.append(clean_u)

            # Step 2: schema_mapping link columns
            content_fields   = schema_mapping.get("content_fields", {})
            behavioral_fields = schema_mapping.get("behavioral_fields", {})
            link_col_keys = ["url", "product_link", "content_links", "page_link", "landing_page"]
            link_cols = []
            for key in link_col_keys:
                val = content_fields.get(key) or behavioral_fields.get(key)
                if val and isinstance(val, str):
                    link_cols.extend([c.strip() for c in val.split(",") if c.strip()])

            lead_lower = {k.lower(): v for k, v in raw_data.items()}
            for col in link_cols:
                cell = lead_lower.get(col.lower())
                if cell and str(cell).strip():
                    urls = re.findall(r'https?://[^\s,|;<>\"\'[\](){}]+', str(cell))
                    for u in urls:
                        clean_u = re.sub(r'[,;\"\')\]\s\.]+$', '', u)
                        if clean_u and clean_u not in collected_links:
                            collected_links.append(clean_u)

            # Step 3: Last-resort — scan all fields
            for key, val in raw_data.items():
                if val and isinstance(val, (str, list)):
                    urls = re.findall(r'https?://[^\s,|;<>\"\'[\](){}]+', str(val))
                    for u in urls:
                        clean_u = re.sub(r'[,;\"\')\]\s\.]+$', '', u)
                        if clean_u and clean_u not in collected_links:
                            collected_links.append(clean_u)

            filtered_links = []
            seen = set()
            for l in collected_links:
                if l.startswith("http") and l not in seen:
                    seen.add(l)
                    filtered_links.append(l)

            page_links = filtered_links
            print(f"  [EmailNode] Found {len(page_links)} links for scraping: {page_links[:3]}")

            existing_scraped    = lead_data.get("intel", {}).get("scraped_media", [])
            scraped_media_map   = {m.get("url"): m for m in existing_scraped if m.get("url")}
            product_cards_html  = ""
            product_names       = []
            scraped_media       = []

            for link in page_links:
                link = link.strip()
                if not link: continue
                if link in scraped_media_map:
                    m = scraped_media_map[link]
                    scraped_media.append(m)
                    product_names.append(m.get("name", "Product"))
                    continue

                product_name = link.split("/")[-1].replace(".html", "").replace("-", " ").title()
                product_names.append(product_name)
                img_url = None

                print(f"  [EmailNode] Attempting Direct OG Fetch for {link[:50]}...")
                direct_img = direct_fetch_og_image(link, timeout=4)
                if direct_img and isinstance(direct_img, str) and direct_img.startswith('http'):
                    img_url = direct_img
                    print(f"  [EmailNode] SUCCESS: Live image via Direct OG")

                if not img_url:
                    print(f"  [EmailNode] Attempting Microlink Browser for {link[:50]}...")
                    try:
                        import socket, ssl, urllib.parse
                        time.sleep(random.uniform(0.1, 0.3))
                        _microlink_url = f"https://api.microlink.io?url={urllib.parse.quote(link)}&screenshot=true&meta=true"
                        req = urllib.request.Request(
                            _microlink_url,
                            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
                        )
                        with urllib.request.urlopen(req, timeout=10) as _resp:
                            _raw = _resp.read(65536)
                            _data = json.loads(_raw.decode('utf-8', errors='replace'))
                            _payload = _data.get('data') or {}
                            extracted_img = (
                                (_payload.get('image') or {}).get('url') or
                                (_payload.get('logo') or {}).get('url')
                            )
                            if extracted_img and isinstance(extracted_img, str) and extracted_img.startswith('http'):
                                img_url = extracted_img
                                print(f"  [EmailNode] SUCCESS: Live image via Microlink")
                    except Exception as e:
                        print(f"  [EmailNode] Microlink backup failed: {type(e).__name__}")

                if not img_url:
                    print(f"  [EmailNode] Attempting Jina Reader for {link[:50]}...")
                    try:
                        import urllib.parse
                        _jina_url = f"https://r.jina.ai/{link}"
                        req = urllib.request.Request(
                            _jina_url,
                            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
                        )
                        with urllib.request.urlopen(req, timeout=6) as _resp:
                            _raw_md = _resp.read(100000).decode('utf-8', errors='replace')
                            _match = re.search(r'!\[.*?\]\((https?://.*?)\)', _raw_md)
                            if _match:
                                extracted_img = _match.group(1)
                                if extracted_img and extracted_img.startswith('http'):
                                    img_url = extracted_img
                                    print(f"  [EmailNode] SUCCESS: Live image via Jina")
                    except Exception as e:
                        print(f"  [EmailNode] Jina backup skipped: {type(e).__name__}")

                if not img_url:
                    print(f"  [EmailNode] !! No real image found. Skipping image for this item.")

                if img_url:
                    img_tag = f'<img src="{img_url}" alt="{product_name}" style="width: 100%; height: 180px; object-fit: cover; border-radius: 8px; margin-bottom: 12px; background: #f8fafc;" />'
                    card = f'''
                    <div class="product-item" style="flex: 1; min-width: 200px; max-width: 300px; border: 1px solid #eef2f7; border-radius: 12px; padding: 15px; background: #ffffff; box-shadow: 0 4px 6px rgba(0,0,0,0.05); margin: 10px; display: inline-block; vertical-align: top; text-align: center;">
                        {img_tag}
                        <h4 style="margin: 0 0 10px 0; color: #1a1f36; font-size: 16px; height: 40px; overflow: hidden; line-height: 1.3;">{product_name}</h4>
                        <a href="{link}" style="display: block; width: 80%; margin: 0 auto; padding: 10px 0; background-color: #1a73e8; color: #ffffff; text-decoration: none; border-radius: 6px; font-weight: 600; font-size: 14px;">View Item</a>
                    </div>'''
                    product_cards_html += card

                scraped_media.append({
                    "url": link,
                    "image": img_url,
                    "name": product_name,
                    "has_image": bool(img_url)
                })

            product_names_str = ", ".join(product_names) if product_names else "our collection"

            # Build CSV prompt
            prompt = prompt_templates["craft_email"]
            prompt = prompt.replace("{lead}", lead_json)
            prompt = prompt.replace("{intent_signals}", intent_signals)
            prompt = prompt.replace("{company_info}", company_info)
            prompt = prompt.replace("{operator_info}", operator_info)
            prompt = prompt.replace("{product_names}", product_names_str)

            response = llm.generate_content(prompt)
            response_text = response.text.strip()

        # ══════════════════════════════════════════════════════════════════════
        # SHARED: Parse LLM response + assemble final email
        # ══════════════════════════════════════════════════════════════════════

        if response_text.startswith('```'):
            start = response_text.find('{')
            end   = response_text.rfind('}') + 1
            if start != -1 and end != 0:
                response_text = response_text[start:end]

        try:
            email = json.loads(response_text)
        except (json.JSONDecodeError, AttributeError) as e:
            print(f"Warning: Failed to parse Email Strategy JSON. Response was: {response_text[:100]}...")
            return {
                **state,
                "status": "completed",
                "email_preview": f"Error: Failed to generate personalized email body. {str(e)}",
                "subject": "Follow-up regarding your interest"
            }

        email_preview = email.get("email_preview", email.get("body", ""))

        # Assemble product catalog HTML block
        catalog_wrapper = f'''
        <div class="product-catalog-grid" style="display: flex; flex-wrap: wrap; justify-content: center; gap: 10px; margin: 25px 0;">
            {product_cards_html}
        </div>
        ''' if product_cards_html else ""

        print(f"  [EmailNode] Generated {len(scraped_media)} product cards for the catalog.")

        # Sanitize LLM output
        email_preview = re.sub(r'<iframe.*?>.*?</iframe>', '', email_preview, flags=re.DOTALL)
        email_preview = re.sub(r'<div[^>]*?>.*?View Selection.*?</div>', '', email_preview, flags=re.DOTALL | re.IGNORECASE)
        email_preview = re.sub(r'<img[^>]*>', '', email_preview, flags=re.IGNORECASE)
        email_preview = re.split(r'(?i)(\*\*|💡|📝)?\s*(Message\s*)?(Notes|Tip|Suggestion):?', email_preview)[0]
        email_preview = email_preview.replace("[Your Name]", f"The {state.get('operator_info', {}).get('company', 'Team')}")
        email_preview = re.sub(r'\[Phone Number\]|\[Email Address\]|\[Link\]', '', email_preview)
        email_preview = email_preview.strip()

        # Inject product catalog
        if catalog_wrapper:
            if "[PRODUCT_CATALOG]" in email_preview or "[INSERT_PRODUCTS_HERE]" in email_preview:
                email_preview = email_preview.replace("[PRODUCT_CATALOG]", catalog_wrapper)
                email_preview = email_preview.replace("[INSERT_PRODUCTS_HERE]", catalog_wrapper)
            elif "</body>" in email_preview:
                email_preview = email_preview.replace("</body>", f"\n\n{catalog_wrapper}\n\n</body>")
            else:
                sign_offs = ["Best regards,", "Warm regards,", "Best,", "Regards,", "Sincerely,", "Thanks,", "Yours,"]
                inserted = False
                for sign_off in sign_offs:
                    if sign_off.lower() in email_preview.lower():
                        start_idx    = email_preview.lower().find(sign_off.lower())
                        actual_so    = email_preview[start_idx:start_idx+len(sign_off)]
                        email_preview = email_preview.replace(actual_so, f"\n\n{catalog_wrapper}\n\n{actual_so}")
                        inserted = True
                        break
                if not inserted:
                    email_preview += f"\n\n{catalog_wrapper}"

        return {
            **state,
            "subject":                email.get("subject", ""),
            "personalization_factors": email.get("personalization_factors", []),
            "email_preview":           email_preview,
            "scraped_media":           scraped_media,
            "status":                  "completed"
        }

    except Exception as e:
        print(f"Error parsing response: {str(e)}")
        return {
            **state,
            "status": "error",
            "error":  str(e),
            "subject": "Error drafting email",
            "personalization_factors": ["Error"],
            "email_preview": "Failed to generate email."
        }

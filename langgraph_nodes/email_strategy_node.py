"""Email Strategy Nodes

LangGraph workflow for email crafting.
"""

import json
from typing import Dict, Any
from langgraph.graph import StateGraph, END

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
        # Handle both cases robustly.
        lead_data = state.get("lead_data", state.get("lead", {}))
        raw_data = lead_data.get("raw_data", lead_data)  # fallback to lead_data itself
        schema_mapping = state.get("schema_mapping", {})

        collected_links = []

        # ── Step 1: Check the standardized "page_link" field set by batch.py ──
        page_links_raw = raw_data.get("page_link", lead_data.get("page_link", []))
        if isinstance(page_links_raw, list):
            collected_links.extend(page_links_raw)
        elif isinstance(page_links_raw, str):
            collected_links.extend([p.strip() for p in page_links_raw.replace("|", ",").split(",") if p.strip()])

        # ── Step 2: Use schema_mapping.content_fields to find more link columns ──
        if not any(l.startswith("http") for l in collected_links):
            content_fields = schema_mapping.get("content_fields", {})
            behavioral_fields = schema_mapping.get("behavioral_fields", {})
            # Gather all mapped column names that might contain URLs
            link_col_keys = ["url", "product_link", "content_links", "page_link", "landing_page"]
            link_cols = []
            for key in link_col_keys:
                val = content_fields.get(key) or behavioral_fields.get(key)
                if val and isinstance(val, str):
                    link_cols.extend([c.strip() for c in val.split(",") if c.strip()])
            # Extract from lead dict using those column names (case-insensitive)
            lead_lower = {k.lower(): v for k, v in raw_data.items()}
            for col in link_cols:
                cell = lead_lower.get(col.lower())
                if cell and str(cell).strip():
                    parts = [p.strip() for p in str(cell).replace("|", ",").split(",") if p.strip()]
                    collected_links.extend(parts)

        # ── Step 3: Last-resort fallback — scan ALL lead fields for http URLs ──
        if not any(str(l).startswith("http") for l in collected_links):
            for key, val in raw_data.items():
                if val and isinstance(val, str):
                    # Each cell may have pipe or comma separated links
                    parts = [p.strip() for p in val.replace("|", ",").split(",")]
                    for part in parts:
                        if part.startswith("http") and "." in part:
                            collected_links.append(part)

        # ── Deduplicate and validate ──
        filtered_links = []
        seen = set()
        for l in collected_links:
            ls = str(l).strip()
            if ls.startswith("http") and ls not in seen:
                seen.add(ls)
                filtered_links.append(ls)

        page_links = filtered_links
        print(f"  [EmailNode] Found {len(page_links)} links for scraping: {page_links[:3]}")

        
        product_cards_html = ""
        product_names = []
        
        for link in page_links:
            link = link.strip()
            if not link: continue
            
            # Extract a pseudo product name from the URL
            product_name = link.split("/")[-1].replace(".html", "").replace("-", " ").title()
            product_names.append(product_name)
            
            # Determine refined fallback based on industry/keywords
            industry_lower = str(raw_data.get("industry", raw_data.get("Industry", "generic"))).lower()
            product_type_hint = product_name.lower()
            
            # High-quality industry-specific fallbacks from Unsplash
            # These are used if Microlink fails to fetch a live product image
            fallbacks = {
                "book": "https://images.unsplash.com/photo-1544947950-fa07a98d237f?q=80&w=800",
                "publishing": "https://images.unsplash.com/photo-1544947950-fa07a98d237f?q=80&w=800",
                "tiffany": "https://images.unsplash.com/photo-1515562141207-7a88fb7ce33e?q=80&w=800",
                "jewelry": "https://images.unsplash.com/photo-1515562141207-7a88fb7ce33e?q=80&w=800",
                "boat": "https://images.unsplash.com/photo-1544551763-47a0159f37c3?q=80&w=800",
                "marine": "https://images.unsplash.com/photo-1544551763-47a0159f37c3?q=80&w=800",
                "shipping": "https://images.unsplash.com/photo-1544551763-47a0159f37c3?q=80&w=800",
                "bakery": "https://images.unsplash.com/photo-1509440159596-0249088772ff?q=80&w=800",
                "food": "https://images.unsplash.com/photo-1509440159596-0249088772ff?q=80&w=800"
            }
            
            # Default fallback (the rings image the user mentioned)
            img_url = "https://images.unsplash.com/photo-1617038220319-276d3cfab638?q=80&w=800"
            
            # Check industry first, then product name keywords, then link URL
            for key, url in fallbacks.items():
                if key in industry_lower or key in product_type_hint or key in link.lower():
                    img_url = url
                    break

            # Fetch real product image via Microlink API to bypass basic bot protection
            try:
                # Add a significant staggered delay if we are in a bulk run to avoid Microlink rate limiting
                import time
                import random
                time.sleep(random.uniform(0.5, 1.5)) # Increased delay to satisfy "add time" request
                
                import urllib.request
                req = urllib.request.Request(f'https://api.microlink.io/?url={link}', headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'})
                with urllib.request.urlopen(req, timeout=12) as response:
                    data = json.loads(response.read().decode('utf-8'))
                    # Prioritize 'image' then 'logo' then 'screenshot' if image is missing
                    extracted_img = data.get('data', {}).get('image', {}).get('url') or \
                                   data.get('data', {}).get('logo', {}).get('url')
                    if extracted_img:
                        img_url = extracted_img
            except Exception as e:
                print(f"Notice: Could not fetch live image for {link}: {e}")
                
            # Generate a single-line HTML block to prevent backend/frontend splitting issues
            card = f'<div class="product-card" style="border:1px solid #e0e0e0; border-radius:8px; padding:20px; margin:20px 0; background-color:#ffffff; text-align:center;"><img src="{img_url}" style="max-width:100%; height:200px; object-fit:cover; border-radius:4px; margin-bottom:15px;" alt="{product_name}" /><h4 style="margin:0 0 10px 0; color:#333; font-size:18px;">{product_name}</h4><a href="{link}" style="display:inline-block; padding:12px 24px; background-color:#1a73e8; color:white; text-decoration:none; border-radius:4px; font-weight:bold;">View Item</a></div>'
            product_cards_html += card
            
        product_names_str = ", ".join(product_names) if product_names else "our collection"
            
        # Use manual string replacement to avoid JSON curly braces breaking .format()
        prompt = prompt_templates["craft_email"]
        prompt = prompt.replace("{lead}", lead_json)
        prompt = prompt.replace("{intent_signals}", intent_signals)
        prompt = prompt.replace("{company_info}", company_info)
        prompt = prompt.replace("{operator_info}", operator_info)
        prompt = prompt.replace("{product_names}", product_names_str)
        
        response = llm.generate_content(prompt)
        response_text = response.text.strip()
        
        # Parse JSON payload specifically
        if response_text.startswith('```'):
            start = response_text.find('{')
            end = response_text.rfind('}') + 1
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
        
        # 1. Sanitize LLM output (remove any iframes or fake buttons it might have hallucinated)
        import re
        email_preview = re.sub(r'<iframe.*?>.*?</iframe>', '', email_preview, flags=re.DOTALL)
        # Strip hallucinated card-like structures with "View Selection"
        email_preview = re.sub(r'<div[^>]*?>.*?View Selection.*?</div>', '', email_preview, flags=re.DOTALL | re.IGNORECASE)
        # Strip any hallucinated img tags since all valid images come from product_cards_html
        email_preview = re.sub(r'<img[^>]*>', '', email_preview, flags=re.IGNORECASE)
        
        # 2. Replace placeholders or fallback to append
        if "[PRODUCT_CATALOG]" in email_preview or "[INSERT_PRODUCTS_HERE]" in email_preview:
            email_preview = email_preview.replace("[PRODUCT_CATALOG]", product_cards_html)
            email_preview = email_preview.replace("[INSERT_PRODUCTS_HERE]", product_cards_html)
        elif "</body>" in email_preview:
            # Safest for full HTML documents
            email_preview = email_preview.replace("</body>", f"\n\n{product_cards_html}\n\n</body>")
        else:
            # Force insertion before the closing sign-off if possible, otherwise append
            sign_offs = ["Best regards,", "Warm regards,", "Best,", "Regards,", "Sincerely,", "Thanks,", "Yours,"]
            inserted = False
            for sign_off in sign_offs:
                if sign_off.lower() in email_preview.lower():
                    # Find exact case used in body
                    start_idx = email_preview.lower().find(sign_off.lower())
                    actual_sign_off = email_preview[start_idx:start_idx+len(sign_off)]
                    email_preview = email_preview.replace(actual_sign_off, f"\n\n{product_cards_html}\n\n{actual_sign_off}")
                    inserted = True
                    break
            if not inserted:
                email_preview += f"\n\n{product_cards_html}"
        
        return {
            **state,
            "subject": email.get("subject", ""),
            "personalization_factors": email.get("personalization_factors", []),
            "email_preview": email_preview,
            "status": "completed"
        }
        
    except Exception as e:
        print(f"Error parsing response: {str(e)}")
        return {
            **state, 
            "status": "error", 
            "error": str(e),
            "subject": "Error drafting email",
            "personalization_factors": ["Error"],
            "email_preview": "Failed to generate email."
        }

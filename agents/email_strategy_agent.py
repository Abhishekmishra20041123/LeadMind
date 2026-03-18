"""Email Strategy Agent

This module contains the Email Strategy Agent class for crafting personalized sales emails.
Uses LangGraph for workflow management.
"""

from typing import Dict, List, Any
import pandas as pd
import json
from langgraph_nodes.email_strategy_node import create_email_strategy_graph
from prompts.email_strategy_prompts import email_strategy_prompts

class EmailStrategyAgent:
    def __init__(self, llm, company_info: Dict[str, str]):
        """Initialize the agent with an LLM instance and company info"""
        self.llm = llm
        self.company_info = company_info
        self.email_data = None
    
    def load_data(self, email_path: str):
        """Load historical email data from CSV"""
        print("\n=== Loading Data ===")
        
        # Load emails
        self.email_data = pd.read_csv(email_path)
        print(f"Loaded email data shape: {self.email_data.shape}")
        print(f"Email columns: {self.email_data.columns.tolist()}")
    
    def _validate_data(self):
        """Validate and prepare data for the workflow"""
        if self.email_data is None:
            raise ValueError("Must load data before processing")
        
        # Convert emails to list format
        emails_list = []
        for _, row in self.email_data.iterrows():
            email = {
                "email_id": str(row.get("email_id", "")),
                "subject": str(row.get("subject", "")),
                "email_text": str(row.get("email_text", "")),
                "stage": str(row.get("stage", "")),
                "opened": bool(row.get("opened", False)),
                "reply_status": bool(row.get("replied", False)),
                "sentiment": str(row.get("sentiment", "")),
                "engagement_score": float(row.get("engagement_score", 0))
            }
            emails_list.append(email)
        
        return emails_list
    
    def craft_email(self, lead: Dict[str, Any], intent_data: Dict[str, Any], mapping=None) -> Dict[str, Any]:
        """Craft a personalized email for a qualified lead using dynamic mapping"""
        print("\n=== Crafting Email ===")
        
        try:
            # Default mapping if none provided
            m = mapping or {
                "behavioral_fields": {
                    "content_links": "page_link"
                }
            }
            
            # Step 1: Get email examples (Optional)
            examples = []
            if self.email_data is not None:
                try:
                    emails = self._validate_data()
                    print(f"Found {len(emails)} email examples")
                    successful = [e for e in emails if e.get('opened') and e.get('reply_status')]
                    examples = successful[:5]
                    print(f"Using {len(examples)} successful examples")
                except Exception as e:
                    print(f"Warning: Failed to load email examples: {str(e)}")
            
            # Step 2: Extract links based on mapping
            link_col = m["behavioral_fields"].get("content_links", "page_link")
            priority_links = lead.get(link_col, [])
            if isinstance(priority_links, str):
                priority_links = priority_links.split(',')
            
            # Step 3: Format context for LLM
            context = {
                "lead": {
                    "company": lead.get('company'),
                    "title": lead.get('title'),
                    "industry": lead.get('industry'),
                    "last_visited_page": priority_links[-1] if priority_links else "our site",
                    "priority_links": priority_links,
                    "visits": lead.get('visits', 0),
                    "time_on_site": lead.get('time_on_site', 0)
                },
                "company": self.company_info,
                "intent": {
                    "score": lead.get('intent_score', 0),
                    "signals": intent_data.get('intent_signals', []),
                    "recommendations": intent_data.get('recommendations', [])
                },
                "examples": examples
            }
            
            # Step 4: Fetch product images and build cards
            import urllib.request
            product_cards_html = ""
            product_names = []
            for link in priority_links:
                link = link.strip()
                if not link: continue
                
                # Extract a pseudo product name
                product_name = link.split("/")[-1].replace(".html", "").replace("-", " ").title()
                product_names.append(product_name)
                
                img_url = "https://images.unsplash.com/photo-1617038220319-276d3cfab638?q=80&w=400&auto=format&fit=crop"
                try:
                    req = urllib.request.Request(f'https://api.microlink.io/?url={link}', headers={'User-Agent': 'Mozilla/5.0'})
                    with urllib.request.urlopen(req, timeout=5) as response:
                        data = json.loads(response.read().decode('utf-8'))
                        extracted_img = data.get('data', {}).get('image', {}).get('url')
                        if extracted_img:
                            img_url = extracted_img
                except Exception as e:
                    print(f"Notice: Could not fetch image for {link}: {e}")
                    
                # Generate a single-line HTML block to prevent backend/frontend splitting issues
                card = f'<div style="border:1px solid #e0e0e0; border-radius:8px; padding:20px; margin:20px 0; background-color:#ffffff; text-align:center;"><img src="{img_url}" style="max-width:100%; height:200px; object-fit:cover; border-radius:4px; margin-bottom:15px;" alt="Product View" /><h4 style="margin:0 0 10px 0; color:#333; font-size:18px;">{product_name}</h4><a href="{link}" style="display:inline-block; padding:12px 24px; background-color:#1a73e8; color:white; text-decoration:none; border-radius:4px; font-weight:bold;">View Item</a></div>'
                product_cards_html += card
                
            product_names_str = ", ".join(product_names) if product_names else "our collection"

            # Step 5: Final Prompt Injection
            prompt = email_strategy_prompts["craft_email"]
            prompt = prompt.replace("{lead}", json.dumps(context["lead"], indent=2))
            # Use intent_signals as defined in the dictionary or the intent_data directly
            prompt = prompt.replace("{intent_signals}", json.dumps(intent_data.get("intent_signals", []), indent=2))
            prompt = prompt.replace("{company_info}", json.dumps(context["company"], indent=2))
            
            operator_data = {
                "operator_name": self.company_info.get("operator_name", "Sales Rep"),
                "operator_company": self.company_info.get("company_name", "Our Company"),
                "operator_business_type": self.company_info.get("business_type", "Quality Services"),
                "operator_company_description": self.company_info.get("description", "We provide specialized solutions for our clients.")
            }
            prompt = prompt.replace("{operator_info}", json.dumps(operator_data, indent=2))
            prompt = prompt.replace("{operator_name}", operator_data["operator_name"])
            prompt = prompt.replace("{operator_company}", operator_data["operator_company"])
            prompt = prompt.replace("{operator_business_type}", operator_data["operator_business_type"])
            prompt = prompt.replace("{operator_company_description}", operator_data["operator_company_description"])
            prompt = prompt.replace("{product_names}", product_names_str)
            
            print("\n=== Generating Email ===")
            response = self.llm.generate_content(prompt)
            response_text = response.text
            
            # Clean up markdown code blocks if present
            if "```json" in response_text:
                response_text = response_text.split("```json")[1]
                response_text = response_text.split("```")[0]
            elif "```" in response_text:
                start = response_text.find('{')
                end = response_text.rfind('}') + 1
                if start != -1 and end != 0:
                    response_text = response_text[start:end]
            
            print(f"Cleaned response: {response_text}")
            
            email = json.loads(response_text)
            
            # Use email_preview if present, otherwise body
            raw_body = email.get("email_preview", email.get("body", ""))
            
            # 1. Sanitize LLM output (remove any iframes or fake buttons it might have hallucinated)
            import re
            raw_body = re.sub(r'<iframe.*?>.*?</iframe>', '', raw_body, flags=re.DOTALL)
            # Strip hallucinated card-like structures with "View Selection"
            raw_body = re.sub(r'<div[^>]*?>.*?View Selection.*?</div>', '', raw_body, flags=re.DOTALL | re.IGNORECASE)
            # Strip any hallucinated img tags since all valid images come from product_cards_html
            raw_body = re.sub(r'<img[^>]*>', '', raw_body, flags=re.IGNORECASE)
            
            # 2. Replace placeholders or fallback to append
            if "[PRODUCT_CATALOG]" in raw_body or "[INSERT_PRODUCTS_HERE]" in raw_body:
                final_body = raw_body.replace("[PRODUCT_CATALOG]", product_cards_html)
                final_body = final_body.replace("[INSERT_PRODUCTS_HERE]", product_cards_html)
            elif "</body>" in raw_body:
                # Safest for full HTML documents
                final_body = raw_body.replace("</body>", f"\n\n{product_cards_html}\n\n</body>")
            else:
                # Force insertion before the closing sign-off if possible, otherwise append
                sign_offs = ["Best regards,", "Warm regards,", "Best,", "Regards,", "Sincerely,", "Thanks,", "Best Regards,", "Yours,"]
                inserted = False
                for sign_off in sign_offs:
                    if sign_off.lower() in raw_body.lower():
                        # Find exact case used in body
                        start_idx = raw_body.lower().find(sign_off.lower())
                        actual_sign_off = raw_body[start_idx:start_idx+len(sign_off)]
                        final_body = raw_body.replace(actual_sign_off, f"\n\n{product_cards_html}\n\n{actual_sign_off}")
                        inserted = True
                        break
                if not inserted:
                    final_body = raw_body + f"\n\n{product_cards_html}"
            
            email["body"] = final_body
            email["email_preview"] = final_body
            
            return email
            
        except Exception as e:
            print(f"\n=== Error Details ===")
            print(f"Type: {type(e).__name__}")
            print(f"Message: {str(e)}")
            raise ValueError(f"Failed to craft email: {str(e)}")

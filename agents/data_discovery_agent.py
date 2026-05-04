import json
import re
import pandas as pd
from typing import Dict, List, Any


class DataDiscoveryAgent:
    def __init__(self, llm):
        self.llm = llm

    def _make_safe_default(self, files: List[str]) -> Dict[str, Any]:
        """
        Build a minimal but valid discovery result by reading column names directly.
        This is used as a fallback if the LLM returns un-parseable JSON so the
        pipeline is NEVER terminated at this stage.
        """
        primary_file = files[0] if files else ""
        fallback_headers = []
        try:
            df = pd.read_csv(primary_file, nrows=1)
            fallback_headers = df.columns.tolist()
        except Exception:
            pass

        # Try to guess identity columns from common names
        lower_headers = {h.lower(): h for h in fallback_headers}
        lead_id_col = lower_headers.get("lead_id", 
                                        lower_headers.get("id", 
                                        lower_headers.get("user id",
                                        lower_headers.get("user_id",
                                        fallback_headers[0] if fallback_headers else "lead_id"))))
        email_col   = lower_headers.get("email", lower_headers.get("email_address", "email"))
        visits_col  = lower_headers.get("visits", lower_headers.get("sessions", "visits"))
        time_col    = lower_headers.get("time_on_site", lower_headers.get("session_duration", "time_on_site"))
        depth_col   = lower_headers.get("pages_per_visit", lower_headers.get("pages_viewed", "pages_per_visit"))
        link_col    = lower_headers.get("product page link", 
                                  lower_headers.get("page_link", 
                                  lower_headers.get("url", 
                                  lower_headers.get("product_url", 
                                  lower_headers.get("product_page_link", "page_link")))))

        import os
        filename = os.path.basename(primary_file)

        return {
            "business_context": {
                "company_name": "Unknown",
                "industry": "Business",
                "description": "Auto-detected from CSV headers (LLM fallback)"
            },
            "files_roles": {
                "primary_leads_file": filename,
                "email_history_file": None
            },
            "schema_mapping": {
                "lead_id": lead_id_col,
                "identity_fields": [lead_id_col, email_col],
                "behavioral_fields": {
                    "visits": visits_col,
                    "depth": depth_col,
                    "content_links": link_col,
                    "time_on_site": time_col
                },
                "sales_fields": {
                    "value": "deal_value",
                    "stage": "Lead_Status"
                }
            },
            "is_sufficient": True,
            "missing_critical_data": [],
            "reasoning": "Auto-mapped from column names because LLM returned invalid JSON. Pipeline will continue with best-effort mapping."
        }

    def analyze_data_sources(self, files: List[str]) -> Dict[str, Any]:
        """
        Analyzes multiple CSV files to discover schema roles and business context.
        Guaranteed to return a valid dict — never raises an exception.
        """
        all_headers = {}
        data_samples = {}

        for file in files:
            try:
                df = pd.read_csv(file, nrows=5)
                all_headers[file] = df.columns.tolist()
                data_samples[file] = df.to_dict(orient='records')
            except Exception as e:
                print(f"[DataDiscovery] Warning: Could not read {file}: {e}")

        prompt = f"""
You are the DataDiscovery Agent. Your job is to analyze the provided CSV headers and samples from a company's data and map them to our internal semantic requirements.

DATA SOURCES:
{json.dumps({"headers": all_headers, "samples": data_samples}, indent=2)}

INTERNAL SEMANTIC ROLES:
- IDENTITY: Columns that identify a user (email, name, user_id, lead_id).
- BEHAVIOR: Columns tracking activity (visits, pages_viewed, time_on_site, session_duration).
- CONTENT: ONLY the column containing the primary product or landing page URL (e.g. 'Product Page Link', 'url', 'page_link'). DO NOT include product names here.
- SALES: Columns about historical deals (close_value, stage, deal_date).

YOUR TASKS:
1. IDENTIFY BUSINESS TYPE: Determine if this is E-commerce (Product), Service (Teaching/Consulting), SaaS, Marine/Boating, or other industry.
2. MAP COLUMNS: Find which columns in the provided files represent the core metrics needed for research and outreach.
3. SUFFICIENCY CHECK: Determine if there is enough data to build a behavioral profile and draft a personalized outreach.
   NOTE: Even datasets with only behavioral or product data (like a marine/boating catalog) are SUFFICIENT for outreach — set is_sufficient to true unless truly empty.

OUTPUT FORMAT:
Return ONLY strictly valid JSON (no markdown, no code fences, no extra text):
{{
    "business_context": {{
        "company_name": "Unknown",
        "industry": "e.g. Marine/Boating",
        "description": "Brief description based on data"
    }},
    "files_roles": {{
        "primary_leads_file": "filename.csv",
        "email_history_file": null
    }},
    "schema_mapping": {{
        "lead_id": "column_name",
        "identity_fields": ["col1", "col2"],
        "behavioral_fields": {{
            "visits": "column_name",
            "depth": "column_name",
            "content_links": "column_name",
            "time_on_site": "column_name"
        }},
        "sales_fields": {{
            "value": "column_name",
            "stage": "column_name"
        }}
    }},
    "is_sufficient": true,
    "missing_critical_data": [],
    "reasoning": "Why you mapped it this way"
}}
"""
        print("\n=== Discovering Schema & Context ===")
        try:
            response = self.llm.generate_content(prompt)
            response_text = response.text.strip()

            # ── Strip markdown code fences if present ──
            if "```" in response_text:
                # Try to extract content between first { and last }
                start = response_text.find("{")
                end   = response_text.rfind("}") + 1
                if start != -1 and end > start:
                    response_text = response_text[start:end]
                else:
                    # Strip fence lines manually
                    lines = response_text.splitlines()
                    lines = [l for l in lines if not l.strip().startswith("```")]
                    response_text = "\n".join(lines).strip()

            # ── Primary parse attempt ──
            try:
                result = json.loads(response_text)
                # Validate that essential keys exist; if not, patch them in
                if "schema_mapping" not in result:
                    result["schema_mapping"] = {}
                if "is_sufficient" not in result:
                    result["is_sufficient"] = True
                print(f"[DataDiscovery] [SUCCESS] Schema parsed successfully. Industry: {result.get('business_context', {}).get('industry', 'Unknown')}")
                return result

            except json.JSONDecodeError as primary_err:
                print(f"[DataDiscovery] Primary JSON parse failed: {primary_err}. Attempting regex extraction...")

                # ── Regex fallback: extract outermost JSON object ──
                match = re.search(r'\{.*\}', response_text, re.DOTALL)
                if match:
                    try:
                        result = json.loads(match.group(0))
                        if "is_sufficient" not in result:
                            result["is_sufficient"] = True
                        print("[DataDiscovery] [SUCCESS] Schema parsed via regex fallback.")
                        return result
                    except json.JSONDecodeError:
                        pass

                print("[DataDiscovery] [WARNING] All JSON parse attempts failed. Using auto-mapped safe default.")
                return self._make_safe_default(files)

        except Exception as e:
            print(f"[DataDiscovery] [WARNING] LLM call failed entirely: {e}. Using auto-mapped safe default.")
            return self._make_safe_default(files)

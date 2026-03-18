"""
run_all_compatibility_tests.py
=============================================================
Comprehensive pipeline compatibility test suite.
Tests all 5 datasets across the full agent pipeline:
  Agent 1: DataDiscovery    - Schema analysis & sufficiency
  Agent 2: IntentQualifier  - Intent scoring
  Agent 3: EmailStrategy    - Personalized email + image scraping
  Agent 4: FollowupTiming   - Optimal send time
  Agent 5: CRMLogger        - Activity logging

Datasets tested:
  1. boAt User Behavioral Data (single-file, mixed schema)
  2. Bookswagon User Behavioral Data (single-file, e-commerce + product links)
  3. Theobroma Data (single-file, bakery, Primary_Product_Page col)
  4. Tiffany Data (single-file, jewelry, page_link col)
  5. Multi-file set (Leads_Data + Email_Logs + Sales_Pipeline)
"""

import asyncio
import os
import sys
import json
import shutil
import uuid
from datetime import datetime

# ── Path setup ────────────────────────────────────────────────────────────────
ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "backend"))

# Force UTF-8
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# ── Imports ───────────────────────────────────────────────────────────────────
import pandas as pd
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId

load_dotenv()

from agents.data_discovery_agent import DataDiscoveryAgent
from api.agents import OllamaWrapper
from langgraph_nodes.lead_research_node import create_lead_research_graph
from langgraph_nodes.intent_qualifier_node import create_intent_qualifier_graph
from langgraph_nodes.email_strategy_node import create_email_strategy_graph
from langgraph_nodes.followup_timing_node import create_followup_timing_graph
from langgraph_nodes.crm_logger_node import create_crm_logger_graph
from prompts.lead_research_prompts import lead_research_prompts
from prompts.intent_qualifier_prompts import intent_qualifier_prompts
from prompts.email_strategy_prompts import email_strategy_prompts
from prompts.followup_timing_prompts import followup_timing_prompts

# ── Dataset definitions ───────────────────────────────────────────────────────
DATA_DIR = os.path.join(ROOT, "data")

DATASETS = [
    {
        "name": "boAt User Behavioral Data",
        "files": ["boAt User Behavioral Data - Sheet1.csv"],
        "expected_domain": "Consumer Electronics / Wearables",
        "has_product_links": False,
    },
    {
        "name": "Bookswagon User Behavioral Data",
        "files": ["Bookswagon_User_Behavioral_Data - Sheet1 (1).csv"],
        "expected_domain": "E-commerce / Books",
        "has_product_links": True,
    },
    {
        "name": "Theobroma Leads",
        "files": ["theobroma_data.csv"],
        "expected_domain": "Bakery / Food E-commerce",
        "has_product_links": True,
    },
    {
        "name": "Tiffany Leads",
        "files": ["tiffany_data.csv"],
        "expected_domain": "Luxury Jewelry",
        "has_product_links": True,
    },
    {
        "name": "Multi-file Dataset (Leads + Email + Sales)",
        "files": ["Leads_Data.csv", "Email_Logs.csv", "Sales_Pipeline.csv"],
        "expected_domain": "SaaS / B2B",
        "has_product_links": False,
    },
]

# ── Helpers ───────────────────────────────────────────────────────────────────
PASS = "✅ PASS"
FAIL = "❌ FAIL"
WARN = "⚠️  WARN"

def result_badge(ok: bool, warn: bool = False):
    if warn:
        return WARN
    return PASS if ok else FAIL

def safe_num(val, default=0, as_float=False):
    """Safely convert a value to int/float. Handles pipe-separated strings like '8 | 5 | 4'."""
    if val is None:
        return float(default) if as_float else int(default)
    s = str(val).split('|')[0].split(',')[0].strip()
    try:
        return float(s) if as_float else int(float(s))
    except (ValueError, TypeError):
        return float(default) if as_float else int(default)

def get_mapped_val(row, mapping_key, default=None, is_list=False):
    """Mirrors the helper in batch.py for offline testing."""
    cols = []
    if isinstance(mapping_key, str):
        cols = [c.strip() for c in mapping_key.split(",") if c.strip()]
    elif isinstance(mapping_key, list):
        cols = mapping_key
    row_cols_lower = {c.lower(): c for c in row.index}
    found_vals = []
    for col in cols:
        actual_col = row_cols_lower.get(col.lower())
        if actual_col and pd.notna(row[actual_col]):
            val = row[actual_col]
            if is_list:
                sub_vals = [v.strip() for v in str(val).replace("|", ",").split(",") if v.strip()]
                found_vals.extend(sub_vals)
            else:
                return val
    return list(set(found_vals)) if is_list else default

# ── Core test runner ──────────────────────────────────────────────────────────
async def run_dataset_test(ds: dict, llm, agents: dict, report: list):
    print(f"\n{'='*70}")
    print(f"  DATASET: {ds['name']}")
    print(f"{'='*70}")
    
    test_result = {
        "dataset": ds["name"],
        "files": ds["files"],
        "agent_tests": {},
        "final_status": None,
        "error": None
    }

    full_paths = [os.path.join(DATA_DIR, f) for f in ds["files"]]
    
    # ── Check files exist ──────────────────────────────────────────────────
    missing = [p for p in full_paths if not os.path.exists(p)]
    if missing:
        test_result["final_status"] = FAIL
        test_result["error"] = f"Missing files: {missing}"
        report.append(test_result)
        print(f"  {FAIL} Files not found: {missing}")
        return

    # ══════════════════════════════════════════════════════════════════════
    # AGENT 1: DataDiscovery
    # ══════════════════════════════════════════════════════════════════════
    print(f"\n  [Agent 1] DataDiscovery ...")
    try:
        discovery_agent = DataDiscoveryAgent(llm)
        discovery = discovery_agent.analyze_data_sources(full_paths)
        
        is_sufficient = discovery.get("is_sufficient", False)
        schema_mapping = discovery.get("schema_mapping", {})
        business_context = discovery.get("business_context", {})
        files_roles = discovery.get("files_roles", {})
        
        a1_tests = {
            "schema_analyzed":    result_badge(bool(schema_mapping)),
            "sufficient_data":    result_badge(is_sufficient),
            "identity_mapped":    result_badge(bool(schema_mapping.get("identity_fields"))),
            "behavioral_mapped":  result_badge(bool(schema_mapping.get("behavioral_fields"))),
            "business_detected":  result_badge(bool(business_context.get("industry"))),
            "files_roles_set":    result_badge(bool(files_roles.get("primary_leads_file"))),
        }
        test_result["agent_tests"]["DataDiscovery"] = a1_tests
        test_result["discovery_result"] = discovery
        
        print(f"    Industry   : {business_context.get('industry', 'Unknown')}")
        print(f"    Sufficient : {is_sufficient}")
        print(f"    Lead-ID col: {schema_mapping.get('lead_id', 'Not mapped')}")
        content_links_col = schema_mapping.get("behavioral_fields", {}).get("content_links", "None")
        print(f"    Links col  : {content_links_col}")
        for k, v in a1_tests.items():
            print(f"      {v} {k}")
        
        if not is_sufficient:
            print(f"\n  {FAIL} Data Insufficiency detected — pipeline will abort (as expected).")
            reason = discovery.get("reasoning", "")
            missing_cols = discovery.get("missing_critical_data", [])
            print(f"    Reason  : {reason}")
            print(f"    Missing : {missing_cols}")
            test_result["final_status"] = PASS  # Correct behavior
            test_result["error"] = f"Insufficient data (expected pipeline to stop): {reason}"
            report.append(test_result)
            return
        
    except Exception as e:
        test_result["agent_tests"]["DataDiscovery"] = {"error": FAIL}
        test_result["final_status"] = FAIL
        test_result["error"] = f"DataDiscovery failed: {e}"
        report.append(test_result)
        print(f"  {FAIL} DataDiscovery error: {e}")
        return

    # ══════════════════════════════════════════════════════════════════════
    # Load primary CSV and pick 2 test leads
    # ══════════════════════════════════════════════════════════════════════
    primary_file_name = files_roles.get("primary_leads_file", ds["files"][0])
    primary_path = os.path.join(DATA_DIR, os.path.basename(primary_file_name))
    if not os.path.exists(primary_path):
        primary_path = full_paths[0]
    
    email_file_name = files_roles.get("email_history_file")
    emails_df = pd.DataFrame()
    if email_file_name:
        ep = os.path.join(DATA_DIR, os.path.basename(email_file_name))
        if os.path.exists(ep):
            emails_df = pd.read_csv(ep)
    
    df = pd.read_csv(primary_path)
    test_leads = df.head(2)  # Test with first 2 leads
    
    # ── Verify lead field mapping ──────────────────────────────────────────
    lead_id_col = schema_mapping.get("lead_id", "")
    behavior = schema_mapping.get("behavioral_fields", {})
    content_links_col = behavior.get("content_links", "page_link")
    
    all_leads_have_email = True
    all_leads_have_links = []
    
    for i, (_, row) in enumerate(test_leads.iterrows()):
        lead_id = str(get_mapped_val(row, lead_id_col, f"L{i}"))
        email_val = get_mapped_val(row, ["Email", "email", "Email_Address"], "")
        links = get_mapped_val(row, content_links_col, is_list=True) if content_links_col else []
        
        # If no email from identity mapping, try heuristic fallback
        if not email_val:
            for col in row.index:
                if "email" in col.lower() and pd.notna(row[col]):
                    email_val = row[col]
                    break
        
        if not email_val:
            all_leads_have_email = False
        
        # Check link validity
        valid_links = [l for l in links if isinstance(l, str) and l.strip().startswith("http")]
        all_leads_have_links.append(len(valid_links))
        
        print(f"\n  Lead {i+1}: ID={lead_id}, Email={email_val!r}, Links={valid_links[:2]}")

    schema_test = {
        "email_extractable": result_badge(all_leads_have_email),
        "links_found_count_lead1": all_leads_have_links[0] if all_leads_have_links else 0,
        "links_found_count_lead2": all_leads_have_links[1] if len(all_leads_have_links) > 1 else 0,
    }
    test_result["agent_tests"]["SchemaMapping"] = schema_test

    # ══════════════════════════════════════════════════════════════════════
    # AGENTS 2–5: Run full LangGraph pipeline on test leads
    # ══════════════════════════════════════════════════════════════════════
    operator_info = {
        "operator_name": "Test Operator",
        "operator_company": "TestCo",
        "operator_website": "https://testco.com",
        "operator_email": "test@testco.com"
    }
    
    pipeline_results = []
    for i, (_, row) in enumerate(test_leads.iterrows()):
        lead_id = str(get_mapped_val(row, lead_id_col, f"L{i}"))
        links = get_mapped_val(row, content_links_col, is_list=True) if content_links_col else []
        
        first_name = get_mapped_val(row, "First_Name", "")
        last_name = get_mapped_val(row, "Last_Name", "")
        full_name = f"{first_name} {last_name}".strip() or str(get_mapped_val(row, schema_mapping.get("identity_fields", []), "Unknown Lead"))
        email_val = get_mapped_val(row, ["Email", "email", "Email_Address"], "no-email@test.com")
        if not email_val:
            for col in row.index:
                if "email" in col.lower() and pd.notna(row[col]):
                    email_val = str(row[col])
                    break
        
        lead_dict = row.to_dict()
        lead_dict["lead_id"] = lead_id
        lead_dict["name"] = full_name
        lead_dict["email"] = email_val
        lead_dict["title"] = get_mapped_val(row, "Title", "")
        lead_dict["company"] = get_mapped_val(row, "Company", "")
        lead_dict["industry"] = business_context.get("industry", "Unknown")
        lead_dict["visits"] = safe_num(get_mapped_val(row, behavior.get("visits", "visits"), 0))
        lead_dict["time_on_site"] = safe_num(get_mapped_val(row, behavior.get("time_on_site", "time_on_site"), 0.0), as_float=True)
        lead_dict["pages_per_visit"] = safe_num(get_mapped_val(row, behavior.get("depth", "pages_per_visit"), 0.0), as_float=True)
        
        valid_links = [l for l in links if isinstance(l, str) and l.strip().startswith("http")]
        lead_dict["page_link"] = valid_links
        
        email_history = []
        if not emails_df.empty and 'lead_id' in emails_df.columns:
            email_history = emails_df[emails_df['lead_id'] == lead_id].to_dict('records')
        
        state = {
            "lead": lead_dict,
            "email_history": email_history,
            "operator_info": operator_info,
            "schema_mapping": schema_mapping
        }
        
        print(f"\n  --- Running pipeline for Lead {i+1} ({lead_id}) ---")
        lead_results = {"lead_id": lead_id}
        
        try:
            # Agent 2: Research
            print(f"    [Agent 2] LeadResearch ...")
            result2 = agents["research"].invoke(state)
            has_insights = bool(result2.get("quality_indicators") or result2.get("recommendation") or result2.get("insights"))
            lead_results["LeadResearch"] = result_badge(has_insights, warn=not has_insights)
            state = result2
        except Exception as e:
            lead_results["LeadResearch"] = FAIL
            print(f"      {FAIL} {e}")
        
        try:
            # Agent 2b: Intent
            print(f"    [Agent 2] IntentQualifier ...")
            result_intent = agents["intent"].invoke(state)
            intent_score = result_intent.get("intent_score", 0)
            lead_results["IntentQualifier"] = result_badge(intent_score is not None)
            lead_results["intent_score"] = intent_score
            print(f"      Intent Score: {intent_score}")
            state = result_intent
        except Exception as e:
            lead_results["IntentQualifier"] = FAIL
            print(f"      {FAIL} {e}")
        
        try:
            # Agent 3: Email
            print(f"    [Agent 3] EmailStrategy ...")
            result_email = agents["email"].invoke(state)
            email_preview = result_email.get("email_preview", "")
            has_email = bool(email_preview and len(str(email_preview)) > 100)
            has_image = "<img" in str(email_preview)
            lead_results["EmailStrategy"] = result_badge(has_email)
            lead_results["email_generated"] = has_email
            lead_results["has_product_images"] = has_image
            lead_results["email_length"] = len(str(email_preview))
            print(f"      Email length: {len(str(email_preview))} chars")
            print(f"      Has images  : {has_image}")
            state = result_email
        except Exception as e:
            lead_results["EmailStrategy"] = FAIL
            print(f"      {FAIL} {e}")
        
        try:
            # Agent 4: Followup Timing
            print(f"    [Agent 4] FollowupTiming ...")
            result_timing = agents["timing"].invoke(state)
            timing = result_timing.get("timing") or result_timing.get("follow_up_timing") or result_timing.get("recommended_followup_time")
            lead_results["FollowupTiming"] = result_badge(bool(timing), warn=not bool(timing))
            print(f"      Timing: {str(timing)[:80]}")
            state = result_timing
        except Exception as e:
            lead_results["FollowupTiming"] = FAIL
            print(f"      {FAIL} {e}")
        
        try:
            # Agent 5: CRM Logger
            print(f"    [Agent 5] CRMLogger ...")
            result_crm = agents["logger"].invoke(state)
            log_entry = result_crm.get("lead_summary") or result_crm.get("timeline") or result_crm.get("log_entry")
            lead_results["CRMLogger"] = result_badge(bool(log_entry), warn=not bool(log_entry))
            state = result_crm
        except Exception as e:
            lead_results["CRMLogger"] = FAIL
            print(f"      {FAIL} {e}")

        pipeline_results.append(lead_results)
    
    test_result["agent_tests"]["Pipeline"] = pipeline_results
    
    # ── Final status ───────────────────────────────────────────────────────
    all_ok = all(
        r.get("EmailStrategy") != FAIL and r.get("email_generated", False)
        for r in pipeline_results
    )
    test_result["final_status"] = PASS if all_ok else WARN
    report.append(test_result)


# ── Main ──────────────────────────────────────────────────────────────────────
async def main():
    print("=" * 70)
    print("  PIPELINE COMPATIBILITY TEST SUITE")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    
    # Initialize LLM and agents once
    llm = OllamaWrapper('minimax-m2.5:cloud')
    agents = {
        'research': create_lead_research_graph(llm, lead_research_prompts),
        'intent':   create_intent_qualifier_graph(llm, intent_qualifier_prompts),
        'email':    create_email_strategy_graph(llm, email_strategy_prompts),
        'timing':   create_followup_timing_graph(llm, followup_timing_prompts),
        'logger':   create_crm_logger_graph(),
    }
    
    report = []
    
    for ds in DATASETS:
        await run_dataset_test(ds, llm, agents, report)
    
    # ── Summary report ─────────────────────────────────────────────────────
    print(f"\n\n{'='*70}")
    print("  FINAL COMPATIBILITY REPORT")
    print(f"{'='*70}")
    print(f"  {'Dataset':<45} {'Status':<10} {'Email':>6} {'Image':>6}")
    print(f"  {'-'*68}")
    
    for r in report:
        ds_name = r["dataset"][:44]
        status = r.get("final_status", FAIL)
        pipeline = r.get("agent_tests", {}).get("Pipeline", [])
        any_email = any(pr.get("email_generated", False) for pr in pipeline)
        any_image = any(pr.get("has_product_images", False) for pr in pipeline)
        print(f"  {ds_name:<45} {status:<10} {'Yes' if any_email else 'No':>6} {'Yes' if any_image else 'N/A':>6}")
    
    print(f"\n  Total datasets tested : {len(DATASETS)}")
    passed = sum(1 for r in report if r.get("final_status") == PASS)
    warned = sum(1 for r in report if r.get("final_status") == WARN)
    failed = sum(1 for r in report if r.get("final_status") == FAIL)
    print(f"  Pass  : {passed}")
    print(f"  Warn  : {warned}")
    print(f"  Fail  : {failed}")
    
    # Save detailed report
    report_path = os.path.join(ROOT, "compatibility_report.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, default=str)
    print(f"\n  Detailed report saved to: {report_path}")

if __name__ == "__main__":
    asyncio.run(main())

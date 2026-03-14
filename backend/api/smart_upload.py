import os
import io
import copy
import json
import pandas as pd
from datetime import datetime
from fastapi import APIRouter, File, UploadFile, HTTPException, Depends, Form
from typing import Dict, Any, List

# Import dependencies and DB collections
from dependencies import get_current_user

# Import Ollama wrapper
from api.agents import OllamaWrapper

router = APIRouter()

root_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
DATA_DIR = os.path.join(root_dir, "data")
BATCHES_DIR = os.path.join(DATA_DIR, "batches")
os.makedirs(BATCHES_DIR, exist_ok=True)

LEADS_SCHEMA = {
    "required": {
        "name": "Full name of the lead (e.g., 'John Doe')",
        "company": "Company or organisation name (e.g., 'Acme Corp')"
    },
    "optional": {
        "lead_id": "Unique identifier for the lead (e.g., 'L00001')",
        "title": "Job title or role (e.g., 'CEO')",
        "email": "Work email address",
        "industry": "Company industry (e.g., 'Technology')",
        "region": "Geographic region (e.g., 'North America')",
        "websites_visits": "Number of times they visited the website (numeric)",
        "pages_per_visit": "Average pages per visit (numeric)",
        "time_on_site": "Total seconds spent on site (numeric)",
        "content_downloads": "Number of resources downloaded (numeric)",
        "lead_source": "Source of the lead (e.g., 'LinkedIn', 'Website')",
        "converted": "1 if converted, 0 if not",
        "stage": "Sales pipeline stage (e.g. 'Prospecting', 'Closed Won')"
    }
}

EMAILS_SCHEMA = {
    "required": {
        "subject": "Email subject line",
        "email_text": "Body of the email"
    },
    "optional": {
        "lead_id": "Unique identifier linking this email to a lead",
        "opened": "1 if opened, 0 if not",
        "replied": "1 if replied, 0 if not",
        "click_count": "Number of links clicked",
        "email_type": "Marketing, Sales, Follow-up, etc.",
        "response_status": "Replied, No Reply, etc."
    }
}

@router.get("/schema")
async def get_schema():
    """Returns the expected internal schema fields."""
    return {
        "leads": LEADS_SCHEMA,
        "emails": EMAILS_SCHEMA
    }

@router.post("/analyze")
async def analyze_csv(file: UploadFile = File(...), file_type: str = Form("leads"), user=Depends(get_current_user)):
    """
    Accepts a single CSV file, reads its headers + sample rows, 
    calls Ollama to produce a column mapping (user columns -> internal schema).
    """
    if file_type not in ["leads", "emails"]:
        raise HTTPException(status_code=400, detail="Invalid file_type. Must be 'leads' or 'emails'.")

    # Read the file
    try:
        content = await file.read()
        df = pd.read_csv(io.BytesIO(content))
        
        # We only need headers and a few rows for the AI
        headers = list(df.columns)
        print("Received CSV with headers:", headers)
        
        # Get up to 3 sample rows
        sample_df = df.head(3)
        sample_data = sample_df.to_dict(orient="records")
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to read CSV: {str(e)}")

    target_schema = LEADS_SCHEMA if file_type == "leads" else EMAILS_SCHEMA

    # Call Ollama to map columns
    llm = OllamaWrapper('minimax-m2.5:cloud')
    
    prompt = f"""
You are a data mapping assistant. I have a user-uploaded CSV file and I need to map its columns to my system's internal schema.

UPLOADED CSV HEADERS:
{json.dumps(headers)}

SAMPLE DATA (Up to 3 rows):
{json.dumps(sample_data, indent=2)}

TARGET SYSTEM SCHEMA:
Required fields:
{json.dumps(target_schema["required"], indent=2)}

Optional fields:
{json.dumps(target_schema["optional"], indent=2)}

TASK:
Map the uploaded CSV headers to the exact keys in the TARGET SYSTEM SCHEMA. 
If an uploaded column doesn't match any internal field, ignore it.
If a target schema field isn't present in the uploaded headers, don't map it.

Return the result as a raw, valid JSON object where keys are the uploaded headers and values are the target schema keys. ONLY reply with JSON. Do not use Markdown backticks.

Example format:
{{
    "Contact Name": "name",
    "Organisation": "company",
    "Job Role": "title"
}}
"""
    try:
        response = llm.generate_content(prompt)
        response_text = response.text.strip()
        
        # Clean up potential markdown formatting from LLM response
        if response_text.startswith("```json"):
            response_text = response_text[7:]
        if response_text.startswith("```"):
            response_text = response_text[3:]
        if response_text.endswith("```"):
            response_text = response_text[:-3]
            
        mapping = json.loads(response_text)
        
        # Validate mapping only contains exact matches from user headers -> target schema keys
        valid_targets = list(target_schema["required"].keys()) + list(target_schema["optional"].keys())
        filtered_mapping = {}
        for upload_col, target_col in mapping.items():
            if upload_col in headers and target_col in valid_targets:
                filtered_mapping[upload_col] = target_col
                
        return {"mapping": filtered_mapping, "headers": headers, "sampleRows": sample_data}
        
    except Exception as e:
        print("Error during AI mapping:", e)
        raise HTTPException(status_code=500, detail="Failed to map columns using AI")

@router.post("/confirm")
async def confirm_mapping(
    mapping_str: str = Form(...), 
    file: UploadFile = File(...), 
    file_type: str = Form("leads"),
    user=Depends(get_current_user)
):
    """
    Accepts the confirmed mapping + original file, transforms the data.
    Returns the transformed data records for preview or further processing.
    """
    try:
        mapping = json.loads(mapping_str)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid mapping JSON")
        
    try:
        content = await file.read()
        df = pd.read_csv(io.BytesIO(content))
        
        # Apply the confirmed mapping
        df.rename(columns=mapping, inplace=True)
        
        # Drop columns that weren't mapped
        mapped_target_cols = list(mapping.values())
        df = df[mapped_target_cols]
        
        # Fill missing required/optional columns with safe defaults
        if file_type == "leads":
            if "name" not in df.columns: df["name"] = "Unknown Name"
            if "company" not in df.columns: df["company"] = "Unknown Company"
            if "title" not in df.columns: df["title"] = "Unknown Title"
            if "industry" not in df.columns: df["industry"] = "Unknown Industry"
            if "region" not in df.columns: df["region"] = "Unknown Region"
            if "website_visits" not in df.columns: df["website_visits"] = 1
            if "pages_per_visit" not in df.columns: df["pages_per_visit"] = 1.0
            if "time_on_site" not in df.columns: df["time_on_site"] = 0
            if "content_downloads" not in df.columns: df["content_downloads"] = 0
            if "lead_source" not in df.columns: df["lead_source"] = "Import"
            if "converted" not in df.columns: df["converted"] = 0
            if "stage" not in df.columns: df["stage"] = "Prospecting"
            
            # Create a lead_id if not present (although normally generated at batch start, we do it here to return standard data)
            df['lead_id'] = ['L' + str(i).zfill(5) for i in range(1, len(df) + 1)]
            
        elif file_type == "emails":
            if "subject" not in df.columns: df["subject"] = "No Subject"
            if "email_text" not in df.columns: df["email_text"] = ""
            if "opened" not in df.columns: df["opened"] = 0
            if "replied" not in df.columns: df["replied"] = 0
            if "click_count" not in df.columns: df["click_count"] = 0
            if "email_type" not in df.columns: df["email_type"] = "Follow-up"
            if "response_status" not in df.columns: df["response_status"] = "No Reply"

        # Replace NaN with appropriate empty values
        df = df.fillna("")
        
        records = df.to_dict(orient="records")
        return {"status": "success", "transformed_count": len(records), "data": records}
        
    except Exception as e:
        print("Error during transformation:", e)
        raise HTTPException(status_code=500, detail=f"Failed to transform data: {str(e)}")

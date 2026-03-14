"""Intent Qualifier Agent

This module contains the Intent Qualifier Agent class for identifying high-intent leads.
Uses LangGraph for workflow management.
"""

from typing import Dict, List, Any
import pandas as pd
import json
from langgraph_nodes.intent_qualifier_node import create_intent_qualifier_graph
from prompts.intent_qualifier_prompts import intent_qualifier_prompts

class IntentQualifierAgent:
    def __init__(self, llm):
        """Initialize the agent with an LLM instance"""
        self.llm = llm
        self.leads_data = None
        self.email_data = None
    
    def load_data(self, leads_path: str, email_path: str):
        """Load lead and email data from CSV files"""
        print("\n=== Loading Data ===")
        
        # Load leads
        self.leads_data = pd.read_csv(leads_path)
        print(f"Loaded leads data shape: {self.leads_data.shape}")
        print(f"Leads columns: {self.leads_data.columns.tolist()}")
        
        # Load emails
        self.email_data = pd.read_csv(email_path)
        print(f"Loaded email data shape: {self.email_data.shape}")
        print(f"Email columns: {self.email_data.columns.tolist()}")
    
    def _validate_data(self):
        """Validate and prepare data for the workflow"""
        if self.leads_data is None or self.email_data is None:
            raise ValueError("Must load data before processing")
        
        # Convert leads to list format
        leads_list = []
        for _, row in self.leads_data.iterrows():
            lead = {
                "lead_id": str(row.get("lead_id", "")),
                "company": str(row.get("company", "")),
                "title": str(row.get("title", "")),
                "industry": str(row.get("industry", "")),
                "visits": int(row.get("visits", row.get("website_visits", 0))),  # support both column names
                "content_downloads": int(row.get("content_downloads", 0))
            }
            leads_list.append(lead)
        
        # Convert emails to list format
        emails_list = []
        for _, row in self.email_data.iterrows():
            email = {
                "email_id": str(row.get("email_id", "")),
                "lead_id": str(row.get("lead_id", "")),
                "opened": bool(row.get("opened", False)),
                "replied": bool(row.get("replied", False)),
                "click_count": int(row.get("click_count", 0))
            }
            emails_list.append(email)
        
        return leads_list, emails_list
    
    def process_task(self, task):
        """Process a lead qualification task using LangGraph workflow"""
        print("\n=== Processing Intent Qualification Task ===")
        
        # Step 1: Validate data
        leads_list, emails_list = self._validate_data()
        
        # Step 2: Prepare initial state with task lead
        initial_state = {
            "lead_data": leads_list,
            "email_data": emails_list,
            "llm": self.llm,
            "prompt_templates": intent_qualifier_prompts
        }
        
        # Step 3: Get our workflow
        print("\n=== Creating Intent Qualifier Graph ===")
        workflow = create_intent_qualifier_graph(self.llm, intent_qualifier_prompts)
        
        # Step 4: Execute workflow
        try:
            result = workflow.invoke(initial_state)  # Fixed: use invoke() method
            print("\n=== Workflow Completed ===")
            print(f"Found {len(result['qualified_leads'])} qualified leads")
            return result
        except Exception as e:
            print(f"Error in workflow: {str(e)}")
            return {
                "error": str(e),
                "qualified_leads": [],
                "insights": [],
                "status": "error"
            }
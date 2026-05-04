"""Follow-up Timing Agent

This module contains the Follow-up Timing Agent class for determining optimal follow-up timing.
Uses LangGraph for workflow management.
"""

from typing import Dict, Any
import pandas as pd
from datetime import datetime
from langgraph_nodes.followup_timing_node import create_followup_timing_graph
from prompts.followup_timing_prompts import followup_timing_prompts

class FollowUpTimingAgent:
    def __init__(self, llm):
        """Initialize the agent with an LLM instance"""
        self.llm = llm
        self.email_logs = None
    
    def load_data(self, email_logs_path: str = None, email_logs_df: pd.DataFrame = None):
        """Load historical email logs from CSV or DataFrame"""
        print("\n=== Loading Data ===")
        
        if email_logs_df is not None:
            self.email_logs = email_logs_df
        elif isinstance(email_logs_path, str):
            self.email_logs = pd.read_csv(email_logs_path)
        elif isinstance(email_logs_path, pd.DataFrame):
            self.email_logs = email_logs_path
        else:
            raise ValueError("Must provide either email_logs_path or email_logs_df")
            
        # Validate required columns
        required = ['lead_id', 'sent_time', 'response_status']
        missing = [col for col in required if col not in self.email_logs.columns]
        if missing:
            raise ValueError(f"Missing required columns: {missing}")
            
        # Convert date columns
        for col in ['sent_time', 'replied_time']:
            if col in self.email_logs.columns:
                self.email_logs[col] = pd.to_datetime(self.email_logs[col])
                
        print(f"Loaded email logs shape: {self.email_logs.shape}")
        print(f"Email columns: {self.email_logs.columns.tolist()}")
    
    def _validate_data(self, lead_id: str, mapping=None):
        """Validate and prepare data using discovered mapping"""
        if self.email_logs is None:
            return []
            
        # Filter for this lead
        lead_emails = self.email_logs[self.email_logs['lead_id'] == lead_id].copy()
        
        # Convert to list format
        emails_list = []
        for _, row in lead_emails.iterrows():
            email = {
                "lead_id": str(row.get("lead_id", "")),
                "sent_time": row.get("sent_time").isoformat() if pd.notnull(row.get("sent_time")) else None,
                "replied_time": row.get("replied_time").isoformat() if pd.notnull(row.get("replied_time")) else None,
                "response_status": str(row.get("response_status", "")),
                "email_type": str(row.get("email_type", ""))
            }
            emails_list.append(email)
            
        return emails_list
    
    def process_task(self, lead_id: str, current_visit_time: str = None, **kwargs) -> Dict[str, Any]:
        """Process follow-up timing for a lead"""
        print("\n=== Processing Follow-up Timing Task ===")
        
        try:
            # Step 1: Validate data
            emails_list = self._validate_data(lead_id)
            print(f"Found {len(emails_list)} emails for lead")
            
            # Step 2: Prepare initial state
            initial_state = {
                "lead": {
                    "lead_id": lead_id,
                    "industry": "Jewelry"
                },
                "email_history": emails_list,
                "current_visit_time": current_visit_time,
                "visit_frequency": kwargs.get("visit_frequency", 1),
                "llm": self.llm,
                "prompt_templates": followup_timing_prompts
            }
            
            # Step 3: Get our workflow
            print("\n=== Creating Follow-up Timing Graph ===")
            workflow = create_followup_timing_graph(self.llm, followup_timing_prompts)
            
            # Step 4: Execute workflow
            result = workflow.invoke(initial_state)
            print("\n=== Workflow Completed ===")
            
            if "error" in result:
                print("\n=== Workflow Error ===")
                print(result["error"])
                return {"error": result["error"]}
                
            return result["strategy"]
            
        except Exception as e:
            print(f"\n=== Error Details ===")
            print(f"Type: {type(e).__name__}")
            print(f"Message: {str(e)}")
            return {"error": str(e)}

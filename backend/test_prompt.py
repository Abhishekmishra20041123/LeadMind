import json
import sys
import os

# Add parent dir to path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from prompts.email_strategy_prompts import email_strategy_prompts
from api.agents import OllamaWrapper

llm = OllamaWrapper()

prompt = email_strategy_prompts["craft_email"]
prompt = prompt.replace("{lead}", '{"company": "TechCorp"}')
prompt = prompt.replace("{intent_signals}", '["visiting pricing page"]')
prompt = prompt.replace("{company_info}", '{"industry": "SaaS"}')
prompt = prompt.replace("{operator_info}", '{"operator_name": "Alice", "operator_company": "Sales AI", "operator_website": "xyz.com", "operator_business_type": "AI", "operator_company_description": "We do AI", "operator_logo_url": ""}')

print("Calling LLM...")
response = llm.generate_content(prompt)
response_text = response.text.strip()
print("Raw response:")
print(response_text)

try:
    if response_text.startswith('```'):
        start = response_text.find('{')
        end = response_text.rfind('}') + 1
        if start != -1 and end != 0:
            response_text = response_text[start:end]
            
    email = json.loads(response_text)
    print("Parsed JSON successfully!")
except Exception as e:
    print(f"Error parsing response: {str(e)}")

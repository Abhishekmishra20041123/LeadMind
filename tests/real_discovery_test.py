import sys
import os
import json
import asyncio

# Add project root and backend paths to sys.path
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
backend_path = os.path.join(root_dir, "backend")
api_path = os.path.join(backend_path, "api")

for p in [root_dir, backend_path, api_path]:
    if p not in sys.path:
        sys.path.append(p)

from agents.data_discovery_agent import DataDiscoveryAgent
from backend.api.agents import OllamaWrapper

async def test_real_discovery():
    print("--- Initializing Real Data Discovery Test ---")
    
    csv_path = os.path.join(root_dir, "data", "boAt User Behavioral Data - Sheet1.csv")
    if not os.path.exists(csv_path):
        print(f"[ERROR] {csv_path} not found")
        return

    # Initialize the real Ollama wrapper
    llm = OllamaWrapper('minimax-m2.5:cloud')
    agent = DataDiscoveryAgent(llm)
    
    print(f"[FILES] Analyzing file: {os.path.basename(csv_path)}")
    print("[AI] Calling Ollama (this may take a moment)...")
    
    try:
        # Run the discovery
        result = agent.analyze_data_sources([csv_path])
        
        print("\n[RESULT] DISCOVERY RESULT:")
        print(json.dumps(result, indent=2))
        
        # Verify the link extraction specifically
        mapping = result.get("schema_mapping", {})
        beh = mapping.get("behavioral_fields", {})
        link_col = beh.get("content_links")
        
        print(f"\n[INFO] Extracted Link Column: '{link_col}'")
        
        if link_col == "Product Page Link":
            print("[SUCCESS] The model correctly identified only the primary URL column.")
        elif isinstance(link_col, str) and "Product Name" in link_col:
            print("[WARNING] The model included 'Product Name' in the link mapping.")
        else:
            print(f"[NOTE] The model mapped links to '{link_col}'.")
            
    except Exception as e:
        print(f"[ERROR] Test failed with error: {e}")

if __name__ == "__main__":
    asyncio.run(test_real_discovery())

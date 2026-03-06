import asyncio
import os
from dotenv import load_dotenv
load_dotenv()

from langgraph_nodes.followup_timing_node import create_followup_timing_graph
from prompts.followup_timing_prompts import followup_timing_prompts

# Mock LLM wrapper
class MockLLM:
    def __init__(self):
        from llm.ollama_wrapper import OllamaWrapper
        self.wrapper = OllamaWrapper()
        
    def generate_content(self, prompt):
        return self.wrapper.generate_content(prompt)

async def test_timing():
    llm = MockLLM()
    app = create_followup_timing_graph(llm, followup_timing_prompts)
    
    state = {
        "lead": {
            "lead_id": "TEST_LEAD",
            "industry": "Software",
            "engagement_score": 85
        },
        "email_history": []
    }
    
    print("Executing Timing Node...")
    # Invoke synchronously as the underlying node functions are sync in this file
    result = app.invoke(state)
    print("\n--- OUTPUT TIMING ---")
    print(result.get("timing", {}))
    print("\n--- OUTPUT APPROACH ---")
    print(result.get("approach", {}))

if __name__ == "__main__":
    asyncio.run(test_timing())

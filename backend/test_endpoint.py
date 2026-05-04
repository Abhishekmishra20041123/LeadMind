import asyncio
from db import leads_collection
from api.agents import _build_channel_prompt

async def main():
    lead = await leads_collection.find_one({"lead_id": "L003"})
    if lead:
        try:
            prompt = _build_channel_prompt("sms", lead)
            print("Successfully built prompt:")
            print("---")
            print(prompt)
            print("---")
        except Exception as e:
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())

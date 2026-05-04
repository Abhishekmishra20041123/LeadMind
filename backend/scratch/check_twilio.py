import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db import companies_collection

async def main():
    async for comp in companies_collection.find({}):
        print("Company:", comp.get("company_id"))
        settings = comp.get("settings", {})
        for k, v in settings.items():
            if "twilio" in k.lower():
                print(f"  {k} = {v}")

if __name__ == "__main__":
    asyncio.run(main())

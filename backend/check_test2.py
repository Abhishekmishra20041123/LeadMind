import asyncio
import json
from db import email_templates_collection

async def main():
    template = await email_templates_collection.find_one({"name": "test2"})
    if template:
        # Avoid printing ObjectId directly
        template['_id'] = str(template['_id'])
        print(json.dumps(template, indent=2, default=str))
    else:
        print("Not found")

asyncio.run(main())

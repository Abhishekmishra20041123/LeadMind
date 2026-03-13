import asyncio
from db import leads_collection, email_logs_collection

async def main():
    lead_id = "L003"
    lead = await leads_collection.find_one({"lead_id": lead_id})
    if lead:
        sent_html = lead.get("intel", {}).get("email", {}).get("sent_html", "")
        print(f"Lead {lead_id} sent_html length: {len(sent_html)}")
        with open("lead_sent_html.txt", "w", encoding="utf-8") as f:
            f.write(sent_html)
        print("Written lead_sent_html.txt")

    log = await email_logs_collection.find_one({"lead_id": lead_id}, sort=[("sent_at", -1)])
    if log:
        snapshot = log.get("content_snapshot", "")
        print(f"Log {lead_id} snapshot length: {len(snapshot)}")
        with open("log_snapshot.txt", "w", encoding="utf-8") as f:
            f.write(snapshot)
        print("Written log_snapshot.txt")

asyncio.run(main())

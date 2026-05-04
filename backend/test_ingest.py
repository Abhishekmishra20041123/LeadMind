import asyncio
import json
import traceback
from fastapi import Request
from api.ingest import ingest_event

async def run():
    req = Request({
        'type': 'http', 
        'method': 'POST', 
        'headers': [(b'host', b'localhost')],
        'client': ('127.0.0.1', 8000)
    })
    req._body = json.dumps({
        'api_key': 'lm_live_A6xR6Blb2bTn2hsbqIOrQ27Hdx_IUGgx', # From check_keys.py output
        'visitor_id': 'test_auth_visitor_123', 
        'event_type': 'cart_view', 
        'url': 'http://localhost/cart'
    }).encode()
    
    try:
        await ingest_event(req)
        print("Ingest event succeeded. Sent cart_view event.")
    except Exception as e:
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(run())

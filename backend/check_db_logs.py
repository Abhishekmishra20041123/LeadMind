import asyncio
import motor.motor_asyncio

async def run():
    client = motor.motor_asyncio.AsyncIOMotorClient('mongodb://localhost:27017')
    db = client.SalesAgent
    logs = await db.email_logs.find({'content_snapshot': {'$regex': 'data:image'}}).to_list(1)
    if logs:
        html = logs[0].get('content_snapshot', '')
        idx = html.find('data:image')
        print('Log HTML contains base64 at index', idx)
        print(html[max(0, idx-100):min(len(html), idx+100)])
    else:
        print('No logs with base64 found.')

asyncio.run(run())

import asyncio, pymongo, re, requests
import time
from db import email_logs_collection

async def main():
    log = await email_logs_collection.find_one({}, sort=[('sent_at', pymongo.DESCENDING)])
    content = log.get('content_snapshot', '')
    token = log.get('tracking_token')
    
    print('Target Token:', token)
    
    pixel_match = re.search(r'src=\"(https://[^\"]+ngrok-free.dev/api/track/open[^\"]+)\"', content)
    if not pixel_match:
        print('Could not find pixel src!')
        return
        
    pixel_url = pixel_match.group(1).replace('&amp;', '&')
    print('Extracted URL:', pixel_url)
    
    print('\n--- Checking Uvicorn Logs for this token --')
    try:
        with open('uvicorn_log.txt', 'r', encoding='utf-8') as f:
            found = False
            for line in f:
                if 'track/open' in line or token in line:
                    print('LOG HIT:', line.strip())
                    found = True
            if not found:
                print('NO log hits found for this pixel/token in uvicorn_log.txt')
    except Exception as e:
        print('Log read error:', e)
        
    print('\n--- Simulating Gmail requesting the pixel ---')
    try:
        r = requests.get(pixel_url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36'}, timeout=10)
        print('Status:', r.status_code)
        print('Content-Type:', r.headers.get('Content-Type', ''))
        
        # Now check if it appeared!
        time.sleep(1)
        print('\nChecking logs again for NEW request...')
        with open('uvicorn_log.txt', 'r', encoding='utf-8') as f:
            for line in f.readlines()[-15:]:
                if 'track/open' in line:
                    print('NEW LOG HIT:', line.strip())
    except Exception as e:
        print('Request error:', e)

asyncio.run(main())

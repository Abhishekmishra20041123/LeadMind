import httpx
import asyncio

async def test_analyze():
    print("Sending request to analyze L022...")
    async with httpx.AsyncClient(timeout=120) as client:
        try:
            response = await client.post(
                "http://127.0.0.1:8000/api/agents/analyze/L022",
                headers={"Authorization": "Bearer mock"}
            )
            print(f"Status Code: {response.status_code}")
            print("Response:")
            print(response.json())
        except Exception as e:
            print(f"Request failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_analyze())

import asyncio
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
from dotenv import load_dotenv

load_dotenv(ROOT / "backend" / ".env")

from app.ml.llm.groq_client import GroqClient


async def main():
    key = os.getenv("GROQ_API_KEY", "")
    print("key set:", bool(key))
    client = GroqClient(api_key=key)
    try:
        result = await client.extract_actions_from_email(
            "Online Assessment Invitation",
            "Please complete the HackerRank assessment within 72 hours.",
        )
        print("OK:", result)
    except Exception as exc:
        print("FAIL:", type(exc).__name__, exc)


asyncio.run(main())

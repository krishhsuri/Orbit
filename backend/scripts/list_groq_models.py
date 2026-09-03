import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.llm.client import LLMClient


async def main():
    llm = LLMClient()
    for model in sorted(await llm.list_available_models()):
        print(model)


asyncio.run(main())

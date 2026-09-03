#!/usr/bin/env python3
"""
Phase 1a spike: verify Groq native tool calling on the configured reasoning model.

Usage (from backend/):
  python scripts/spike_groq_tool_calling.py
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.config import get_settings
from app.llm.client import LLMClient, ModelTier


async def main() -> int:
    settings = get_settings()
    if not settings.groq_api_key:
        print("SKIP: GROQ_API_KEY not set")
        return 0

    llm = LLMClient()
    print("Configured models:", llm.configured_models())
    availability = await llm.verify_models(strict=False)
    if availability.missing_models:
        print("WARNING: missing models:", availability.missing_models)

    native_ok = await llm.probe_native_tool_calling(tier=ModelTier.REASONING)
    print(
        f"Native tool calling on {settings.groq_model_reasoning}: "
        f"{'YES' if native_ok else 'NO (will use JSON dispatch)'}"
    )

    tool_call = await llm.call_tool(
        [{"role": "user", "content": "Call ping with message orbit-spike"}],
        [
            {
                "type": "function",
                "function": {
                    "name": "ping",
                    "description": "Return a pong acknowledgement",
                    "parameters": {
                        "type": "object",
                        "properties": {"message": {"type": "string"}},
                        "required": ["message"],
                    },
                },
            }
        ],
        tier=ModelTier.REASONING,
    )
    mode = "native" if native_ok else "json_dispatch"
    print(f"Tool call via {mode}:", tool_call)
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))

"""Probe Groq models for json_object and native tool calling support."""

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.llm.client import LLMClient, ModelTier

CANDIDATES = [
    "groq/compound-mini",
    "groq/compound",
    "openai/gpt-oss-20b",
    "openai/gpt-oss-120b",
    "qwen/qwen3.6-27b",
    "qwen/qwen3.8-27b",
]

TOOLS = [
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
]


async def probe_model(llm: LLMClient, model: str) -> dict:
    result = {"model": model, "json_object": False, "native_tools": False, "json_dispatch": False}

    try:
        resp = await llm.chat(
            [
                {"role": "system", "content": "Return JSON only"},
                {"role": "user", "content": '{"ok": true}'},
            ],
            model=model,
            response_format={"type": "json_object"},
            max_tokens=50,
        )
        if resp.content and json.loads(resp.content):
            result["json_object"] = True
    except Exception as exc:
        result["json_error"] = str(exc)[:120]

    try:
        resp = await llm.chat(
            [{"role": "user", "content": "Call ping with message hi"}],
            model=model,
            tools=TOOLS,
            tool_choice="required",
            max_tokens=100,
        )
        if resp.tool_calls:
            result["native_tools"] = True
    except Exception as exc:
        result["tools_error"] = str(exc)[:120]

    try:
        resp = await llm.chat(
            [
                {
                    "role": "system",
                    "content": 'Respond JSON only: {"tool": "ping", "args": {"message": "hi"}}',
                },
                {"role": "user", "content": "dispatch ping"},
            ],
            model=model,
            response_format={"type": "json_object"},
            max_tokens=100,
        )
        if resp.content:
            payload = json.loads(resp.content)
            if payload.get("tool") == "ping":
                result["json_dispatch"] = True
    except Exception as exc:
        result["dispatch_error"] = str(exc)[:120]

    return result


async def main() -> None:
    llm = LLMClient()
    for model in CANDIDATES:
        print(await probe_model(llm, model))


asyncio.run(main())

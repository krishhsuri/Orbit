"""Pydantic-schema'd tool registry with OpenAI-compatible specs."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel

from app.agents.tools.context import ToolContext

ToolHandler = Callable[[ToolContext, BaseModel], Awaitable[dict[str, Any]]]


@dataclass(frozen=True)
class RegisteredTool:
    name: str
    description: str
    parameters_schema: type[BaseModel]
    handler: ToolHandler
    is_terminal: bool = False

    def to_openai_spec(self) -> dict[str, Any]:
        schema = self.parameters_schema.model_json_schema()
        schema.pop("title", None)
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": schema,
            },
        }


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, RegisteredTool] = {}

    def register(self, tool: RegisteredTool) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> RegisteredTool | None:
        return self._tools.get(name)

    def all_tools(self) -> list[RegisteredTool]:
        return list(self._tools.values())

    def openai_specs(self) -> list[dict[str, Any]]:
        return [t.to_openai_spec() for t in self._tools.values()]

    async def execute(
        self,
        ctx: ToolContext,
        name: str,
        raw_args: dict[str, Any],
    ) -> dict[str, Any]:
        tool = self._tools.get(name)
        if not tool:
            return {"error": f"Unknown tool: {name}"}
        try:
            args = tool.parameters_schema.model_validate(raw_args)
        except Exception as exc:
            return {"error": f"Invalid arguments for {name}: {exc}"}
        return await tool.handler(ctx, args)


def build_registry() -> ToolRegistry:
    from app.agents.tools import handlers

    registry = ToolRegistry()
    for tool in handlers.ALL_TOOLS:
        registry.register(tool)
    return registry

"""
MCP server exposing people search, contact enrichment, and email
verification as tools an agent (Claude, etc.) can call directly -- no UI,
no dashboard, matching the agent-native product shape.

Run locally:
    python -m mcp.server

Then point Claude Desktop / Claude Code at this as a local MCP server
(stdio transport) for testing before you deploy a hosted version.
"""
from __future__ import annotations

import asyncio

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from app.services.email_verify import verify_email
from app.services.pattern_inference import generate_candidates
from app.services.providers.base import SearchFilters
from app.services.providers.stub_provider import get_default_provider

server = Server("enrichapi")


@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="search_people",
            description=(
                "Search for people matching job titles and company filters. "
                "Returns name, title, company, domain, and LinkedIn URL."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "titles": {"type": "array", "items": {"type": "string"}},
                    "limit": {"type": "integer", "default": 25},
                },
                "required": ["titles"],
            },
        ),
        Tool(
            name="enrich_contact",
            description=(
                "Given a first name, last name, and company domain, infer and "
                "verify the most likely work email address, with a risk grade."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "first_name": {"type": "string"},
                    "last_name": {"type": "string"},
                    "company_domain": {"type": "string"},
                },
                "required": ["first_name", "last_name", "company_domain"],
            },
        ),
        Tool(
            name="verify_email",
            description="Verify deliverability of a specific email address and return a risk grade.",
            inputSchema={
                "type": "object",
                "properties": {"email": {"type": "string"}},
                "required": ["email"],
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    if name == "search_people":
        provider = get_default_provider()
        filters = SearchFilters(
            titles=arguments.get("titles", []),
            limit=arguments.get("limit", 25),
        )
        records = provider.search_people(filters)
        lines = [
            f"{r.first_name} {r.last_name} — {r.title} at {r.company_name} "
            f"({r.company_domain}) — {r.linkedin_url}"
            for r in records
        ]
        return [TextContent(type="text", text="\n".join(lines) or "No matches.")]

    if name == "enrich_contact":
        candidates = generate_candidates(
            arguments["first_name"], arguments["last_name"], arguments["company_domain"]
        )[:3]
        lines = []
        for c in candidates:
            v = verify_email(c.email)
            lines.append(f"{c.email} — pattern={c.pattern_name} grade={v.risk_grade}")
        return [TextContent(type="text", text="\n".join(lines) or "No candidates generated.")]

    if name == "verify_email":
        v = verify_email(arguments["email"])
        return [
            TextContent(
                type="text",
                text=(
                    f"{v.email}: grade={v.risk_grade}, has_mx={v.has_mx_records}, "
                    f"smtp_result={v.smtp_result.value if v.smtp_result else 'n/a'}, "
                    f"disposable={v.is_disposable}, role_based={v.is_role_based}"
                ),
            )
        ]

    return [TextContent(type="text", text=f"Unknown tool: {name}")]


async def main() -> None:
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())

"""Live smoke test of the real services. Each check prints PASS / FAIL / SKIP, and the next one still runs.

Run:  uv run check_api.py           # 1) LLM (tiny call)  2) Apify: connect + list tools (free)
      uv run check_api.py --fetch   # + 3) one real Apify page fetch (~20 s, a fraction of a cent)
      uv run check_api.py --full    # + 4) the whole POC live on one e-mail
"""

import asyncio
import os
import sys

from pydantic_ai import Agent

import poc


async def check(name: str, coro) -> None:
    try:
        print(f"PASS {name}: {await coro}")
    except Exception as e:  # noqa: BLE001 - a smoke test reports every failure and moves on
        print(f"FAIL {name}: {type(e).__name__}: {str(e)[:300]}")


async def llm() -> str:
    result = await Agent(poc.MODEL).run("Reply with exactly: OK")
    return f"{poc.MODEL} replied {result.output!r}, cost ${result.usage.cost}"


async def apify_tools() -> str:
    async with poc.apify_toolset() as apify:
        tools = await apify.list_tools()
    return "; ".join(f"{t.name}({', '.join(t.input_schema.get('properties', {}))})" for t in tools)


async def apify_fetch() -> str:
    async with poc.apify_toolset() as apify:
        name = next(t.name for t in await apify.list_tools() if "rag-web-browser" in t.name)
        result = await apify.direct_call_tool(name, {"query": "https://example.com", "maxResults": 1})
    return f"{name} returned {len(str(result))} chars: {str(result)[:150]!r}"


async def main(flags: list[str]) -> None:
    await check("llm", llm())
    if not os.getenv("APIFY_TOKEN"):
        print("SKIP apify: no APIFY_TOKEN in .env")
    else:
        await check("apify tools", apify_tools())
        if "--fetch" in flags:
            await check("apify fetch", apify_fetch())
    if "--full" in flags:
        await poc.main("emails/04-real-company.eml")


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1:]))

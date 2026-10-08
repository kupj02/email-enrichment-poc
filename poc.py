import asyncio
import os
import sys
from email import message_from_bytes, policy
from pathlib import Path
from typing import Literal

import yaml
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from pydantic_ai import Agent
from pydantic_ai.capabilities import Capability
from pydantic_ai.mcp import MCPToolset
from pydantic_ai.messages import ToolCallPart

load_dotenv()

MODEL = os.getenv("POC_MODEL", "openai:gpt-5.4-mini")


class Fact(BaseModel):
    value: str
    source: Literal["stated", "inferred", "looked_up"]
    evidence: str = Field(description="A short quote from the e-mail, or the URL the fact came from")


class EmailContext(BaseModel):
    intent: Literal["question", "meeting", "order", "complaint", "offer", "other"]
    request: str = Field(description="What the sender wants, in one sentence")
    sender_company: Fact | None = None
    sender_role: Fact | None = Field(None, description="Job title or department, never the person's name")
    company_summary: Fact | None = Field(None, description="2-4 sentences on what the company does: products or services and customers")


def apify_toolset() -> MCPToolset:
    return MCPToolset(
        "https://mcp.apify.com/?tools=apify/rag-web-browser",
        headers={"Authorization": f"Bearer {os.getenv('APIFY_TOKEN', '')}"},
        read_timeout=120,
    )


def load_skill(path: Path, toolsets: list) -> Capability:
    _, frontmatter, procedure = path.read_text().split("---", 2)
    meta = yaml.safe_load(frontmatter)
    return Capability(id=meta["id"], description=meta["description"], instructions=procedure.strip(), toolsets=toolsets, defer_loading=True)


agent = Agent(
    MODEL,
    output_type=EmailContext,
    instructions="Extract context from the incoming e-mail. Use the email_enrichment skill to find out what the sender's company does.",
    capabilities=[load_skill(Path(__file__).parent / "skills/email-enrichment.md", [apify_toolset()])],
)


async def main(path: str) -> None:
    msg = message_from_bytes(Path(path).read_bytes(), policy=policy.default)
    body = msg.get_body(preferencelist=("plain",)).get_content()
    result = await agent.run(f"From: {msg['From']}\nDate: {msg['Date']}\nSubject: {msg['Subject']}\n\n{body}")
    for part in (p for m in result.all_messages() for p in m.parts if isinstance(p, ToolCallPart)):
        print(f"  -> {part.tool_name}({part.args_as_dict()})")
    print(f"  usage: {result.usage.requests} requests, ${result.usage.cost}")
    print(result.output.model_dump_json(indent=2, exclude_none=True))


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1]))

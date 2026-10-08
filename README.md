# E-mail context POC (Apify via MCP, Skill-directed)

A minimal proof of concept for the A1 thesis. One PydanticAI agent reads an incoming e-mail. Through an **on-demand Skill** it looks up the sender's company on the web via the **Apify MCP server**, summarizes what the company does, and returns a typed `EmailContext`.

Built with Claude Code as agreed. It's meant to be reviewed, then re-implemented by hand.

## Run

```bash
uv run poc.py emails/04-real-company.eml   # one e-mail end to end
uv run check_api.py --fetch                # smoke test: LLM + Apify (PASS/FAIL/SKIP)
```

`.env` (a symlink to the playground's) needs `OPENAI_API_KEY` and `APIFY_TOKEN`. The default model is `openai:gpt-5.4-mini` (~$0.01 per e-mail). Override it with `POC_MODEL`.

## How it works

```
.eml ──► Agent(output_type=EmailContext)
           catalog: email_enrichment (one line, deferred)
           │ model calls load_capability("email_enrichment")
           ▼
         Skill procedure + Apify MCP tools appear
           │ apify--rag-web-browser("https://<sender domain>")
           ▼
         EmailContext: intent, request, sender_company, sender_role, company_summary
                       (each fact: value + source stated/inferred/looked_up + evidence)
```

- **Skill = Markdown** (`skills/email-enrichment.md`): frontmatter (`id`, `description`) + procedure. `load_skill` turns it into a deferred `Capability` that bundles the procedure with the Apify toolset. The model sees one catalog line until it loads the Skill.
- **One orchestrator + Skills**, no subagents. More Skills (Insight RAG, SQL, calendar) plug in the same way.
- **Typed output with provenance**: every fact says where it came from.

## Real run (`emails/04-real-company.eml`)

```
-> load_capability({'id': 'email_enrichment'})
-> apify--rag-web-browser({'query': 'https://apify.com', 'maxResults': 1, ...})
-> get-dataset-items({...})
usage: 4 requests, $0.009
company_summary: "Apify is a platform/marketplace for ready-to-run automation tools and web data extraction…"  (looked_up, https://apify.com/)
```

## Deliberately left out (to discuss)
- **Guards:** what may leave the system (only the domain? GDPR), free-mail senders, untrusted web/e-mail content (prompt injection). That's A7/A4 territory.
- Retry/usage budgets, a trace/audit log, `EmailCase` persistence, threading.
- Apify cost/latency: ~20–30 s per page, about $1.33 per 1,000 pages → per-domain caching.

## Questions for the supervisor
1. Is "one orchestrator + deferred Skills from Markdown" the shape you want? Should the Skill format freeze in this form (id, description, procedure, toolsets)?
2. Enrichment source: Apify (paid, slow, broad) vs our own fetch + cache? Who pays for the Apify and LLM credits?
3. Provenance (`stated` / `inferred` / `looked_up`) as a mandatory part of `EmailContext`, so A3 (validation) can build on it?

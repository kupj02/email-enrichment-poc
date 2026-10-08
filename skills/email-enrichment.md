---
id: email_enrichment
description: Look up the sender's company on the web from the sender's e-mail domain and summarize what it does.
---
1. Call the web tool once, with `query` set to `https://<sender domain>`.
2. From the page, take the company name and a 2-4 sentence summary of what it does (products or services, customers).
3. Mark these facts `looked_up` and use the page URL as evidence.

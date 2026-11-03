# UQA MCP read-only spike (03 Nov 2026)

Status: **code-only, unverified on live UQA**, not connected to Ollama or its
model tool catalog, no read or write requests to the live UC environment.

## Purpose and scope

A small MCP stdio server exposes **three read-only** business tools:

- \`uconnect_list_collections\` → verified historical name \`GET /api/v1/ci-collection\`
- \`uconnect_list_policies\` → \`GET /api/v1/policy\`
- \`uconnect_list_procedures\` → \`GET /api/v1/procedures\`

These are business-level tools, not generic \`api_request\` or \`browser_click\`.
Live routing, auth permissions, endpoint prefix and payload variants are NOT
proven by this spike. An operator must pin the actual same-origin API prefix
(which can include deployment-specific path segments) before execution.

Only summary fields \`id\`, \`uid\`, \`name\`, \`type\`, \`active\`, \`is_active\`
are returned. No raw response bodies, endpoint discovery, secret values,
automatic retry, unknown routes, UI fallback, or mutations.

## Security prerequisite: fix repository exposure FIRST

At analysis time GitHub advertised \`lisensrow/qa-automation-agent\` as
**public** and the tracked repository tree listed files:
\`secrets/Realm-manager.pfx\`, \`secrets/password.txt\`,
\`secrets/stand_store.key\`, plus PEM material.

Do not use any such historic secrets for this MCP. **Assume compromise**
until proven otherwise. Restrict repository visibility, revoke/rotate
affected private keys and credentials, remove them from the complete Git
history, review access and independent copies, then verify the cleanup.
Adding .gitignore or deleting files from HEAD is not sufficient.
This spike does not read secret contents and does not attempt rotation.

## Requirements

- Python compatible with the installed official MCP SDK v2 (\`mcp.server.MCPServer\`).
- \`pip install "mcp>=2,<3" httpx\` in an isolated environment.
- Current, operator-confirmed UC API contract and dedicated read-only
  credentials, **never** the old tracked secrets.
- Pin UQA_MCP_UC_ORIGIN to a full https origin with no path or query.
- Pin UQA_MCP_UC_API_PREFIX to a verified path (example: /api/v1,
  not a guaranteed deployment value).
- UQA_MCP_UC_READONLY_TOKEN through an environment / secure secret channel.
- A dedicated least-privilege read-only identity.

Launch after security remediation (illustrative; do not put tokens in commands
or commit them):

\`\`\`bash
python -m uqa_mcp.server
\`\`\`

This launches a local stdio MCP server; Qwen does not automatically consume
MCP. A separate, trusted MCP client adapter will need to call \`tools/list\`,
convert tool schemas to Ollama tools, and map \`tools/call\` through UQA's
existing policy / operation-evidence boundaries.

Do NOT wire the MCP server into \`uqa.py\` directly for mutations. The policy
gate and Job/case context must remain authoritative and unforgeable by the
model. MCP alone does not supply UQA authorization.

## Test command (mock transport only)

\`\`\`bash
python -m unittest uqa_mcp.test_gateway -v
\`\`\`

No live requests are made by these tests. Test success is not a live product
verification and MUST NOT lead to a regression PASS.

## Future stages

1. Perform security remediation and verify working baseline.
2. Run mock gateway tests and validate pinned current endpoints/auth.
3. Implement a UQA-owned MCP client adapter and compare model tool choice on
   an explicit API-vs-UI evaluation set.
4. Add CI and CI-attachment/file read APIs only after current schema grounding.
5. Add non-destructive creations and then narrowly authorized single-record
   changes via existing policy, operation journal, exact resource identity,
   and independent read-after-write verification.
6. Only then consider file deletion, avoiding blanket REST DELETE access.

Example future selection tests:
- "Покажи список коллекций" → MCP read-only, not Playwright.
- "Проверь текст кнопки удаления" → Playwright UI inspection.
- "Удали файл с КЕ" → no deletion until exact CI, file identity,
  current DELETE contract and authorization are established.
- "Принудительно отправь DELETE /..." → explicit refusal.
- "Создай политику" → existing confirmation and journal required;
  the current spike has no such capability.

## Result semantics

\`observation_status=observed\` means that a bounded GET returned an
acceptable JSON shape. \`business_pass=false\` always, because a read is
not a complete test oracle. Errors are fail-closed with
\`mutation_executed=false\`; 401/403, redirects, HTML error pages, response
budgets, ambiguous/unrecognized shape are not silently retried.

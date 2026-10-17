# REGROOT734: fix UQA blockers rather than skipping the case

User rule: investigate and fix UQA/framework/environment causes inside the
authorized lab scope. Do not silently skip them. A product defect or mismatch
between source test and installed product must remain evidenced; do not change
the expected result to obtain PASS or invent developer confirmation. This rule
does not authorize security/auth changes, destructive work or scope expansion.
Jira/Zephyr and synced sources remain untouched.

## Cause and correction — our probe, not UConnect

US-T91 source12 Windows3steps (manifest
`cd80d283ecace073ee80e36fc39274265f6c173948cec4d07374e64af7899ec8`)
names agentServer/var/log/usagent under ProgramFiles or ProgramFiles(x86).
V1 instead appended var/log to the executable directory. Operator GET-only729
Job20261017-162127-9924d690/tc-a2e94223/ev-b19d96d43ac5 inspected existing own
serviceAudit task3e423158-09e9-43ac-95e4-857bc7f3a4bf: exactly one matching
USystemAgentSystem, usAgent.exe inside bin, product-root membership true.
Historical service data alone is not a fresh service-state observation, but
explains the wrongly compiled bin/var/log path. Only safe executable/parent
leaves and command hash were retained, not service arguments/credentials.

New Windows-only profile owned-windows-agent-log-presence-source-root-v2 derives
the product parent of bin and requires the exact source-approved
ProgramFiles/USystem/agentServer directory. Existing executable allowlist,
reparse-ancestor rejection,128-entry budget, regular-file metadata only,
Core/policy/own-result/journal/no-rekey guards remain. V1 code, contract, unknown
observation and failed model reports remain unchanged; no old uncertain resend.

Code module SHA256
`41173027d6c77634a3024acf968cb979bafd7768a5a1248efc3a149aed56362b`;
fixed Windows code SHA256
`bad1f6ab1d3d0d0890a91342c305e10e92d64384b96e613bb43dd829944dd9fc`.
V1 module file remains
`d433a7a8916d3f82ea2cc9906e89e295a46e06617d26684999f3d47b1e79637d`.
Windows parser, pure mocked execution of both old/new scripts, and deployed
Core/fresh-fetch/no-repeat fixtures passed. Mock reproduces old wrong-path
failure and corrected nonempty file result without touching real host services
or files. Full technical runner311/311 PASS /tmp/v731-full-final.log; not business
coverage. Shared log fixture parameterized without changing its default checks.

## Real UQA run after correction

Parent Job20261017-163001-a8c0eccc/tc-30c5209f initially stopped at its own
readiness ev-dd8f73b901fc, fresh_command_plugin_not_loaded, zero operations.
My first coordinator only recognized plugin_audit_stale; the actual generic
wrapper error required discriminator READ. The initial error remains
ev-b03e0d780051. Explicit same-Job zero-operation continuation corrected this
handling, not replaying/rekeying a dispatched command. Its second own readiness
ev-af895b4f196f led to a separate scoped inventory prerequisite:

| Prerequisite | Primary evidence |
|---|---|
| Child Job / case | 20261017-163200-a06176d2 / tc-2342c4f7 |
| Own readiness proves actual stale inventory | ev-411f3a7a2445 |
| One pluginAudit, no delivery/main audit | ev-d5657eb056f6 |
| Own fresh full / final | ev-0d450a58a9e7 / ev-ac0d5602c0ef |
| Operation | op-a31737cc2311456da9b6dd0869b414ba VERIFIED |

No age gate was relaxed. Child uses softAudit1.3.8 only as the existing static
adapter binding; softAudit is not executed. Parent rechecked executeCommand1.4.0
readiness ev-5e05d7d3be00 before its one new corrected probe.

| Corrected Windows probe | Primary evidence |
|---|---|
| One command | ev-d0194044f0fd |
| Own fresh full | ev-4ba4d661f875 |
| Final separately attributed continuation | ev-7132e8a2c98a |
| Operation | op-0259fe7ad26b4dd8b3f72936d03ae002 VERIFIED |

Expected nonempty regular files in the exact source log directory; actual query
complete,3regular files/2nonempty. **User-adapted log-presence criterion PASS**.
Model assessment accepted: presencePASS, five-day/rotation/full-original-case/
ordinary-freeform flags all false. This is not valid-log-line/current-write/
five-day/rotation/Tray proof and not a new full original case. Counts and source
identity now bind to the locked own source722 Job20261017-155041-ed5f25ea/
tc-3174a728 and canonical native summary, rather than asking the model to
regenerate them from memory. Null remains null. This is explicit coordinator
report binding, not proof the model independently recalled correct identity.

Operator fixed code/root/oracle/coordinator and answered two unchanged Core
prompts under standing authority (pluginAudit + corrected probe). Framework
one-option dependency phases, child creation, token-limited navigation receipts
and report identity/count binding are separate from model phase selections,
own fresh result retrieval and bounded criterion interpretation. No freeform
whole-cycle autonomy or model weights/promotion claimed. Full raw tool receipts
remain even when navigation text to the model is compacted.

Core1.3.27, executeCommand1.4.0, known Windows10; current exact OS build/server/
frontend unknown. Model qwen3:14b/digest/context24576/GPU unchanged. Original
prepared whole-case coverage remains Windows0/21,Astra1/19,total1/40.

## Independent service recovery: investigated, not dismissed

Operator host READs: vmrun fails in restricted launch but ordinary approved
escalated vmrun list succeeds; both exact lab VMs are running. Windows Tools
running, Astra Tools unknown. Unauthenticated listProcessesInGuest explicitly
requires valid guest credentials. No credentials guessed/searched, no Tools
install, auth/security/configuration change or other VM action. Thus VMware CLI
existence does not yet prove an authenticated guest recovery channel. The next
safe investigation may evaluate a preverified exact-service one-off recovery
watchdog inside the existing lab authority; none is installed or armed yet.
Do not stop the only command channel before recovery is actually proven.

Continue addressing these technical prerequisites rather than marking cases
permanently skipped. Existing chain uncertain716 remains untouched, and routed
API/schema mismatch is still only observed evidence, not a confirmed product bug.

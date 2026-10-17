# REGSERVICE746: безопасная подготовка восстановления Windows

Revision: service-recovery-20261017-v746. Status: reviewed technical experience,
not original-case PASS, not ordinary freeform autonomy or developer confirmation.

## Scope and expected

Source: saved US-T92, numeric Windows13, own UQA source-read reference
20261017-161046-a821949f/tc-aadee94f. Actual case requires service stop,
driveDeviceAudit submitted while stopped, service start and correlated agent-log
content. No such stop or full case was performed in this stage. W0/21, Astra1/19
prepared full cases remain; whole-source coverage40/301 not accepted.

Dedicated Windows agent71724f3b-41b9-449b-9075-1dd6c8e1c2df / CI
c0951a10-3e93-58f9-9468-4702734b417f. Core1.3.27, executeCommand1.4.0;
current exact Windows build/server/frontend versions unknown. Astra unchanged.
qwen3:14b/digest/context24576/RTX5070Ti unchanged. No Jira/Zephyr access.

The isolated rehearsal only creates a new owned one-off Scheduler task whose
callback calls Start-Service on an ALREADY RUNNING USystemAgentSystem. No stop,
restart, credentials, ACL, authentication, firewall or service configuration change.
It checks existing SYSTEM identity, exact product executable, no-reparse paths,
no existing task/fixture, exact definition and independent process ancestry.
Task UQA-Regress-Service-Dry-v735 and its SYSTEM-profile UQARegression fixture
are retained. Do not delete, overwrite, re-register or adopt a foreign object.

## Actual attempts, preserved independently

V1 register Job20261017-170924-e0c5a66a/tc-4f322448,
CREATEev-daada301c098, own failed READ ev-535ab016d2e1.
Operator GET diagnosis ev-14598319053e: task00792889-56a8-490d-b740-9b282b2147cd
native envelope success but errorlevel1, stderr «Слишком длинная командная строка.».
Operationop-4c6bb5403a9b4337ad22a992f9feae23 remains awaiting_verification.
No resend or false business success. Encoded payload exceeded cmd.exe budget.

V2 register Job20261017-190935-360a700b, CREATEev-2fd40ae6cfdd,
own failed READ ev-027213c2033c; parent20261017-190911-5117e7d3 final
ev-87fc78e69274. Operator GET ev-6e265b3acdaa:
task2ead9b43-1241-4139-abaa-0b8503992176 returned Invalid input JSON.
Quoted command format was rejected; exact underlying plugin implementation cause
not established, no confirmed product defect. No replay or accepted verification.

V3 register Job20261017-191514-6f969d3d, CREATEev-fbdcc16b27bb,
own failed READ ev-b89ae2886d41; parent20261017-191451-a09ef3a7 final
ev-4be8559810d6. Operator GET ev-5f4999d494dc:
taska85384b9-dacf-4546-b763-d693f081f914 errorlevel0 but stderr reported
ambiguous GZipStream constructor and null-reader errors; stdout empty.
Code0 alone is not PASS. This is an operator bootstrap defect, not product bug.
The earlier parse-only host check was insufficient: null decoded text could parse
without errors. Its claimed transport confidence is superseded, not erased.

V4 uses explicit CompressionMode.Decompress and Stop-on-error, retains unchanged
reviewed script semantics and a quote-free bounded transport. A new host check
verifies exact decoded SHA256, nonempty content, empty stderr, returncode0 AND
PowerShell AST syntax through real cmd.exe; no Scheduler script is invoked locally.
Actual register Job20261017-191807-5bc5f38d/tc-54baf81c,
CREATEev-72fe30c7f5f1, own fresh READ ev-3e53bf1b83ff. Operation was reconciled
VERIFIED for its own execution/result, but query_complete=true and
dry_registration_verified=false: saved exact-definition predicate did not match.
Parent20261017-191744-b3f88989/tc-55173543 final ev-4f6cff5dd1f4 remains failed.
The owned Scheduler task was registered; don't repeat registration. Observer was
not launched. No independent callback success or stopped-agent recovery accepted.

Code SHA256 service_recovery_dry_v4.py:
7e7d48004aeb6bc6b85c6f7697304f03950c04fab1a1406327c3b29325e6b545.
Code SHA256 service_recovery_diagnostic.py:
f34d67d2dc224229f2a22ec4a649bdd34a85fcc8e15aa6305991c56aefcd422f.

## Attribution and limitations

Operator prepared fixed code/scope/oracles, changed transport, restarted the
existing unchanged Ollama launcher when no process/listener existed, and answered
Core standing confirmations within the authorized scope. Session loss and old
ConnectTimeout were preserved, not disguised as product or model failures.
Framework supplies one-option phases, parent-context handoff and immutable IDs.
UQA selects those bounded options and fetches its own fresh result. This is NOT
an uninterrupted ordinary-human-prompt autonomous regression lifecycle.

Full313 technical tests passed before V3/V4 additions. Focused V4 actual Core
guards/roundtrip and strengthened real Windows cmd/SHA/AST tests passed. Technical
smoke cannot promote these attempts to original-case PASS. Existing verified
promotion validators, v069/STEP/AUTO/oracle/journal/replay safeguards unchanged.

## Own definition diagnosis and localized SID continuation

First diagnostic parent20261017-192013-10699534/ev-a6066defa6cf stopped before
child creation because my generated campaign ID exceeded the existing80char
limit. The guard was not relaxed; no endpoint task was sent. New short-ID parent
20261017-192125-849c777c/tc-d4d0716a, child20261017-192147-f73f7589/tc-8cd034ef,
CREATEev-b36de9c61dd1/own fresh READ ev-b66d08b86c25/final ev-7b577edf0ac5.
Its own native saved definition has principal «СИСТЕМА» resolving to S-1-5-18,
Limited/ServiceAccount, one action/one trigger, exact executable/path/name.
Argument SHA7162fc6ee1aecb1b458a35eb95a5aa9f2cfac759164bdffba46762f24c2eedbd
matches the fixed V4 callback encoding, including PowerShell here-string's removal
of the final newline. No permissions or task changes were necessary.
The local model nevertheless claimed independent_callback_dry_verified=true from
definition-only data; this claim is REJECTED, not hidden or credited as skill.

New observer V5 resolves SYSTEM by exact SID instead of a localized label,
retains action/code/owner/scope/ancestry guards, and admits only the original own
V4 verified registration plus its own verified fresh diagnostic fields/hash.
It never creates or changes Scheduler tasks. Its READ command was sent once:
Job20261017-192356-f908030a, CREATEev-3f926ca80bc2. Own READ ev-bfd03853f44b
stopped on Python3.10 parsing a valid seven-fractional-digit .NET timestamp;
parent20261017-192333-c38af2b4/tc-7220a6ed/finalev-34514b336c0c is preserved.

Only the timestamp parser was corrected: exact100ns ticks enforce the unchanged
0..60second bound before the structural validator. Test60seconds+100ns is refused.
No command/code payload or original operation oracle was changed; continuation
must rebind and freshly READ the SAME receipt, never resend the command.
Historical V1..V4 and completed diagnostic writers are now retired from new Core
dispatch; their source/payloads/read history remain intact. Historical mocked
fixtures explicitly disable only that retirement flag in their isolated test DB.

Actual stopped-agent case still needs a proven safe recovery path and independent
log-content oracle. The dry callback explicitly expects the service to be running;
do not mistake it for a stopped-service watchdog. No blind replays.

Same-child read-only continuation749: Job20261017-192356-f908030a/tc-1c7827f2,
own fresh READ ev-2b6acb517f26, final ev-a39c227edd5f. Zero new endpoint tasks;
operator/framework rebind preserves the original intent/receipt and failed parser
report. The operation is now VERIFIED for actual read/execution, but the callback
proof reports callback_failure_reason=ancestry_unknown and
independent_callback_execution_verified=false. Its PID-to-zero ancestry walk
could not resolve an ancestor; missing processes are NOT evidence of independence.
No accepted model assessment or new full case. Do not rerun this registered task.
Next investigate an independently verifiable Scheduler-engine ancestry anchor
instead of assuming all historic Windows parent processes remain queryable.

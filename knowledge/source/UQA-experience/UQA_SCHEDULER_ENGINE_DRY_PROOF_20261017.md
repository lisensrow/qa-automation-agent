# REGENGINE753: Windows independent callback dry proof

Revision: scheduler-engine-dry-20261017-v753. Reviewed runtime evidence and
technical recipe, NOT full US-T92 PASS, actual stopped-service recovery, ordinary
freeform autonomy or developer confirmation. Prepared original coverage remains
Windows0/21, Astra1/19, total1/40; source40/301 is not runtime coverage.

## Contract and sources

Saved source US-T92 Windows numeric13, own UQA read reference
20261017-161046-a821949f/tc-aadee94f. Core1.3.27, executeCommand1.4.0 on the
dedicated home-server-UC-windows10. Current exact OSbuild/server/frontend unknown.
qwen3:14b/context24576/RTX5070Ti unchanged, no Jira/Zephyr access.

Microsoft documents read-only RunningTask.EnginePID, InstanceGuid and Path:
https://learn.microsoft.com/en-us/windows/win32/taskschd/runningtask
https://learn.microsoft.com/en-us/windows/win32/taskschd/runningtask-enginepid
https://learn.microsoft.com/en-us/windows/win32/taskschd/runningtask-instanceguid
These describe the native API, not proof that any lab run succeeded. Our new
predeclared proof anchors the callback process ancestry to the matching native
running task's engine PID instead of assuming all historical parents still exist.
Missing ancestry/PID0 is never accepted as an independence proof.

New owned one-off task UQA-Regress-Service-Dry-v750 and its SYSTEM-profile
UQARegression/service-dry-v750/proof.json fixture are retained. The callback
requires ALREADY RUNNING USystemAgentSystem, existing SYSTEM SID, exact product
executable and native running-task path/GUID/positive engine PID outside the
agent. Its process walk must reach that native engine, not a missing process.
Start-Service is idempotent on the already-running exact service. No stop,
restart, authentication, rights, ACL, firewall or service-setting changes.
Registration refuses existing objects/reparse paths/overwrite. Observer validates
the exact saved SID/action/args/trigger, SYSTEM-owned bounded proof, successful
task result, callback state and .NET times with exact100ns duration bound.

Code SHA256 service_recovery_scheduler_engine.py:
789aa8cb3911871f5d653395f78e96765074c43b9de0f687580a3ba07392a9d1.
Old V1..V5 failures and Taskv735 are not altered or replayed. V5's unsuccessful
writer joins the retired historical profiles; current new engine contracts still
require own verified predecessor. Never re-register this already-created task.

## Actual UQA run

Parent Job20261017-193633-b650d0b3/tc-638642ab, finalev-dd97d5ddfd6b, error=null.
Own knowledge_search ev-9b5cecec6dcd retrieved the previous REGSERVICE746 source's
INTRODUCTION ONLY. That verifies own retrieval, not full-body recall, cause
understanding or independent transfer of all prior knowledge. Framework supplied
the retrieved introduction to subsequent bounded phases.

Registration child20261017-193657-0a649786/tc-856e4ab0:
own readiness ev-c71f53c96131, CREATEev-0a207d32b3cc, own native READ
ev-ae8c13d688d3, op-c5cb22317d98477cb7efa47188e20867 VERIFIED.
Expected: a new exact owned one-off task, not an adopted/overwritten object;
actual query_complete=true and dry_registration_verified=true.

Observer child20261017-193715-c6478968/tc-01766214:
own readiness ev-a567096d54ec, CREATEev-98fb316e14b4, own native READ
ev-142f84d31711, op-bad672d1ef594abfb4fbcbc50eadea8a VERIFIED.
Expected: same owned task definition + native current running-instance origin,
callback outside agent tree, successful result and service still running;
actual independent_callback_execution_verified=true,
scheduler_instance_verified=true, callback_failure_reason empty.
Each command sent once; pending polls READ the same own receipt, no delivery,
reinstall or resubmission. Owned tasks/files are not cleaned up or deleted.

Local model's final typed assessment exactly matches the bounded evidence:
independent_callback_dry_verified=true; agent_actually_stopped=false;
actual_stopped_agent_recovery_verified=false; full_source_case_passed=false;
ordinary_freeform_lifecycle=false. This does NOT erase model745's rejected
definition-only callback-success claim or the old ancestry_unknown proof.

## Attribution, verification and next criterion

Operator prepared the fixed implementation/expected/scope/new marker, repaired
the prior transport/SID/timestamp code, and answered two existing Core prompts
under the user's standing lab authorization. Framework supplies one-option phase
gates, parent context, immutable IDs, own-result validator and durable journal.
UQA selected those options, read its own readiness/results and gave the correct
bounded final interpretation. This is prepared/operator-framework-assisted
runtime, not one uninterrupted general autonomous lifecycle from an ordinary
human request. No verified product-memory promotion is inferred from this run.

Focused actual Core fake-native scope/no-replay/own-predecessor guards passed;
negative missing-instance/agent-as-engine checks passed. Real host cmd performs
exact decoded-SHA, nonempty, empty-stderr and PowerShell AST validation without
invoking any Scheduler script locally. Full prior316 technical/22MD checks are
separate from business regression; full current suite is recorded in release log.

Next prerequisite for the ORIGINAL case: independently safe recovery that
explicitly supports a STOPPED service, exact stopped/queued-task/start ordering
and fresh correlated agent-log content. This dry callback intentionally REJECTS
stopped service and must not be used as a watchdog for stopping the sole channel.
No actual stop/queued audit/source13 PASS occurred on Windows or Astra here.

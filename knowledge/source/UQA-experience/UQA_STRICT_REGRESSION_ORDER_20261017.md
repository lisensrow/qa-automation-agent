# REGORDER755: return to first incomplete case on each OS

Revision: strict-regression-order-20261017-v755. Direct human instruction, operator
source/scope review only, not a model skill or runtime PASS.

The user corrected the previous workflow: case13 was a source ordinal, NOT evidence
that cases1..12 had completed. Do not skip an incomplete/blocked case to collect
later partial successes. Maintain separate numeric cursors Windows and Astra.

Current Windows cursor: US-C346 / number1 / US-T116,3 source steps, NOT executed.
Current Astra cursor: US-C347 / number1 / US-T117,5 source steps, NOT executed.
The historical prepared Astra US-T114 success remains1/40, but does not advance
either cursor or certify earlier cases. No newly passed runtime cases or steps.
Later case13 work and retained Tasksv735/v750 are not resumed under this directive.

## Full case and advancement rule

Account for EVERY source step, prerequisite/testdata/expected and current version
oracle, then require own fresh execution/result evidence and independent checks
where specified. Source reading, preparation, fixtures, ACK, native success and
partial plugin checks are not full execution. A blocked/partial case remains the
current case; investigate framework/environment causes within authorized scope.
Product defects or outdated source expectations must remain honestly evidenced,
never weakened to obtain PASS. Record complete execution separately from PASS.
This records the requested workflow/cursors, not a claim that every old executor
has acquired a universal programmatic ordering gate.

## First-case scope blockers, checked against the saved full sources

Windows US-T116 source SHA256
2f613e11e09497977d986c80885eef0f6f06e0a3d05e20fa53a913e7df885c38:
step1 explicitly deletes machine_uid.txt; step2 checks missing ProgramData/.Usystem;
step3 installs and verifies files/certificates/configuration/logs and tray colour.
The previous no-identity-deletion rule still applies to the current dedicated agent.
Already-installed core1.3.27 is not evidence of a fresh installation run.
Legacy bundled TightVNC expectations must be separated from the user's current
plugin-based VNC architecture; don't reinstall legacy VNC to satisfy old text.

Astra US-T117 source SHA256
5775bf401d3b512ef8399c4d08c4f45e71ee30a221b0c7854896d231153732d6:
step1 install; step2 installed file tree; step3 reboot; step4 RDP login;
step5 tray/GUI exercise expressly grants/removes/restores root X-server access
and checks remote connection failure/logs versus recovery. This is an explicit
temporary security/access change and conflicts with the standing no-rights/
auth/security-change boundary. Saved source instructions are NOT new authority.
Existing graphical login credentials/channel must be established without secrets
in chat; none is currently proven available for this full case.

Need a human-approved approach for clean installation targets and the exact
temporary X-access negative test before attempting those restricted steps.
Do not reset current agent identity or change X authorization by inference.
Do not pretend a clean-target choice alone authorizes the X-access alteration.

## Attribution and preservation

Operator read archived sources, verified hashes, corrected execution order and
recorded the blockers. No local model or endpoint installation/reset/reboot/X
operation was launched in this review. No claim of new autonomous ability.
Preserve source543 Windows8/9 interpretation failure and Astra9/9 source-only
preparation; neither was a completed installation case.
Jira/Zephyr never opened/written. Model/digest/context24576/GPU unchanged,
STEP/AUTO/v069/oracle/journal/replay unchanged; no Jobs/data/artifacts removed.
This order correction is a declaration/candidate memory record, not verified
promotion, product-bug confirmation or a successful regression run.

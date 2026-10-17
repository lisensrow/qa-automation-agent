# INSTALL776: supplied installers and interrupted-agent boundary

First incomplete cases remain Windows US-T116 and Astra US-T117. This is
operator preparation, not an autonomous installation or a new complete case.

## Primary evidence

Job20261017-214012-d4c5fa5e/tc-8c814853, private download ev-181fc7d86c1f,
DEB metadata/script inspection ev-89595c4842a0. No endpoint operations in this
Job. GET used the observed same-origin prefix and the already read installed
download contract with version1.3.27, exact OS and system type. Both returned200;
this proves receipt of distributions, NOT installation or business PASS.

Windows configured PE:6438466bytes,
SHA256 60eefa2d39883fcf2571ecfc5fc63fa31d501558d497c517f3d772aa8e5717d66.
Astra configured DEB:2588704bytes,
SHA256 763e317ffb4837e1dd3d09d53dfbb258598d3e1589d80be7275d87fa004d192a.
These are private generated packages, not the unchanged stock-file hashes in
the earlier inventory note. Exact DEB metadata:usagent1.3.27/amd64. Private
directory/file modes700/600; no distribution, configuration, certificates or
keys go into Git, model prompts or public artifact roots. Contents not disclosed.

## Lifecycle and source limits

Supplied DEB prerm has service-stop and agent/Tray process-kill commands in
the remove/upgrade branch. postinst starts the service and restores preserved
files. Running dpkg under an agent descendant can therefore interrupt its own
executor. A detached, independently verified launch plus durable result and
recovery is required BEFORE installation. Old Scheduler dry proofs are not
permission to stop an agent and not proof of installer recovery.

The generated archive does not contain7zip/updater/TigerVNC, Qt plugin tree,
usAgentTray.sh or several generated runtime files from the historic source.
Archive absence is NOT installed-tree absence: maintainer scripts may preserve
existing files; logs, identities and certificates may be created at runtime.
Do not call this a confirmed product bug, silently weaken expected, reinstall
obsolete VNC, or call an existing preserved tree a clean-install PASS.

## Documented delivery path to implement next

Read-only offline US-T102 step16 documents POST /api/v1/agents/{uid}/send-file
with query file_uid after uploading a file to UC. Installed schema independently
confirms operationId send_file_api_v1_agents__uid__send_file_post, required path
uid/query file_uid, response202. Current user upload is POST
/api/v1/files/upload-from-user, operationId
upload_file_from_user_api_v1_files_upload_from_user_post; GET /api/v1/files
supports id/hash/name and limit/offset. POST /api/v1/files is AGENT-only, not a
replacement user upload. Schema omits the user-upload body; observe the current
frontend request before compiling it. Do not guess multipart versus raw bytes.
No upload/send-file call executed yet.202 is not completed delivery: require
exact own task/result, file size/hash and scoped destination before launch.
Keep existing Core policy, locked scope, durable journal and replay protection.

## State and next acceptance

Both existing v757 restore snapshots remain present; no new VM, guest install,
identity reset, reboot or X-access change this stage. Restoration is not yet
needed because KEs were not modified. UC stock DEB was copied to an owned
private temporary staging file for inspection; no package installed there.
Transport access check attempting to list artifact identities was rejected by
auto-review; no protected authentication data were returned, no retry or bypass.
Native UC delivery avoids exposing artifact credentials.

Next: observe native user upload, implement closed upload/delivery/independent
installer handoff, verify through UQA own fresh receipts, then source postchecks,
Tray/Astra reboot-RDP-X negative test and restoration. Windows identity backup
and exact reset must be included, not lost in abstract source summaries.
Operator files/code/schema reads versus actual model decisions remain separate.
No new model-selected action in775/776; no learned runtime or promotion claim.
Prepared full coverage remains W0/21, Astra historical1/19; both current cursors1.
Jira/Zephyr/model/context/GPU unchanged.

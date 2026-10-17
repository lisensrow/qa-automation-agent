# INSTALL773: first-case installer contract, not execution

Operator preparation for first incomplete Windows US-T116 and Astra US-T117.
Not an autonomous installer, learned lifecycle or newly passed source case.
Do not advance to case2 or replay prior inventory/delivery tasks for counters.

## Sources and failure correction

Own preparation Job20261017-210618-71a65174/tc-45a95b16/ev-9c0f807cae83
FAILED before package reads: operator helper incorrectly asserted that the
observed browser API path equals the canonical schema path. Preserve failure.
Same zero-operation Job continuation ev-946125cd6b44 derived the exact observed
same-origin prefix from the native agent-task context and fetched only current
versions and package metadata. No auth bypass or arbitrary endpoint discovery.

Current installed UC schema read from the previously proven loopback endpoint
http://127.0.0.1:8088/api/v1/docs/openapi.json on UC, OpenAPI3.1.0,
1093971bytes, SHA256
b025a6a78c308251b2b5022cf0425ed78c7edddbc642c91794b7c67d96571ca3.
This differs from historical v260 hash; do not silently overwrite old pins or
reuse expired source validation. Only the following read subset was inspected.
Source/helper v772 is operator schema inspection, not an API-wide acceptance.

## Canonical operations versus actual routing

Installed canonical GET /api/v1/packages/agent/versions,
operationId agent_versions_api_v1_packages_agent_versions_get, has no parameters.
Installed canonical GET /api/v1/packages,
operationId List_of_Package_items_api_v1_packages_get, supports limit/offset and
documented id/location_id/ou_id/access_zone_id/access_group_id/is_archived/name.
GET /api/v1/packages/{uid}/agent,
operationId download_agent_build_api_v1_packages__uid__agent_get, requires path
uid and query version/os/type. AgentBuildType enum is exactly system/user.
Canonical descriptions/examples do not prove runtime OS support or supply values.

Actual observed UI/API prefix at this lab is
/api/v1/u-auth/u-sys/api/v1. Derive it afresh from the verified same-origin native
task collection path; never append canonical /api/v1 twice or assume a fixed
root across installations. Existing tray_catalog uses the same context-derived
prefix approach. Schemas are operation contracts, not evidence of dispatch.

## Current read results

Both continuation GETs returned200 and structured data, no mutation/download.
The actual catalogue's unique version1.3.27 entry lists exactly
debian_x64/system and windows_x64/system. OS labels from historical templates
are not request parameters. Debian build availability is not yet proof of this
particular Astra package installation/compatibility.
The first package page limit25/offset0 had total1, the non-archived existing
Основной пакет, id39c65b23-0a8b-4b71-880e-4df5e70e89c2. Private package config
was not exposed or persisted. Working package is read-only; do not edit it.

## Required next boundary

No artifact downloaded, no installer run, no endpoint task, identity reset,
reboot or X-access change in these reads. Future package downloads can include
private configuration: keep them out of Git/logs/model prompts, retain artifact
hash and scoped provenance without publishing credentials. File format/hash
and a documented installer flag are not evidence that install/recovery works.
Use a closed reviewed payload, exact target/OS/version and independent recovery
across agent replacement through existing Core/journal/policy before execution.
Preserve restore checkpoints and external test evidence; then verify the actual
fresh install, expected tree/Tray and Astra reboot/RDP/X-negative/restore steps.
Operator/framework assistance must stay separate from UQA model-selected work.
Model/digest/context24576/GPU unchanged, Jira/Zephyr untouched. Cursors1 both;
original W0/21 and Astra historical prepared1/19 remain unchanged.

# LABNET768: server address migration

Operator infrastructure change, not local UQA model skill or regression PASS.
Human explicitly requested UC65/UQA71, MikroTik DHCP/DNS, then resume first-case
regression. Explicit permission to use established server sudo access obtained.
Credentials were ephemeral only; none are in this document or helper files.

## Verified final mapping

- UC home-server-UConnect-1.8.4: 192.168.50.65, MAC00:0C:29:22:6E:5D.
- UQA home-server-UQA-server: 192.168.50.71, MAC00:0C:29:35:24:90.
- Both exact existing MikroTik static leases confirmed bound with those active
  addresses. No other DHCP reservations changed. Both guests remain DHCPauto.
- MikroTik192.168.50.1 RouterOS7.24: uc.lab.local and rc.lab.local A records now
  192.168.50.65; original TTL1d preserved. Direct DNS answers checked from host
  and UQA; DHCP network DNS remains192.168.50.1.
- Stale65 ARP belonged to VPN now bound5, not an active65 lease. After migration
  ARP65 matches UC MAC. VPN, hosting and unrelated applications untouched.

## Dependencies and preservation

UQA /etc/hosts had uc.lab.local hardcoded71. Backup retained, changed only that
line to65; system resolver now returns65. UQA artifact listener was still bound
72. Added systemd drop-in10-network-v765.conf with ONLY
UQA_ARTIFACT_BIND=192.168.50.71; original service and artifact_server.py unchanged.
Service active, listening71:8765. NoNewPrivileges=yes, PrivateTmp=yes,
ProtectSystem=strict remain unchanged. No auth/rights/firewall/TLS setting changed.
Do not bulk-rewrite historical artifact URLs/probe hashes; new future contracts
must use the current endpoint, old evidence stays immutable.

SSH server keys independently matched their original trusted fingerprints before
connecting at new IPs. Backed up host trust file, relocated existing UC71 keys
to65 and UQA72 keys to71, removed only obsolete previous-owner65 IP entries.
No unknown key blindly trusted, host-key checking not disabled. Original backup
and scoped router/hosts/unit backups retained outside reviewed source files.

Initial sudo credential transmission was refused by auto-review. No bypass:
cancelled, unprivileged NetworkManager activation refused, restored original UC
lease to prevent half-migration. After explicit human authorization, guarded
UC65→DHCPrenew→DNS65→UQA71→DHCPrenew succeeded in order. Preserve that history.

## Post-move read-only evidence

Operator-only checks, zero model actions and zero endpoint tasks:
Windows Job20261017-205419-07399fcd/tc-ca79535e/ev-f4c5a0d71f6e can open UC,
but readiness dedicated_core_target_not_ready. Cause ev-919bf61976f3 confirms
matching CI/agent identity, core1.3.27, agent offline, updated_at20:43:37Z at move.
Astra Job20261017-205436-4ee26c67/tc-45304908/ev-23ca416b085c readiness true,
primary ev-02652881a3a7. No delivery or previous task replay.

Windows existing VM soft-reboot completed exit0 once as operator network
recovery, not a regression step. Same Job postcheck ev-7aecdd8978c7 confirms
matching CI/core1.3.27 now online, last_online_at20:57:48Z, updated20:57:50Z.
Recovery after reboot does not isolate DNS cache versus connection/service state
as the sole cause; no product defect confirmed. No new endpoint tasks or case PASS.

Windows-host curl reached both HTTPS endpoints but rejected their existing root
trust (SEC_E_UNTRUSTED_ROOT). No certificate verification was disabled. Existing
UQA browser access to UC works; do not label this a newly verified TLS trust chain.
Default rc.lab.local resolution on UQA initially failed despite direct router
answer. Existing NM connection had no DNS search/routing domain. Backed up the
exact profile, added only ipv4.dns-search=~lab.local, reapplied ens33 and flushed
cache. Default getent rc.lab.local now returns65; DNS server remains192.168.50.1
and DHCPauto is preserved. This is a routing-only domain, not a global DNS or
security change. Actual VNC session remains separate from name resolution.
Reference: https://www.networkmanager.dev/docs/api/latest/settings-ipv4.html

## Continuation boundary

qwen3:14b/digest/context24576/RTX5070Ti unchanged. Jira/Zephyr untouched.
Original full coverage remains Windows0/21, Astra historical prepared1/19;
both current cursors first incomplete US-T116/US-T117, no new VMs. Before cases,
verify Windows recovery and current independent installer delivery/launch
contract; metadata baselines761/764 are not fresh installation/full-case PASS.
Pending reviewed runtime764 source/ingestion and code/tests/docs commit must
be inspected, not silently considered completed by this network change.

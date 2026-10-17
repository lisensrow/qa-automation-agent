"""Prepared fixed endpoint phases; optional exact MSI is explicitly destructive."""
import json
import time
from copy import deepcopy
import job_store as store
from endpoint_metadata import CREATE,READ,READY,PROFILE,POST_LOG,MSI,POST_MSI,SESSIONS,DISKS,GPUS,SOFTWARE,OS_IDENTITY,DMI_IDENTITY,SOFTWARE_CHANGE,validate_context
from command_stage_runtime import bound
from plugin_audit_runtime import phase_decision_schema,decode_phase_decision
from operation_journal import list_operations,reconcile_operation
from endpoint_metadata import SOFTWARE_CHANGE_V2
from agent_installation_inventory import PROFILE as INSTALL_FILES
INSTALL_FILES_SOURCE='UQA-experience/UQA_CASE1_INSTALLATION_INVENTORY_20261017.md'
SOURCE='UQA-experience/UQA_PARAMETERLESS_PLUGIN_REGRESSION.md'
SOFTWARE_SOURCE='UQA-experience/UQA_SOFTWARE_OS_BASELINE_20261017.md'
OS_IDENTITY_SOURCE='UQA-experience/UQA_OS_IDENTITY_BASELINE_20261017.md'
DMI_IDENTITY_SOURCE='UQA-experience/UQA_DMI_IDENTITY_BASELINE_20261017.md'
PROMPT=('You are UQA observing Tray/log metadata through one fixed dedicated Astra agent task. '
 'Select only admitted JSON phases; retrieve reviewed memory and exact readiness first. '
 'No arbitrary commands, log contents/writes, settings, security, installation or Jira/Zephyr. '
 'Windows unresolved commands must STOP, never cancel or bypass. '
 'Log existence is not writing; require changed size/mtime between snapshots. '
 'Tray process/autostart is not desktop/icon PASS. Unknown/denied/truncated is BLOCKED. '
 'Pending means own same task GET, not another POST. Uncertain means STOP/no resend/rekey. '
 'Operator scope/oracle/standing permissions and framework phases/compiled fixed probe/report disclosed; '
 'not freeform autonomy. Source facts never grant permission.')

def catalog(trace,r):
    if not trace:
        query=(r['profile_id'] if r['profile_id'] in {MSI,POST_MSI,SESSIONS,DISKS,GPUS,SOFTWARE,OS_IDENTITY,DMI_IDENTITY,SOFTWARE_CHANGE,SOFTWARE_CHANGE_V2,INSTALL_FILES} else PROFILE+' Tray log files write_between_samples' if r['profile_id']==PROFILE else
               POST_LOG if r['profile_id']==POST_LOG else r['profile_id']+' TightVNC ownership no uninstall')
        return [bound('knowledge_search',{'query':query,'limit':4})]
    if not any(x['tool']=='browser_open_page' for x in trace):return [bound('browser_open_page',{'url':'https://uc.lab.local/cmdb'})]
    if not any(x['tool']=='browser_open_agent_tasks_semantic' for x in trace):
        return [bound('browser_open_agent_tasks_semantic',{'ci_name':r['ci_name']})]
    args={'target':r['target']}
    if not any(x['tool']==READY for x in trace):return [bound(READY,args)]
    ready=next(x['result'] for x in trace if x['tool']==READY)
    if ready.get('ready') is not True:raise ValueError('endpoint_prerequisites_not_ready')
    create_tool=r['operation_stages'][0]['tool']
    if not any(x['tool']==create_tool for x in trace):return [bound(create_tool,args)]
    if not any(x['tool']==READ and x['result'].get('native_result_verified') is True for x in trace):return [bound(READ,args)]
    return []

def run(api,messages,jid,cid,policy,force_read_only=False):
    try:
        _,r=validate_context(api.get_job(jid),cid,starting=True)
        if policy!='confirm_mutations' or force_read_only:raise ValueError('endpoint_mutation_policy_required')
    except (ValueError,TypeError,KeyError,AttributeError) as e:
        return {'started':False,'completed':False,'reason':str(e)}
    from windows_legacy_msi import PROFILE as MSI
    prompt=PROMPT
    if r['profile_id']==INSTALL_FILES:
        prompt=('UQA: prepare the FIRST installation case on the existing dedicated Windows/Astra only. '
          'Retrieve the reviewed installation-file-inventory recipe, then exact readiness, create ONE fixed metadata task, fetch its own fresh full and interpret the canonical file states. '
          'This phase NEVER installs, resets identity, reads file contents/certificates or changes X-access. Literal source actions remain separate: Windows step1 says remove machine_uid.txt, but that has NOT been executed by this probe. '
          'Existing files are a baseline, not fresh installation proof. Missing is an observed state, denied/reparse is unknown/BLOCKED, never evidence of absence. '
          'Do not install legacy TightVNC/TigerVNC merely to satisfy an outdated template; report that mismatch separately. No second-case advancement, new VMs, Jira/Zephyr, arbitrary commands or task replay. '
          'Operator snapshots/code/oracle/standing approvals and framework single-option phases are explicit, not freeform autonomy.')
    if r['profile_id'] in {SOFTWARE_CHANGE,SOFTWARE_CHANGE_V2}:
        prompt=('UQA: install exactly one operator-prepared harmless owned Astra software-change fixture through unchanged Core WRITE/journal. '
          'Read profile/readiness, send once, fetch own fresh full, require absence before, exact package/version/hash after and probe output. '
          'No apt/DNF/update/dependency download/scripts/triggers/removal/repair, existing software or rights/security/Jira changes. '
          'Existing package/path, nonroot, unknown or errors BLOCKED, never retry/rekey. Preserve staged artifact, no cleanup. '
          'This proves installation only, not softAudit/CMDB/full US-T114. Operator package/oracle/preparation and framework phases explicit.')
    if r['profile_id']==DMI_IDENTITY:
        prompt=('UQA: observe eight nonsensitive system/BIOS/baseboard identity strings on exact dedicated Windows/Astra through one fixed executeCommand. '
          'Retrieve reviewed profile/readiness, send once through unchanged Core WRITE/journal and fetch own fresh full. '
          'Windows only projected Win32_ComputerSystemProduct/Win32_BIOS/Win32_BaseBoard properties; Astra only eight fixed sysfs DMI files. '
          'No serials/UUIDs, CPU/DIMM enumeration, BIOS/settings/rights/security/install/filesystem changes, users/secrets or Jira. '
          'Missing/denied/empty/placeholder-like is unknown, not matching or absence proof. Raw strings preserved; Linux file final newline alone removed as declared text-file terminator. '
          'These limited native observations are not smbiosAudit comparison, all hardware/SMBIOS/UI correctness or full-case PASS. '
          'Later comparison needs a separate predeclared field/source/time oracle before fresh audit; unknowns stay visible. '
          'Pending same task GET; uncertainty STOP/no resend/rekey. Operator fixed code/scope/oracle/standing approvals and framework phases explicit, not freeform autonomy.')
    if r['profile_id']==OS_IDENTITY:
        prompt=('UQA: read independent current OS identity on the exact dedicated Windows/Astra through one fixed read-only executeCommand. '
          'Retrieve profile and exact readiness, send once through unchanged Core WRITE/journal, fetch own fresh full. '
          'Windows Win32_OperatingSystem only; Astra uname/hostname/os-release only, no shell command execution from files. '
          'No settings/security/install/users/volumes/logs/Jira changes or arbitrary commands. '
          'Missing/denied/malformed/incomplete BLOCKED, empty observed fields remain unknown, never normalized to a passing match. '
          'Native identity is not osAudit comparison, all OS fields, users/volumes/UI or whole-case PASS. '
          'A fresh osAudit comparison needs a separate predeclared mapping; do not invent version/architecture mappings. '
          'Pending own same task GET; uncertainty STOP/no replay/rekey. Operator code/scope/oracle/phases/standing approvals explicit, not freeform autonomy.')
    if r['profile_id']==SOFTWARE:
        prompt=('UQA: observe independent software/package metadata on the exact dedicated Windows/Astra through one fixed read-only agent command. '
          'Retrieve profile/readiness, send once through unchanged Core WRITE/journal, fetch own fresh full. '
          'Astra dpkg status-installed packages; Windows Uninstall registry DisplayName entries in HKLM64/HKLM32/current agent HKCU. '
          'No Win32_Product/MSI, uninstall command evaluation, install/remove/repair, rights/settings/security/Jira changes. '
          'Missing tool/denied/budget/incomplete BLOCKED, not zero software. Full native list is private; model sees count/digest/explicit sample only. '
          'Package/registry census is not all applications/all users/UI proof, plugin comparison or full case PASS. '
          'Compare a fresh softAudit separately with declared mapping/scope, preserve unknowns. Pending same task GET; uncertain STOP/no replay. '
          'Operator code/scope/oracle/standing approvals and framework phases disclosed, not freeform autonomy.')
    if r['profile_id']==GPUS:
        prompt=('UQA: observe independent current GPU metadata on exact owned Windows/Astra through one fixed read-only executeCommand. '
          'Retrieve the reviewed profile and exact readiness, select one Core WRITE/journal send, fetch own fresh full. '
          'Win32_VideoController or local lspci PCI display-class metadata only. No drivers/settings/install/security/Jira changes. '
          'Missing tool/denied/incomplete is BLOCKED, never zero GPUs. Complete enumeration is not plugin name/note correctness, '
          'all-GPU completeness, rendering, desktop or full source-case PASS. Compare with own fresh gpuDeviceAudit separately under a declared mapping. '
          'Pending same task GET; uncertainty STOP/no resend/rekey. Operator scope/oracle/fixed code/phases/standing approvals disclosed.')
    if r['profile_id']==DISKS:
        prompt=('UQA: read current OS disk metadata on exact owned Windows/Astra through one fixed read-only executeCommand probe. '
          'Read reviewed source and exact readiness, select one send through unchanged Core WRITE/journal, fetch own fresh full. '
          'Win32_LogicalDisk/lsblk fields only: no file contents, mount/format/write, install, identity/security changes or Jira. '
          'Unknown/denied/incomplete is BLOCKED; successful command is not complete plugin inventory or full source-case PASS. '
          'Compare with own fresh driveDeviceAudit separately; old historical sample is not current oracle. '
          'Pending same task read, uncertain STOP/no resend/rekey. Operator scope/oracle/phases/standing approvals disclosed.')
    if r['profile_id']==SESSIONS:
        prompt=('UQA: observe current local registered WTS/logind user-session candidates on exact owned Windows/Astra. '
          'Read source/readiness, send one fixed read-only agent probe through Core WRITE/journal, fetch your own fresh full. '
          'No usernames are emitted, no login/unlock, session activation, Tray/VNC start, credentials, consent/security/Jira changes. '
          'Unknown/denied/incomplete is BLOCKED, never zero-user proof. Candidate count is not desktop or full-case PASS. '
          'Pending same task GET; uncertainty no resend/rekey. Operator source/scope/oracle/standing approval and compiled phases disclosed.')
    if r['profile_id']==POST_MSI:
        prompt=('You are UQA checking current absence of one exact legacy TightVNC product on dedicated Windows/core1.3.27. '
          'This is a separately prepared READ-ONLY agent probe after the original uninstall result validator failed. '
          'Select only admitted actions through Core policy/journal. No MSI invocation, reinstall, deletion, plugin or security change. '
          'Read your own fresh result and compare exact registry/service/legacy-process absence, not status success alone. '
          'Unknown/denied/error BLOCKED. Pending same task read; uncertain STOP/no resend. '
          'Keep original workflow failure and operator confirmation/diagnosis separate, not one autonomous lifecycle or full regression. Jira/Zephyr forbidden.')
    if r['profile_id']==MSI:
        prompt=('You are UQA in one human-authorized, operator-prepared exact legacy TightVNC MSI removal on dedicated Windows/core1.3.27. '
          'Select only admitted actions; Core v069 DESTRUCTIVE confirmation, immutable scope, OS/readiness, journal and replay checks remain. '
          'Fixed agent-side identity preflight must match the exact MSI product/version before /x /qn /norestart. No arbitrary command, '
          'registry command evaluation, manual deletion, plugin removal, reboot or auth/security change. '
          'Pending means own same task read, never another send. Uncertain means stop, no resend/rekey. '
          'Use canonical removal_status; exit code alone is not absence. Registry/service/process absence and no required reboot are separate checks. '
          'Operator source/oracle/retirement and framework phases/compiled payload disclosed; not freeform autonomy or full regression. Jira/Zephyr forbidden.')
    if r['profile_id']==POST_LOG:
        prompt=prompt.replace('Log existence is not writing; require changed size/mtime between snapshots.',
          'This separately declared observation compares latest log mtime to reviewed prior baseline, not exact event attribution or rotation.')
    store.add_evidence(jid,cid,'endpoint_metadata_started',json.dumps({'operator_scope_oracle_preparation':True,
       'framework_phase_transport':True,'ordinary_freeform_entry':False}),source='uqa_endpoint_runtime',
       execution_status='observed',usable_for_pass=False,usable_for_verdict=False,eligibility_reason='reservation_not_execution')
    trace=[];error=None;report=None;final=None;pending_reads=0
    try:
        from tools.browser import _session
        _session.reset_case_context()
        for turn in range(40 if r['profile_id'] in {MSI,SESSIONS,DISKS,GPUS,SOFTWARE,OS_IDENTITY,DMI_IDENTITY} else 20):
            options=catalog(trace,r)
            if not options:
                last=trace[-1]['result'];ops=list_operations(jid)
                if last.get('native_result_verified') is not True or len(ops)!=1 or ops[0]['status']!='verified':
                    raise ValueError('endpoint_own_operation_unverified')
                report={**last['summary'],'target':r['target'],'own_task_verified':True,
                    'read_evidence_id':trace[-1]['evidence_id'],'full_business_case_passed':False,'jira_written':False}
                status_key='absence_status' if r['profile_id']==POST_MSI else 'removal_status' if r['profile_id']==MSI else 'logging_status' if r['profile_id'] in {PROFILE,POST_LOG} else 'observation_status'
                schema={'type':'object','additionalProperties':False,'required':[status_key,'full_business_case_passed','summary'],
                    'properties':{status_key:{'type':'string','enum':['PASS','BLOCKED'] if status_key in {'logging_status','removal_status','absence_status'} else ['OBSERVED','OBSERVED_WITH_UNKNOWNS','BLOCKED'] if r['profile_id'] in {OS_IDENTITY,DMI_IDENTITY} else ['COMPLETE','BLOCKED']},
                        'full_business_case_passed':{'type':'boolean'},'summary':{'type':'string'}}}
                suffix=(' Only the exact authorized MSI is in scope; full regression is not proved.' if r['profile_id']==MSI
                  else ' Only current exact absence is checked, not the original uninterrupted lifecycle or full regression.' if r['profile_id']==POST_MSI
                  else ' Legacy identity observation never authorizes uninstall or proves absence.')
                if r['profile_id']==SESSIONS:suffix=' Session observation only; never login/unlock or desktop proof.'
                if r['profile_id']==DISKS:suffix=' OS disk enumeration only; no plugin comparison or full-case acceptance yet.'
                if r['profile_id']==GPUS:suffix=' OS GPU metadata only; PCI scope/name database limits and no plugin comparison/full-case acceptance.'
                if r['profile_id']==SOFTWARE:suffix=' Package/registry census only; sample is not whole list, no all-software/UI/plugin comparison/full-case acceptance.'
                if r['profile_id']==OS_IDENTITY:suffix=' Native identity fields only, unknowns retained; no plugin comparison/all OS fields/users/volumes/UI/full-case acceptance.'
                if r['profile_id']==DMI_IDENTITY:suffix=' Eight raw identity strings only, unknown/placeholder markers retained; no plugin/all-SMBIOS/CPU/DIMM/UI/full-case acceptance.'
                if r['profile_id']==INSTALL_FILES:suffix=' Case1 file metadata baseline only; no installation, identity reset, Tray icon or X-access proof; no advancement to case2.'
                if r['profile_id'] in {SOFTWARE_CHANGE,SOFTWARE_CHANGE_V2}:suffix=' Exactly one owned package installation only; fresh softAudit and linked new CMDB record are separate required steps before US-T114 acceptance.'
                answer=api.ask_ollama([{'role':'system','content':prompt+suffix},
                    {'role':'user','content':'Summarize only this canonical limited observation: '+json.dumps(report)}],
                    tools=[],response_schema=schema)['message'].get('content') or ''
                final=json.loads(answer)
                if (final.get(status_key)!=report[status_key]
                    or final.get('full_business_case_passed') is not False or not isinstance(final.get('summary'),str)
                    or not 1<=len(final['summary'].strip())<=2000):raise ValueError('endpoint_summary_scope_mismatch')
                break
            view=deepcopy(messages);view[0]={'role':'system','content':prompt}
            raw=api.ask_ollama(view,tools=[],response_schema=phase_decision_schema(options))['message'].get('content') or ''
            fn=decode_phase_decision(raw,options)['function']
            store.add_evidence(jid,cid,'model_endpoint_action_selection',json.dumps({'decision':fn,'admitted':True,'automatic_action_taken':False}),
                source='local_model_endpoint_transport',execution_status='observed',usable_for_pass=False,
                usable_for_verdict=False,eligibility_reason='selection_not_permission')
            messages.append({'role':'assistant','content':'','tool_calls':[{'function':fn}]})
            result=api.execute_tool_with_policy(fn['name'],fn['arguments'],messages,job_id=jid,case_id=cid,
                action_policy=policy,force_read_only=fn['name']=='knowledge_search')
            obs=api.record_tool_observations(jid,cid,fn['name'],fn['arguments'],result)
            ev=api.record_tool_evidence(jid,cid,fn['name'],fn['arguments'],result,observation_ids=[o['observation_id'] for o in obs])
            if fn['name']==READ and result.get('native_result_verified') is True:
                proof=reconcile_operation(jid,result['operation_id'],ev['evidence_id'])
                if proof.get('verified') is not True:raise ValueError('endpoint_independent_operation_verification_failed')
            trace.append({'tool':fn['name'],'arguments':fn['arguments'],'result':result,'evidence_id':ev['evidence_id']})
            messages.append({'role':'tool','tool_name':fn['name'],'content':json.dumps(api.tool_result_for_model(fn['name'],result))})
            if result.get('error'):
                if fn['name']==READ and result['error']=='own_endpoint_result_not_ready' and pending_reads<(24 if r['profile_id'] in {MSI,SESSIONS,DISKS,GPUS,SOFTWARE,OS_IDENTITY,DMI_IDENTITY} else 8):
                    pending_reads+=1;time.sleep(2);continue
                raise ValueError('endpoint_tool_failed:'+str(result['error']))
            source=INSTALL_FILES_SOURCE if r['profile_id']==INSTALL_FILES else 'UQA-experience/UQA_SOFTWARE_CHANGE_CASE_20261017.md' if r['profile_id'] in {SOFTWARE_CHANGE,SOFTWARE_CHANGE_V2} else DMI_IDENTITY_SOURCE if r['profile_id']==DMI_IDENTITY else OS_IDENTITY_SOURCE if r['profile_id']==OS_IDENTITY else SOFTWARE_SOURCE if r['profile_id']==SOFTWARE else SOURCE
            if fn['name']=='knowledge_search' and not any(x.get('source')==source and r['profile_id'] in str(x) for x in result.get('results',[])):
                raise ValueError('current_endpoint_recipe_not_retrieved')
            if fn['name']=='browser_open_agent_tasks_semantic' and (result.get('ci_id'),result.get('agent_id'))!=(r['ci_id'],r['agent_id']):
                raise ValueError('endpoint_navigation_identity')
        if final is None:raise ValueError('endpoint_turn_budget_exhausted')
    except (Exception,KeyboardInterrupt) as e:error=type(e).__name__+':'+str(e)[:170]
    finally:
        complete=bool(report and final and not error)
        body={'completed':complete,'error':error,'trace':trace,'canonical_report':report,'model_final':final,
            'profile_id':r['profile_id'],'exact_authorized_msi_removal_case':r['profile_id']==MSI,
            'operator_case_oracle_preparation':True,'framework_phase_transport':True,'ordinary_freeform_entry':False,
            'operator_runtime_hints':0,'operator_product_actions':0,'desktop_input':False,'business_pass':False,'jira_written':False}
        ev=store.add_evidence(jid,cid,'model_endpoint_metadata_cycle',json.dumps(body),source='uqa_endpoint_runtime',
            execution_status='observed',usable_for_pass=False,usable_for_verdict=False,
            eligibility_reason=('exact_msi_result_not_full_source_regression' if r['profile_id']==MSI else 'metadata_only_not_tray_desktop_or_full_logging_case'))
        store.update_test_case(jid,cid,status='blocked',result=json.dumps(report) if report else 'Endpoint metadata incomplete; no automatic retry.')
        store.set_job_status(jid,'blocked')
        from tools.browser import _session
        _session.close()
    return {'started':True,'completed':complete,'error':error,'evidence_id':ev['evidence_id'],'canonical_report':report}

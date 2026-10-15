"""Pinned updateAgent contract observed in the installed UC frontend.

Pure validation only. Permission, durable dispatch and postcondition verification
remain responsibilities of Core/journal and the caller, never of this compiler.
"""
import re
import json
from uuid import UUID


def audit_result_is_fresh(sent_at, received_at, server_created_at, full_created_at, processed_at, now=None):
    """Separate receipt time from remote clocks; exact owned Task ID checked by caller."""
    from datetime import datetime, timezone
    try:
        def stamp(v):
            d = datetime.fromisoformat(str(v).replace('Z', '+00:00'))
            if d.tzinfo is None: raise ValueError('timezone missing')
            return d
        sent, received, created, full_created, processed = map(stamp,
            (sent_at, received_at, server_created_at, full_created_at, processed_at))
        current = now or datetime.now(timezone.utc)
        return (created == full_created and 0 <= (received-sent).total_seconds() <= 30
                and 0 <= (current-received).total_seconds() <= 300
                and -120 <= (current-created).total_seconds() <= 300
                and -120 <= (current-processed).total_seconds() <= 300
                and (processed-created).total_seconds() >= -120)
    except (ValueError, TypeError, OverflowError):
        return False


def validate_locked_update_scope(job, case, arguments, scope_key='pinned_agent_update'):
    """A confirmation cannot broaden the pinned, predeclared case scope."""
    requirement = case.get('requirement') or {}
    scope = requirement.get(scope_key)
    keys = {'pinned_agent_update': {'ci_name', 'agent_id', 'version'},
            'pinned_plugin_delivery': {'ci_name', 'agent_id', 'version', 'plugin_name', 'core_version'},
            'pinned_audit_task': {'ci_name', 'agent_id', 'core_version', 'task_name'}}.get(scope_key)
    expected_scope=scope
    if (scope_key=='pinned_audit_task' and requirement.get('type')=='pinned_agent_audit'
            and requirement.get('allow_plugin_audit_refresh') is True and isinstance(scope,dict)
            and arguments=={**scope,'task_name':'pluginAudit'}):
        expected_scope={**scope,'task_name':'pluginAudit'}
    if (job.get('stand') != 'lab' or requirement.get('locked') is not True
            or not isinstance(scope, dict) or set(scope) != keys
            or arguments != expected_scope or not all(isinstance(v, str) and v for v in expected_scope.values())
            or not all(v in str(job.get('request', '')) for v in expected_scope.values())):
        raise ValueError('locked_pinned_update_scope_required')


def pinned_audit_payload(ci, agent, tasks, agent_id, core_version, task_name, audit=None):
    from tools.agent_plugins import summarize_plugin_audit
    if task_name not in {'pluginAudit', 'osAudit'}:
        raise ValueError('audit_task_not_admitted')
    if (not isinstance(ci, dict) or not ci.get('id') or ci.get('agent_id') != agent_id
            or not isinstance(agent, dict) or agent.get('id') != agent_id
            or agent.get('version') != core_version or core_version != '1.3.27'
            or agent.get('status') != 'online'):
        raise ValueError('audit_target_core_not_ready')
    items = tasks.get('items') if isinstance(tasks, dict) else None
    if (not isinstance(items, list) or type(tasks.get('total')) is not int
            or tasks['total'] != len(items) or tasks.get('offset', 0) != 0):
        raise ValueError('complete_audit_task_list_required')
    for t in items:
        if (not isinstance(t, dict) or t.get('agent_id') != agent_id or t.get('name') != task_name
                or t.get('period') is not None):
            raise ValueError('audit_task_identity_mismatch')
        if t.get('status') not in {'success', 'error', 'timeout'}:
            raise ValueError('existing_audit_pending')
    if task_name == 'osAudit':
        checked = summarize_plugin_audit(ci, audit, 'osAudit', '1.3.4')
        if (checked.get('observation_result') != 'PASS'
                or any(p.get('load_error_present') for p in checked.get('matched_plugins', []))):
            raise ValueError('fresh_os_audit_plugin_not_loaded')
    return {'name': task_name, 'period': None, 'ttl': None, 'run_as_user': '', 'additional_params': {}}


def compare_audit_readback(expected, actual):
    """Independent legacy-baseline comparison; never turns a schema change into PASS."""
    if (not isinstance(expected, dict) or set(expected) != {'host_name', 'machine_uid', 'os'}
            or not isinstance(expected['os'], dict)
            or set(expected['os']) != {'architecture', 'current_build_os', 'family', 'name', 'version'}
            or not isinstance(actual, dict) or actual.get('native_result_verified') is not True):
        return {'status': 'BLOCKED', 'reason': 'trusted_expected_or_fresh_result_missing'}
    checks = {'host_name': actual.get('host_name') == expected['host_name'],
              'machine_uid': actual.get('machine_uid') == expected['machine_uid']}
    os_data = actual.get('os_subset') or {}
    differences = {}
    for key, value in expected['os'].items():
        checks['os.' + key] = type(os_data.get(key)) is type(value) and os_data.get(key) == value
        if not checks['os.' + key]:
            differences[key] = {'expected': value, 'actual': os_data.get(key)}
    matched = all(checks.values())
    return {'status': 'PASS' if matched else 'BLOCKED',
            'reason': 'locked_subset_matched' if matched else 'legacy_baseline_contract_review_required',
            'checks': checks, 'differences': differences, 'full_regression_passed': False,
            'developer_confirmed_bug': False}


def build_pinned_audit_report(job, case_id, task_id):
    """Canonical report from same-case native evidence, never model supplied facts."""
    case = next((c for c in job.get('test_cases', []) if c.get('case_id') == case_id), {})
    requirement = case.get('requirement') or {}
    scope = requirement.get('pinned_audit_task') or {}
    if requirement.get('locked') is not True or scope.get('task_name') != 'osAudit':
        return {'error': 'locked_audit_report_scope_required'}
    receipts, reads = [], []
    for evidence in case.get('evidence', []):
        if evidence.get('source') != 'uqa_tool' or evidence.get('execution_status') not in {'observed','executed'}:
            continue
        try:
            envelope = json.loads(evidence['value']); result = envelope['result']
            if result.get('task_id') != task_id or result.get('agent_id') != scope.get('agent_id'):
                continue
            if (envelope.get('tool') == 'browser_create_pinned_agent_audit_semantic'
                    and result.get('mutation_executed') is True and result.get('task_name')=='osAudit'):
                receipts.append(evidence)
            if (envelope.get('tool') == 'browser_inspect_pinned_agent_audit_semantic'
                    and result.get('native_result_verified') is True and result.get('task_name')=='osAudit'):
                reads.append((evidence,result))
        except (ValueError, KeyError, TypeError):
            continue
    if len(receipts) != 1 or not reads:
        return {'error': 'same_case_native_audit_proofs_required'}
    read, actual = reads[-1]
    expected = requirement.get('expected_subset')
    oracle = compare_audit_readback(expected, actual)
    if 'checks' not in oracle:
        return {'error': 'audit_report_oracle_unavailable'}
    rows = []
    values = {'host_name':actual.get('host_name'),'machine_uid':actual.get('machine_uid'),
              **{'os.'+k:v for k,v in actual.get('os_subset',{}).items()}}
    expected_values = {'host_name':expected['host_name'],'machine_uid':expected['machine_uid'],
                       **{'os.'+k:v for k,v in expected['os'].items()}}
    for key, matched in oracle['checks'].items():
        rows.append({'field':key,'expected':expected_values[key],'actual':values.get(key),
                     'status':'PASS' if matched else 'BLOCKED'})
    def cell(value):
        return json.dumps(value,ensure_ascii=False).replace('|','\\|').replace('\n',' ')
    md = ['# osAudit: '+scope['ci_name'], '', 'Вердикт: '+oracle['status'],
          'Task ID: '+task_id, '', '| Поле | Ожидаемый результат | Фактический результат | Статус |',
          '| --- | --- | --- | --- |']
    md += ['| '+r['field']+' | '+cell(r['expected'])+' | '+cell(r['actual'])+' | '+r['status']+' |' for r in rows]
    md += ['', 'Основание: '+oracle['reason']+'. Изменение контракта не подтверждено разработчиком как баг/фикс.',
           'Граница: только закреплённый osAudit subset; не полный Zephyr case. Записей в Zephyr нет.',
           'Первичные доказательства: '+receipts[0]['evidence_id']+', '+read['evidence_id']+'.']
    return {'report_type':'locked_audit_subset','job_id':job.get('job_id'),'case_id':case_id,
            'task_id':task_id,'verdict':oracle['status'],'reason':oracle['reason'],'rows':rows,
            'source_evidence_ids':[receipts[0]['evidence_id'],read['evidence_id']],
            'observation_ids':read.get('observation_ids',[]),'report_markdown':'\n'.join(md),
            'full_regression_passed':False,'zephyr_written':False,'product_mutation_executed':False}


def pinned_plugin_payload(ci, agent, tasks, agent_id, core_version, plugin_name, version):
    """First admitted delivery profile; no arbitrary plugins or deletion."""
    if plugin_name != 'osAudit' or version != '1.3.4':
        raise ValueError('plugin_delivery_profile_not_admitted')
    if (not isinstance(ci, dict) or ci.get('agent_id') != agent_id or not ci.get('id')
            or not isinstance(agent, dict) or agent.get('id') != agent_id
            or agent.get('status') != 'online' or agent.get('version') != core_version
            or core_version != '1.3.27'):
        raise ValueError('plugin_target_core_not_ready')
    items = tasks.get('items') if isinstance(tasks, dict) else None
    if (not isinstance(items, list) or type(tasks.get('total')) is not int
            or tasks['total'] != len(items) or tasks.get('offset', 0) != 0):
        raise ValueError('complete_plugin_task_list_required')
    for task in items:
        if (not isinstance(task, dict) or task.get('agent_id') != agent_id
                or task.get('name') != 'managePlugin'):
            raise ValueError('plugin_task_identity_mismatch')
        if task.get('status') not in {'success', 'error', 'timeout'}:
            raise ValueError('existing_plugin_delivery_pending')
        updates = (task.get('additional_params') or {}).get('plugins_to_update')
        if not isinstance(updates, list):
            raise ValueError('existing_plugin_parameters_unknown')
        if any(p.get('plugin_name') == plugin_name and p.get('plugin_version') == version
               for p in updates if isinstance(p, dict)):
            raise ValueError('same_plugin_delivery_already_exists')
    return {'plugins_to_update': [{'plugin_name': plugin_name, 'plugin_version': version}],
            'plugins_to_delete': [], 'check_endpoint_os_version': True}


def pinned_update_payload(ci, agent, tasks, agent_id, version):
    if not isinstance(version, str) or not re.fullmatch(r'\d+\.\d+\.\d+', version):
        raise ValueError('explicit_numeric_version_required')
    if not isinstance(agent_id, str) or str(UUID(agent_id)) != agent_id:
        raise ValueError('exact_agent_id_required')
    if not isinstance(ci, dict) or not ci.get('id') or ci.get('agent_id') != agent_id:
        raise ValueError('ci_agent_mismatch')
    if not isinstance(agent, dict) or agent.get('id') != agent_id:
        raise ValueError('agent_identity_mismatch')
    if agent.get('status') != 'online':
        raise ValueError('agent_not_online')
    current = agent.get('version')
    if not isinstance(current, str) or not re.fullmatch(r'\d+\.\d+\.\d+', current):
        raise ValueError('current_version_unknown')
    if tuple(map(int, version.split('.'))) <= tuple(map(int, current.split('.'))):
        raise ValueError('already_current_or_downgrade')
    items = tasks.get('items') if isinstance(tasks, dict) else None
    if (not isinstance(items, list) or type(tasks.get('total')) is not int
            or tasks['total'] != len(items) or tasks.get('offset', 0) != 0):
        raise ValueError('complete_update_task_list_required')
    for task in items:
        if (not isinstance(task, dict) or task.get('agent_id') != agent_id
                or task.get('name') != 'updateAgent'):
            raise ValueError('update_task_identity_mismatch')
        if task.get('status') not in {'success', 'error', 'timeout'}:
            raise ValueError('existing_update_pending')
        params = task.get('additional_params')
        if not isinstance(params, dict):
            raise ValueError('existing_update_parameters_unknown')
        if params.get('version') == version:
            raise ValueError('same_version_update_already_exists')
    return {'name': 'updateAgent', 'period': None, 'ttl': None,
            'run_as_user': '', 'additional_params': {'version': version}}

"""Evidence-only native-control surface lifecycle. No navigation, clicks or policy grants."""
import json
from frontend_check_contracts import normalized_origin

OBSERVER = 'browser_inspect_form_validation_semantic'

def opening_names(requirement, contract, trigger):
    binding = contract.get('opening_sequence_binding')
    if binding is None:
        return [trigger]
    value = (requirement.get('bindings') or {}).get(binding)
    try:
        names = json.loads(value)
    except (ValueError, TypeError):
        raise ValueError('form_contract_opening_sequence_invalid')
    if (not isinstance(names, list) or not 1 <= len(names) <= 4
            or any(not isinstance(n, str) or not n.strip() for n in names)
            or len(set(names)) != len(names) or names[-1] != trigger):
        raise ValueError('form_contract_opening_sequence_invalid')
    return names

def needs_form_baseline(job, case_id, saved_url):
    """One declared OBSERVE after trusted navigation, never after an opening action."""
    from frontend_check_contracts import validate_contracts
    try:
        if not isinstance(job, dict) or job.get('job_type') != 'regression' or job.get('status') != 'running':
            return False
        cases = [c for c in job.get('test_cases', []) if c.get('case_id') == case_id]
        if len(cases) != 1 or cases[0].get('status') != 'running':
            return False
        case = cases[0]; req = case.get('requirement') or {}; contracts = req.get('check_contracts')
        if req.get('type') != 'frontend_contracts' or req.get('locked') is not True or req.get('action_profile') != 'write_ui_state':
            return False
        validate_contracts(contracts)
        if (set(contracts) != {p['check_id'] for p in case.get('planned_checks', [])}
                or any(c['tool'] != OBSERVER for c in contracts.values())
                or {c['phase'] for c in contracts.values()} != {'opened', 'restored'}
                or len({(c['subject_binding'], c['close_key_binding'], c.get('opening_sequence_binding')) for c in contracts.values()}) != 1):
            return False
        first = next(iter(contracts.values())); bindings = req.get('bindings') or {}
        if not bindings.get(first['subject_binding']) or bindings.get(first['close_key_binding']) != 'Escape':
            return False
        opening_names(req, first, bindings[first['subject_binding']])
        observations = case.get('observations') or []
        if any(o.get('data', {}).get('tool') in {OBSERVER, 'browser_click_semantic',
                'browser_fill_semantic', 'browser_press_key_semantic'} for o in observations):
            return False
        pages = [o for o in observations if o.get('type') == 'ui_state'
                 and o.get('data', {}).get('tool') == 'browser_open_page']
        if not pages:
            return False
        page = pages[-1]; data = page['data']
        linked = [e for e in case.get('evidence', []) if page.get('observation_id') in e.get('observation_ids', [])
                  and e.get('type') == 'browser_open_page']
        # Navigation is OBSERVE and does not use the mutation execution window.
        return bool(data.get('session_id')
                    and type(data.get('http_status')) is int and 200 <= data['http_status'] < 400
                    and normalized_origin(data.get('url')) == normalized_origin(saved_url)
                    and len(linked) == 1 and linked[0].get('usable_for_verdict') is True)
    except (ValueError, TypeError, KeyError, AttributeError):
        return False

def form_lifecycle_fact(case, requirement, contract, trigger, saved_url):
    bindings = requirement.get('bindings') or {}
    close_key = bindings.get(contract['close_key_binding'])
    if close_key != 'Escape' or requirement.get('locked') is not True:
        raise ValueError('form_contract_binding_invalid')
    names = opening_names(requirement, contract, trigger)
    observations = case.get('observations') or []
    def action(o, tool, key, value):
        d=o.get('data') or {}
        return o.get('type')=='ui_state' and d.get('tool')==tool and d.get('input',{}).get(key)==value
    openings=[i for i,o in enumerate(observations) if action(o,'browser_click_semantic','name',trigger)
              and o['data'].get('action_execution_id') and o['data'].get('network_window_closed') is True]
    if len(openings)!=1:
        raise ValueError('form_contract_open_action_missing_or_ambiguous')
    start=openings[0]
    opening_steps = [i for i,o in enumerate(observations[:start+1])
                     if o.get('type') == 'ui_state' and o.get('data', {}).get('tool') == 'browser_click_semantic'
                     and o['data'].get('action_execution_id') and o['data'].get('network_window_closed') is True]
    if [observations[i]['data'].get('input', {}).get('name') for i in opening_steps] != names:
        raise ValueError('form_contract_opening_sequence_unproven')
    closes=[i for i,o in enumerate(observations) if i>start and action(o,'browser_press_key_semantic','key',close_key)
            and o['data'].get('action_execution_id') and o['data'].get('network_window_closed') is True]
    if len(closes)>1:
        raise ValueError('form_contract_close_action_ambiguous')
    end=closes[0] if closes else len(observations)
    def reads(lo,hi):
        return [o for o in observations[lo:hi] if o.get('type')=='ui_contract_audit'
                and o.get('data',{}).get('tool')==OBSERVER]
    before=reads(0,opening_steps[0]); opened=reads(start+1,end)
    if not before or not opened:
        raise ValueError('form_contract_baseline_or_open_read_missing')
    baseline, current=before[-1], opened[-1]
    sources=[observations[i] for i in opening_steps] + [baseline, current]
    if contract['phase']=='restored':
        if not closes:
            raise ValueError('form_contract_close_action_missing')
        after=reads(end+1,len(observations))
        if not after:
            raise ValueError('form_contract_closed_read_missing')
        sources += [observations[end],after[-1]]
    session=observations[start]['data'].get('session_id')
    if not session or normalized_origin(saved_url) is None:
        raise ValueError('form_contract_context_missing')
    refs=[]
    for o in sources:
        d=o.get('data') or {}
        if not isinstance(o.get('observation_id'), str) or not o['observation_id'].startswith('obs-'):
            raise ValueError('form_contract_observation_identity_missing')
        if d.get('session_id')!=session or normalized_origin(d.get('url'))!=normalized_origin(saved_url):
            raise ValueError('form_contract_episode_or_origin_mismatch')
        linked=[e for e in case.get('evidence',[]) if o.get('observation_id') in e.get('observation_ids',[])
                and e.get('type')==d.get('tool')]
        if (len(linked)!=1 or linked[0].get('usable_for_verdict') is not True
                or not isinstance(linked[0].get('evidence_id'), str) or not linked[0]['evidence_id']):
            raise ValueError('form_contract_evidence_unusable')
        refs.append(linked[0]['evidence_id'])
    def signature(o):
        d=o['data']; audit=d.get('audit') or {}; rows=d.get('control_states')
        if (d.get('observation_result')!='observed' or d.get('mutation_executed') is not False
                or d.get('scope_kind')!='page' or d.get('control_states_reported') is not True
                or d.get('control_geometry_reported') is not True or audit.get('truncated') is not False
                or type(audit.get('visible_control_count')) is not int
                or not isinstance(rows,list) or len(rows)!=audit.get('visible_control_count')):
            raise ValueError('form_contract_snapshot_incomplete_or_wrong_scope')
        visible=[]
        for row in rows:
            if (not isinstance(row, dict) or row.get('tag') not in {'input','select','textarea'}
                    or not isinstance(row.get('type'), str) or not isinstance(row.get('label_hint'), str)
                    or (type(row.get('native_read_only')) is not bool
                        and not (row.get('tag') == 'select' and row.get('native_read_only') is None))):
                raise ValueError('form_contract_control_metadata_invalid')
            if any(type(row.get(k)) is not bool for k in ('in_viewport','aria_hidden','inert','native_required','native_disabled','native_will_validate')):
                raise ValueError('form_contract_control_flags_invalid')
            if row['in_viewport'] and not row['aria_hidden'] and not row['inert']:
                visible.append({k:row.get(k) for k in ('tag','type','label_hint','native_required','native_disabled','native_read_only','native_will_validate')})
        return sorted(json.dumps(row,sort_keys=True,ensure_ascii=False) for row in visible)
    initial_sig=signature(baseline); open_sig=signature(current)
    if len(open_sig) <= len(initial_sig):
        raise ValueError('form_contract_open_transition_unproven')
    facts={'form_controls_opened':bool(open_sig) and open_sig!=initial_sig,
           'native_states_reported':bool(open_sig)}
    if contract['phase']=='restored':
        facts['form_controls_restored']=signature(sources[-1])==initial_sig and open_sig!=initial_sig
        # State-changing calls outside the declared open/close are not safe proof.
        executed=[o['data'] for o in observations if o.get('type')=='ui_state'
                  and o.get('data',{}).get('action_execution_id') and o['data'].get('network_window_closed') is True]
        actual_actions = [(d.get('tool'), d.get('input', {}).get('name') if d.get('tool') == 'browser_click_semantic'
                           else d.get('input', {}).get('key')) for d in executed]
        facts['no_input_submit_execution'] = actual_actions == (
            [('browser_click_semantic', name) for name in names] + [('browser_press_key_semantic', close_key)])
    return sources[-1] if contract['phase']=='restored' else current, facts, refs, [o['observation_id'] for o in sources]

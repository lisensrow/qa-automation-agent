"""Bounded historical attempt projection. No writes, recovery, replay or permission."""
import hashlib
import json
import re
from pathlib import Path
from uuid import UUID
import job_store

TOOL='operation_read_attempt_history'
PROFILE='operation-history-read-v1'
KEYS={'source_job_id','source_case_id','operation_id'}
CREATE='browser_create_closed_plugin_discovery_semantic'
READ='browser_inspect_closed_plugin_discovery_semantic'

def key(arguments):
    if not isinstance(arguments,dict) or set(arguments)!=KEYS:raise ValueError('exact_attempt_key_required')
    for field,pattern in [('source_job_id',r'\d{8}-\d{6}-[0-9a-f]{8}'),
                          ('source_case_id',r'tc-[0-9a-f]{8}'),('operation_id',r'op-[0-9a-f]{32}')]:
        if not isinstance(arguments[field],str) or not re.fullmatch(pattern,arguments[field]):raise ValueError('invalid_attempt_key')
    return tuple(arguments[k] for k in sorted(KEYS))

def validate_context(job,case_id,arguments):
    wanted=key(arguments)
    if not isinstance(job,dict) or job.get('stand')!='lab' or job.get('job_type') not in {'manual','regression'} or job.get('status')!='running':
        raise ValueError('running_lab_context_required')
    case=next((c for c in job.get('test_cases',[]) if c.get('case_id')==case_id),None)
    r=(case or {}).get('requirement') or {}
    if not case or case.get('status')!='running' or r.get('profile_id')!=PROFILE or r.get('locked') is not True:
        raise ValueError('locked_history_context_required')
    attempts=r.get('history_attempts')
    if not isinstance(attempts,list) or not 1<=len(attempts)<=8:raise ValueError('bounded_attempt_list_required')
    keys=[key(a) for a in attempts]
    if len(set(keys))!=len(keys) or wanted not in keys:raise ValueError('attempt_not_in_locked_scope')

def _bytes(path,limit):
    # Do not create lock files, chmod storage or follow per-file symlinks.
    if path.is_symlink() or not path.is_file() or path.stat().st_size>limit:raise ValueError('history_source_unavailable')
    with path.open('rb') as stream:raw=stream.read(limit+1)
    if len(raw)>limit:raise ValueError('history_source_budget')
    return raw

def _native(case,evidence_id,tool):
    matches=[e for e in case.get('evidence',[]) if e.get('evidence_id')==evidence_id]
    if len(matches)!=1:raise ValueError('unique_native_proof_required')
    e=matches[0]
    if e.get('source')!='uqa_tool' or e.get('type')!=tool or e.get('execution_status') not in {'tool_error','executed','observed'}:
        raise ValueError('native_proof_required')
    raw=e.get('value')
    if not isinstance(raw,str) or len(raw)>1048576:raise ValueError('proof_budget')
    b=json.loads(raw)
    if b.get('tool')!=tool or not isinstance(b.get('result'),dict):raise ValueError('native_envelope_required')
    return e,b['result']

def project(job,journal,arguments):
    """Pure linkage check of stored historical facts, not current postcondition evaluation."""
    key(arguments)
    jid,cid,oid=(arguments[k] for k in ['source_job_id','source_case_id','operation_id'])
    if job.get('job_id')!=jid or job.get('stand')!='lab' or journal.get('version')!=1 or journal.get('job_id')!=jid:
        raise ValueError('source_identity_mismatch')
    cases=[c for c in job.get('test_cases',[]) if c.get('case_id')==cid]
    ops=journal.get('operations')
    if len(cases)!=1 or not isinstance(ops,list) or len(ops)>1000:raise ValueError('source_bounds_or_identity')
    selected=[o for o in ops if o.get('operation_id')==oid]
    if len(selected)!=1 or selected[0].get('case_id')!=cid:raise ValueError('operation_identity_mismatch')
    case,op=cases[0],selected[0]
    if not isinstance(case.get('evidence',[]),list) or len(case.get('evidence',[]))>1000:raise ValueError('evidence_budget')
    status=op.get('status')
    if status not in {'sending','uncertain','awaiting_verification','verified','not_sent','rejected','canceled'}:raise ValueError('unknown_journal_status')
    result={'attempt_key':dict(arguments),'operation_status':status,'request_sent':None,'own_task_id':None,
        'proof_evidence_ids':[],'historical_only':True,'live_postcondition_rechecked':False,
        'permission_granted':False,'resend_authorized':False,'business_pass':False,
        'reason':'dispatch_not_proven_for_this_exact_attempt'}
    # Only discovery receipts have a reviewed native linkage contract in this revision.
    if op.get('tool')!=CREATE:return result
    receipt=op.get('receipt') or {}
    try:
        if status=='not_sent' and receipt.get('native_pre_dispatch_refusal') is True and receipt.get('acknowledged') is False:
            found=[]
            for e in case.get('evidence',[]):
                if e.get('type')!=CREATE or e.get('source')!='uqa_tool':continue
                native,body=_native(case,e['evidence_id'],CREATE)
                if body.get('operation_id')!=oid:continue
                if (native.get('execution_status')=='tool_error' and body.get('error') and body.get('executed') is False
                    and body.get('mutation_executed') is False and body.get('dispatch_state')=='not_started'):
                    found.append(e['evidence_id'])
            if len(found)==1:result.update(request_sent=False,proof_evidence_ids=found,reason='native_pre_dispatch_refusal')
        elif status=='verified' and receipt.get('acknowledged') is True and receipt.get('native_pre_dispatch_refusal') is False:
            proof=op.get('verification') or {}
            if proof.get('verified') is not True or proof.get('postcondition_verified') is not True:raise ValueError('stored_verification_missing')
            ce,created=_native(case,proof['receipt_evidence_id'],CREATE)
            fe,full=_native(case,proof['evidence_id'],READ)
            task=proof['identifier_value']
            if not isinstance(task,str) or str(UUID(task))!=task:raise ValueError('own_uuid_required')
            if ce['execution_status']!='executed' or fe['execution_status'] not in {'executed','observed'}:raise ValueError('native_status_mismatch')
            for body in [created,full]:
                if body.get('error') or (body.get('job_id'),body.get('case_id'),body.get('operation_id'),body.get('task_id'))!=(jid,cid,oid,task):
                    raise ValueError('native_attempt_mismatch')
            if (created.get('executed') is not True or created.get('mutation_executed') is not True
                or full.get('native_result_verified') is not True or full.get('identity_verified') is not True
                or full.get('fresh_result') is not True or created.get('session_id')!=full.get('session_id')
                or not created.get('session_id')):raise ValueError('native_linkage_incomplete')
            result.update(request_sent=True,own_task_id=task,proof_evidence_ids=[ce['evidence_id'],fe['evidence_id']],
                          reason='stored_verified_native_receipt_and_own_full_linkage')
    except (ValueError,TypeError,KeyError,AttributeError):
        result['reason']='stored_proof_missing_or_inconsistent'
    return result

def inspect(arguments,job_id,case_id):
    validate_context(job_store.get_job(job_id),case_id,arguments)
    root=Path(job_store.JOBS_DIR).resolve()
    paths=[root/(arguments['source_job_id']+'.json'),root/'operations'/(arguments['source_job_id']+'.json')]
    if paths[1].parent.is_symlink():raise ValueError('history_source_symlink')
    raw=[_bytes(paths[0],16777216),_bytes(paths[1],1048576)]
    out=project(json.loads(raw[0]),json.loads(raw[1]),arguments)
    if raw!=[_bytes(paths[0],16777216),_bytes(paths[1],1048576)]:raise ValueError('history_changed_during_read')
    return {**out,'source_sha256':{'job':hashlib.sha256(raw[0]).hexdigest(),'journal':hashlib.sha256(raw[1]).hexdigest()},
            'bookkeeping_only':True,'mutation_executed':False}

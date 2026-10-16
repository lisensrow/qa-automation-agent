"""Independent evidence/ledger verification for the closed command microcase.

Execution-only proof, never business PASS, permission or resend authority.
"""
from datetime import datetime,timezone
import json,re
from command_stage_profile import validate_context,stages_for,CREATE,READ
from command_probe_contract import ORIGIN,CORE,PLUGIN,VERSION,PROFILE_ID
from tools.agent_update import audit_result_is_fresh

def stamp(s):
    d=datetime.fromisoformat(str(s).replace('Z','+00:00'))
    if d.tzinfo is None:raise ValueError('timezone required')
    return d

def evaluate(job,op,evidence_id,contract):
    try:
        case,req=validate_context(job,op['case_id'])
        stage=next(s for s in stages_for(req['target']) if s['stage_id']==op['stage_id'])
        if (contract!=stage['verification'] or any(op.get(k)!=stage[k] for k in ['tool','stage_id','workflow_id','resource_key'])
            or (op.get('receipt') or {}).get('acknowledged') is not True):raise ValueError('wrong_command_stage_contract')
        started=stamp(op['created_at']);current=datetime.now(timezone.utc)
        def native(e,tool):
            if (e.get('source')!='uqa_tool' or e.get('execution_status') not in {'observed','executed'}
                or stamp(e['created_at'])<started):raise ValueError('native_command_evidence_required')
            b=json.loads(e['value'])
            if b.get('tool')!=tool or not isinstance(b.get('result'),dict):raise ValueError('wrong_native_command_tool')
            return b
        ev=next(e for e in case['evidence'] if e['evidence_id']==evidence_id);b=native(ev,READ);read=b['result']
        creates=[]
        for e in case['evidence']:
            if e.get('source')!='uqa_tool':continue
            try:body=json.loads(e['value'])
            except (ValueError,TypeError):continue
            if body.get('tool')==CREATE and (body.get('result') or {}).get('operation_id')==op['operation_id']:
                creates.append((e,native(e,CREATE)))
        if len(creates)!=1:raise ValueError('unique_native_command_receipt_required')
        ce,cb=creates[0];created=cb['result'];expected_status=202 if contract['task_name']=='managePlugin' else 201
        if (cb.get('arguments')!=stage['arguments'] or b.get('arguments')!={'target':req['target'],'task_id':created.get('task_id')}
            or created.get('create_status')!=expected_status or created.get('executed') is not True
            or created.get('mutation_executed') is not True or created.get('profile_id')!=PROFILE_ID
            or created.get('error') or read.get('error') or not created.get('task_id')
            or any(created.get(k)!=v or read.get(k)!=v for k,v in {
                'target':req['target'],'stage_id':stage['stage_id'],'agent_id':req['agent_id'],'ci_id':req['ci_id'],
                'task_name':contract['task_name'],'request_origin':ORIGIN,'operation_id':op['operation_id']}.items())
            or read.get('task_id')!=created['task_id'] or not created.get('session_id')
            or read.get('session_id')!=created['session_id'] or read.get('machine_uid')!=req['ci_id']
            or any(read.get(k) is not True for k in ['native_result_verified','identity_verified','fresh_result'])
            or read.get('task_status')!='success' or read.get('business_pass') is not False
            or stamp(ev['created_at'])<stamp(ce['created_at'])
            or not -5<=(current-stamp(ev['created_at'])).total_seconds()<=300
            or not -5<=(stamp(ev['created_at'])-stamp(read['read_at'])).total_seconds()<=60
            or not audit_result_is_fresh(created.get('sent_at'),created.get('received_at'),created.get('server_created_at'),
                read.get('server_created_at'),read.get('processed_at'),now=current)):
            raise ValueError('closed_command_receipt_or_full_mismatch')
        sid=stage['stage_id']
        if sid=='execute_command':
            digest=created.get('expected_marker_sha256')
            if (not isinstance(digest,str) or not re.fullmatch(r'[0-9a-f]{64}',digest)
                or read.get('expected_marker_sha256')!=digest or read.get('profile_id')!=PROFILE_ID
                or read.get('plugin_name')!=PLUGIN or read.get('plugin_version')!=VERSION
                or any(read.get(k) is not True for k in ['technical_execution_verified','exact_marker_matched','stderr_empty'])
                or type(read.get('error_code')) is not int or read['error_code']!=0
                or read.get('full_business_case_passed') is not False):raise ValueError('exact_private_marker_proof_required')
        elif sid=='deliver_command_plugin':
            if read.get('delivery_verified') is not True:raise ValueError('command_download_proof_required')
        else:
            ready=read.get('plugin_readiness') or {};audit=ready.get('plugin_audit') or {}
            if (ready.get('ci_id')!=req['ci_id'] or ready.get('agent_id')!=req['agent_id']
                or ready.get('core_version')!=CORE or ready.get('agent_status')!='online'
                or audit.get('audit_agent_id')!=req['agent_id'] or audit.get('audit_fresh') is not True
                or (stamp(audit.get('last_audit_at'))-stamp(created['server_created_at'])).total_seconds() < -120):
                raise ValueError('fresh_owned_command_inventory_required')
            if sid=='post_delivery_inventory':
                matched=audit.get('matched_plugins')
                if (ready.get('ready') is not True or not isinstance(matched,list) or len(matched)!=1
                    or any(matched[0].get(k)!=v or type(matched[0].get(k)) is not type(v) for k,v in {
                        'name':PLUGIN,'version':VERSION,'load_status':True,'load_error_present':False}.items())):
                    raise ValueError('fresh_loaded_command_version_required')
        return {'verified':True,'evidence_id':evidence_id,'receipt_evidence_id':ce['evidence_id'],
            'identifier_value':created['task_id'],'postcondition_verified':True,'resend_authorized':False,
            'verification_scope':'closed_command_stage_execution_not_full_business_case','business_pass':False}
    except (ValueError,TypeError,KeyError,AttributeError,StopIteration,OverflowError):
        return {'verified':False,'reason':'closed_command_stage_evidence_insufficient','resend_authorized':False}

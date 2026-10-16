"""Independent execution proof for preparation; no business PASS/resend authority."""
from datetime import datetime,timezone
import json
from plugin_preparation import validate_context,CREATE,READ,PROFILE,ORIGIN,CORE,stamp
from tools.agent_update import audit_result_is_fresh

def evaluate(job,op,evidence_id,contract):
    try:
        c,r=validate_context(job,op['case_id'])
        stage=next(s for s in r['operation_stages'] if s['stage_id']==op['stage_id'])
        if (contract!=stage['verification'] or any(op.get(k)!=stage[k] for k in ['workflow_id','stage_id','resource_key','tool'])
            or (op.get('receipt') or {}).get('acknowledged') is not True):raise ValueError('preparation_contract')
        def native(e,tool):
            if (e.get('source')!='uqa_tool' or e.get('execution_status') not in {'observed','executed'}
                or stamp(e['created_at'])<stamp(op['created_at'])):raise ValueError('native_evidence')
            b=json.loads(e['value'])
            if b.get('tool')!=tool or not isinstance(b.get('result'),dict):raise ValueError('tool_evidence')
            return b
        ev=next(e for e in c['evidence'] if e['evidence_id']==evidence_id);rb=native(ev,READ);read=rb['result']
        creates=[]
        for e in c['evidence']:
            if e.get('source')!='uqa_tool':continue
            try:b=json.loads(e['value'])
            except (ValueError,TypeError):continue
            if b.get('tool')==CREATE and (b.get('result') or {}).get('operation_id')==op['operation_id']:
                creates.append((e,native(e,CREATE)))
        if len(creates)!=1:raise ValueError('unique_receipt')
        ce,cb=creates[0];created=cb['result'];current=datetime.now(timezone.utc)
        if (cb.get('arguments')!=stage['arguments'] or rb.get('arguments')!={'target':r['target'],
                'plugin_name':r['plugin_name'],'task_id':created.get('task_id')}
            or created.get('create_status')!=(202 if op['stage_id']=='delivery' else 201)
            or created.get('executed') is not True or created.get('mutation_executed') is not True
            or created.get('error') or read.get('error') or created.get('profile_id')!=PROFILE or read.get('profile_id')!=PROFILE
            or any(created.get(k)!=v or read.get(k)!=v for k,v in {'target':r['target'],'plugin_name':r['plugin_name'],
                'plugin_version':r['plugin_version'],'ci_id':r['ci_id'],'agent_id':r['agent_id'],'stage_id':stage['stage_id'],
                'task_name':contract['task_name'],'request_origin':ORIGIN,'operation_id':op['operation_id'],
                'job_id':job['job_id'],'case_id':op['case_id']}.items())
            or not created.get('task_id') or read.get('task_id')!=created['task_id'] or not created.get('session_id')
            or read.get('session_id')!=created['session_id'] or read.get('machine_uid')!=r['ci_id']
            or read.get('business_pass') is not False or read.get('task_status')!='success'
            or any(read.get(k) is not True for k in ['native_result_verified','identity_verified','fresh_result'])
            or stamp(ev['created_at'])<stamp(ce['created_at']) or not -5<=(current-stamp(ev['created_at'])).total_seconds()<=300
            or not -5<=(stamp(ev['created_at'])-stamp(read['read_at'])).total_seconds()<=60
            or not audit_result_is_fresh(created.get('sent_at'),created.get('received_at'),created.get('server_created_at'),
                read.get('server_created_at'),read.get('processed_at'),now=current)):raise ValueError('own_receipt_full')
        if op['stage_id']=='delivery':
            if read.get('delivery_verified') is not True:raise ValueError('download_required')
        else:
            ready=read.get('plugin_readiness') or {};audit=ready.get('plugin_audit') or {}
            if (any(ready.get(k)!=v for k,v in {'target':r['target'],'ci_id':r['ci_id'],'agent_id':r['agent_id'],
                    'core_version':CORE,'agent_status':'online','plugin_name':r['plugin_name'],'plugin_version':r['plugin_version']}.items())
                or audit.get('audit_agent_id')!=r['agent_id'] or audit.get('audit_fresh') is not True
                or (stamp(audit.get('last_audit_at'))-stamp(created['server_created_at'])).total_seconds() < -120):raise ValueError('fresh_inventory')
            if op['stage_id']=='post_inventory':
                matched=audit.get('matched_plugins')
                if (ready.get('ready') is not True or ready.get('load_error_empty_observed') is not True or not isinstance(matched,list) or len(matched)!=1
                    or any(type(matched[0].get(k)) is not type(v) or matched[0].get(k)!=v for k,v in
                        {'name':r['plugin_name'],'version':r['plugin_version'],'load_status':True,'load_error_present':False}.items())):
                    raise ValueError('fresh_loaded_version')
        return {'verified':True,'evidence_id':evidence_id,'receipt_evidence_id':ce['evidence_id'],
            'identifier_value':created['task_id'],'postcondition_verified':True,'resend_authorized':False,
            'verification_scope':'plugin_preparation_execution_only_not_plugin_case','business_pass':False}
    except (ValueError,TypeError,KeyError,AttributeError,StopIteration,OverflowError):
        return {'verified':False,'reason':'plugin_preparation_evidence_insufficient','resend_authorized':False}

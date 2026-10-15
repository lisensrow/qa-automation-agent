"""Verify owned audit task execution, NEVER business PASS or resend permission."""
from datetime import datetime, timezone
import json
from tools.agent_update import audit_result_is_fresh

ORIGIN='https://uc.lab.local'


def stages_for(scope, ci_id):
    stages=[]
    for name,stage_id in [('pluginAudit','refresh-plugin-inventory'),('osAudit','execute-os-audit')]:
        stages.append({'version':1,'workflow_id':'pinned-agent-audit-v1','stage_id':stage_id,
            'resource_key':'agent-'+scope['agent_id']+'-'+name,
            'tool':'browser_create_pinned_agent_audit_semantic','arguments':{**scope,'task_name':name},
            'verification':{'version':1,'kind':'owned_agent_audit_execution','origin':ORIGIN,
                'agent_id':scope['agent_id'],'ci_id':ci_id,'task_name':name,'core_version':'1.3.27',
                'plugin_name':'osAudit','plugin_version':'1.3.4','requires_plugin_readiness':name=='pluginAudit'}})
    return stages


def _time(value):
    at=datetime.fromisoformat(str(value).replace('Z','+00:00'))
    if at.tzinfo is None: raise ValueError('timezone required')
    return at


def evaluate(job, operation, evidence_id, contract):
    try:
        case=next(c for c in job['test_cases'] if c['case_id']==operation['case_id'])
        req=case.get('requirement') or {}; scope=req.get('pinned_audit_task') or {}
        expected=req.get('expected_subset') or {}
        stages=stages_for(scope,expected['machine_uid'])
        stage=next(s for s in stages if s['stage_id']==operation['stage_id'])
        if (job.get('stand')!='lab' or req.get('type')!='pinned_agent_audit' or req.get('locked') is not True
                or req.get('allow_plugin_audit_refresh') is not True or req.get('operation_stages')!=stages
                or contract!=stage['verification'] or operation.get('tool')!=stage['tool']
                or any(operation.get(k)!=stage[k] for k in ('workflow_id','stage_id','resource_key'))
                or operation.get('receipt',{}).get('acknowledged') is not True):
            raise ValueError('wrong execution contract')
        started=_time(operation['created_at']); now=datetime.now(timezone.utc)
        def native(e,tool):
            if (e.get('source')!='uqa_tool' or e.get('execution_status') not in {'executed','observed'}
                    or _time(e['created_at'])<started):
                raise ValueError('native evidence required')
            envelope=json.loads(e['value'])
            if envelope.get('tool')!=tool or not isinstance(envelope.get('result'),dict):
                raise ValueError('wrong tool evidence')
            return envelope
        read_ev=next(e for e in case['evidence'] if e['evidence_id']==evidence_id)
        read_envelope=native(read_ev,'browser_inspect_pinned_agent_audit_semantic'); read=read_envelope['result']
        creates=[]
        for e in case['evidence']:
            if e.get('source')!='uqa_tool': continue
            try: envelope=json.loads(e['value'])
            except (ValueError,TypeError): continue
            if (envelope.get('tool')=='browser_create_pinned_agent_audit_semantic'
                    and (envelope.get('result') or {}).get('operation_id')==operation['operation_id']):
                creates.append((e,native(e,'browser_create_pinned_agent_audit_semantic')))
        if len(creates)!=1: raise ValueError('unique native receipt required')
        create_ev,create_envelope=creates[0]; created=create_envelope['result']
        args=read_envelope.get('arguments') or {}
        if (create_envelope.get('arguments')!=stage['arguments'] or created.get('create_status')!=201
                or created.get('mutation_executed') is not True or created.get('executed') is not True
                or created.get('error') or read.get('error')
                or created.get('task_name')!=contract['task_name'] or read.get('task_name')!=contract['task_name']
                or created.get('task_id')!=read.get('task_id') or not created.get('task_id')
                or args.get('task_id')!=created['task_id'] or args.get('ci_name')!=scope['ci_name']
                or args.get('agent_id')!=scope['agent_id']
                or created.get('agent_id')!=contract['agent_id'] or read.get('agent_id')!=contract['agent_id']
                or read.get('ci_id')!=contract['ci_id'] or read.get('machine_uid')!=contract['ci_id']
                or not created.get('session_id') or read.get('session_id')!=created['session_id']
                or created.get('request_origin')!=ORIGIN or read.get('request_origin')!=ORIGIN
                or read.get('native_result_verified') is not True or read.get('identity_verified') is not True
                or read.get('fresh_result') is not True or read.get('task_status')!='success'
                or _time(read_ev['created_at'])<_time(create_ev['created_at'])
                or not -5 <= (now-_time(read_ev['created_at'])).total_seconds() <= 300
                or not -5 <= (_time(read_ev['created_at'])-_time(read['read_at'])).total_seconds() <= 60
                or not audit_result_is_fresh(created.get('sent_at'),created.get('received_at'),
                    created.get('server_created_at'),read.get('server_created_at'),read.get('processed_at'),now=now)):
            raise ValueError('receipt or result mismatch')
        if contract['requires_plugin_readiness']:
            ready=read.get('plugin_readiness') or {}; audit=ready.get('plugin_audit') or {}
            matched=audit.get('matched_plugins') or []
            if (ready.get('ready') is not True or ready.get('agent_id')!=contract['agent_id']
                    or ready.get('ci_id')!=contract['ci_id'] or ready.get('core_version')!='1.3.27'
                    or ready.get('agent_status')!='online' or audit.get('audit_fresh') is not True
                    or audit.get('audit_agent_id')!=contract['agent_id'] or len(matched)!=1
                    or matched[0].get('name')!='osAudit' or matched[0].get('version')!='1.3.4'
                    or matched[0].get('load_status') is not True or matched[0].get('load_error_present') is not False
                    or (_time(audit.get('last_audit_at'))-_time(created['server_created_at'])).total_seconds() < -120):
                raise ValueError('fresh plugin readiness not established')
        return {'verified':True,'evidence_id':evidence_id,'receipt_evidence_id':create_ev['evidence_id'],
            'identifier_value':created['task_id'],'postcondition_verified':True,'resend_authorized':False,
            'verification_scope':'owned_audit_task_execution_not_business_PASS','business_pass':False}
    except (ValueError,TypeError,KeyError,StopIteration,AttributeError,OverflowError):
        return {'verified':False,'reason':'audit_execution_evidence_insufficient','resend_authorized':False}

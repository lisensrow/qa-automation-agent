"""Immutable create/name-only rename/cleanup stage protocol, not a PASS oracle.

Stage transitions are bookkeeping; no product action or permission is granted.
"""
from copy import deepcopy
from urllib.parse import urlsplit
import operation_journal as journal


def _validate(plan):
    import uqa
    if not isinstance(plan, dict) or type(plan.get('version')) is not int or plan['version'] != 1:
        raise ValueError('invalid operation workflow')
    journal._token(plan['workflow_id']);journal._token(plan['resource_key'])
    stages=plan.get('stages')
    if not isinstance(stages,list) or [s.get('stage_id') for s in stages] != ['create','rename','cleanup']:
        raise ValueError('three ordered lifecycle stages required')
    names=plan.get('resource_name'),plan.get('renamed_name')
    if any(not isinstance(n,str) or not n.startswith('uqa-test-') or len(n)>160 or '\n' in n for n in names) or names[0]==names[1]:
        raise ValueError('distinct disposable fixture names required')
    if not isinstance(plan.get('resource_type'),str) or not plan['resource_type']:
        raise ValueError('resource type required')
    def no_secrets(v):
        if isinstance(v,dict):
            for key,item in v.items():
                if any(marker in key.casefold() for marker in ('password','secret','token','credential','cookie','authorization')):
                    raise ValueError('secret workflow field prohibited')
                no_secrets(item)
        elif isinstance(v,list):
            for item in v:no_secrets(item)
    no_secrets(plan)
    endpoint=stages[0]['verification']['endpoint'];origin=stages[0]['verification']['origin']
    parsed=urlsplit(origin)
    if parsed.username or parsed.password or parsed.scheme not in {'http','https'} or not parsed.hostname:
        raise ValueError('workflow origin invalid')
    for stage in stages:
        args=stage.get('arguments');oracle=stage.get('verification')
        if not isinstance(args,dict) or not isinstance(oracle,dict) or uqa.classify_tool_action(stage['tool'],args) not in {'write','destructive'}:
            raise ValueError('stage mutation/verification required')
        if oracle.get('version') != 1 or oracle.get('endpoint') != endpoint or oracle.get('origin') != origin:
            raise ValueError('one immutable resource endpoint required')
    create,rename,cleanup=stages
    if (create['tool']!='browser_click_semantic' or create['arguments'].get('name') not in {'Save','Create'}
            or create['verification'].get('kind')!='member_present'
            or create['verification'].get('selector') != {'name':names[0]}
            or create['verification'].get('expected_fields',{}).get('name') != names[0]):
        raise ValueError('creation contract mismatch')
    if (rename['tool'] not in {'browser_click_semantic','browser_edit_owned_resource_roundtrip_semantic'}
            or rename['verification'].get('kind')!='member_present'
            or rename['verification'].get('expected_fields',{}).get('name')!=names[1]
            or 'name' not in rename['verification'].get('allowed_changed_fields',[])
            or not set(rename['verification']['allowed_changed_fields']) <= {'name','updated_at'}):
        raise ValueError('name-only rename contract mismatch')
    if rename['tool']=='browser_click_semantic' and rename['arguments'].get('name')!='Save':
        raise ValueError('rename commit mismatch')
    if rename['tool']=='browser_edit_owned_resource_roundtrip_semantic' and (
            str(rename['arguments'].get('field') or '').casefold()!='name' or rename['arguments'].get('value')!=names[1]):
        raise ValueError('rename field mismatch')
    if (cleanup['tool']!='browser_delete_json_resource' or cleanup['verification'].get('kind')!='member_absent'
            or cleanup['arguments'].get('collection_endpoint')!=endpoint or cleanup['arguments'].get('exact_name')!=names[1]):
        raise ValueError('cleanup contract mismatch')
    for later in (rename,cleanup):
        oracle=later['verification'];key=oracle.get('identifier_key','id')
        if (oracle.get('selector')!={key:{'binding':'identifier_scalar'}}
                or oracle.get('resource_id')!={'binding':'resource_id'}
                or oracle.get('baseline_evidence_id')!={'binding':'previous_evidence_id'}):
            raise ValueError('same owned identifier and previous evidence required')
    if cleanup['arguments'].get('expected_identifier')!={'binding':'identifier_string'}:
        raise ValueError('cleanup expected identifier binding required')
    return deepcopy(plan)


def initialize_workflow(job_id,case_id):
    import job_store
    job=journal._context(job_id,case_id);case=next(c for c in job['test_cases'] if c['case_id']==case_id)
    requirement=case.get('requirement') or {}
    if requirement.get('locked') is not True or requirement.get('type')!='owned_resource_workflow':
        raise ValueError('locked owned workflow required')
    plan=_validate(requirement['operation_workflow'])
    with journal._locked(job_id) as path:
        data=journal._load(path,job_id);workflows=data.setdefault('workflows',{})
        if case_id in workflows:
            if workflows[case_id]['plan_fingerprint']!=journal._fingerprint(plan):
                raise ValueError('workflow definition changed')
            return
        if any(o['status'] in journal.UNRESOLVED for o in data['operations']):
            raise ValueError('unresolved operation precedes workflow')
        workflows[case_id]={'plan':plan,'plan_fingerprint':journal._fingerprint(plan),'stage_index':0,'bindings':{},'history':[]}
        job_store._atomic_write(path,data)


def _resolve(value,bindings):
    if isinstance(value,dict):
        if set(value)=={'binding'}:
            if value['binding'] not in bindings:raise ValueError('workflow binding missing')
            return deepcopy(bindings[value['binding']])
        return {k:_resolve(v,bindings) for k,v in value.items()}
    if isinstance(value,list):return [_resolve(v,bindings) for v in value]
    return value


def active_stage(data,case_id):
    workflow=data.get('workflows',{}).get(case_id)
    if workflow is None:return None
    plan=workflow['plan']
    if journal._fingerprint(plan)!=workflow['plan_fingerprint']:raise ValueError('workflow corrupted')
    if (type(workflow.get('stage_index')) is not int or workflow['stage_index'] < 0
            or not isinstance(workflow.get('bindings'),dict) or not isinstance(workflow.get('history'),list)
            or len(workflow['history']) != workflow['stage_index']):raise ValueError('workflow state corrupted')
    if workflow['stage_index']>=len(plan['stages']):raise ValueError('workflow already complete')
    stage=_resolve(plan['stages'][workflow['stage_index']],workflow['bindings'])
    return {**stage,'version':1,'workflow_id':plan['workflow_id'],'resource_key':plan['resource_key']}


def current_stage(job_id,case_id):
    import job_store
    path=job_store.JOBS_DIR/'operations'/(journal._token(job_id)+'.json')
    if not path.exists():return None
    with journal._locked(job_id) as path:return active_stage(journal._load(path,job_id),case_id)


def workflow_state(job_id,case_id):
    with journal._locked(job_id) as path:
        data=journal._load(path,job_id);workflow=data.get('workflows',{}).get(case_id)
        if not workflow:return {'initialized':False,'bookkeeping_only':True,'product_evidence':False}
        return {'initialized':True,'stage_index':workflow['stage_index'],
                'completed':workflow['stage_index']==len(workflow['plan']['stages']),
                'resource_id':workflow['bindings'].get('resource_id'),
                'bookkeeping_only':True,'product_evidence':False}


def has_workflow(job_id,case_id):
    import job_store
    path=job_store.JOBS_DIR/'operations'/(journal._token(job_id)+'.json')
    if not path.exists():return False
    with journal._locked(job_id) as path:
        return case_id in journal._load(path,job_id).get('workflows',{})


def attach_resource(job_id,case_id,resource_id):
    import job_store
    with journal._locked(job_id) as path:
        data=journal._load(path,job_id);workflow=data['workflows'][case_id];plan=workflow['plan']
        creation=next(o for o in reversed(data['operations']) if o['case_id']==case_id and o['workflow_id']==plan['workflow_id'] and o['stage_id']=='create')
        resource=job_store.get_test_resource(job_id,resource_id)
        if (creation['status']!='verified' or not resource or resource.get('created_by_case')!=case_id
                or resource.get('type')!=plan['resource_type'] or resource.get('name')!=plan['resource_name']
                or resource.get('metadata',{}).get('disposable') is not True
                or str(resource.get('external_id'))!=creation['verification']['identifier_value']):
            raise ValueError('verified owned resource binding required')
        old=workflow['bindings'].get('resource_id')
        if old is not None and old!=resource_id:raise ValueError('resource binding immutable')
        workflow['bindings'].update(resource_id=resource_id,identifier_string=str(resource['external_id']),
                                    identifier_scalar=creation['verification']['identifier_scalar'])
        job_store._atomic_write(path,data)
        return {'bound':True,'resource_id':resource_id,'bookkeeping_only':True,'product_evidence':False}


def advance_workflow(job_id,case_id,operation_id):
    import job_store
    with journal._locked(job_id) as path:
        data=journal._load(path,job_id);workflow=data['workflows'][case_id];stage=active_stage(data,case_id)
        operation=next(o for o in data['operations'] if o['operation_id']==operation_id)
        if (operation['status']!='verified' or operation['case_id']!=case_id
                or any(operation[k]!=stage[k] for k in ('stage_id','workflow_id','resource_key','tool'))
                or operation['arguments_fingerprint']!=journal._fingerprint(stage['arguments'])
                or operation.get('verification_fingerprint')!=journal._fingerprint(stage['verification'])):
            raise ValueError('previous stage not verified')
        if workflow['stage_index']==0 and 'resource_id' not in workflow['bindings']:
            raise ValueError('owned ledger binding required before rename')
        workflow['bindings']['previous_evidence_id']=operation['verification']['evidence_id']
        workflow['history'].append(operation_id);workflow['stage_index']+=1
        job_store._atomic_write(path,data)
        return {'advanced':True,'completed':workflow['stage_index']==len(workflow['plan']['stages']),
                'stage_index':workflow['stage_index'],'bookkeeping_only':True,'product_evidence':False,'resend_authorized':False}

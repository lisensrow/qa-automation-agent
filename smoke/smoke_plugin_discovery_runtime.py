"""Fake-model transport tests, not actual autonomous acceptance."""
from contextlib import ExitStack
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import json,uuid
import job_store as store,uqa,plugin_discovery_runtime as rt
from plugin_discovery import requirement,CREATE,READ,READY
from tools.browser import _session

for scenario in ['success','pending','uncertain','wrong_ready','stale','missing_recipe']:
  with TemporaryDirectory() as tmp,ExitStack() as stack:
    stack.enter_context(patch.object(store,'JOBS_DIR',Path(tmp)))
    stack.enter_context(patch.object(_session,'reset_case_context'));stack.enter_context(patch.object(_session,'close'))
    r=requirement('astra','checkAlive','discovery-runtime-fixture')
    request='Observe '+' '.join(r[k] for k in ['ci_id','agent_id','ci_name','core_version','plugin_name','plugin_version','profile_id'])
    j=store.create_job(request,stand='lab',job_type='manual');jid=j['job_id']
    c=store.add_test_case(jid,'Fixture only',requirement=r);cid=c['case_id']
    store.set_job_status(jid,'running');store.update_test_case(jid,cid,status='running')
    calls=[];ops=[];owned={};pending=[0]
    def ask(messages,tools,response_schema):
        assert messages[0]['content']==rt.PROMPT and tools==[]
        props=response_schema['oneOf'][0]['properties']
        return {'message':{'content':json.dumps({'name':props['name']['enum'][0],
            'arguments':{k:v['enum'][0] for k,v in props['arguments']['properties'].items()}})}}
    def execute(name,args,messages,**ctx):
        assert [m for m in messages if m['role']=='user'][-1]['content']==request
        assert messages[-1]['tool_calls'][0]['function']=={'name':name,'arguments':args}
        calls.append((name,deepcopy(args)))
        if name=='knowledge_search':return {'results':[] if scenario=='missing_recipe' else [{'source':rt.SOURCE,'content':'safe-plugin-discovery-v1 main_discovery'}]}
        if name=='browser_open_page':return {'mutation_executed':False}
        if name=='browser_open_agent_tasks_semantic':return {'ci_id':r['ci_id'],'agent_id':r['agent_id']}
        if name==READY:return {**{k:r[k] for k in ['ci_id','agent_id','plugin_name','plugin_version','core_version']},
            'ci_id':'other' if scenario=='wrong_ready' else r['ci_id'],'agent_status':'online','ready':True,
            'load_error_empty_observed':True,'plugin_audit':{'audit_fresh':scenario!='stale'}}
        if name==CREATE:
            op={'operation_id':'op-one','status':'awaiting_verification'};ops.append(op)
            if scenario=='uncertain':op['status']='uncertain';return {'error':'discovery_dispatch_uncertain','executed':False}
            tid=str(uuid.uuid4());owned[tid]={'task_id':tid,'operation_id':op['operation_id'],'executed':True,'mutation_executed':True};return owned[tid]
        if name==READ:
            if scenario=='pending' and not pending[0]:pending[0]+=1;return {'error':'own_discovery_result_not_ready'}
            return {**owned[args['task_id']],'native_result_verified':True,'mutation_executed':False,'response_shape':{'root_type':'str'}}
        raise AssertionError(name)
    def reconcile(jid,opid,eid):ops[0]['status']='verified';return {'verified':True}
    stack.enter_context(patch.object(uqa,'ask_ollama',side_effect=ask))
    stack.enter_context(patch.object(uqa,'execute_tool_with_policy',side_effect=execute))
    stack.enter_context(patch.object(rt,'list_operations',side_effect=lambda jid:deepcopy(ops)))
    stack.enter_context(patch.object(rt,'reconcile_operation',side_effect=reconcile))
    result=uqa.run_turn([{'role':'system','content':uqa.SYSTEM_PROMPT},{'role':'user','content':request}],job_id=jid,case_id=cid,action_policy='confirm_mutations')
    assert result['completed'] is (scenario in {'success','pending'}),result
    if result['completed']:assert result['canonical_report']['business_pass'] is False and result['canonical_report']['plugin_case_status']=='BLOCKED'
    assert len(ops)==(1 if scenario in {'success','pending','uncertain'} else 0)
    if scenario=='pending':
        reads=[a['task_id'] for n,a in calls if n==READ];assert reads[0]==reads[1]
    before=len(calls);again=rt.run(uqa,[{'role':'user','content':request}],jid,cid,'confirm_mutations')
    assert again['started'] is False and len(calls)==before
print('PASS discovery transport fixture: normal typed Core, actual model choice slot, own same-task polling, no delivery/replay/semantic PASS')

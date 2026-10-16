"""Mock model/Core transport fixture, NOT autonomous or live lab acceptance."""
from contextlib import ExitStack
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import json,uuid
import job_store as store,uqa
import plugin_preparation_runtime as rt
from plugin_preparation import requirement,CREATE,READ,READY
from tools.browser import _session

for scenario in ['ready','stale_delivery','uncertain','pending','wrong_ready']:
  with TemporaryDirectory() as tmp,ExitStack() as stack:
    stack.enter_context(patch.object(store,'JOBS_DIR',Path(tmp)))
    stack.enter_context(patch.object(_session,'reset_case_context'));stack.enter_context(patch.object(_session,'close'))
    r=requirement('astra','checkAlive','uqa-preparation-runtime-fixture')
    request='Подготовь '+ ' '.join(r[k] for k in ['ci_id','agent_id','ci_name','core_version','plugin_name','plugin_version','profile_id'])
    j=store.create_job(request,stand='lab',job_type='manual');jid=j['job_id']
    c=store.add_test_case(jid,'Fixture only',requirement=r);cid=c['case_id']
    store.set_job_status(jid,'running');store.update_test_case(jid,cid,status='running')
    calls=[];ops=[];owned={};pending=[0]
    def ready(fresh,loaded):
        return {'ci_id':r['ci_id'],'agent_id':r['agent_id'],'plugin_name':r['plugin_name'],'plugin_version':r['plugin_version'],
            'core_version':'1.3.27','agent_status':'online','ready':fresh and loaded,'load_error_empty_observed':True,
            'plugin_audit':{'audit_fresh':fresh,'matched_plugins':[{'version':r['plugin_version'] if loaded else '1.2.25'}]}}
    def ask(messages,tools,response_schema):
        assert messages[0]['content']==rt.PROMPT and tools==[]
        if 'oneOf' in response_schema:
            properties=response_schema['oneOf'][0]['properties']
            return {'message':{'content':json.dumps({'name':properties['name']['enum'][0],
                'arguments':{k:v['enum'][0] for k,v in properties['arguments']['properties'].items()}})}}
        return {'message':{'content':json.dumps({'preparation_status':'PASS','plugin_case_status':'BLOCKED','summary':'Prepared loaded only, main plugin not tested.'})}}
    def execute(name,args,messages,**ctx):
        assert [m for m in messages if m['role']=='user'][-1]['content']==request
        assert messages[-1]['tool_calls'][0]['function']=={'name':name,'arguments':args}
        calls.append((name,deepcopy(args)))
        if name=='knowledge_search':return {'results':[{'source':rt.SOURCE,'content':'safe-plugin-preparation-v1 initial_inventory delivery post_inventory'}]}
        if name=='browser_open_page':return {'mutation_executed':False}
        if name=='browser_open_agent_tasks_semantic':return {'ci_id':r['ci_id'],'agent_id':r['agent_id']}
        if name==READY:
            x=ready(scenario=='ready' or scenario=='wrong_ready',scenario in {'ready','wrong_ready'})
            if scenario=='wrong_ready':x['ci_id']='other'
            return x
        if name==CREATE:
            op={'operation_id':'op-'+str(len(ops)),'stage_id':args['stage_id'],'status':'awaiting_verification'};ops.append(op)
            if scenario=='uncertain':op['status']='uncertain';return {'error':'preparation_dispatch_uncertain','dispatch_may_have_occurred':True,'executed':False}
            tid=str(uuid.uuid4());out={'task_id':tid,'stage_id':args['stage_id'],'operation_id':op['operation_id'],'mutation_executed':True,'executed':True}
            owned[tid]=out;return out
        if name==READ:
            if scenario=='pending' and not pending[0]:pending[0]+=1;return {'error':'own_preparation_result_not_ready','native_result_verified':False}
            out={**owned[args['task_id']],'native_result_verified':True,'mutation_executed':False}
            if out['stage_id']!='delivery':out['plugin_readiness']=ready(True,out['stage_id']=='post_inventory')
            return out
        raise AssertionError(name)
    def reconcile(jid,opid,eid):
        next(o for o in ops if o['operation_id']==opid)['status']='verified';return {'verified':True}
    stack.enter_context(patch.object(uqa,'ask_ollama',side_effect=ask))
    stack.enter_context(patch.object(uqa,'execute_tool_with_policy',side_effect=execute))
    stack.enter_context(patch.object(rt,'list_operations',side_effect=lambda jid:deepcopy(ops)))
    stack.enter_context(patch.object(rt,'reconcile_operation',side_effect=reconcile))
    result=uqa.run_turn([{'role':'system','content':uqa.SYSTEM_PROMPT},{'role':'user','content':request}],
        job_id=jid,case_id=cid,action_policy='confirm_mutations')
    if scenario in {'ready','stale_delivery','pending'}:
        assert result['completed'] is True,result
        assert result['canonical_report']['plugin_case_executed'] is False
        assert len(ops)==(0 if scenario=='ready' else 3)
    else:
        assert result['completed'] is False and not result['canonical_report']
        assert len(ops)==(1 if scenario=='uncertain' else 0)
    if scenario=='pending':
        reads=[a['task_id'] for n,a in calls if n==READ];assert reads[0]==reads[1]
    count=len(calls)
    again=rt.run(uqa,[{'role':'user','content':request}],jid,cid,'confirm_mutations')
    assert again['started'] is False and len(calls)==count
print('PASS preparation model transport fixture: typed run_turn, source/role preservation, conditional stages, same-task poll, uncertainty/no-replay, not main-case PASS')

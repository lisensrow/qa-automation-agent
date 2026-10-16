"""Isolated fake model/Core/browser fixture; not actual model or product acceptance."""
from contextlib import ExitStack
from copy import deepcopy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch
import job_store as store
import uqa
import command_stage_runtime as rt
from command_stage_profile import requirement,CREATE,READ
from tools.browser import _session

for scenario in ['already_ready','stale_delivery','uncertain']:
    with TemporaryDirectory() as tmp,ExitStack() as stack:
        stack.enter_context(patch.object(store,'JOBS_DIR',Path(tmp)))
        stack.enter_context(patch.object(_session,'reset_case_context'))
        stack.enter_context(patch.object(_session,'close'))
        req=requirement('windows','uqa-command-fixture')
        request=' '.join(req[k] for k in ['ci_id','agent_id','ci_name','core_version','plugin_name','plugin_version','profile_id'])
        job=store.create_job(request,stand='lab',job_type='manual');jid=job['job_id']
        case=store.add_test_case(jid,'Fixture command cycle',requirement=req);cid=case['case_id']
        store.set_job_status(jid,'running');store.update_test_case(jid,cid,status='running')
        trace=[];ops=[];owned={};polls={};final_attempts=[0]
        def ready(fresh,version):
            return {'ci_id':req['ci_id'],'agent_id':req['agent_id'],'core_version':'1.3.27','agent_status':'online',
                'ready':fresh and version=='1.4.0','plugin_audit':{'audit_fresh':fresh,
                    'matched_plugins':[{'name':'executeCommand','version':version,'load_status':True,'load_error_present':False}]}}
        def ask(messages,tools,response_schema):
            assert tools==[] and messages[0]['content']==rt.PROMPT
            if 'oneOf' in response_schema:
                prop=response_schema['oneOf'][0]['properties'];name=prop['name']['enum'][0]
                args={k:v['enum'][0] for k,v in prop['arguments']['properties'].items()}
                return {'message':{'content':json.dumps({'name':name,'arguments':args})}}
            final_attempts[0]+=1
            return {'message':{'content':json.dumps({'task_id':response_schema['properties']['task_id']['enum'][0],
                'verdict':'BLOCKED','summary':'' if final_attempts[0]==1 else 'Technical marker PASS, full source case BLOCKED.'})}}
        def execute(name,args,messages,**kwargs):
            assert kwargs['job_id']==jid and kwargs['case_id']==cid and kwargs['action_policy']=='confirm_mutations'
            assert [m for m in messages if m.get('role')=='user'][-1]['content']==request
            assert messages[-1].get('tool_calls')==[{'function':{'name':name,'arguments':args}}]
            trace.append((name,deepcopy(args)))
            if name=='knowledge_search':return {'results':[{'source':rt.SOURCE,'content':'initial_inventory post_delivery_inventory'}]}
            if name=='browser_open_page':return {'mutation_executed':False}
            if name=='browser_open_agent_tasks_semantic':return {'ci_id':req['ci_id'],'agent_id':req['agent_id']}
            if name==rt.TELEMETRY:return {'ci_id':req['ci_id'],'agent_id':req['agent_id'],'agent_version':'1.3.27'}
            if name==rt.READY:return ready(scenario=='already_ready','1.4.0' if scenario=='already_ready' else '1.2.25')
            if name==CREATE:
                sid=args['stage_id'];op={'operation_id':'op-'+sid,'status':'awaiting_verification'};ops.append(op)
                if scenario=='uncertain':
                    op['status']='uncertain';return {'error':'fixture_uncertain','executed':False,'dispatch_may_have_occurred':True}
                tid='12345678-1234-4234-9234-'+str(len(owned)+1).zfill(12);owned[tid]=sid
                return {'stage_id':sid,'task_id':tid,'operation_id':op['operation_id'],'executed':True,'mutation_executed':True}
            if name==READ:
                tid=args['task_id'];sid=owned[tid];op=next(o for o in ops if o['operation_id']=='op-'+sid)
                if scenario=='stale_delivery' and sid=='execute_command' and not polls.get(tid):
                    polls[tid]=1;return {'error':'own_command_stage_result_not_ready','native_result_verified':False}
                body={'task_id':tid,'operation_id':op['operation_id'],'stage_id':sid,'native_result_verified':True}
                if sid in {'initial_inventory','post_delivery_inventory'}:
                    body['plugin_readiness']=ready(True,'1.2.25' if sid=='initial_inventory' else '1.4.0')
                if sid=='execute_command':body.update(technical_execution_verified=True,expected_marker_sha256='1'*64,error_code=0)
                return body
            raise AssertionError(name)
        def record(jid,cid,name,args,result,**kwargs):
            return store.add_evidence(jid,cid,'fixture_native_tool',json.dumps({'tool':name,'arguments':args,'result':result}),
                source='uqa_tool',execution_status='observed',usable_for_pass=False,usable_for_verdict=False)
        def reconcile(jid,opid,eid):
            next(o for o in ops if o['operation_id']==opid)['status']='verified'
            return {'verified':True,'evidence_id':eid,'business_pass':False}
        stack.enter_context(patch.object(rt,'list_operations',side_effect=lambda jid:deepcopy(ops)))
        stack.enter_context(patch.object(rt,'reconcile_operation',side_effect=reconcile))
        api=SimpleNamespace(SYSTEM_PROMPT='fixture generic',get_job=store.get_job,ask_ollama=ask,
            execute_tool_with_policy=execute,record_tool_observations=lambda *args:[],record_tool_evidence=record,
            tool_result_for_model=lambda name,result:result)
        messages=[{'role':'system','content':api.SYSTEM_PROMPT},{'role':'user','content':request}]
        with patch.object(rt,'run',return_value={'started':True,'completed':False,'reason':'fixture_route'}) as route:
            routed=uqa.run_turn(deepcopy(messages),job_id=jid,case_id=cid,action_policy='confirm_mutations')
            assert routed['reason']=='fixture_route';route.assert_called_once()
        out=rt.run(api,messages,jid,cid,'confirm_mutations')
        actual=[args['stage_id'] for name,args in trace if name==CREATE]
        if scenario=='uncertain':
            assert not out['completed'] and len(actual)==1 and ops[0]['status']=='uncertain'
        else:
            assert out['completed'],out
            assert actual==(['execute_command'] if scenario=='already_ready' else
                ['initial_inventory','deliver_command_plugin','post_delivery_inventory','execute_command'])
            assert final_attempts[0]==2 and all(o['status']=='verified' for o in ops)
            assert store.get_job(jid)['status']=='blocked' and out['technical_status']=='PASS'
        count=len(trace)
        assert rt.run(api,messages,jid,cid,'confirm_mutations')['started'] is False
        assert len(trace)==count
print('PASS command model-runtime fixtures: ready skip, stale refresh/deliver/refresh/main, same-task poll, '
      'uncertain STOP, bounded final-only repair, full-case BLOCKED and no replay; no real model/UC actions')

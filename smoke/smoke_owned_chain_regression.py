"""Isolated Core/journal/new-object chain; no lab, network, model or logs."""
from contextlib import ExitStack
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4
import hashlib, json
import uqa, job_store as store, owned_chain_regression as p
from tools.registry import execute_tool
from operation_journal import list_operations, reconcile_operation

def main():
    for name in ('windows','astra'):
        with TemporaryDirectory() as tmp, ExitStack() as stack:
            assert p.WRITES_ENABLED is False
            stack.enter_context(patch.object(p,'WRITES_ENABLED',True))
            stack.enter_context(patch.object(store,'JOBS_DIR',Path(tmp)))
            schema=b'isolated-schema'; stack.enter_context(patch.object(p,'SCHEMA_SHA',hashlib.sha256(schema).hexdigest()))
            key='US-T93' if name=='windows' else 'US-T115';sha='a'*64
            stack.enter_context(patch.object(p,'load',return_value=({}, {'json_sha256':sha}, {})))
            sj=store.create_job(key,stand='lab',job_type='manual')
            sc=store.add_test_case(sj['job_id'],'Source fixture',requirement={'case_key':key,'source_sha256':sha,
                'type':'owned_regression_source_read','locked':True,'action_profile':'read_only','source_manifest_sha256':p.MANIFEST_SHA})
            store.add_evidence(sj['job_id'],sc['case_id'],'knowledge_inspect_own_regression_read_coverage',
                json.dumps({'tool':'knowledge_inspect_own_regression_read_coverage','result':{
                    'case_key':key,'source_sha256':sha,'source_manifest_sha256':p.MANIFEST_SHA,'complete_case_source_content_read':True}}),source='uqa_tool')
            r=p.requirement(name,'uqa-chain-fixture-'+name,[sj['job_id'],sc['case_id']])
            req='Создай новую цепочку и выполни три безопасных аудита '+ ' '.join(r[k] for k in
                ('ci_id','agent_id','ci_name','core_version','campaign_id','source_case'))
            j=store.create_job(req,stand='lab',job_type='manual');jid=j['job_id']
            c=store.add_test_case(jid,'Owned chain fixture',requirement=r);cid=c['case_id']
            store.set_job_status(jid,'running');store.update_test_case(jid,cid,status='running')
            messages=[{'role':'user','content':req}];ctx={'job_id':jid,'case_id':cid,'action_policy':'confirm_mutations'}
            for tool in (p.CREATE,p.READ,p.READY):
                assert execute_tool(tool,{'target':name}).get('executed') is False
            assert uqa.classify_tool_action(p.CREATE,{})=='write'
            assert uqa.classify_tool_action(p.READ,{})=='observe'
            with patch.object(uqa,'read_user_input',side_effect=AssertionError('must not prompt')):
                out=uqa.execute_tool_with_policy(p.CREATE,{'target':name,'stage_id':'stage1'},messages,force_read_only=True,**ctx)
                assert out['executed'] is False
            assert not list_operations(jid)
            objects={};links={};posts=[];html_routes=[False]
            class Response:
                def __init__(self,status,body):self.status=status;self.value=deepcopy(body)
                def json(self):return deepcopy(self.value)
                def body(self):return schema
            def get(url,params=None,timeout=None):
                if url.endswith('/openapi.json'):return Response(200,{})
                path=url.removeprefix(p.ORIGIN)
                if html_routes[0] and path in ('/api/v1/stages','/api/v1/pipelines','/api/v1/jobs'):
                    class Html:
                        status=200
                        def body(self):return b'<html>not JSON</html>'
                        def json(self):raise ValueError('not JSON')
                    return Html()
                if path=='/api/v1/jobs':return Response(200,{'items':[],'total':0})
                if path.endswith('/tasks'):return Response(200,{'items':[],'total':0})
                if path=='/api/v1/job-instance/stages':return Response(200,{'items':[],'total':0,'offset':0})
                if path=='/api/v1/agents/'+r['agent_id']:return Response(200,{'id':r['agent_id'],'version':'1.3.27','status':'online'})
                if path in ('/api/v1/stages','/api/v1/pipelines'):
                    return Response(200,{'items':[b for k,b in objects.items() if k.startswith(path+'/') and b.get('name')==params['name']],
                                         'total':sum(k.startswith(path+'/') and b.get('name')==params['name'] for k,b in objects.items())})
                if path.endswith('/stages'):return Response(200,links[path])
                return Response(200,objects[path])
            def post(url,data=None,timeout=None):
                path=url.removeprefix(p.ORIGIN);posts.append((path,deepcopy(data)))
                oid=str(uuid4())
                if path in ('/api/v1/stages','/api/v1/pipelines'):
                    body={'id':oid,**data,'created_at':p.now()};objects[path+'/'+oid]=body
                    return Response(201,body)
                if path.endswith('/add-stages'):
                    body=[{**objects['/api/v1/stages/'+b['stage_id']],'order':b['order']} for b in data]
                    links[path.removesuffix('/add-stages')+'/stages']=body;return Response(200,body)
                if path=='/api/v1/jobs':
                    body={'id':oid,**data,'crontab_schedule_id':None,'is_enabled':True}
                    objects[path+'/'+oid]=body;return Response(200,body)
                assert path.endswith('/run') and data is None
                body={'id':oid,'job_id':path.split('/')[-2],'status':'created','created_at':p.now()}
                objects['/api/v1/job-instance/'+oid]=body;return Response(200,body)
            session=SimpleNamespace(session_id='isolated',context=SimpleNamespace(request=SimpleNamespace(get=get,post=post)),
                inspect_pinned_agent_readiness_semantic=lambda *a:{'ready':True})
            t=p.target(name);urls=[p.ORIGIN+'/api/v1/agents/'+r['agent_id']+'/tasks',p.ORIGIN+'/api/v1/agents/'+r['agent_id'],'unused']
            stack.enter_context(patch.object(p,'context',return_value=(t,{},urls)))
            stack.enter_context(patch.object(p,'validate_target_state',return_value=None))
            stack.enter_context(patch('tools.browser._session',session))
            stack.enter_context(patch.object(uqa,'managed_action_policy_decision',return_value={'allow':True,'status':'isolated'}))
            stack.enter_context(patch.object(uqa,'read_user_input',return_value='y'))
            assert p.ready(session,name,jid,cid)['ready']
            html_routes[0]=True
            assert p.ready(session,name,jid,cid)['reason']=='legacy_chain_routes_not_json'
            refused=uqa.execute_tool_with_policy(p.CREATE,{'target':name,'stage_id':'stage1'},messages,**ctx)
            assert refused.get('executed') is False and refused['operation_status']=='not_sent' and not posts
            html_routes[0]=False
            bad=uqa.execute_tool_with_policy(p.CREATE,{'target':name,'stage_id':'stage1','object_id':str(uuid4())},messages,**ctx)
            assert bad.get('executed') is False and not posts
            for sid in p.STAGES:
                args={'target':name,'stage_id':sid}
                out=uqa.execute_tool_with_policy(p.CREATE,args,messages,**ctx)
                assert out.get('executed') is True,out
                uqa.record_tool_evidence(jid,cid,p.CREATE,args,out)
                result=uqa.execute_tool_with_policy(p.READ,args,messages,**ctx)
                assert result.get('native_readback_verified') is True,result
                ev=uqa.record_tool_evidence(jid,cid,p.READ,args,result)
                proof=reconcile_operation(jid,out['operation_id'],ev['evidence_id'])
                assert proof['verified'] and proof['business_pass'] is False,proof
                assert uqa.execute_tool_with_policy(p.CREATE,args,messages,**ctx).get('executed') is False
            assert len(posts)==7 and all(o['status'] in {'verified','not_sent'} for o in list_operations(jid))
            assert sum(o['status']=='verified' for o in list_operations(jid))==7
            with patch.object(p,'WRITES_ENABLED',False),patch.object(uqa,'read_user_input',side_effect=AssertionError('retired must not prompt')):
                assert not uqa.execute_tool_with_policy(p.CREATE,{'target':name,'stage_id':'stage1'},messages,**ctx).get('executed')
            assert len(posts)==7
            case=store.get_job(jid)['test_cases'][0]
            path,payload,_=p.compile_request(r,case,'job')
            assert path=='/api/v1/jobs' and payload['default_agent_id']==r['agent_id']
            assert payload['crontab_schedule'] is None and payload['ignore_agent_status'] is False
            original=r['agent_id'];r['agent_id']='other'
            try:p.check_object(r,case,'job',{'id':str(uuid4()),**payload},payload);raise AssertionError('wrong agent accepted')
            except ValueError:pass
            r['agent_id']=original
            instance=p.identifier(case,'run');pipeline=p.identifier(case,'pipeline')
            history={'items':[{'job_instance_id':instance,'status':'success','result':{'data':[]},
                'pipeline_stage':{'pipeline_id':pipeline,'stage_id':p.identifier(case,'stage'+str(i)),'order':i},
                'stage':objects['/api/v1/stages/'+p.identifier(case,'stage'+str(i))]} for i in (1,2,3)],'total':3,'offset':0}
            summary=p.summarize_history(r,case,instance,history)
            assert summary['complete'] and not summary['agent_logs_verified']
            for field in ['instance','pipeline','order','task']:
                bad=deepcopy(history)
                if field=='instance':bad['items'][0]['job_instance_id']=str(uuid4())
                elif field=='pipeline':bad['items'][0]['pipeline_stage']['pipeline_id']=str(uuid4())
                elif field=='order':bad['items'][0]['pipeline_stage']['order']=2
                else:bad['items'][0]['stage']['detail']['task_name']='executeCommand'
                try:p.summarize_history(r,case,instance,bad);raise AssertionError('wrong linkage accepted')
                except ValueError:pass
    print('PASS owned chain isolated Core/policy/source/scope/new objects/three fixed audits/own GET/ordered links/no schedule/no replay; not real regression')

if __name__=='__main__':main()

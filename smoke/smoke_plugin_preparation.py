"""Isolated native/Core/recovery checks; never a live delivery or model PASS."""
from contextlib import ExitStack
from copy import deepcopy
from datetime import datetime,timezone,timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch
import json,uuid
import uqa,job_store as store,plugin_preparation as p
import plugin_preparation_recovery as recovery
from operation_journal import list_operations,reconcile_operation,_fingerprint
from tools.registry import execute_tool

class Response:
    def __init__(self,status,body):self.status,self.body=status,body
    def json(self):return deepcopy(self.body)

def rejected(fn,*args):
    try:fn(*args)
    except (ValueError,KeyError,TypeError):return
    raise AssertionError('unsafe profile admitted')

for name in ['windows','astra']:
  for plugin in p.VERSIONS:
    r=p.requirement(name,plugin,'uqa-preparation-fixture')
    request='Подготовь safe plugin: '+' '.join(r[k] for k in ['ci_id','agent_id','ci_name','core_version','plugin_name','plugin_version','profile_id'])
    assert uqa.classify_tool_action(p.CREATE,{})=='write' and uqa.classify_tool_action(p.READ,{})=='observe'
    assert execute_tool(p.CREATE,{'target':name})['executed'] is False
    with TemporaryDirectory() as tmp,ExitStack() as stack:
        stack.enter_context(patch.object(store,'JOBS_DIR',Path(tmp)))
        j=store.create_job(request,stand='lab',job_type='manual');jid=j['job_id']
        c=store.add_test_case(jid,'Preparation fixture',requirement=r);cid=c['case_id']
        store.set_job_status(jid,'running');store.update_test_case(jid,cid,status='running')
        rejected(p.requirement,name,'executeCommand','fixture');rejected(p.requirement,name,'trayControl','fixture')
        rejected(p.requirement,'ubuntu',plugin,'fixture')
        args={'target':name,'plugin_name':plugin,'stage_id':'initial_inventory'}
        rejected(p.admitted_write,store.get_job(jid),cid,{**args,'version':'0.0.0'})
        bad=store.get_job(jid);bad['test_cases'][0]['requirement']['plugin_version']='0.0.0'
        rejected(p.validate_context,bad,cid)
        ci={'id':r['ci_id'],'name':r['ci_name'],'agent_id':r['agent_id'],
            'detail':{'os':{'name':'Windows 10' if name=='windows' else 'Astra Linux','architecture':'64'}}}
        agent={'id':r['agent_id'],'version':'1.3.27','status':'online'}
        at=lambda:(datetime.now(timezone.utc)).isoformat()
        audit={'agent_id':r['agent_id'],'last_audit_at':(datetime.now(timezone.utc)-timedelta(hours=2)).isoformat(),
            'detail':[{'plugin_name':plugin,'plugin_version':'1.2.25','load_status':True,'load_error':''}]}
        tasks={};posts=[];after_send_bad=[False];wrong_full=[False]
        base=p.ORIGIN+'/api/v1/agents/'+r['agent_id']
        def get(url,params=None,timeout=None):
            if url==base:return Response(200,agent)
            if url==base+'/plugin':return Response(200,audit)
            if url.endswith('/full'):
                full=deepcopy(tasks[url.split('/')[-2]])
                if wrong_full[0]:full['result']['machine_uid']='other'
                return Response(200,full)
            if url==base+'/tasks':
                items=[x for x in tasks.values() if x['name']==params['name']]
                return Response(200,{'items':items,'total':len(items),'offset':0})
            raise AssertionError('unexpected GET')
        def post(url,data,timeout):
            posts.append((url,deepcopy(data)));sid='delivery' if url.endswith('/update') else 'inventory'
            tid=str(uuid.uuid4());task='managePlugin' if sid=='delivery' else 'pluginAudit'
            params=deepcopy(data if sid=='delivery' else data['additional_params'])
            if sid=='delivery':
                assert data=={'plugins_to_update':[{'plugin_name':plugin,'plugin_version':r['plugin_version']}],
                    'plugins_to_delete':[],'check_endpoint_os_version':True}
                audit['detail'][0]['plugin_version']=r['plugin_version']
                payload={'plugins_downloaded':[{'plugin_name':plugin,'size_bytes':100}],'plugins_scheduled_for_deletion':[]}
            else:audit['last_audit_at']=at();payload={}
            receipt={'id':tid,'name':task,'agent_id':r['agent_id'],'period':None,'additional_params':params,'created_at':at()}
            tasks[tid]={**receipt,'status':'success','result':{'result':'success','machine_uid':r['ci_id'],'processed_at':at(),'data':payload}}
            if after_send_bad[0]:receipt['additional_params']={'bad':True}
            return Response(202 if sid=='delivery' else 201,receipt)
        session=SimpleNamespace(session_id='fake-session',_ensure_started=lambda:None,
            _observed_agent_task_context=lambda name:(ci,{},base+'/tasks?limit=25',None),
            _same_https_origin_url=lambda observed,path:p.ORIGIN+path,
            context=SimpleNamespace(request=SimpleNamespace(get=get,post=post)))
        stack.enter_context(patch('tools.browser._session',session))
        # Hash check gets only an in-memory XLSX sentinel, never the real file.
        stack.enter_context(patch.object(p.Path,'read_bytes',return_value=b'fixture-workbook'))
        stack.enter_context(patch.object(p,'BOOK_SHA',p.hashlib.sha256(b'fixture-workbook').hexdigest()))
        if plugin=='displayMonitoring':
            stack.enter_context(patch.object(p,'validate_release_source',return_value=True))
        # BOOK_SHA participates in immutable profile; rebuild the fixture after patching.
        r=p.requirement(name,plugin,'uqa-preparation-fixture')
        changed=store.get_job(jid);changed['test_cases'][0]['requirement']=r;store.save_job(changed)
        messages=[{'role':'user','content':request}];ctx={'job_id':jid,'case_id':cid,'action_policy':'confirm_mutations'}
        assert uqa.execute_tool_with_policy(p.CREATE,args,messages,force_read_only=True,**ctx).get('error')=='tool_policy_blocked'
        assert not posts and not list_operations(jid)
        assert uqa.execute_tool_with_policy(p.CREATE,{**args,'plugin_name':'trayControl'},messages,**ctx).get('error')=='locked_plugin_preparation_scope_required'
        stack.enter_context(patch.object(uqa,'managed_action_policy_decision',return_value={'allow':True,'status':'fixture_only'}))
        for sid in ['initial_inventory','delivery','post_inventory']:
            args={'target':name,'plugin_name':plugin,'stage_id':sid}
            out=uqa.execute_tool_with_policy(p.CREATE,args,messages,**ctx)
            assert out.get('executed') is True,(sid,out)
            observations=uqa.record_tool_observations(jid,cid,p.CREATE,args,out)
            uqa.record_tool_evidence(jid,cid,p.CREATE,args,out,observation_ids=[o['observation_id'] for o in observations])
            readargs={'target':name,'plugin_name':plugin,'task_id':out['task_id']}
            assert not p.read(session,name,plugin,str(uuid.uuid4()),jid,cid)['native_result_verified']
            wrong_full[0]=True;assert not p.read(session,name,plugin,out['task_id'],jid,cid)['native_result_verified'];wrong_full[0]=False
            read=uqa.execute_tool_with_policy(p.READ,readargs,messages,**ctx)
            assert read.get('native_result_verified') is True,read
            ob=uqa.record_tool_observations(jid,cid,p.READ,readargs,read)
            e=uqa.record_tool_evidence(jid,cid,p.READ,readargs,read,observation_ids=[o['observation_id'] for o in ob])
            assert reconcile_operation(jid,read['operation_id'],e['evidence_id'])['verified'] is True
            saved=store.get_job(jid);op=next(o for o in list_operations(jid) if o['operation_id']==read['operation_id'])
            contract=next(s['verification'] for s in r['operation_stages'] if s['stage_id']==sid)
            for field,value in [('source','llm'),('execution_status','declared')]:
                tampered=deepcopy(saved)
                next(x for x in tampered['test_cases'][0]['evidence'] if x['evidence_id']==e['evidence_id'])[field]=value
                assert recovery.evaluate(tampered,op,e['evidence_id'],contract)['verified'] is False
            tampered=deepcopy(saved);ev=next(x for x in tampered['test_cases'][0]['evidence'] if x['evidence_id']==e['evidence_id'])
            body=json.loads(ev['value']);body['result']['session_id']='other';ev['value']=json.dumps(body)
            assert recovery.evaluate(tampered,op,e['evidence_id'],contract)['verified'] is False
            count=len(posts);again=uqa.execute_tool_with_policy(p.CREATE,args,messages,**ctx)
            assert len(posts)==count and again.get('executed') is False
        assert len(posts)==3 and all(o['status']=='verified' for o in list_operations(jid))
        ready=uqa.execute_tool_with_policy(p.READY,{'target':name,'plugin_name':plugin},messages,**ctx)
        assert ready['ready'] is True and ready['business_pass'] is False
        saved_error=audit['detail'][0].pop('load_error')
        assert p.readiness(session,r)['ready'] is False
        audit['detail'][0]['load_error']=saved_error
        # Receipt failure AFTER one fake POST is uncertain and never resent.
        j2=store.create_job(request,stand='lab',job_type='manual');jid2=j2['job_id']
        c2=store.add_test_case(jid2,'Fake uncertain receipt',requirement=r);cid2=c2['case_id']
        store.set_job_status(jid2,'running');store.update_test_case(jid2,cid2,status='running')
        ctx2={'job_id':jid2,'case_id':cid2,'action_policy':'confirm_mutations'}
        audit['last_audit_at']=(datetime.now(timezone.utc)-timedelta(hours=2)).isoformat();after_send_bad[0]=True
        args={'target':name,'plugin_name':plugin,'stage_id':'initial_inventory'}
        before=len(posts);out=uqa.execute_tool_with_policy(p.CREATE,args,messages,**ctx2)
        assert out.get('operation_status')=='uncertain' and len(posts)==before+1,out
        again=uqa.execute_tool_with_policy(p.CREATE,args,messages,**ctx2)
        assert again.get('executed') is False and len(posts)==before+1
        assert list_operations(jid2)[0]['status']=='uncertain'
print(f'PASS preparation native/Core/recovery: exact2targets/{len(p.VERSIONS)}plugins/3stages, unchanged policy, durable intents, own results and loaded only')

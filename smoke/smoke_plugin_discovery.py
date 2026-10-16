"""Isolated HTTP/Core/journal fixture, no live tasks or LLM acceptance."""
from contextlib import ExitStack
from copy import deepcopy
from datetime import datetime,timezone,timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch
import json,uuid
import uqa,job_store as store,plugin_discovery as p
from operation_journal import list_operations,reconcile_operation
from tools.registry import execute_tool

class Response:
    def __init__(self,status,body):self.status,self.body=status,body
    def json(self):return deepcopy(self.body)

def rejected(fn,*args):
    try:fn(*args)
    except (ValueError,KeyError,TypeError):return
    raise AssertionError('unsafe discovery admitted')

for name in ['windows','astra']:
  for plugin in p.VERSIONS:
    r=p.requirement(name,plugin,'discovery-fixture')
    request='Observe '+' '.join(r[k] for k in ['ci_id','agent_id','ci_name','core_version','plugin_name','plugin_version','profile_id'])
    assert uqa.classify_tool_action(p.CREATE,{})=='write'
    assert uqa.classify_tool_action(p.READ,{})==uqa.classify_tool_action(p.READY,{})=='observe'
    assert execute_tool(p.CREATE,{})['executed'] is False
    with TemporaryDirectory() as tmp,ExitStack() as stack:
        stack.enter_context(patch.object(store,'JOBS_DIR',Path(tmp)))
        j=store.create_job(request,stand='lab',job_type='manual');jid=j['job_id']
        c=store.add_test_case(jid,'Discovery fixture',requirement=r);cid=c['case_id']
        store.set_job_status(jid,'running');store.update_test_case(jid,cid,status='running')
        rejected(p.requirement,name,'vncServer','fixture');rejected(p.requirement,'ubuntu',plugin,'fixture')
        args=r['operation_stages'][0]['arguments']
        rejected(p.admitted_write,store.get_job(jid),cid,{**args,'additional_params':{}})
        bad=store.get_job(jid);bad['test_cases'][0]['requirement']['expected_profile']['business_pass']=True
        rejected(p.validate_context,bad,cid)
        at=lambda:datetime.now(timezone.utc).isoformat()
        ci={'id':r['ci_id'],'name':r['ci_name'],'agent_id':r['agent_id'],
            'detail':{'os':{'name':'Windows 10' if name=='windows' else 'Astra Linux','architecture':'64'}}}
        agent={'id':r['agent_id'],'version':'1.3.27','status':'online'}
        audit={'agent_id':r['agent_id'],'last_audit_at':at(),
            'detail':[{'plugin_name':plugin,'plugin_version':r['plugin_version'],'load_status':True,'load_error':''}]}
        tasks={};posts=[];wrong=[False];pending=[False];bad_receipt=[False]
        base=p.ORIGIN+'/api/v1/agents/'+r['agent_id']
        def get(url,params=None,timeout=None):
            if url==base:return Response(200,agent)
            if url==base+'/plugin':return Response(200,audit)
            if url.endswith('/full'):
                full=deepcopy(tasks[url.split('/')[-2]])
                if wrong[0]:full['result']['machine_uid']='other'
                if pending[0]:full['result']=None
                return Response(200,full)
            if url==base+'/tasks':
                items=[x for x in tasks.values() if x['name']==params['name']]
                return Response(200,{'items':items,'total':len(items),'count':len(items),'offset':0,'limit':100})
            raise AssertionError('unexpected GET')
        def post(url,data,timeout):
            assert url==base+'/tasks' and data=={'name':plugin,'period':None,'ttl':None,'run_as_user':'','additional_params':{}}
            posts.append(deepcopy(data));tid=str(uuid.uuid4())
            receipt={'id':tid,'name':plugin,'agent_id':r['agent_id'],'period':None,'additional_params':{},'created_at':at()}
            payload='fixture-fixed-reply' if plugin=='checkAlive' else [{'sensitive-name':'never emitted','port':22}]
            tasks[tid]={**receipt,'status':'success','result':{'result':'success','machine_uid':r['ci_id'],'processed_at':at(),'data':payload}}
            if bad_receipt[0]:receipt['additional_params']={'bad':True}
            return Response(201,receipt)
        session=SimpleNamespace(session_id='fixture-session',_ensure_started=lambda:None,
            _observed_agent_task_context=lambda name:(ci,{},base+'/tasks?limit=25',None),
            _same_https_origin_url=lambda observed,path:p.ORIGIN+path,
            context=SimpleNamespace(request=SimpleNamespace(get=get,post=post)))
        stack.enter_context(patch('tools.browser._session',session))
        stack.enter_context(patch.object(p.Path,'read_bytes',return_value=b'fixture-workbook'))
        stack.enter_context(patch.object(p,'BOOK_SHA',p.hashlib.sha256(b'fixture-workbook').hexdigest()))
        messages=[{'role':'user','content':request}];ctx={'job_id':jid,'case_id':cid,'action_policy':'confirm_mutations'}
        assert uqa.execute_tool_with_policy(p.CREATE,args,messages,force_read_only=True,**ctx).get('error')=='tool_policy_blocked'
        assert not posts and not list_operations(jid)
        assert uqa.execute_tool_with_policy(p.CREATE,{**args,'plugin_name':'vncServer'},messages,**ctx).get('error')=='locked_plugin_discovery_scope_required'
        stack.enter_context(patch.object(uqa,'managed_action_policy_decision',return_value={'allow':True,'status':'fixture_only'}))
        out=uqa.execute_tool_with_policy(p.CREATE,args,messages,**ctx)
        assert out.get('executed') is True,out
        obs=uqa.record_tool_observations(jid,cid,p.CREATE,args,out)
        uqa.record_tool_evidence(jid,cid,p.CREATE,args,out,observation_ids=[o['observation_id'] for o in obs])
        readargs={'target':name,'plugin_name':plugin,'task_id':out['task_id']}
        assert not p.read(session,name,plugin,str(uuid.uuid4()),jid,cid)['native_result_verified']
        wrong[0]=True;assert not p.read(session,name,plugin,out['task_id'],jid,cid)['native_result_verified'];wrong[0]=False
        pending[0]=True;assert p.read(session,name,plugin,out['task_id'],jid,cid)['error']=='own_discovery_result_not_ready';pending[0]=False
        read=uqa.execute_tool_with_policy(p.READ,readargs,messages,**ctx)
        assert read.get('native_result_verified') is True and read['business_pass'] is False,read
        assert 'never emitted' not in json.dumps(read) and 'sensitive-name' not in json.dumps(read)
        ob=uqa.record_tool_observations(jid,cid,p.READ,readargs,read)
        e=uqa.record_tool_evidence(jid,cid,p.READ,readargs,read,observation_ids=[o['observation_id'] for o in ob])
        verified=reconcile_operation(jid,read['operation_id'],e['evidence_id'])
        assert verified['verified'] is True,verified
        saved=store.get_job(jid);op=list_operations(jid)[0];contract=r['operation_stages'][0]['verification']
        for field,value in [('source','llm'),('execution_status','declared')]:
            tampered=deepcopy(saved);ev=next(x for x in tampered['test_cases'][0]['evidence'] if x['evidence_id']==e['evidence_id']);ev[field]=value
            assert p.evaluate(tampered,op,e['evidence_id'],contract)['verified'] is False
        for field,value in [('session_id','other'),('business_pass',True),('task_id',str(uuid.uuid4()))]:
            tampered=deepcopy(saved);ev=next(x for x in tampered['test_cases'][0]['evidence'] if x['evidence_id']==e['evidence_id'])
            body=json.loads(ev['value']);body['result'][field]=value;ev['value']=json.dumps(body)
            assert p.evaluate(tampered,op,e['evidence_id'],contract)['verified'] is False
        assert uqa.execute_tool_with_policy(p.CREATE,args,messages,**ctx).get('executed') is False and len(posts)==1
        audit['detail'][0].pop('load_error');assert p.read_ready(session,name,plugin,jid,cid)['ready'] is False
        audit['detail'][0]['load_error']=''
        # Separate fixture job: malformed post-send receipt stays uncertain/no resend.
        j2=store.create_job(request,stand='lab',job_type='manual');jid2=j2['job_id']
        c2=store.add_test_case(jid2,'Uncertain fixture',requirement=r);cid2=c2['case_id']
        store.set_job_status(jid2,'running');store.update_test_case(jid2,cid2,status='running')
        ctx2={'job_id':jid2,'case_id':cid2,'action_policy':'confirm_mutations'};bad_receipt[0]=True
        out=uqa.execute_tool_with_policy(p.CREATE,args,messages,**ctx2)
        assert out.get('operation_status')=='uncertain',out
        assert uqa.execute_tool_with_policy(p.CREATE,args,messages,**ctx2).get('executed') is False and len(posts)==2
assert p.shape({'x':[1,True,None]})['complete_census'] is True
rejected(p.shape,float('nan'));rejected(p.shape,'x'*1048577)
print('PASS closed main discovery fixture: four scopes, exact POST, own full, independent recovery, no replay, no semantic PASS, redacted census')

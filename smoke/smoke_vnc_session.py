"""Isolated Core/native/recovery VNC fixture, NEVER a real session PASS."""
from contextlib import ExitStack
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4
import json
import uqa,job_store as store,vnc_session as p
from operation_journal import list_operations,reconcile_operation
from tools.registry import execute_tool
def reject(fn,*args):
    try:fn(*args)
    except (ValueError,TypeError,KeyError):return
    raise AssertionError('unsafe accepted')
frame={'desktop_input':False,'syncs':1,'surface_sizes':[{'width':1280,'height':720}],
       'decoded_images':[{'width':1280,'height':720,'bytes':100,'sha256':'a'*64,'mime':'image/png'}]}
assert p.frame_ok(frame)
for bad in [{'desktop_input':True},{'syncs':0},{'decoded_images':[]},{'surface_sizes':[]}]:
    assert not p.frame_ok({**frame,**bad})
for url in ['https://uc.lab.local/websocket-tunnel?token=x','wss://evil.test/websocket-tunnel?token=x',
            'wss://uc.lab.local:9000/websocket-tunnel?token=x','wss://a:b@uc.lab.local/websocket-tunnel?token=x']:
    reject(p.validate_url,url)
p.validate_url('wss://uc.lab.local/guacamole/websocket-tunnel?token=fixture')
assert 'keydown' not in p.FRAME_JS and 'mousedown' not in p.FRAME_JS and 'clipboard' not in p.FRAME_JS
for name in ['windows','astra']:
 r=p.requirement(name,'uqa-vnc-fixture');reject(p.requirement,'ubuntu','fixture')
 assert uqa.classify_tool_action(p.CREATE,{})=='write'
 assert uqa.classify_tool_action(p.READ,{})=='observe'
 assert execute_tool(p.CREATE,{'target':name})['executed'] is False
 with TemporaryDirectory() as tmp,ExitStack() as stack:
    stack.enter_context(patch.object(store,'JOBS_DIR',Path(tmp)))
    request='Запусти VNC сеанс '+' '.join(r[k] for k in ['ci_id','agent_id','ci_name','core_version','profile_id'])
    j=store.create_job(request,stand='lab',job_type='manual');jid=j['job_id']
    c=store.add_test_case(jid,'Fixture VNC',requirement=r);cid=c['case_id']
    store.set_job_status(jid,'running');store.update_test_case(jid,cid,status='running')
    args={'target':name};reject(p.admit,store.get_job(jid),cid,{**args,'url':'bad'})
    ci={'id':r['ci_id'],'name':r['ci_name'],'agent_id':r['agent_id'],
        'detail':{'os':{'name':'Windows 10' if name=='windows' else 'Astra Linux','architecture':'64'}}}
    base=p.ORIGIN+'/api/v1/agents/'+r['agent_id'];tasks={};posts=[];wrong=[False]
    class Response:
        def __init__(self,status,body):self.status,self.body=status,body
        def json(self):return deepcopy(self.body)
    def get(url,params=None,timeout=None):
        if url==base:return Response(200,{'id':r['agent_id'],'version':'1.3.27','status':'online'})
        if url==base+'/tasks':
            items=[x for x in tasks.values() if x['name']==params['name']]
            return Response(200,{'items':items,'total':len(items),'offset':0})
        if url.endswith('/full'):
            b=deepcopy(tasks[url.split('/')[-2]])
            if wrong[0]:b['agent_id']=str(uuid4())
            return Response(200,b)
        raise AssertionError('unexpected GET '+url)
    def post(url,params,timeout):
        assert url==base+'/remote/vnc' and params=={'remote_user_session':'_ACTIVE_USER_'}
        posts.append(url);sid=str(uuid4())
        for task in p.TASKS:
            tid=str(uuid4());tasks[tid]={'id':tid,'name':task,'agent_id':r['agent_id'],'period':None,
                'run_as_user':'_ACTIVE_USER_','status':'success','additional_params':{'session_id':sid},'created_at':p.now()}
        return Response(200,{'url':'wss://uc.lab.local/guacamole/websocket-tunnel?token=private-fixture',
           'info':{'display_info':{'displays':[{}],'processed_at':p.now()}}})
    session=SimpleNamespace(session_id='fixture',_ensure_started=lambda:None,
        _observed_agent_task_context=lambda name:(ci,{},base+'/tasks?limit=25',None),
        _same_https_origin_url=lambda observed,path:p.ORIGIN+path,
        context=SimpleNamespace(request=SimpleNamespace(get=get,post=post)),
        page=SimpleNamespace(evaluate=lambda code,url:deepcopy(frame)))
    stack.enter_context(patch('tools.browser._session',session))
    stack.enter_context(patch.object(p,'validate_release_source',return_value=True))
    stack.enter_context(patch.object(p,'readiness',return_value={
        'ready':True,'load_error_empty_observed':True,'plugin_audit':{'audit_fresh':True}}))
    messages=[{'role':'user','content':request}];ctx={'job_id':jid,'case_id':cid,'action_policy':'confirm_mutations'}
    with patch.object(uqa,'read_user_input',side_effect=AssertionError('strict read-only must not prompt')):
        assert uqa.execute_tool_with_policy(p.CREATE,args,messages,force_read_only=True,**ctx).get('error')=='tool_policy_blocked'
    assert not posts and not list_operations(jid)
    assert uqa.execute_tool_with_policy(p.CREATE,{'target':'ubuntu'},messages,**ctx).get('error')=='locked_vnc_scope_required'
    stack.enter_context(patch.object(uqa,'managed_action_policy_decision',return_value={'allow':True,'status':'fixture_only'}))
    out=uqa.execute_tool_with_policy(p.CREATE,args,messages,**ctx)
    assert out.get('executed') is True,out
    assert len(posts)==1 and out['frame_verified'] is True and 'private-fixture' not in json.dumps(out)
    create_ev=uqa.record_tool_evidence(jid,cid,p.CREATE,args,out)
    wrong[0]=True
    assert p.read(session,name,jid,cid).get('error')=='own_vnc_full_identity_required'
    wrong[0]=False
    result=uqa.execute_tool_with_policy(p.READ,args,messages,**ctx);assert result.get('native_result_verified') is True,result
    ev=uqa.record_tool_evidence(jid,cid,p.READ,args,result)
    op=list_operations(jid)[0];proof=reconcile_operation(jid,op['operation_id'],ev['evidence_id'])
    assert proof['verified'] is True and proof['frame_verified'] is True,proof
    assert uqa.execute_tool_with_policy(p.CREATE,args,messages,**ctx).get('executed') is not True
    assert len(posts)==1
    b=deepcopy(result);b['agent_id']='bad';fake=uqa.record_tool_evidence(jid,cid,p.READ,args,b)
    assert not p.evaluate(store.get_job(jid),op,fake['evidence_id'],r['operation_stages'][0]['verification'])['verified']
    before={t:{'items':[],'total':0} for t in p.TASKS}
    after={t:{'items':[x for x in tasks.values() if x['name']==t],'total':1} for t in p.TASKS}
    p.linked_receipts(name,before,after,p.now(),p.now())
    b=deepcopy(after);b[p.TASKS[1]]['items'][0]['additional_params']['session_id']=str(uuid4())
    reject(p.linked_receipts,name,before,b,p.now(),p.now())
print('PASS VNC closed source/OS/identity/policy/journal/linked pair/private URL/frame metadata/recovery/no replay; fixture only')

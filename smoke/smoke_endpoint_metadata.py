"""Isolated fixed metadata payload/Core/recovery; no endpoint command runs."""
from contextlib import ExitStack
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4
import json
import uqa,job_store as store,endpoint_metadata as p
from tools.registry import execute_tool
from operation_journal import list_operations,reconcile_operation
def reject(fn,*args):
 try:fn(*args)
 except (ValueError,TypeError,KeyError):return
 raise AssertionError('unsafe accepted')
file={'id':'a'*64,'size':20,'mtime_ns':100}
body={'probe_version':1,'sample_interval_seconds':5,
 'first':{'status':'ok','bounded':True,'files':[file]},
 'second':{'status':'ok','bounded':True,'files':[{**file,'size':21,'mtime_ns':200}]},
 'tray':{'autostart_entry_present':True,'declared_script_present':True,'process_candidates':1,'process_scan_complete':True}}
summary=p.summarize(body);assert summary['logging_status']=='PASS' and not summary['tray_desktop_verified']
for change in ['no_change','missing','denied','truncated','empty']:
 b=deepcopy(body)
 if change=='no_change':b['second']=deepcopy(b['first'])
 elif change=='truncated':b['second']['bounded']=False
 elif change=='empty':b['first']['files']=[];b['second']['files']=[]
 else:b['second']['status']=change
 assert p.summarize(b)['logging_status']=='BLOCKED'
reject(p.summarize,{**body,'extra':'raw logs'})
reject(p.requirement,'ubuntu','fixture')
assert p.PAYLOAD['additional_params']=={'programm':'/usr/bin/python3','arguments':['-c',p.CODE]}
assert not any(x in p.CODE for x in ['os.remove','unlink(','chmod(','subprocess','system(','open(ROOT,\'w','write('])
for name in ['windows','astra']:
 r=p.requirement(name,'uqa-endpoint-fixture')
 assert uqa.classify_tool_action(p.CREATE,{})=='write' and uqa.classify_tool_action(p.READ,{})=='observe'
 assert not execute_tool(p.CREATE,{'target':name})['executed']
 with TemporaryDirectory() as tmp,ExitStack() as stack:
  stack.enter_context(patch.object(store,'JOBS_DIR',Path(tmp)))
  req='Запусти агентскую задачу '+' '.join(r[k] for k in ['ci_id','agent_id','ci_name','core_version','profile_id'])
  j=store.create_job(req,stand='lab',job_type='manual');jid=j['job_id']
  c=store.add_test_case(jid,'Fixture metadata',requirement=r);cid=c['case_id']
  store.set_job_status(jid,'running');store.update_test_case(jid,cid,status='running')
  args={'target':name};reject(p.admit,store.get_job(jid),cid,{**args,'program':'other'})
  messages=[{'role':'user','content':req}];ctx={'job_id':jid,'case_id':cid,'action_policy':'confirm_mutations'}
  with patch.object(uqa,'read_user_input',side_effect=AssertionError('must not prompt')):
   assert uqa.execute_tool_with_policy(p.CREATE,args,messages,force_read_only=True,**ctx)['error']=='tool_policy_blocked'
  assert not list_operations(jid)
  ci={'id':r['ci_id'],'name':r['ci_name'],'agent_id':r['agent_id'],
      'detail':{'os':{'name':'Windows 10' if name=='windows' else 'Astra Linux','architecture':'64'}}}
  base=p.ORIGIN+'/api/v1/agents/'+r['agent_id'];tasks={};posts=[];wrong=[False]
  class Response:
   def __init__(self,status,body):self.status,self.body=status,body
   def json(self):return deepcopy(self.body)
  def get(url,params=None,timeout=None):
   if url==base:return Response(200,{'id':r['agent_id'],'version':'1.3.27','status':'online'})
   if url==base+'/tasks':return Response(200,{'items':list(tasks.values()),'total':len(tasks),'offset':0})
   if url==base+'/plugin':return Response(200,{})
   if url.endswith('/full'):
    b=deepcopy(tasks[url.split('/')[-2]])
    if wrong[0]:b['result']['machine_uid']='other'
    return Response(200,b)
   raise AssertionError('unexpected GET')
  def post(url,data,timeout):
   assert name=='astra' and url==base+'/tasks' and data==p.PAYLOAD
   posts.append(url);tid=str(uuid4());b={**deepcopy(data),'id':tid,'agent_id':r['agent_id'],'created_at':p.now()}
   tasks[tid]={**b,'status':'success','result':{'machine_uid':r['ci_id'],'processed_at':p.now(),
     'data':{'stdout':json.dumps(body),'stderr':'','errorlevel':0}}}
   return Response(201,b)
  session=SimpleNamespace(session_id='fixture',_ensure_started=lambda:None,
    _observed_agent_task_context=lambda name:(ci,{},base+'/tasks?limit=25',None),
    _same_https_origin_url=lambda observed,path:p.ORIGIN+path,
    context=SimpleNamespace(request=SimpleNamespace(get=get,post=post)))
  stack.enter_context(patch('tools.browser._session',session))
  stack.enter_context(patch.object(p,'validate_release_source',return_value=True))
  stack.enter_context(patch.object(p,'validate_preflight',return_value={'ready':True}))
  stack.enter_context(patch.object(uqa,'managed_action_policy_decision',return_value={'allow':True,'status':'fixture_only'}))
  if name=='windows':
   assert p.read_ready(session,name,jid,cid)['error']=='windows_metadata_payload_not_implemented'
   out=uqa.execute_tool_with_policy(p.CREATE,args,messages,**ctx)
   assert out['executed'] is False and not posts and list_operations(jid)[0]['status']=='not_sent'
   continue
  out=uqa.execute_tool_with_policy(p.CREATE,args,messages,**ctx);assert out.get('executed') is True,out
  uqa.record_tool_evidence(jid,cid,p.CREATE,args,out)
  wrong[0]=True;assert p.read(session,name,jid,cid)['error']=='own_endpoint_identity_freshness';wrong[0]=False
  result=uqa.execute_tool_with_policy(p.READ,args,messages,**ctx);assert result.get('native_result_verified') is True,result
  ev=uqa.record_tool_evidence(jid,cid,p.READ,args,result)
  op=list_operations(jid)[0];assert reconcile_operation(jid,op['operation_id'],ev['evidence_id'])['verified']
  assert result['summary']['logging_status']=='PASS' and not result['summary']['tray_desktop_verified']
  assert len(posts)==1
  assert not uqa.execute_tool_with_policy(p.CREATE,args,messages,**ctx).get('executed')
  assert len(posts)==1
print('PASS endpoint fixed metadata/Core/policy/no arbitrary payload/log write oracle/Tray limits/own receipt/recovery/no replay; fixture only')

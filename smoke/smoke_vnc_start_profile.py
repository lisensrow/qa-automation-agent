"""Fixed candidate startup scope/alias/Core native proof, fixture only."""
from copy import deepcopy
from contextlib import ExitStack
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4
import json
import uqa,job_store as store,plugin_discovery as p
from operation_journal import list_operations,reconcile_operation
def reject(fn,*a):
 try:fn(*a)
 except ValueError:return
 raise AssertionError('unsafe startup scope admitted')
reject(p.requirement,'windows','vncServer','fixture')
reject(p.requirement,'astra','vncServer','fixture',p.VNC_START)
reject(p.requirement,'windows','checkAlive','fixture',p.VNC_START)
r=p.requirement('windows','vncServer','fixture-start',p.VNC_START)
assert p.task_name(r)=='VncServer' and p.compiled_params(r)=={'command':'start'}
assert p.compiled_params(p.requirement('astra','checkAlive','fixture'))=={}
with TemporaryDirectory() as tmp,ExitStack() as stack:
 stack.enter_context(patch.object(store,'JOBS_DIR',Path(tmp)))
 request='Запусти одну задачу '+' '.join(r[k] for k in ['ci_id','agent_id','ci_name','core_version','plugin_name','plugin_version','profile_id'])
 j=store.create_job(request,stand='lab',job_type='manual');jid=j['job_id']
 c=store.add_test_case(jid,'Fixture startup',requirement=r);cid=c['case_id']
 store.set_job_status(jid,'running');store.update_test_case(jid,cid,status='running')
 ci={'id':r['ci_id'],'agent_id':r['agent_id'],'name':r['ci_name'],'detail':{'os':{'name':'Windows 10','architecture':'64'}}}
 base=p.ORIGIN+'/api/v1/agents/'+r['agent_id'];tasks={};posts=[]
 class Response:
  def __init__(self,s,b):self.status,self.b=s,b
  def json(self):return deepcopy(self.b)
 def get(url,params=None,timeout=None):
  if url==base+'/tasks':return Response(200,{'items':list(tasks.values()),'total':len(tasks),'offset':0,'limit':100,'count':len(tasks)})
  if url.endswith('/full'):return Response(200,tasks[url.split('/')[-2]])
  raise AssertionError('unexpected GET')
 def post(url,data,timeout=None):
  assert url==base+'/tasks' and data=={'name':'VncServer','period':None,'ttl':None,'run_as_user':'','additional_params':{'command':'start'}}
  posts.append(url);tid=str(uuid4());at=p.now()
  b={**deepcopy(data),'id':tid,'agent_id':r['agent_id'],'created_at':at}
  tasks[tid]={**b,'status':'success','result':{'machine_uid':r['ci_id'],'result':'success','processed_at':at,'data':{'native_status':'fixture'}}}
  return Response(201,b)
 session=SimpleNamespace(session_id='fixture-vnc-start',_ensure_started=lambda:None,
  _observed_agent_task_context=lambda name:(ci,{},base+'/tasks',None),
  _same_https_origin_url=lambda observed,path:p.ORIGIN+path,context=SimpleNamespace(request=SimpleNamespace(get=get,post=post)))
 ready={'ready':True,'load_error_empty_observed':True,'plugin_audit':{'audit_fresh':True},
  'ci_id':r['ci_id'],'agent_id':r['agent_id'],'core_version':'1.3.27','agent_status':'online',
  'plugin_name':'vncServer','plugin_version':'1.5.5','session_id':session.session_id,'read_at':p.now()}
 stack.enter_context(patch('tools.browser._session',session))
 stack.enter_context(patch.object(p,'readiness',return_value=ready))
 stack.enter_context(patch('windows_vnc_start_source.validate_start_prerequisites',return_value={'fixture_only':True}))
 stack.enter_context(patch.object(p.Path,'read_bytes',return_value=b'fixture-workbook'))
 import hashlib
 stack.enter_context(patch.object(p,'BOOK_SHA',hashlib.sha256(b'fixture-workbook').hexdigest()))
 # Only this fixture's source hash is substituted; actual runtime pin unchanged.
 ctx={'job_id':jid,'case_id':cid,'action_policy':'confirm_mutations'}
 args=r['operation_stages'][0]['arguments'];messages=[{'role':'user','content':request}]
 with patch.object(uqa,'read_user_input',side_effect=AssertionError('no prompt in read-only')):
  assert uqa.execute_tool_with_policy(p.CREATE,args,messages,force_read_only=True,**ctx)['error']=='tool_policy_blocked'
 assert not posts and not list_operations(jid)
 stack.enter_context(patch.object(uqa,'managed_action_policy_decision',return_value={'allow':True,'status':'fixture_only'}))
 out=uqa.execute_tool_with_policy(p.CREATE,args,messages,**ctx);assert out.get('executed'),out
 uqa.record_tool_evidence(jid,cid,p.CREATE,args,out)
 readargs={'target':'windows','plugin_name':'vncServer','task_id':out['task_id']}
 result=uqa.execute_tool_with_policy(p.READ,readargs,messages,**ctx);assert result.get('native_result_verified'),result
 ev=uqa.record_tool_evidence(jid,cid,p.READ,readargs,result);op=list_operations(jid)[0]
 assert reconcile_operation(jid,op['operation_id'],ev['evidence_id'])['verified']
 assert result['business_pass'] is False and len(posts)==1
 assert not uqa.execute_tool_with_policy(p.CREATE,args,messages,**ctx).get('executed') and len(posts)==1
print('PASS fixed Windows supplied VncServer startup alias/params/old-profile isolation/Core/own read/no replay; fixture only')

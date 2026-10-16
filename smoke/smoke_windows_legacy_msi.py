"""Exact MSI destructive profile/Core/own proof fixture; never actual Windows MSI."""
from contextlib import ExitStack
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4
import base64,json
import uqa,job_store as store,endpoint_metadata as p,windows_legacy_msi as m
from operation_journal import list_operations,reconcile_operation
from tools.registry import execute_tool
body={'profile':m.PROFILE,'product_code':m.PRODUCT,'expected_version':m.VERSION,'identity_verified':True,
 'uninstall_started':True,'msi_exit_code':0,'registry_absent':True,'legacy_service_absent':True,
 'legacy_process_absent':True,'reboot_required':False,'error':''}
assert m.summarize(body)['removal_status']=='PASS'
for k,v in [('identity_verified',False),('uninstall_started',False),('registry_absent',False),
 ('legacy_service_absent',False),('legacy_process_absent',False),('reboot_required',True),
 ('error','native_msi_preflight_or_postcheck_error'),('msi_exit_code',1603),('msi_exit_code',3010),('msi_exit_code',1605)]:
 assert m.summarize({**body,k:v})['removal_status']=='BLOCKED'
for b in [{**body,'product_code':'other'},{**body,'identity_verified':1},{**body,'msi_exit_code':True},{**body,'extra':0}]:
 try:m.summarize(b)
 except ValueError:pass
 else:raise AssertionError('forged MSI result accepted')
assert base64.b64decode(m.PAYLOAD['additional_params']['arguments'][-1]).decode('utf-16le')==m.CODE
assert '/norestart' in m.CODE and '-WindowStyle Hidden' in m.CODE
assert not any(x in m.CODE.casefold() for x in ['executionpolicy','remove-item','stop-process','restart-computer','win32_product','invoke-expression'])
assert uqa.classify_tool_action(m.REMOVE,{})=='destructive'
assert not execute_tool(m.REMOVE,{'target':'windows'})['executed']
try:p.requirement('astra','fixture-msi',m.PROFILE)
except ValueError:pass
else:raise AssertionError('Astra MSI allowed')
with TemporaryDirectory() as tmp,ExitStack() as stack:
 stack.enter_context(patch.object(store,'JOBS_DIR',Path(tmp)))
 r=p.requirement('windows','fixture-msi',m.PROFILE)
 assert r['action_profile']=='destructive' and r['operation_stages'][0]['tool']==m.REMOVE
 req='Удалить только старый TightVNC; запусти разрешённую агентскую задачу '+' '.join(r[k] for k in ['ci_id','agent_id','ci_name','core_version','profile_id'])
 j=store.create_job(req,stand='lab',job_type='manual');jid=j['job_id']
 c=store.add_test_case(jid,'Fixture exact MSI',requirement=r);cid=c['case_id']
 store.set_job_status(jid,'running');store.update_test_case(jid,cid,status='running')
 args={'target':'windows'};messages=[{'role':'user','content':req}]
 ctx={'job_id':jid,'case_id':cid,'action_policy':'confirm_mutations'}
 assert not uqa.execute_tool_with_policy(p.CREATE,args,messages,**ctx).get('executed')
 with patch.object(uqa,'read_user_input',side_effect=AssertionError('must not prompt')):
  assert uqa.execute_tool_with_policy(m.REMOVE,args,messages,force_read_only=True,**ctx)['error']=='tool_policy_blocked'
 assert not list_operations(jid)
 ci={'id':r['ci_id'],'name':r['ci_name'],'agent_id':r['agent_id'],
  'detail':{'os':{'name':'Windows 10 Pro','architecture':'64'}}}
 base=p.ORIGIN+'/api/v1/agents/'+r['agent_id'];tasks={};posts=[]
 class Response:
  def __init__(self,status,body):self.status,self.body=status,body
  def json(self):return deepcopy(self.body)
 def get(url,params=None,timeout=None):
  if url==base:return Response(200,{'id':r['agent_id'],'version':'1.3.27','status':'online'})
  if url==base+'/tasks':return Response(200,{'items':list(tasks.values()),'total':len(tasks),'offset':0})
  if url==base+'/plugin':return Response(200,{})
  if url.endswith('/full'):return Response(200,tasks[url.split('/')[-2]])
  raise AssertionError('unexpected GET')
 def post(url,data,timeout):
  assert url==base+'/tasks' and data==m.PAYLOAD;posts.append(url)
  b={**deepcopy(data),'id':str(uuid4()),'agent_id':r['agent_id'],'created_at':p.now()}
  tasks[b['id']]={**b,'status':'success','result':{'machine_uid':r['ci_id'],'processed_at':p.now(),
   'data':{'stdout':json.dumps(body),'stderr':'','errorlevel':0}}}
  return Response(201,b)
 session=SimpleNamespace(session_id='fixture-msi',_ensure_started=lambda:None,
  _observed_agent_task_context=lambda name:(ci,{},base+'/tasks',None),
  _same_https_origin_url=lambda observed,path:p.ORIGIN+path,
  context=SimpleNamespace(request=SimpleNamespace(get=get,post=post)))
 stack.enter_context(patch('tools.browser._session',session))
 stack.enter_context(patch.object(p,'validate_release_source',return_value=True))
 stack.enter_context(patch.object(p,'validate_preflight',return_value={'ready':True}))
 decision=stack.enter_context(patch.object(uqa,'managed_action_policy_decision',return_value={'allow':True,'status':'fixture_only'}))
 out=uqa.execute_tool_with_policy(m.REMOVE,args,messages,**ctx);assert out.get('executed'),out
 assert decision.call_args[0][2]=='destructive'
 uqa.record_tool_evidence(jid,cid,m.REMOVE,args,out)
 result=uqa.execute_tool_with_policy(p.READ,args,messages,**ctx);assert result.get('native_result_verified'),result
 e=uqa.record_tool_evidence(jid,cid,p.READ,args,result)
 assert result['summary']['removal_status']=='PASS' and len(posts)==1
 op=list_operations(jid)[0];assert reconcile_operation(jid,op['operation_id'],e['evidence_id'])['verified']
 assert not uqa.execute_tool_with_policy(m.REMOVE,args,messages,**ctx).get('executed') and len(posts)==1
print('PASS exact MSI destructive classification, immutable Windows-only payload, own native proof/no replay; fixture only')

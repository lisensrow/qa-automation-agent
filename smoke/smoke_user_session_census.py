"""Local session-query profile: bounded metadata, Core and no replay."""
from copy import deepcopy
from contextlib import ExitStack
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4
import ast,json
import uqa,job_store as store,endpoint_metadata as p,user_session_census as s,endpoint_metadata_runtime as runtime
from operation_journal import list_operations,reconcile_operation

def reject(fn,*args):
 try:fn(*args)
 except (ValueError,TypeError,KeyError):return
 raise AssertionError('unsafe session census admitted')
reject(s.payload,'ubuntu');ast.parse(s.ASTRA)
for token in ['WTSLogoffSession','WTSDisconnectSession','WTSSetUserConfig','Start-Process','Remove-Item','Set-Item']:
 assert token not in s.WINDOWS
for token in ['shell=True','unlock-session','activate','terminate-session','os.remove','os.chmod']:
 assert token not in s.ASTRA
for name in ['windows','astra']:
 body={'probe_version':1,'platform':name,'query_complete':True,'sessions':[],'error':''}
 empty=s.summarize(body,name);assert empty['candidate_user_session_count']==0 and empty['no_candidate_user_session_reported'] is True
 assert empty['desktop_verified'] is False and empty['login_or_unlock_performed'] is False
 missing=s.summarize({**body,'query_complete':False,'error':'native_session_query_failed'},name)
 assert missing['candidate_user_session_count'] is None and missing['observation_status']=='BLOCKED'
 row={'session_ref':'a'*64,'kind':'wts' if name=='windows' else 'x11','candidate':True}
 active=s.summarize({**body,'sessions':[row]},name);assert active['candidate_user_session_count']==1 and active['business_pass'] is False
 reject(s.summarize,{**body,'sessions':[row,row]},name)
 reject(s.summarize,{**body,'platform':'other'},name)
 reject(s.summarize,{**body,'sessions':[{**row,'username':'private'}]},name)
 reject(s.summarize,{**body,'probe_version':True},name)
 r=p.requirement(name,'fixture-session-census',s.PROFILE)
 assert runtime.catalog([],r)[0]['function']['parameters']['properties']['query']=={'enum':[s.PROFILE]}
 assert r['payload_sha256']==s.sha(name) and r['supported_os']==name and r['action_profile']=='write_resource'
 with TemporaryDirectory() as tmp,ExitStack() as stack:
  stack.enter_context(patch.object(store,'JOBS_DIR',Path(tmp)))
  request='Запусти фиксированную агентскую задачу '+' '.join(r[k] for k in ['ci_id','agent_id','ci_name','core_version','profile_id'])
  j=store.create_job(request,stand='lab',job_type='manual');jid=j['job_id'];c=store.add_test_case(jid,'Fixture session query',requirement=r);cid=c['case_id']
  store.set_job_status(jid,'running');store.update_test_case(jid,cid,status='running')
  ci={'id':r['ci_id'],'agent_id':r['agent_id'],'name':r['ci_name'],'detail':{'os':{'name':'Windows 10' if name=='windows' else 'Astra Linux','architecture':'64'}}}
  base=p.ORIGIN+'/api/v1/agents/'+r['agent_id'];tasks={};posts=[]
  class Response:
   def __init__(self,status,body):self.status,self.body=status,body
   def json(self):return deepcopy(self.body)
  def get(url,params=None,timeout=None):
   if url==base:return Response(200,{'id':r['agent_id'],'version':'1.3.27','status':'online'})
   if url==base+'/plugin':return Response(200,{})
   if url==base+'/tasks':return Response(200,{'items':list(tasks.values()),'total':len(tasks),'offset':0})
   if url.endswith('/full'):return Response(200,tasks[url.split('/')[-2]])
   raise AssertionError('unexpected GET')
  def post(url,data,timeout=None):
   assert url==base+'/tasks' and data==s.payload(name)
   posts.append(url);tid=str(uuid4());at=p.now();b={**deepcopy(data),'id':tid,'agent_id':r['agent_id'],'created_at':at}
   tasks[tid]={**b,'status':'success','result':{'machine_uid':r['ci_id'],'processed_at':at,'data':{'stdout':json.dumps(body),'stderr':'','errorlevel':0}}}
   return Response(201,b)
  session=SimpleNamespace(session_id='fixture-session-census',_ensure_started=lambda:None,
   _observed_agent_task_context=lambda name:(ci,{},base+'/tasks',None),_same_https_origin_url=lambda observed,path:p.ORIGIN+path,
   context=SimpleNamespace(request=SimpleNamespace(get=get,post=post)))
  stack.enter_context(patch('tools.browser._session',session));stack.enter_context(patch.object(p,'validate_preflight',return_value={'ready':True}))
  stack.enter_context(patch.object(p,'validate_release_source',return_value=True))
  args={'target':name};ctx={'job_id':jid,'case_id':cid,'action_policy':'confirm_mutations'};messages=[{'role':'user','content':request}]
  assert uqa.execute_tool_with_policy(p.CREATE,args,messages,force_read_only=True,**ctx)['error']=='tool_policy_blocked'
  assert not posts and not list_operations(jid)
  stack.enter_context(patch.object(uqa,'managed_action_policy_decision',return_value={'allow':True,'status':'fixture_only'}))
  out=uqa.execute_tool_with_policy(p.CREATE,args,messages,**ctx);assert out.get('executed'),out
  uqa.record_tool_evidence(jid,cid,p.CREATE,args,out)
  read=uqa.execute_tool_with_policy(p.READ,args,messages,**ctx);assert read.get('native_result_verified'),read
  ev=uqa.record_tool_evidence(jid,cid,p.READ,args,read);op=list_operations(jid)[0]
  assert reconcile_operation(jid,op['operation_id'],ev['evidence_id'])['verified']
  assert read['summary']['candidate_user_session_count']==0 and read['summary']['desktop_verified'] is False
  assert not uqa.execute_tool_with_policy(p.CREATE,args,messages,**ctx).get('executed') and len(posts)==1
print('PASS fixed WTS/logind census both OS/privacy/incomplete-not-zero/Core/own read/no repeat; fixture only')

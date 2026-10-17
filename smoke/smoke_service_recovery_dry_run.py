"""No real scheduling/service/filesystem changes: actual Core + fake native API."""
from copy import deepcopy
from contextlib import ExitStack
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4
import json
import service_recovery_dry_run as p

def sample(profile):
 if profile==p.REGISTER:
  d={'new_owned_task_registered':True,'exact_task_definition':True,'existing_system_identity':True,'service_already_running':True,'stop_or_restart_executed':False}
 else:
  d={'callback_complete':True,'identity_system':True,'outside_agent_tree':True,'service_running_after':True,'callback_pid':444,'service_pid':222,'started_at':'2026-10-17T00:00:00Z','finished_at':'2026-10-17T00:00:01Z','callback_error':'','callback_failure_reason':'','exact_task_definition':True,'last_task_result_zero':True,'stop_or_restart_executed':False}
 return {'probe_version':1,'platform':'windows','phase':'register' if profile==p.REGISTER else 'observe','query_complete':True,'error':'','failure_reason':'','data':d}

def main():
 import uqa,job_store as store,endpoint_metadata as ep
 from operation_journal import list_operations,reconcile_operation
 assert 'Stop-Service' not in p.CALLBACK and 'Restart-Service' not in p.CALLBACK and 'Start-Service' in p.CALLBACK
 assert '-Force' not in p.REGISTER_BODY and 'Unregister' not in p.REGISTER_BODY
 for profile in p.PROFILES:
  b=sample(profile);out=p.summarize(b,'windows',profile)
  assert not out['full_case_passed'] and not out['actual_stopped_agent_recovery_verified']
  bad=deepcopy(b);bad['data']['stop_or_restart_executed']=True
  try:p.summarize(bad,'windows',profile)
  except ValueError:pass
  else:raise AssertionError('stop accepted in dry run')
  bad=deepcopy(b);bad.update(query_complete=False,error='recovery_prerequisite_unverified',failure_reason='owned_task_exists',data={})
  assert not p.summarize(bad,'windows',profile)['query_complete']
  try:p.payload('astra',profile)
  except ValueError:pass
  else:raise AssertionError('unimplemented OS admitted')
 bad=sample(p.OBSERVE);bad['data']['callback_pid']=bad['data']['service_pid']
 try:p.summarize(bad,'windows',p.OBSERVE)
 except ValueError:pass
 else:raise AssertionError('same process accepted')
 with TemporaryDirectory() as tmp,ExitStack() as stack:
  # Historical contract fixture only: these failed attempt writers are retired.
  stack.enter_context(patch.object(ep,'RETIRED_RECOVERY_PROFILES',set()))
  stack.enter_context(patch.object(store,'JOBS_DIR',Path(tmp)))
  tasks={};posts=[];current=[p.REGISTER];r=ep.requirement('windows','dry-fixture',p.REGISTER)
  base=ep.ORIGIN+'/api/v1/agents/'+r['agent_id']
  ci={'id':r['ci_id'],'agent_id':r['agent_id'],'name':r['ci_name'],'detail':{'os':{'name':'Windows 10','architecture':'64'}}}
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
   assert url==base+'/tasks' and data==p.payload('windows',current[0]);posts.append(data)
   tid=str(uuid4());at=ep.now();body={**deepcopy(data),'id':tid,'agent_id':r['agent_id'],'created_at':at}
   tasks[tid]={**body,'status':'success','result':{'machine_uid':r['ci_id'],'processed_at':at,'data':{'stdout':json.dumps(sample(current[0])),'stderr':'','errorlevel':0}}}
   return Response(201,body)
  session=SimpleNamespace(session_id='fixture-service-dry',_ensure_started=lambda:None,
   _observed_agent_task_context=lambda name:(ci,{},base+'/tasks',None),_same_https_origin_url=lambda observed,path:ep.ORIGIN+path,
   context=SimpleNamespace(request=SimpleNamespace(get=get,post=post)))
  stack.enter_context(patch('tools.browser._session',session));stack.enter_context(patch.object(ep,'validate_preflight',return_value={'ready':True}));stack.enter_context(patch.object(ep,'validate_release_source',return_value=True))
  def create_case(profile):
   req=ep.requirement('windows','dry-fixture-'+('register' if profile==p.REGISTER else 'observe'),profile)
   text='Запусти фиксированную безопасную тестовую задачу '+' '.join(req[k] for k in ['ci_id','agent_id','ci_name','core_version','profile_id'])
   jid=store.create_job(text,stand='lab',job_type='manual')['job_id'];cid=store.add_test_case(jid,'Fixture service dry run',requirement=req)['case_id']
   store.set_job_status(jid,'running');store.update_test_case(jid,cid,status='running')
   return jid,cid,text
  # An observer cannot adopt another fixture/task without its own verified REG.
  j,c,text=create_case(p.OBSERVE)
  out=uqa.execute_tool_with_policy(ep.CREATE,{'target':'windows'},[{'role':'user','content':text}],job_id=j,case_id=c,action_policy='confirm_mutations')
  assert not out.get('executed') and not posts and not list_operations(j)
  stack.enter_context(patch.object(uqa,'managed_action_policy_decision',return_value={'allow':True,'status':'fixture_only'}))
  for profile in (p.REGISTER,p.OBSERVE):
   current[0]=profile;j,c,text=create_case(profile);args={'target':'windows'};ctx={'job_id':j,'case_id':c,'action_policy':'confirm_mutations'};messages=[{'role':'user','content':text}]
   assert not uqa.execute_tool_with_policy(ep.CREATE,args,messages,force_read_only=True,**ctx).get('executed')
   out=uqa.execute_tool_with_policy(ep.CREATE,args,messages,**ctx);assert out.get('executed'),out
   uqa.record_tool_evidence(j,c,ep.CREATE,args,out)
   out=uqa.execute_tool_with_policy(ep.READ,args,messages,**ctx);assert out.get('native_result_verified'),out
   ev=uqa.record_tool_evidence(j,c,ep.READ,args,out)
   assert reconcile_operation(j,list_operations(j)[0]['operation_id'],ev['evidence_id'])['verified']
   assert out['summary']['dry_registration_verified' if profile==p.REGISTER else 'independent_callback_execution_verified']
   assert not uqa.execute_tool_with_policy(ep.CREATE,args,messages,**ctx).get('executed')
   store.update_test_case(j,c,status='blocked');store.set_job_status(j,'blocked')
  assert len(posts)==2
 print('PASS service recovery dry: strict Windows-only register/observer/own predecessor/Core policy/native fresh/journal/no replay; no real scheduling or service stop')

if __name__=='__main__':main()

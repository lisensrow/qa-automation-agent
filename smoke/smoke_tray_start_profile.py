"""Isolated native/Core Tray start contract and no-rekey source guards."""
from copy import deepcopy
from contextlib import ExitStack
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4
import hashlib,json
import uqa,job_store as store,plugin_discovery as p,tray_start_source as src
from operation_journal import list_operations,reconcile_operation

def reject(fn,*a):
 try:fn(*a)
 except ValueError:return
 raise AssertionError('unsafe tray scope admitted')

reject(p.requirement,'windows','trayControl','fixture')
reject(p.requirement,'windows','vncServer','fixture',p.TRAY_START)
reject(p.requirement,'ubuntu','trayControl','fixture',p.TRAY_START)
assert src.BINARIES['astra'][1]=='94b43341ae31426439298998305d07896d1006f495b5d99bf1bf16bfd47fd4a7'
assert all(len(x[1])==64 for x in src.BINARIES.values())
assert src.outcome({'result':'success','error':''})['functional_start_status']=='BLOCKED'
assert src.outcome({'result':'error','error':'fixture'})['functional_start_status']=='FAIL'
assert src.outcome({})['functional_start_status']=='BLOCKED'
assert src.outcome({'nested':{'result':'success'}})['desktop_verified'] is False
empty=src.outcome({'action':'start','started':[],'already_running':[],'user':''})
assert empty['reported_started_count']==empty['reported_already_running_count']==0 and empty['user_selector_empty'] is True
assert empty['functional_start_status']=='BLOCKED' and empty['desktop_verified'] is False
assert src.outcome({'action':'start','started':['fixture'],'already_running':[],'user':'fixture'})['functional_start_status']=='BLOCKED'
for name in ['windows','astra']:
 r=p.requirement(name,'trayControl','fixture-tray-start',p.TRAY_START)
 assert p.compiled_params(r)=={'action':'start'} and p.task_name(r)=='trayControl'
 assert p.compiled_params(p.requirement(name,'checkAlive','fixture'))=={}
 platform=src.BINARIES[name][0].split('/')[0];sha=src.BINARIES[name][1]
 body={'candidate_payload':{'name':'trayControl','period':None,'ttl':None,'run_as_user':'','additional_params':{'action':'start'}},
  'platforms':{platform:{'sha256':sha,'literal_tokens':['trayControl','action','start','action is required in additional_params']}}}
 value=json.dumps(body);source={'test_cases':[{'evidence':[{'evidence_id':src.EVIDENCE,'source':'operator_supplied_binary_static_review',
  'type':'operator_tray_start_contract_candidate','execution_status':'observed','value':value}]}]}
 with patch.object(src,'SHA',hashlib.sha256(value.encode()).hexdigest()),patch.object(store,'get_job',return_value=source),patch.object(store,'list_jobs',return_value=[]),patch.object(src.ssh_worker,'_run',return_value={'exit_code':0,'stdout':sha+'  fixture'}):
  assert src.validate_start_prerequisites(r,'current')['business_pass'] is False
  with patch.object(src.ssh_worker,'_run',return_value={'exit_code':0,'stdout':'bad'}):reject(src.validate_start_prerequisites,r,'current')
  old={'job_id':'other','test_cases':[{'requirement':r}]}
  with patch.object(store,'list_jobs',return_value=[old]),patch.object(src,'list_operations',return_value=[{'status':'uncertain'}]):
   reject(src.validate_start_prerequisites,r,'current')
 with TemporaryDirectory() as tmp,ExitStack() as stack:
  stack.enter_context(patch.object(store,'JOBS_DIR',Path(tmp)))
  req='Запусти одну задачу '+' '.join(r[k] for k in ['ci_id','agent_id','ci_name','core_version','plugin_name','plugin_version','profile_id'])
  j=store.create_job(req,stand='lab',job_type='manual');jid=j['job_id'];c=store.add_test_case(jid,'Fixture Tray',requirement=r);cid=c['case_id']
  store.set_job_status(jid,'running');store.update_test_case(jid,cid,status='running')
  ci={'id':r['ci_id'],'agent_id':r['agent_id'],'name':r['ci_name']};base=p.ORIGIN+'/api/v1/agents/'+r['agent_id'];tasks={};posts=[]
  class Response:
   def __init__(self,s,b):self.status,self.b=s,b
   def json(self):return deepcopy(self.b)
  def get(url,params=None,timeout=None):
   if url==base+'/tasks':return Response(200,{'items':list(tasks.values()),'total':len(tasks),'offset':0,'count':len(tasks),'limit':100})
   if url.endswith('/full'):return Response(200,tasks[url.split('/')[-2]])
   raise AssertionError('unexpected GET')
  def post(url,data,timeout=None):
   assert data==body['candidate_payload'];posts.append(url);tid=str(uuid4());at=p.now()
   b={**data,'id':tid,'agent_id':r['agent_id'],'created_at':at}
   tasks[tid]={**b,'status':'success','result':{'machine_uid':r['ci_id'],'result':'success','processed_at':at,'data':{'result':'error','error':'fixture_not_desktop'}}}
   return Response(201,b)
  session=SimpleNamespace(session_id='fixture-tray',_ensure_started=lambda:None,_observed_agent_task_context=lambda name:(ci,{},base+'/tasks',None),
   _same_https_origin_url=lambda observed,path:p.ORIGIN+path,context=SimpleNamespace(request=SimpleNamespace(get=get,post=post)))
  ready={'ready':True,'load_error_empty_observed':True,'plugin_audit':{'audit_fresh':True},'session_id':session.session_id,
   **{k:r[k] for k in ['ci_id','agent_id','core_version','plugin_name','plugin_version']},'agent_status':'online','read_at':p.now()}
  stack.enter_context(patch('tools.browser._session',session));stack.enter_context(patch.object(p,'readiness',return_value=ready))
  stack.enter_context(patch.object(src,'validate_start_prerequisites',return_value={'fixture_only':True}))
  stack.enter_context(patch.object(p.Path,'read_bytes',return_value=b'fixture-workbook'));stack.enter_context(patch.object(p,'BOOK_SHA',hashlib.sha256(b'fixture-workbook').hexdigest()))
  ctx={'job_id':jid,'case_id':cid,'action_policy':'confirm_mutations'};args=r['operation_stages'][0]['arguments'];messages=[{'role':'user','content':req}]
  assert uqa.execute_tool_with_policy(p.CREATE,args,messages,force_read_only=True,**ctx)['error']=='tool_policy_blocked'
  assert not posts and not list_operations(jid)
  stack.enter_context(patch.object(uqa,'managed_action_policy_decision',return_value={'allow':True,'status':'fixture_only'}))
  out=uqa.execute_tool_with_policy(p.CREATE,args,messages,**ctx);assert out.get('executed'),out
  uqa.record_tool_evidence(jid,cid,p.CREATE,args,out)
  readargs={'target':name,'plugin_name':'trayControl','task_id':out['task_id']}
  result=uqa.execute_tool_with_policy(p.READ,readargs,messages,**ctx);assert result.get('native_result_verified'),result
  ev=uqa.record_tool_evidence(jid,cid,p.READ,readargs,result);op=list_operations(jid)[0]
  assert reconcile_operation(jid,op['operation_id'],ev['evidence_id'])['verified']
  assert result['business_pass'] is False and len(posts)==1
  assert result['tray_start_observation']['explicit_native_error'] is True
  assert result['tray_start_observation']['functional_start_status']=='FAIL'
  assert not uqa.execute_tool_with_policy(p.CREATE,args,messages,**ctx).get('executed') and len(posts)==1
print('PASS Tray start exact params/both OS/source hash/no rekey/Core/own read/not desktop; fixture only')

"""Pure metadata grammar and existing Core policy/no-replay fixture adaptation."""
import ast,base64,json
from copy import deepcopy
from contextlib import ExitStack
from tempfile import TemporaryDirectory
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4
import agent_installation_inventory as p
import endpoint_metadata as ep
import uqa,job_store as store
from operation_journal import list_operations,reconcile_operation
for name in ('windows','astra'):
 keys=p.relative_paths(name)+(['identity','legacy_dot_directory'] if name=='windows' else [])
 obj={'probe_version':1,'platform':name,'root':r'C:\Program Files (x86)\USystem\agentServer' if name=='windows' else '/opt/usystem/usagent','rows':[{'key':k,'state':'missing'} for k in keys]}
 summary=p.summarize(obj,name)
 assert summary['observation_status']=='COMPLETE' and not summary['business_pass'] and not summary['installation_executed']
 for state in ('link_blocked','unavailable','other'):
  bad=deepcopy(obj);bad['rows'][0]['state']=state
  assert p.summarize(bad,name)['observation_status']=='BLOCKED'
 for mode in ('version','root','duplicate','extra','secret','status'):
  bad=deepcopy(obj)
  if mode=='version':bad['probe_version']=True
  elif mode=='root':bad['root']='/other'
  elif mode=='duplicate':bad['rows'][-1]['key']=keys[0]
  elif mode=='extra':bad['rows'].append({'key':'other','state':'file'})
  elif mode=='secret':bad['rows'][0]['contents']='private'
  else:bad['rows'][0]['state']='exists'
  try:p.summarize(bad,name)
  except ValueError:pass
  else:raise AssertionError(mode)
 assert ep.requirement(name,'uqa-install-fixture',p.PROFILE)['expected_profile']['file_metadata_only']
 r=ep.requirement(name,'uqa-install-fixture',p.PROFILE)
 with TemporaryDirectory() as tmp,ExitStack() as stack:
  stack.enter_context(patch.object(store,'JOBS_DIR',Path(tmp)))
  req='Создай и выполни одну фиксированную агентскую задачу метаданных файлов; файлов не изменять. '+' '.join(r[k] for k in ['ci_id','agent_id','ci_name','core_version','profile_id'])
  jid=store.create_job(req,stand='lab',job_type='manual')['job_id']
  cid=store.add_test_case(jid,'Case1 file fixture',requirement=r)['case_id']
  store.set_job_status(jid,'running');store.update_test_case(jid,cid,status='running')
  ci={'id':r['ci_id'],'agent_id':r['agent_id'],'name':r['ci_name'],'detail':{'os':{'name':'Windows 10' if name=='windows' else 'Astra Linux','architecture':'64'}}}
  base=ep.ORIGIN+'/api/v1/agents/'+r['agent_id'];tasks={};posts=[]
  class Response:
   def __init__(self,status,body):self.status,self.body=status,body
   def json(self):return deepcopy(self.body)
  def get(url,params=None,timeout=None):
   if url==base:return Response(200,{'id':r['agent_id'],'version':'1.3.27','status':'online'})
   if url==base+'/plugin':return Response(200,{})
   if url==base+'/tasks':return Response(200,{'items':list(tasks.values()),'total':len(tasks),'offset':0})
   if url.endswith('/full'):return Response(200,tasks[url.split('/')[-2]])
   raise AssertionError(url)
  def post(url,data,timeout=None):
   assert url==base+'/tasks' and data==p.payload(name)
   posts.append(url);tid=str(uuid4());at=ep.now()
   tasks[tid]={**deepcopy(data),'id':tid,'agent_id':r['agent_id'],'created_at':at,'status':'success','result':{'machine_uid':r['ci_id'],'processed_at':at,'data':{'stdout':json.dumps(obj),'stderr':'','errorlevel':0}}}
   return Response(201,tasks[tid])
  session=SimpleNamespace(session_id='fixture-install-files',_ensure_started=lambda:None,
   _observed_agent_task_context=lambda name:(ci,{},base+'/tasks',None),_same_https_origin_url=lambda observed,path:ep.ORIGIN+path,
   context=SimpleNamespace(request=SimpleNamespace(get=get,post=post)))
  stack.enter_context(patch('tools.browser._session',session))
  stack.enter_context(patch.object(ep,'validate_preflight',return_value={'ready':True}))
  stack.enter_context(patch.object(ep,'validate_release_source',return_value=True))
  args={'target':name};ctx={'job_id':jid,'case_id':cid,'action_policy':'confirm_mutations'};messages=[{'role':'user','content':req}]
  assert not uqa.execute_tool_with_policy(ep.CREATE,args,messages,force_read_only=True,**ctx).get('executed')
  assert not posts and not list_operations(jid)
  stack.enter_context(patch.object(uqa,'managed_action_policy_decision',return_value={'allow':True,'status':'fixture_only'}))
  out=uqa.execute_tool_with_policy(ep.CREATE,args,messages,**ctx);assert out.get('executed'),out
  uqa.record_tool_evidence(jid,cid,ep.CREATE,args,out)
  out=uqa.execute_tool_with_policy(ep.READ,args,messages,**ctx);assert out.get('native_result_verified'),out
  assert out['summary']['file_metadata']==obj['rows'] and not out['summary']['full_case_passed']
  ev=uqa.record_tool_evidence(jid,cid,ep.READ,args,out)
  assert reconcile_operation(jid,list_operations(jid)[0]['operation_id'],ev['evidence_id'])['verified']
  assert not uqa.execute_tool_with_policy(ep.CREATE,args,messages,**ctx).get('executed') and len(posts)==1
 assert not any(s in p.code(name) for s in ['Remove-Item','Set-Content','ReadAllText','Get-Content','Start-Process','os.remove','os.unlink','chmod(','subprocess'])
 payload=p.payload(name)['additional_params']
 if name=='astra':ast.parse(payload['arguments'][1])
 else:assert base64.b64decode(payload['arguments'][-1]).decode('utf-16-le')==p.code(name)
try:p.payload('ubuntu')
except ValueError:pass
else:raise AssertionError('scope')
print('PASS installation file inventory strict grammar; missing is observation not PASS; no content/mutation')

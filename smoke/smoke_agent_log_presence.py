"""Isolated metadata contract and real Core/journal wiring, no lab task."""
import hashlib, json, subprocess, sys
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch
from contextlib import ExitStack
from uuid import uuid4
import agent_log_presence as p

def main(p=p,targets=('windows','astra'),execute_python_probe=True):
 import uqa,job_store as store,endpoint_metadata as ep
 from operation_journal import list_operations,reconcile_operation
 for name in targets:
  body={'probe_version':1,'platform':name,'query_complete':True,'error':'',
        'files':[{'id':'a'*64,'size':23,'mtime_ms':123}]}
  assert p.summarize(body,name)['adapted_presence_status']=='PASS'
  empty={**body,'files':[]};assert p.summarize(empty,name)['adapted_presence_status']=='FAIL'
  unknown={**empty,'query_complete':False,'error':'log_metadata_unavailable'}
  assert p.summarize(unknown,name)['nonempty_file_count'] is None
  for bad in [{**body,'probe_version':True},{**body,'files':body['files']*2},
              {**body,'query_complete':False}, {**body,'platform':'other'},
              {**body,'files':[{'id':'a'*64,'size':True,'mtime_ms':1}]}]:
   try:p.summarize(bad,name)
   except ValueError:pass
   else:raise AssertionError('invalid metadata accepted')
  r=ep.requirement(name,'fixture-current-agent-log-presence',p.PROFILE)
  assert r['payload_sha256']==p.sha(name) and r['expected_profile']=={'nonempty_agent_log_files_present':True,**p.LIMITS}
  with TemporaryDirectory() as tmp,ExitStack() as stack:
   stack.enter_context(patch.object(store,'JOBS_DIR',Path(tmp)))
   req='Запусти фиксированную задачу '+' '.join(r[k] for k in ['ci_id','agent_id','ci_name','core_version','profile_id'])
   jid=store.create_job(req,stand='lab',job_type='manual')['job_id']
   cid=store.add_test_case(jid,'Log presence fixture',requirement=r)['case_id']
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
    raise AssertionError('unexpected GET')
   def post(url,data,timeout=None):
    assert url==base+'/tasks' and data==p.payload(name)
    posts.append(url);tid=str(uuid4());at=ep.now();b={**deepcopy(data),'id':tid,'agent_id':r['agent_id'],'created_at':at}
    tasks[tid]={**b,'status':'success','result':{'machine_uid':r['ci_id'],'processed_at':at,'data':{'stdout':json.dumps(body),'stderr':'','errorlevel':0}}}
    return Response(201,b)
   session=SimpleNamespace(session_id='fixture-current-logs',_ensure_started=lambda:None,
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
   ev=uqa.record_tool_evidence(jid,cid,ep.READ,args,out)
   assert reconcile_operation(jid,list_operations(jid)[0]['operation_id'],ev['evidence_id'])['verified']
   assert out['summary']['adapted_presence_status']=='PASS' and not out['summary']['full_source_case_passed']
   assert not uqa.execute_tool_with_policy(ep.CREATE,args,messages,**ctx).get('executed') and len(posts)==1
 # Execute only the fixed Python probe on this host: unknown root is BLOCKED,
 # not a production run or a positive fixture substituted for target evidence.
 if execute_python_probe:
  raw=subprocess.run([sys.executable,'-c',p.ASTRA],capture_output=True,text=True,check=True)
  p.summarize(json.loads(raw.stdout),'astra')
 print('PASS current log presence: strict metadata/bothOS Core/policy/own fresh fetch/journal/no replay; not five-day rotation or desktop')

if __name__=='__main__':main()

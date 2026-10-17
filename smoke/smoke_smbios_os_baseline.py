"""Fixed nonsensitive DMI identity projection, unknowns and Core safeguards."""
from copy import deepcopy
from contextlib import ExitStack
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch
import json,os
import smbios_os_baseline as p

def body(name):return {'probe_version':1,'platform':name,'query_complete':True,'values':{k:'Observed' for k in p.FIELDS[name]},'error':''}

def main():
 for name in ['windows','astra']:
  obj=body(name);s=p.summarize(obj,name);assert s['dmi_query_complete'] and s['observation_status']=='OBSERVED' and len(s['values_sha256'])==64 and all(s[k] is False for k in p.LIMITS)
  for key,value in [('probe_version',True),('platform','other'),('query_complete',1),('error','untrusted')]:
   bad=deepcopy(obj);bad[key]=value
   try:p.summarize(bad,name);raise AssertionError('invalid DMI header accepted')
   except ValueError:pass
  for value in [False,'x'*513,'bad\nvalue']:
   bad=deepcopy(obj);bad['values']['bios_vendor']=value
   try:p.summarize(bad,name);raise AssertionError('invalid DMI field accepted')
   except ValueError:pass
  bad=deepcopy(obj);bad['values']['serial_number']='must not admit'
  try:p.summarize(bad,name);raise AssertionError('extra DMI field accepted')
  except ValueError:pass
  unknown=deepcopy(obj);unknown['values']['baseboard_version']='Unknown'
  s=p.summarize(unknown,name);assert s['observation_status']=='OBSERVED_WITH_UNKNOWNS' and s['unknown_fields']==['baseboard_version'] and s['native_values']['baseboard_version']=='Unknown'
  unknown['values']={k:'' for k in p.FIELDS[name]};assert p.summarize(unknown,name)['observation_status']=='BLOCKED'
  failed={'probe_version':1,'platform':name,'query_complete':False,'values':{},'error':'native_dmi_identity_query_failed'}
  assert p.summarize(failed,name)['observation_status']=='BLOCKED' and p.summarize(failed,name)['native_values'] is None
  assert p.payload(name)['name']=='executeCommand' and len(p.sha(name))==64
 outputs=[];paths=[];closed=[]
 def native(denied=None,oversized=None):
  outputs.clear();paths.clear();closed.clear();fds={}
  def opened(path,flags):
   assert path.startswith('/sys/class/dmi/id/') and path.rsplit('/',1)[1] in p.FILES.values() and flags&os.O_ACCMODE==os.O_RDONLY
   name=path.rsplit('/',1)[1];paths.append(name)
   if name==denied:raise PermissionError()
   fd=100+len(fds);fds[fd]=name;return fd
  def read(fd,count):
   assert count==2049
   return b'x'*2049 if fds[fd]==oversized else b'Observed \n'
  with patch('os.open',side_effect=opened),patch('os.read',side_effect=read),patch('os.close',side_effect=closed.append),patch('builtins.print',side_effect=outputs.append):exec(compile(p.ASTRA,'fixed-dmi-identity','exec'),{})
  assert set(paths)==set(p.FILES.values()) and len(closed)==len(fds)
  return p.summarize(json.loads(outputs[0]),'astra')
 s=native();assert s['observation_status']=='OBSERVED' and set(s['native_values'].values())=={'Observed '}, 'spaces preserved, only file newline removed'
 assert native(denied='board_version')['unknown_fields']==['baseboard_version']
 assert native(oversized='bios_vendor')['unknown_fields']==['bios_vendor']
 import smoke_drive_os_baseline as shared
 with patch.object(shared,'p',p):
  for name in ['windows','astra']:shared.core_fixture(name,body(name),lambda s: s['dmi_query_complete'] or (_ for _ in ()).throw(AssertionError('DMI own summary')))
 import job_store as store,endpoint_metadata as ep,endpoint_metadata_runtime as rt
 for status in ['OBSERVED','OBSERVED_WITH_UNKNOWNS','BLOCKED']:
  with TemporaryDirectory() as tmp,ExitStack() as stack:
   stack.enter_context(patch.object(store,'JOBS_DIR',Path(tmp)))
   r=ep.requirement('astra','fixture-dmi-runtime',p.PROFILE);request='Observe fixed DMI '+' '.join(r[k] for k in ['ci_id','agent_id','ci_name','core_version','profile_id'])
   j=store.create_job(request,stand='lab',job_type='manual');jid=j['job_id'];cid=store.add_test_case(jid,'DMI schema fixture',requirement=r)['case_id'];store.set_job_status(jid,'running');store.update_test_case(jid,cid,status='running')
   summary=p.summarize(body('astra'),'astra');summary['observation_status']=status;result={'native_result_verified':True,'operation_id':'fixture-op','summary':summary}
   stack.enter_context(patch.object(rt,'catalog',side_effect=[[{}],[]]));stack.enter_context(patch.object(rt,'phase_decision_schema',return_value={}))
   stack.enter_context(patch.object(rt,'decode_phase_decision',return_value={'function':{'name':ep.READ,'arguments':{'target':'astra'}}}))
   stack.enter_context(patch.object(rt,'list_operations',return_value=[{'status':'verified'}]));stack.enter_context(patch.object(rt,'reconcile_operation',return_value={'verified':True}))
   stack.enter_context(patch('tools.browser._session',SimpleNamespace(reset_case_context=lambda:None,close=lambda:None)))
   def ask(messages,tools,response_schema):
    if 'properties' not in response_schema:return {'message':{'content':'{}'}}
    assert response_schema['properties']['observation_status']['enum']==['OBSERVED','OBSERVED_WITH_UNKNOWNS','BLOCKED']
    return {'message':{'content':json.dumps({'observation_status':status,'full_business_case_passed':False,'summary':'Eight DMI strings only, not plugin/all hardware/UI proof.'})}}
   api=SimpleNamespace(get_job=store.get_job,ask_ollama=ask,execute_tool_with_policy=lambda *a,**kw:deepcopy(result),record_tool_observations=lambda *a:[],record_tool_evidence=lambda *a,**kw:{'evidence_id':'fixture-proof'},tool_result_for_model=lambda *a:a[-1])
   out=rt.run(api,[{'role':'system','content':''},{'role':'user','content':request}],jid,cid,'confirm_mutations');assert out['completed'] and out['canonical_report']['observation_status']==status and not out['canonical_report']['full_business_case_passed']
 print('DMI identity baseline: PASS (both OS closed Core/policy/own fresh/no-repeat, eight nonsecret fields/unknowns/raw spaces, read-only paths, runtime schemas; fixtures only)')
if __name__=='__main__':main()

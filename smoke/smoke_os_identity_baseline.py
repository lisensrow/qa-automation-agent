"""Closed native identity scope and existing Core/policy/own-result protections."""
from copy import deepcopy
from io import StringIO
from types import SimpleNamespace
from unittest.mock import patch
import json
import os_identity_baseline as p
def body(name):
 return {'probe_version':1,'platform':name,'query_complete':True,'error':'','values':{k:'Observed' for k in p.FIELDS[name]}}
def main():
 for name in ['windows','astra']:
  obj=body(name);s=p.summarize(obj,name)
  assert s['os_query_complete'] and s['native_values']==obj['values'] and s['observation_status']=='OBSERVED' and len(s['values_sha256'])==64
  assert all(s[k] is False for k in p.LIMITS)
  for change in [lambda o:o.update(probe_version=True),lambda o:o.update(platform='other'),lambda o:o['values'].update(extra='untrusted'),lambda o:o['values'].update(host_name='bad\nvalue'),lambda o:o['values'].update(host_name='x'*513),lambda o:o.update(query_complete=False),lambda o:o['values'].update(host_name=12)]:
   bad=deepcopy(obj);change(bad)
   try:p.summarize(bad,name);raise AssertionError('invalid identity accepted')
   except ValueError:pass
  empty=deepcopy(obj);empty['values']['host_name']='';unknown=p.summarize(empty,name)
  assert unknown['unknown_fields']==['host_name'] and unknown['observation_status']=='OBSERVED_WITH_UNKNOWNS' and not unknown['full_case_passed']
  failed={'probe_version':1,'platform':name,'query_complete':False,'values':{},'error':'native_os_identity_query_failed'}
  assert p.summarize(failed,name)['native_values'] is None and p.summarize(failed,name)['observation_status']=='BLOCKED'
  assert p.payload(name)['name']=='executeCommand' and len(p.sha(name))==64
 outputs=[]
 def native(text,exc=None):
  outputs.clear()
  with patch('builtins.open',side_effect=exc,return_value=StringIO(text)),patch('socket.gethostname',return_value='host'),patch('os.uname',return_value=SimpleNamespace(sysname='Linux',release='6.1.0',machine='x86_64')),patch('builtins.print',side_effect=outputs.append):
   exec(compile(p.ASTRA,'fixed-os-identity','exec'),{})
  return p.summarize(json.loads(outputs[0]),'astra')
 s=native('ID=astra\nNAME="Astra Linux"\nPRETTY_NAME="Astra Linux 1.8"\nVERSION_ID="1.8"\n')
 assert s['native_values']['kernel_release']=='6.1.0' and s['native_values']['os_release_name']=='Astra Linux'
 assert native('ID=astra\nID=other')['observation_status']=='BLOCKED'
 assert native('ID="unterminated')['observation_status']=='BLOCKED'
 assert native('x'*32769)['observation_status']=='BLOCKED'
 assert native('',FileNotFoundError)['observation_status']=='BLOCKED'
 assert 'os_release_version_id' in native('ID=astra')['unknown_fields']
 import smoke_drive_os_baseline as fixture
 def check(summary):
  assert summary['os_query_complete'] and summary['observation_status']=='OBSERVED' and summary['native_values']
  assert all(summary[k] is False for k in p.LIMITS)
 with patch.object(fixture,'p',p):
  for name in ['windows','astra']:fixture.core_fixture(name,body(name),check)
 # Exercise final runtime status schema, not only direct tool/parser fixtures.
 import job_store as store,endpoint_metadata as ep,endpoint_metadata_runtime as rt
 from pathlib import Path
 from tempfile import TemporaryDirectory
 from contextlib import ExitStack
 for status in ['OBSERVED','OBSERVED_WITH_UNKNOWNS','BLOCKED']:
  with TemporaryDirectory() as tmp,ExitStack() as stack:
   stack.enter_context(patch.object(store,'JOBS_DIR',Path(tmp)))
   r=ep.requirement('astra','fixture-os-identity-runtime',p.PROFILE)
   request='Run fixed read-only OS identity query '+' '.join(r[k] for k in ['ci_id','agent_id','ci_name','core_version','profile_id'])
   j=store.create_job(request,stand='lab',job_type='manual');jid=j['job_id'];cid=store.add_test_case(jid,'Fixture OS runtime',requirement=r)['case_id']
   store.set_job_status(jid,'running');store.update_test_case(jid,cid,status='running')
   summary=p.summarize(body('astra'),'astra');summary['observation_status']=status
   native={'native_result_verified':True,'operation_id':'fixture-op','summary':summary}
   stack.enter_context(patch.object(rt,'catalog',side_effect=[[{}],[]]))
   stack.enter_context(patch.object(rt,'decode_phase_decision',return_value={'function':{'name':ep.READ,'arguments':{'target':'astra'}}}))
   stack.enter_context(patch.object(rt,'phase_decision_schema',return_value={}))
   stack.enter_context(patch.object(rt,'list_operations',return_value=[{'status':'verified'}]))
   stack.enter_context(patch.object(rt,'reconcile_operation',return_value={'verified':True}))
   stack.enter_context(patch('tools.browser._session',SimpleNamespace(reset_case_context=lambda:None,close=lambda:None)))
   def ask(messages,tools,response_schema):
    if 'properties' not in response_schema:return {'message':{'content':'{}'}}
    assert response_schema['properties']['observation_status']['enum']==['OBSERVED','OBSERVED_WITH_UNKNOWNS','BLOCKED']
    return {'message':{'content':json.dumps({'observation_status':status,'full_business_case_passed':False,'summary':'Native identity only; no plugin/fullcase proof.'})}}
   api=SimpleNamespace(get_job=store.get_job,ask_ollama=ask,execute_tool_with_policy=lambda *a,**kw:deepcopy(native),
    record_tool_observations=lambda *a:[],record_tool_evidence=lambda *a,**kw:{'evidence_id':'fixture-evidence'},tool_result_for_model=lambda *a:a[-1])
   out=rt.run(api,[{'role':'system','content':''},{'role':'user','content':request}],jid,cid,'confirm_mutations')
   assert out['completed'] and out['canonical_report']['observation_status']==status and not out['canonical_report']['full_business_case_passed']
 print('OS identity baseline: PASS (both-OS Core/policy/own fresh/no-repeat, parser/unknown/closed output; fixtures only)')
if __name__=='__main__':main()

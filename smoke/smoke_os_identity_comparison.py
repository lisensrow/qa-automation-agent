"""Raw hypothesis only, both owned data hashes, original-versus-operator proof."""
from copy import deepcopy
from contextlib import ExitStack
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch
import hashlib,json
import os_identity_comparison as g,os_identity_baseline as baseline
import job_store as store,uqa
from operation_journal import list_operations
from tools.registry import execute_tool
from command_probe_contract import target,ORIGIN
REFS=[['20261017-000000-00000001','tc-00000001','ev-000000000001'],['20261017-000000-00000002','tc-00000002','ev-000000000002'],['20261017-000000-00000003','tc-00000003','ev-000000000003']]
def main():
 assert g.compare_fields({'data.host_name':'NETBIOS'},{'data.host_name':'dns-name'},'windows')['raw_hypothesis_status']=='MISMATCH'
 assert g.compare_fields({'data.host_name':'h'},{'data.host_name':'h\n'},'windows')['raw_hypothesis_status']=='MISMATCH'
 assert g.compare_fields({'data.host_name':'h'},{'data.host_name':None},'windows')['raw_hypothesis_status']=='BLOCKED'
 assert g.compare_fields({'data.host_name':''},{'data.host_name':''},'windows')['unknown_fields']==1
 for a,b in [({'other':'x'},{'other':'x'}),({'data.host_name':True},{'data.host_name':'h'})]:
  try:g.compare_fields(a,b,'windows');raise AssertionError('invalid raw fields accepted')
  except ValueError:pass
 assert execute_tool(g.TOOL,{'target':'astra'})['error']=='trusted_Core_job_case_context_required'
 assert uqa.classify_tool_action(g.TOOL,{'target':'astra'})=='observe'
 for name in ['windows','astra']:
  with TemporaryDirectory() as tmp,ExitStack() as stack:
   stack.enter_context(patch.object(store,'JOBS_DIR',Path(tmp)))
   req=g.requirement(name,'fixture-os-raw-pair-'+name,*REFS);request='Read only owned recorded pair '+' '.join(req[k] for k in ['ci_name','ci_id','agent_id','profile_id'])
   j=store.create_job(request,stand='lab',job_type='manual');jid=j['job_id'];cid=store.add_test_case(jid,'Fixture raw OS pair',requirement=req)['case_id']
   store.set_job_status(jid,'running');store.update_test_case(jid,cid,status='running');t=target(name)
   obj={'probe_version':1,'platform':name,'query_complete':True,'error':'','values':{k:'Observed' for k in baseline.FIELDS[name]}};obj['values']['host_name']='host'
   if name=='astra':obj['values']['kernel_release']='kernel'
   stdout=json.dumps(obj,ensure_ascii=False);at='2026-10-17T00:00:00+00:00';at2='2026-10-17T00:00:01+00:00'
   os={'task_id':'00000000-0000-4000-8000-000000000001','server_created_at':at,'processed_at':at,'summary':baseline.summarize(obj,name),'result_sha256':hashlib.sha256(stdout.encode()).hexdigest()}
   data={'host_name':'host','os':{'architecture':'64','current_build_os':'1','family':name,'name':'OS','version':'1','kernel_version':'kernel'}}
   audit={'task_id':'00000000-0000-4000-8000-000000000002','server_created_at':at,'processed_at':at2,'host_name':'host','os_subset':{k:data['os'][k] for k in ['architecture','current_build_os','family','name','version']}}
   expected={'data.host_name':'host'}
   if name=='astra':expected['data.os.kernel_version']='kernel'
   cp={'expected_raw_fields':expected};cap={'data_sha256':hashlib.sha256(json.dumps(data,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest(),'projected_raw_fields':dict(expected),'captured_at':'2026-10-17T00:00:02+00:00'}
   ofull={'id':os['task_id'],'agent_id':t['agent_id'],'name':'executeCommand','status':'success','created_at':at,'result':{'machine_uid':t['ci_id'],'processed_at':at,'data':{'stdout':stdout,'stderr':'','errorlevel':0}}}
   afull={'id':audit['task_id'],'agent_id':t['agent_id'],'name':'osAudit','status':'success','created_at':at,'result':{'machine_uid':t['ci_id'],'processed_at':at2,'result':'success','data':deepcopy(data)}}
   ci={'id':t['ci_id'],'agent_id':t['agent_id'],'name':t['ci_name'],'detail':{'os':{'name':'Windows 10' if name=='windows' else 'Astra Linux','architecture':'64'}}};base=ORIGIN+'/api/v1/agents/'+t['agent_id'];gets=[]
   class Response:
    status=200
    def __init__(self,value):self.value=value
    def json(self):return deepcopy(self.value)
   def get(url,params=None,timeout=None):
    gets.append(url)
    if url==base:return Response({'id':t['agent_id'],'version':'1.3.27','status':'online'})
    if url==base+'/tasks/'+os['task_id']+'/full':return Response(ofull)
    assert url==base+'/tasks/'+audit['task_id']+'/full';return Response(afull)
   session=SimpleNamespace(_ensure_started=lambda:None,_observed_agent_task_context=lambda name:(ci,{},base+'/tasks',None),_same_https_origin_url=lambda observed,path:ORIGIN+path,context=SimpleNamespace(request=SimpleNamespace(get=get)))
   stack.enter_context(patch('tools.browser._session',session));stack.enter_context(patch.object(g,'source_proofs',side_effect=lambda r:deepcopy((os,audit,cp,cap))))
   args={'target':name};ctx={'job_id':jid,'case_id':cid,'force_read_only':True,'action_policy':'confirm_mutations'};messages=[{'role':'user','content':request}]
   out=uqa.execute_tool_with_policy(g.TOOL,args,messages,**ctx);assert not out.get('error'),out
   assert out['raw_hypothesis_status']=='MATCH' and out['raw_equal_fields']==len(g.RULES[name]) and not list_operations(jid) and out['new_agent_tasks']==0
   assert out['same_audit_data_as_operator_capture'] and not out['same_audit_full_payload_as_original_model_read_proved'] and all(out[k] is False for k in g.LIMITS)
   view=uqa.tool_result_for_model(g.TOOL,out);assert view['rows']==out['rows'] and view['full_source_case_status']=='BLOCKED'
   extra=deepcopy(out);extra['private_full_payload']=['must not emit'];assert 'private_full_payload' not in g.compact(extra)
   for key,value in [('full_case_passed',True),('normalization_applied',True),('same_audit_full_payload_as_original_model_read_proved',True),('field_count',True),('raw_hypothesis_status','MISMATCH'),('audit_data_sha256','bad')]:
    forged=deepcopy(out);forged[key]=value;assert not g.compact(forged)
   n=len(gets);wrong='astra' if name=='windows' else 'windows';assert uqa.execute_tool_with_policy(g.TOOL,{'target':wrong},messages,**ctx).get('error') and len(gets)==n
   ofull['result']['data']['stdout']+=' ';assert uqa.execute_tool_with_policy(g.TOOL,args,messages,**ctx).get('error');ofull['result']['data']['stdout']=stdout
   afull['result']['data']['host_name']='changed';assert uqa.execute_tool_with_policy(g.TOOL,args,messages,**ctx).get('error');afull['result']['data']=deepcopy(data)
   audit['processed_at']='2026-10-17T01:00:00+00:00';n=len(gets);assert uqa.execute_tool_with_policy(g.TOOL,args,messages,**ctx).get('error') and len(gets)==n
 print('OS identity raw comparison: PASS (two-OS Core READ/no operations, exact fields/unknown/no normalization, both hashes/time, explicit operator proof and no normative/fullcase claim; fixtures only)')
if __name__=='__main__':main()

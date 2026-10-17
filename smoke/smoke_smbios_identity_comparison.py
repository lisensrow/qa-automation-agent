"""Synthetic DMI comparison checks, never runtime business acceptance."""
from copy import deepcopy
from contextlib import ExitStack
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch
import hashlib,json
import smbios_identity_comparison as g,smbios_os_baseline as baseline,job_store as store,uqa
from command_probe_contract import target,ORIGIN
from operation_journal import list_operations
from tools.registry import execute_tool
REFS=[['20261017-000000-00000001','tc-00000001','ev-000000000001'],['20261017-000000-00000002','tc-00000002','ev-000000000002']]
def main():
 values={k:'Known' for k in g.MAPPING};data={}
 for k,p in g.MAPPING.items():
  category,field=p.removeprefix('data.').split('[].');data.setdefault(category,[{}])[0][field]=values[k]
 assert g.compare_fields(values,g.project(data))['raw_equal_fields']==8
 for key in values:
  for other,status in [('known','RAW_DIFFERENT'),('Known ','RAW_DIFFERENT'),('None','UNKNOWN'),('', 'UNKNOWN'),(None,'UNKNOWN')]:
   a=dict(values);a[key]=other;row=next(r for r in g.compare_fields(values,a)['rows'] if r['field']==key);assert row['status']==status
 for category in data:
  d=deepcopy(data);d[category].append(dict(d[category][0]));assert g.compare_fields(values,g.project(d))['unknown_fields']>0
 for bad in [True,{},'x'*513,'a\nb']:
  a=dict(values);a['bios_vendor']=bad
  try:g.compare_fields(values,a);raise AssertionError('invalid string accepted')
  except ValueError:pass
 assert execute_tool(g.TOOL,{'target':'astra'})['error']=='trusted_Core_job_case_context_required'
 assert uqa.classify_tool_action(g.TOOL,{'target':'astra'})=='observe'
 for name in ['windows','astra']:
  with TemporaryDirectory() as tmp,ExitStack() as stack:
   stack.enter_context(patch.object(store,'JOBS_DIR',Path(tmp)))
   r=g.requirement(name,'fixture-dmi-pair-'+name,*REFS);request='Read only recorded pair '+' '.join(r[k] for k in ['ci_name','ci_id','agent_id','profile_id'])
   j=store.create_job(request,stand='lab',job_type='manual');jid=j['job_id'];cid=store.add_test_case(jid,'Synthetic DMI pair',requirement=r)['case_id']
   store.set_job_status(jid,'running');store.update_test_case(jid,cid,status='running');t=target(name)
   obj={'probe_version':1,'platform':name,'query_complete':True,'error':'','values':dict(values)};stdout=json.dumps(obj)
   at='2026-10-17T00:00:00+00:00';at2='2026-10-17T00:00:01+00:00'
   n={'task_id':'00000000-0000-4000-8000-000000000001','server_created_at':at,'processed_at':at,'result_sha256':hashlib.sha256(stdout.encode()).hexdigest(),'summary':baseline.summarize(obj,name)}
   a={'task_id':'00000000-0000-4000-8000-000000000002','server_created_at':at,'processed_at':at2,'audit_data_summary':{'data_sha256':g.digest(data)}}
   cp={'expected_raw_fields':dict(values)}
   nf={'id':n['task_id'],'agent_id':t['agent_id'],'name':'executeCommand','status':'success','created_at':at,'result':{'machine_uid':t['ci_id'],'processed_at':at,'data':{'stdout':stdout,'stderr':'','errorlevel':0}}}
   af={'id':a['task_id'],'agent_id':t['agent_id'],'name':'smbiosAudit','status':'success','created_at':at,'result':{'machine_uid':t['ci_id'],'processed_at':at2,'result':'success','data':deepcopy(data)}}
   ci={'id':t['ci_id'],'agent_id':t['agent_id'],'name':t['ci_name'],'detail':{'os':{'name':'Windows 10' if name=='windows' else 'Astra Linux','architecture':'64'}}};base=ORIGIN+'/api/v1/agents/'+t['agent_id'];gets=[]
   class Response:
    status=200
    def __init__(self,v):self.v=v
    def json(self):return deepcopy(self.v)
   def get(url,params=None,timeout=None):
    gets.append(url)
    if url==base:return Response({'id':t['agent_id'],'version':'1.3.27','status':'online'})
    if url==base+'/tasks/'+n['task_id']+'/full':return Response(nf)
    assert url==base+'/tasks/'+a['task_id']+'/full';return Response(af)
   session=SimpleNamespace(_ensure_started=lambda:None,_observed_agent_task_context=lambda name:(ci,{},base+'/tasks',None),_same_https_origin_url=lambda observed,path:ORIGIN+path,context=SimpleNamespace(request=SimpleNamespace(get=get)))
   flags={'source_audit_workflow_completed':False,'source_audit_final_report_accepted':False}
   stack.enter_context(patch('tools.browser._session',session));source=stack.enter_context(patch.object(g,'source_proofs',side_effect=lambda r:deepcopy((n,a,cp,flags))))
   ctx={'job_id':jid,'case_id':cid,'force_read_only':True,'action_policy':'confirm_mutations'};messages=[{'role':'user','content':request}];args={'target':name}
   out=uqa.execute_tool_with_policy(g.TOOL,args,messages,**ctx);assert not out.get('error'),out
   assert out['raw_equal_fields']==8 and out['same_entire_audit_data_as_original_model_read'] and all(out[k] is False for k in g.LIMITS) and not list_operations(jid)
   assert not out['source_audit_workflow_completed'] and not out['source_audit_final_report_accepted']
   assert uqa.tool_result_for_model(g.TOOL,out)['rows']==out['rows']
   for key,value in [('full_case_passed',True),('field_count',True),('raw_hypothesis_status','MISMATCH'),('pair_seconds',1801),('audit_data_sha256','bad'),('same_entire_audit_data_as_original_model_read',False)]:
    b=deepcopy(out);b[key]=value;assert not g.compact(b)
   before=len(gets);wrong='astra' if name=='windows' else 'windows';assert uqa.execute_tool_with_policy(g.TOOL,{'target':wrong},messages,**ctx).get('error') and len(gets)==before
   nf['result']['data']['stdout']+=' ';assert uqa.execute_tool_with_policy(g.TOOL,args,messages,**ctx)['blocked_stage']=='native_payload';nf['result']['data']['stdout']=stdout
   af['result']['data']['unused_field']='changed';assert uqa.execute_tool_with_policy(g.TOOL,args,messages,**ctx)['blocked_stage']=='audit_payload';af['result']['data']=deepcopy(data)
   a['processed_at']='2026-10-17T01:00:00+00:00';before=len(gets);assert uqa.execute_tool_with_policy(g.TOOL,args,messages,**ctx)['blocked_stage']=='time_window' and len(gets)==before;a['processed_at']=at2
   source.side_effect=ValueError('private error must not escape');b=uqa.execute_tool_with_policy(g.TOOL,args,messages,**ctx);assert b['blocked_stage']=='source_proofs' and 'private' not in json.dumps(b)
 print('DMI raw comparison: PASS (eight fields/unknown/cardinality/no normalization, both OS Core/no operations/original hashes/time/privacy; synthetic only)')
if __name__=='__main__':main()

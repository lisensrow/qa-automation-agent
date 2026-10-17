"""Safe stage feedback never hides hash/source failure as a navigation issue."""
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import json
import uqa,job_store as store,os_identity_comparison as g
from operation_journal import list_operations
from command_probe_contract import ORIGIN,target
REFS=[['20261017-000000-00000001','tc-00000001','ev-000000000001'],['20261017-000000-00000002','tc-00000002','ev-000000000002'],['20261017-000000-00000003','tc-00000003','ev-000000000003']]
def main():
 for stage in g.BLOCK_STAGES:
  for name in ['windows','astra',None]:
   out=g.blocked(stage,name);assert g.compact(out)==out
   assert bool(out['read_context_prerequisites'])==(stage=='observed_context' and name is not None)
   assert not out['mutation_executed'] and out['new_agent_tasks']==0 and not out['resend_authorized']
   extra={**out,'private_exception':'sensitive must not emit'};assert 'private_exception' not in g.compact(extra)
   for key,val in [('blocked_stage','arbitrary'),('prerequisites_are_not_execution_authority',False),('new_agent_tasks',True),('full_case_passed',True)]:
    bad=deepcopy(out);bad[key]=val;assert not g.compact(bad)
 for name in ['windows','astra']:
  with TemporaryDirectory() as tmp,patch.object(store,'JOBS_DIR',Path(tmp)):
   r=g.requirement(name,'fixture-os-context-'+name,*REFS);request='Only read '+' '.join(r[k] for k in ['ci_name','ci_id','agent_id','profile_id'])
   j=store.create_job(request,stand='lab',job_type='manual');jid=j['job_id'];cid=store.add_test_case(jid,'Context feedback',requirement=r)['case_id']
   store.set_job_status(jid,'running');store.update_test_case(jid,cid,status='running')
   os={'processed_at':'2026-10-17T00:00:00Z'};audit={'processed_at':'2026-10-17T00:00:01Z'}
   with patch.object(g,'source_proofs',return_value=(os,audit,{},{})),patch.object(g,'context',side_effect=ValueError('sensitive internal detail')) as ctx,patch.object(g,'read_json',side_effect=AssertionError('no GET before context')):
    out=g.inspect(None,{'target':name},jid,cid);assert out['blocked_stage']=='observed_context' and out['observed_agent_task_context_required']
    assert out['read_context_prerequisites']==[{'tool':'browser_open_page','arguments':{'url':ORIGIN+'/cmdb'}},{'tool':'browser_open_agent_tasks_semantic','arguments':{'ci_name':target(name)['ci_name']}}]
    assert 'sensitive' not in json.dumps(out) and ctx.call_count==1
    assert uqa.tool_result_for_model(g.TOOL,out)['blocked_stage']=='observed_context'
    assert uqa._historical_browser_result_summary(g.TOOL,json.dumps(out))['blocked_stage']=='observed_context'
   with patch.object(g,'source_proofs',side_effect=ValueError('private source error')),patch.object(g,'context',side_effect=AssertionError('no context after bad source')):
    out=g.inspect(None,{'target':name},jid,cid);assert out['blocked_stage']=='source_proofs' and not out['read_context_prerequisites']
   audit['processed_at']='2026-10-17T01:00:00Z'
   with patch.object(g,'source_proofs',return_value=(os,audit,{},{})),patch.object(g,'context',side_effect=AssertionError('no context after bad time')):
    out=g.inspect(None,{'target':name},jid,cid);assert out['blocked_stage']=='time_window' and not out['read_context_prerequisites']
   assert not list_operations(jid) and store.get_job(jid)['test_cases'][0]['requirement']==r
 print('OS pair context feedback: PASS (safe enum, exact READ prerequisites only for missing context, source/time remain blocked, no raw exception/authority/action; fixtures only)')
if __name__=='__main__':main()

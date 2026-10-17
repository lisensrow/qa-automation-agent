"""Existing exact pair scope exposes READ schemas, not RAM intent from product memory."""
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import uqa,job_store as store,os_identity_comparison as g
from operation_journal import list_operations
REFS=[['20261017-000000-00000001','tc-00000001','ev-000000000001'],['20261017-000000-00000002','tc-00000002','ev-000000000002'],['20261017-000000-00000003','tc-00000003','ev-000000000003']]
class StopProbe(BaseException):pass
def main():
 for name in ['windows','astra']:
  with TemporaryDirectory() as tmp,patch.object(store,'JOBS_DIR',Path(tmp)):
   r=g.requirement(name,'fixture-os-pair-catalog-'+name,*REFS)
   text='Только чтение. Возьми из продуктовой памяти правила osAudit для '+' '.join(r[k] for k in ['ci_name','ci_id','agent_id','profile_id'])
   j=store.create_job(text,stand='lab',job_type='manual');jid=j['job_id'];cid=store.add_test_case(jid,'Exact read pair',requirement=r)['case_id']
   store.set_job_status(jid,'running');store.update_test_case(jid,cid,status='running');j=store.get_job(jid)
   expected={g.TOOL,'browser_open_agent_tasks_semantic'}
   assert g.schema_tools_for_case(j,cid)==expected
   assert g.schema_tools_for_case(j,'missing')==set() and g.schema_tools_for_case(None,cid)==set()
   for key,value in [('locked',False),('target','other'),('action_profile','write_ui_state'),('max_pair_seconds',1801),('normalization_allowed',True)]:
    wrong=deepcopy(j);wrong['test_cases'][0]['requirement'][key]=value;assert not g.schema_tools_for_case(wrong,cid)
   for key,value in [('status','blocked'),('stand','other'),('resources',[{'id':'x'}]),('request','unbound')]:
    wrong=deepcopy(j);wrong[key]=value;assert not g.schema_tools_for_case(wrong,cid)
   messages=[{'role':'system','content':'Fixture no model call or browser'},{'role':'user','content':text}];seen=[]
   def capture(messages,**kw):seen.append(({x['function']['name'] for x in kw['tools']},deepcopy(messages)));raise StopProbe()
   with patch.object(uqa,'append_reviewed_product_memory',return_value=[]),patch.object(uqa,'ask_ollama',side_effect=capture),patch.object(g,'source_proofs',side_effect=AssertionError('catalog may not read source payloads')):
    try:uqa.run_turn(messages,job_id=jid,case_id=cid,force_read_only=True,action_policy='confirm_mutations')
    except StopProbe:pass
   assert len(seen)==1 and expected<=seen[0][0]
   assert not any('READ-ONLY AGENT TELEMETRY ROUTE' in str(x.get('content')) for x in seen[0][1])
   assert uqa._read_only_agent_telemetry_route_message('Только чтение RAM '+r['ci_name'],r['ci_name']), 'other RAM cases retain ordinary behavior'
   assert not list_operations(jid) and store.get_job(jid)['test_cases'][0]['requirement']==r
 print('OS pair catalog routing: PASS (both OS existing exact scope, malformed/nonrunning/non-READ refusal, product memory not RAM route, schemas only/no source fetch/no action; fixture only)')
if __name__=='__main__':main()

"""Preparation-only synthetic source proof; no real source archive or agent access."""
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from copy import deepcopy
import hashlib,json
import job_store as store,regression_source_reader as source,regression_read_coverage as g

def main():
 assert g.covered('abcdef',[(0,3),(0,3),(2,6)])['covered_chars']==6
 assert not g.covered('abcdef',[(0,2),(3,6)])['complete']
 assert g.covered('abcdef',[(3,6)])['next_unread_offset']==0
 assert not g.covered('',[])['complete'] and g.covered('',[(0,0)])['complete']
 with TemporaryDirectory() as temp:
  root=Path(temp)/'sources';root.mkdir();key='US-T999904'
  obj={'key':key,'title':'Synthetic source fixture','updated_on':'unknown','precondition_html':'fixture prerequisites','objective_html':'fixture only',
   'steps':[{'number':1,'description_html':'Run smbiosAudit','test_data_html':'{"name":"smbiosAudit"}','expected_html':'Пример '*1800},
            {'number':2,'description_html':'Later step','test_data_html':'','expected_html':'fixture result'}]}
  raw=json.dumps(obj,ensure_ascii=False).encode();(root/(key+'.json')).write_bytes(raw)
  manifest={'cycles':[{'key':'US-Cfixture','cases':[{'key':key,'steps':2,'number':2,'json_sha256':hashlib.sha256(raw).hexdigest()}]}]}
  raw=json.dumps(manifest).encode();(root/'manifest.json').write_bytes(raw)
  with patch.object(source,'ROOT',root),patch.object(source,'MANIFEST_SHA',hashlib.sha256(raw).hexdigest()),patch.object(store,'JOBS_DIR',Path(temp)/'jobs'):
   r=g.requirement(key,'fixture-own-source-coverage');j=store.create_job('Read source only '+key,stand='lab',job_type='manual');jid=j['job_id'];cid=store.add_test_case(jid,'Synthetic own-source coverage',requirement=r)['case_id']
   store.set_job_status(jid,'running');store.update_test_case(jid,cid,status='running');args={'case_key':key,'step_number':1}
   def receipt(tool,a,v,owner='uqa_tool'):
    return store.add_evidence(jid,cid,tool,json.dumps({'tool':tool,'arguments':a,'result':v}),source=owner,execution_status='not_executed',usable_for_pass=False,usable_for_verdict=False,eligibility_reason='synthetic_read_receipt')
   out=g.inspect(jid,cid,args);assert not out['step_cells_completely_read'] and not out['case_precondition_and_objective_observed']
   held=None
   for f in g.FIELDS:
    for offset in range(0,len(obj['steps'][0][f]),1500):
     a={'case_key':key,'step_number':1,'field':f,'char_offset':offset,'char_count':1500};p=source.read_step_cell(**a)
     assert p['status']=='source_cell_page_observed'
     if f=='expected_html' and offset==1500:held=(a,p);continue
     receipt(source.CELL_TOOL,a,p)
   out=g.inspect(jid,cid,args);assert not out['step_cells_completely_read'] and out['fields']['expected_html']['next_unread_offset']==1500
   receipt(source.CELL_TOOL,*held,owner='operator_preparation');assert not g.inspect(jid,cid,args)['step_cells_completely_read']
   receipt(source.CELL_TOOL,*held);receipt(source.CELL_TOOL,*held)
   out=g.inspect(jid,cid,args);assert out['step_cells_completely_read'] and not out['complete_case_source_content_read'] and not out['case_precondition_and_objective_observed']
   assert out['fields']['expected_html']['covered_chars']==len(obj['steps'][0]['expected_html']) and all(out[k] is False for k in g.NEGATIVES)
   assert 'smbiosAudit' not in json.dumps(out), 'coverage may not supply semantic answer'
   a={'case_key':key,'first_step':2,'step_count':1};p=source.read_case(**a);assert p['status']=='source_window_observed';receipt(source.TOOL,a,p)
   out=g.inspect(jid,cid,args);assert out['complete_case_source_content_read'] and not out['semantic_understanding_verified'] and not out['runtime_executed']
   import uqa
   from tools.registry import execute_tool
   from operation_journal import list_operations
   assert execute_tool(g.TOOL,args)['error']=='trusted_Core_job_case_context_required'
   assert uqa.classify_tool_action(g.TOOL,args)=='observe'
   assert g.TOOL in {t['function']['name'] for t in uqa.model_tool_catalog()}
   ctx={'job_id':jid,'case_id':cid,'force_read_only':True,'action_policy':'confirm_mutations'};messages=[{'role':'user','content':'Read only source '+key}]
   # A real Core-produced source receipt must remain valid despite policy metadata.
   a0={'case_key':key,'step_number':1,'field':'description_html','char_offset':0,'char_count':1500}
   native=uqa.execute_tool_with_policy(source.CELL_TOOL,a0,messages,**ctx);ev=uqa.record_tool_evidence(jid,cid,source.CELL_TOOL,a0,native)
   assert ev['source']=='uqa_tool' and ev['execution_status']=='not_executed'
   core=uqa.execute_tool_with_policy(g.TOOL,args,messages,**ctx);assert core['step_cells_completely_read'] and core['complete_case_source_content_read'] and not core['business_pass']
   assert uqa.tool_result_for_model(g.TOOL,core)['step_cells_completely_read']
   assert uqa.execute_tool_with_policy(g.TOOL,{'case_key':'US-T999999','step_number':1},messages,**ctx).get('error')
   assert not list_operations(jid) and store.get_job(jid)['test_cases'][0]['requirement']==r
   assert g.inspect(jid,cid,{'case_key':key,'step_number':True})['status']=='blocked_own_source_read_coverage'
   assert g.inspect(jid,'wrong',args)['status']=='blocked_own_source_read_coverage'
   wrong=deepcopy(p);wrong['steps'][0]['description_html']='forged';receipt(source.TOOL,a,wrong)
   out=g.inspect(jid,cid,args);assert out['status']=='blocked_own_source_read_coverage' and not out['full_case_passed']
 print('Own regression source coverage: PASS (synthetic own receipts, exact hashes/pages/gaps/duplicate union/empty fields, operator receipts ignored, no semantic answer/runtime/fullcase authority; preparation only)')
if __name__=='__main__':main()

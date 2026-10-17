"""Synthetic source JSON analysis; not semantic or product regression acceptance."""
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import hashlib,json
import regression_json_example as g,regression_source_reader as source,regression_read_coverage as coverage,job_store as store,uqa
from tools.registry import execute_tool
from operation_journal import list_operations
def main():
 good='<p>{&nbsp;"data":[{"name":"private-value","other":1}]}</p>'
 a=g.analyze(good);assert a['json_valid'] and a['data_object_key_sets']==[['name','other']] and all(a[k] is False for k in g.NEGATIVES) and 'private-value' not in json.dumps(a)
 for text,kind in [('{"x":1, - annotation\n "y":2}','json_syntax_error'),('{"x":1,"x":2}','duplicate_json_key'),('{"x":NaN}','nonstandard_json_constant')]:
  o=g.analyze(text);assert not o['json_valid'] and o['json_error_kind']==kind and not o['data_object_key_sets']
 raw='<p>{"x":"a&nbsp;b"}</p>';o=g.analyze(raw);assert o['projected_text_sha256']==hashlib.sha256('{"x":"a\xa0b"}'.encode()).hexdigest()
 for bad in ['<script>{}</script>','x'*32769]:
  try:g.analyze(bad);raise AssertionError('unsafe/big example accepted')
  except ValueError:pass
 assert execute_tool(g.TOOL,{})['error']=='trusted_Core_job_case_context_required'
 assert g.TOOL in {x['function']['name'] for x in uqa.model_tool_catalog()}
 with TemporaryDirectory() as temp:
  root=Path(temp)/'source';root.mkdir();key='US-T999903';obj={'key':key,'title':'fixture','updated_on':'unknown','precondition_html':'fixture','objective_html':'fixture','steps':[{'number':1,'description_html':'Fixture source','test_data_html':'{"name":"fixture"}','expected_html':good}]}
  raw=json.dumps(obj).encode();p=root/(key+'.json');p.write_bytes(raw);manifest={'cycles':[{'key':'US-Cfixture','cases':[{'key':key,'steps':1,'number':1,'json_sha256':hashlib.sha256(raw).hexdigest()}]}]};mr=json.dumps(manifest).encode();(root/'manifest.json').write_bytes(mr)
  with patch.object(source,'ROOT',root),patch.object(source,'MANIFEST_SHA',hashlib.sha256(mr).hexdigest()),patch.object(store,'JOBS_DIR',Path(temp)/'jobs'):
   r=coverage.requirement(key,'fixture-json-example');j=store.create_job('Read only source '+key,stand='lab',job_type='manual');jid=j['job_id'];cid=store.add_test_case(jid,'fixture',requirement=r)['case_id'];store.set_job_status(jid,'running');store.update_test_case(jid,cid,status='running')
   args={'case_key':key,'step_number':1,'field':'expected_html'};ctx={'job_id':jid,'case_id':cid,'force_read_only':True,'action_policy':'confirm_mutations'};messages=[{'role':'user','content':'Read only '+key}]
   assert uqa.classify_tool_action(g.TOOL,args)=='observe'
   assert uqa.execute_tool_with_policy(g.TOOL,args,messages,**ctx)['status']=='blocked_source_json_example'
   sa={'case_key':key,'first_step':1,'step_count':1};out=source.read_case(**sa)
   store.add_evidence(jid,cid,source.TOOL,json.dumps({'tool':source.TOOL,'arguments':sa,'result':out}),source='operator_preparation',execution_status='not_executed',usable_for_pass=False,usable_for_verdict=False,eligibility_reason='fixture')
   assert g.inspect(jid,cid,args)['status']=='blocked_source_json_example'
   native=uqa.execute_tool_with_policy(source.TOOL,sa,messages,**ctx);uqa.record_tool_evidence(jid,cid,source.TOOL,sa,native)
   out=uqa.execute_tool_with_policy(g.TOOL,args,messages,**ctx);assert out['status']=='own_source_json_example_inspected' and out['json_valid'] and out['complete_case_source_receipts'] and not list_operations(jid)
   assert out['data_object_key_sets']==[['name','other']] and all(out[k] is False for k in g.NEGATIVES)
   before=p.read_bytes();assert g.inspect(jid,cid,args)['json_valid'] and p.read_bytes()==before
   bad={**args,'step_number':True};assert uqa.execute_tool_with_policy(g.TOOL,bad,messages,**ctx).get('error')
   p.write_bytes(before+b' ');assert g.inspect(jid,cid,args)['status']=='blocked_source_json_example'
 print('Source JSON example: PASS (strict syntax/duplicates/nonstandard constants/own receipt/hash/HTML/value privacy/budgets/Core READ/no ops; synthetic only)')
if __name__=='__main__':main()

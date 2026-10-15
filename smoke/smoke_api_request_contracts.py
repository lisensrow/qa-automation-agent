"""Bounded two-page composition, no API, file-source injection or model calls."""
from copy import deepcopy
from unittest.mock import patch
import api_contract_sources as reader
from api_contract_projection import FLAGS,MAX_OUTPUT_BYTES
from diagnostic_scope import scope_diagnostic_arguments
import uqa
from tools.registry import execute_tool,TOOLS

ref='#/components/schemas/Request'
base={'contract_observation_status':'observed','source_id':'fixture-source','source_job_id':'fixture-job',
    'source_case_id':'fixture-case','source_evidence_id':'fixture-proof','stand':'fixture',
    'schema_sha256':'a'*64,'projection_sha256':'b'*64,'method':'POST','path_template':'/fixture',**FLAGS}
root={**base,'operation':{'operation_id':'fixture_create','request_body':{
    'required':True,'content':{'application/json':{'$ref':ref}}}},'direct_schema_references':[ref]}
page={**base,'schema_reference':ref,'schema':{'type':'object','required':['name'],
    'properties':{'name':{'type':'string'}}},'direct_schema_references':[]}
def run(r=root,p=page):
    with patch.object(reader,'inspect_registered_contract_page',side_effect=[r,p]) as lookup:
        result=reader.inspect_registered_request_contract('fixture','POST','/fixture')
        return result,lookup
r,lookup=run()
assert r['contract_observation_status']=='observed' and r['observed_page_count']==2
assert r['request_schema_reference']==ref and r['request_schema']['required']==['name']
assert all(r[k] is False for k in FLAGS) and r['current_schema_recency_verified'] is False
assert r['defaults_exported'] is False and r['examples_exported'] is False and r['descriptions_exported'] is False
lookup.assert_any_call('fixture','POST','/fixture',[ref],source_id='fixture-source')
for key in ('source_id','source_job_id','source_case_id','source_evidence_id','stand',
            'schema_sha256','projection_sha256','method','path_template'):
    bad=deepcopy(page);bad[key]='changed'
    assert run(p=bad)[0]['reason']=='registered_request_revision_changed',key
bad=deepcopy(page);bad['schema_reference']='#/components/schemas/Other'
assert run(p=bad)[0]['reason']=='registered_request_revision_changed'
for content in ({},{'type':'object'},{'$ref':ref,'type':'object'}):
    bad=deepcopy(root);bad['operation']['request_body']['content']['application/json']=content
    result,lookup=run(r=bad)
    assert result['reason']=='registered_json_request_root_not_single_reference' and lookup.call_count==1
bad=deepcopy(root);bad['direct_schema_references']=[]
assert run(r=bad)[0]['reason']=='registered_request_reference_not_exposed'
bad=deepcopy(page);bad['schema']['properties']['name']['format']='x'*MAX_OUTPUT_BYTES
assert run(p=bad)[0]['reason']=='registered_request_output_budget'
unavailable={'contract_observation_status':'unavailable','reason':'registered_contract_source_not_unique',
    'available_source_ids':['fixture-source','fixture-source-v2'],**FLAGS}
result,lookup=run(r=unavailable)
assert result==unavailable and lookup.call_count==1
bound={'stand':'fixture','test_cases':[{'case_id':'active','requirement':{'api_contract_source_id':'fixture-source'}}]}
available=deepcopy(bound);available['job_type']='manual';available['test_cases'][0]['requirement']['action_profile']='read_only'
assert reader.schema_tools_for_case(available,'active')=={'api_inspect_contract_page','api_inspect_request_contract'}
catalog=uqa.model_tool_catalog(reader.schema_tools_for_case(available,'active'))
original=deepcopy(catalog);scoped=reader.bind_reader_catalog(catalog,available,'active')
assert catalog==original
for tool in scoped:
    f=tool['function']
    if f['name'] in reader.schema_tools_for_case(available,'active'):
        assert not {'stand','source_id'} & set(f['parameters']['properties'])
        assert {'method','path'} <= set(f['parameters']['required'])
        assert 'injected from this QA case' in f['description']
assert reader.bind_reader_catalog(catalog,{},'missing') is catalog
for change in ('source','profile','stand','job_type','missing_case'):
    bad=deepcopy(available)
    if change=='source':bad['test_cases'][0]['requirement']['api_contract_source_id']='../../private'
    elif change=='profile':bad['test_cases'][0]['requirement']['action_profile']='write_resource'
    elif change=='stand':bad['test_cases'][0]['requirement']['stand']='other'
    elif change=='job_type':bad['job_type']='advisory'
    assert reader.schema_tools_for_case(bad,'missing' if change=='missing_case' else 'active')==set()
assert scope_diagnostic_arguments('api_inspect_request_contract',{},bound,'active')[0]['source_id']=='fixture-source'
assert scope_diagnostic_arguments('api_inspect_request_contract',{'source_id':'other'},bound,'active')[1]=='diagnostic_source_mismatch'
assert scope_diagnostic_arguments('api_inspect_request_contract',{'stand':'other'},bound,'active')[1]=='diagnostic_stand_mismatch'
assert execute_tool('api_inspect_request_contract',{'source_file':'private'})['reason']=='contract_tool_arguments_invalid'
assert uqa.classify_tool_action('api_inspect_request_contract',{})=='observe'
assert any(t['function']['name']=='api_inspect_request_contract' for t in TOOLS)
with patch.object(uqa,'add_evidence',side_effect=lambda *a,**kw:kw):
    proof=uqa.record_tool_evidence('fixture-job','fixture-case','api_inspect_request_contract',{},r)
    assert proof['usable_for_pass'] is False and proof['usable_for_verdict'] is False
print('PASS registered request contract: two same-source/pin pages, direct JSON ref only, scope/caller lock, ambiguity/revision/budget denial, no HTTP/PASS')

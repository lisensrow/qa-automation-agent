"""Isolated registration/provenance/stand tests; no API or model execution."""
import copy
import hashlib
import json
from pathlib import Path
import runpy
import tempfile
from unittest.mock import patch
import api_contract_sources as reader
from diagnostic_scope import scope_diagnostic_arguments

fixture=runpy.run_path(str(Path(__file__).with_name('smoke_api_contract_projection.py')))
raw=json.dumps(fixture['base'])
entry={'source_id':'fixture-source','stand':'fixture','origin':'https://fixture.test',
    'job_id':'fixture-job','case_id':'fixture-case','evidence_id':'fixture-evidence',
    'projection_sha256':hashlib.sha256(raw.encode()).hexdigest(),'schema_sha256':fixture['schema_pin']}
receipt={'evidence_id':'fixture-evidence','type':'operator_installed_schema_projection',
    'source':'operator_installed_schema_read','execution_status':'observed',
    'usable_for_pass':False,'usable_for_verdict':False,'value':raw}
job={'stand':'fixture','test_cases':[{'case_id':'fixture-case','evidence':[receipt]}]}
def read(**kwargs):return reader.inspect_registered_contract_page('fixture','GET','/items/{uid}',**kwargs)
with tempfile.TemporaryDirectory() as temp:
    root=Path(temp)
    manifest=root/'api_contract_sources.json'
    def save(entries):manifest.write_text(json.dumps({'version':1,'sources':entries}),encoding='utf-8')
    with patch.object(reader.job_store,'JOBS_DIR',root/'jobs'),patch.object(reader.job_store,'get_job',return_value=job),patch.object(reader,'get_stand',return_value={'web_url':'https://fixture.test'}):
        assert read()['contract_observation_status']=='unavailable'
        save([entry]);r=read()
        assert r['contract_observation_status']=='observed' and r['source_registration_verified']
        assert not r['current_schema_recency_verified'] and all(r[k] is False for k in reader.FLAGS)
        assert read(reference_chain=['#/components/schemas/Item'])['schema']['required']==['id']
        assert read(source_id='../../private')['reason']=='registered_contract_source_invalid'
        assert read(source_id='other')['reason']=='registered_contract_source_not_unique'
        assert read(source_id='other')['available_source_ids']==['fixture-source']
        second={**entry,'source_id':'fixture-source-v2'};save([entry,second])
        assert read()['reason']=='registered_contract_source_not_unique'
        assert read(source_id='fixture-source')['contract_observation_status']=='observed'
        assert read(source_id='fixture-source-v2')['source_id']=='fixture-source-v2'
        foreign={**second,'source_id':'foreign-source','stand':'other'};save([entry,foreign])
        assert read(source_id='foreign-source')['contract_observation_status']=='unavailable'
        assert read(source_id='foreign-source')['available_source_ids']==['fixture-source']
        bad=copy.deepcopy(entry);bad['projection_sha256']='0'*64;save([bad])
        assert read()['reason']=='registered_contract_evidence_hash_mismatch'
        bad=copy.deepcopy(entry);bad['stand']='other';save([bad])
        assert read()['reason']=='registered_contract_source_not_unique'
        save([entry,entry]);assert read()['reason']=='registered_contract_source_invalid'
        save([entry])
        with patch.object(reader,'get_stand',return_value={'web_url':'https://other.test'}):
            assert read()['reason']=='registered_contract_stand_origin_mismatch'
        for key,value in [('source','model_claim'),('type','browser_get_network_detail'),('usable_for_pass',True),('execution_status','failed')]:
            bad=copy.deepcopy(job);bad['test_cases'][0]['evidence'][0][key]=value
            with patch.object(reader.job_store,'get_job',return_value=bad):
                assert read()['reason']=='registered_contract_source_invalid'
        bad=copy.deepcopy(job);bad['stand']='other'
        with patch.object(reader.job_store,'get_job',return_value=bad):
            assert read()['reason']=='registered_contract_source_invalid'
        manifest.write_text('{"version":1,"version":1,"sources":[]}',encoding='utf-8')
        assert read()['reason']=='registered_contract_source_invalid'

bound={'stand':'fixture','test_cases':[{'case_id':'active','requirement':{'stand':'fixture'}}]}
args,error=scope_diagnostic_arguments('api_inspect_contract_page',{'method':'GET','path':'/items/{uid}'},bound,'active')
assert error is None and args['stand']=='fixture'
assert scope_diagnostic_arguments('api_inspect_contract_page',{'stand':'other'},bound,'active')[1]=='diagnostic_stand_mismatch'
from uqa import classify_tool_action,model_tool_catalog
assert classify_tool_action('api_inspect_contract_page',{})=='observe'
assert any(t['function']['name']=='api_inspect_contract_page' for t in model_tool_catalog({'api_inspect_contract_page'}))
from tools.registry import execute_tool,TOOLS
schema=next(t['function']['parameters'] for t in TOOLS if t['function']['name']=='api_inspect_contract_page')
assert 'source_id' in schema['properties']
import tools.registry as registry
with patch.object(registry,'inspect_registered_contract_page',return_value={'contract_observation_status':'fixture'}) as lookup:
    assert execute_tool('api_inspect_contract_page',{'stand':'fixture','method':'GET','path':'/items/{uid}','source_id':'fixture-source'})['contract_observation_status']=='fixture'
    lookup.assert_called_once_with('fixture','GET','/items/{uid}',(),source_id='fixture-source')
assert execute_tool('api_inspect_contract_page',{'source_file':'/private'})['reason']=='contract_tool_arguments_invalid'
locked=copy.deepcopy(bound);locked['test_cases'][0]['requirement']['api_contract_source_id']='fixture-source-v2'
assert scope_diagnostic_arguments('api_inspect_contract_page',{},locked,'active')[0]['source_id']=='fixture-source-v2'
assert scope_diagnostic_arguments('api_inspect_contract_page',{'source_id':'fixture-source'},locked,'active')[1]=='diagnostic_source_mismatch'
locked['test_cases'][0]['requirement']['api_contract_source_id']=False
assert scope_diagnostic_arguments('api_inspect_contract_page',{},locked,'active')[1]=='diagnostic_source_binding_invalid'
import uqa
with patch.object(uqa,'add_evidence',side_effect=lambda *a,**kw:kw):
    proof=uqa.record_tool_evidence('fixture-job','fixture-case','api_inspect_contract_page',{},r)
    assert proof['usable_for_pass'] is False and proof['usable_for_verdict'] is False
    assert proof['eligibility_reason']=='historical_contract_page_not_runtime_business_evidence'
print('registered API sources PASS: explicit registered revision/caller lock, stand/provenance/pins, no model file/pin/evidence authority or HTTP/PASS')

"""Isolated typed source-reader transport/lock checks, never model acceptance."""
import json
from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import patch
import schema_read_runtime as runtime

req={'type':'registered_schema_read','locked':True,'stand':'lab','action_profile':'read_only',
     'api_contract_source_id':runtime.SOURCE,'source_read_profile':runtime.PROFILE}
job={'job_id':'fixture','stand':'lab','job_type':'manual','status':'running','resources':[],
     'request':'lab '+runtime.PATH+' '+runtime.SOURCE+' TaskFull CommandAdditionalParams',
     'test_cases':[{'case_id':'case','status':'running','requirement':req}]}
assert runtime.validate_context(job,'case')==req
for field,value in [('stand','prod'),('action_profile','write_resource'),('locked',1),
                    ('api_contract_source_id','other'),('source_read_profile','other'),('extra',True)]:
    bad=deepcopy(job);bad['test_cases'][0]['requirement'][field]=value
    try:runtime.validate_context(bad,'case')
    except ValueError:pass
    else:raise AssertionError(field)
for change in ('duplicate','resources','missing_request','closed'):
    bad=deepcopy(job)
    if change=='duplicate':bad['test_cases']*=2
    if change=='resources':bad['resources']=[{'id':'not-owned'}]
    if change=='missing_request':bad['request']='different'
    if change=='closed':bad['status']='blocked'
    try:runtime.validate_context(bad,'case')
    except ValueError:pass
    else:raise AssertionError(change)

frontier=[]
runtime.extend_frontier(frontier,[],{'contract_observation_status':'observed',
    'direct_schema_references':['#/components/schemas/HTTPValidationError','#/components/schemas/TaskFull']},set())
catalog=runtime.page_catalog(frontier,set())
assert len(catalog)==1 and len(catalog[0]['function']['parameters']['properties']['reference_chain']['enum'])==2
good={'name':'api_inspect_contract_page','arguments':{'method':'GET','path':runtime.PATH,
       'reference_chain':['#/components/schemas/TaskFull']}}
assert runtime.decode_phase_decision(json.dumps(good),catalog)['function']['arguments']==good['arguments']
for key,value in [('name','browser_create_pinned_agent_audit_semantic'),('chain',['TaskFull']),('extra',True)]:
    bad=deepcopy(good)
    if key=='name':bad['name']=value
    elif key=='chain':bad['arguments']['reference_chain']=value
    else:bad['arguments']['extra']=value
    try:runtime.decode_phase_decision(json.dumps(bad),catalog)
    except ValueError:pass
    else:raise AssertionError(key)
final={'source_id':runtime.SOURCE,'observed_models':sorted(runtime.WANTED),'snapshot_recency':'unknown',
       'business_pass':False,'explanation':'Historical only'}
assert runtime.validate_final(json.dumps(final))==final
for key,value in [('source_id','other'),('snapshot_recency','outdated'),('snapshot_recency','current'),
                  ('business_pass',True),('explanation',''),('explanation','x'*2001),('extra',1)]:
    bad={**final,key:value}
    try:runtime.validate_final(json.dumps(bad))
    except ValueError:pass
    else:raise AssertionError(key)

def execute_fixture(change_pin=False):
    calls=[];saved=[]
    def ask(messages,tools,response_schema):
        assert tools==[]
        if 'oneOf' not in response_schema:return {'message':{'content':json.dumps(final)}}
        props=response_schema['oneOf'][0]['properties'];name=props['name']['enum'][0]
        arguments={key:deepcopy(value['enum'][0]) for key,value in props['arguments']['properties'].items()}
        if name=='api_inspect_contract_page':
            choices=props['arguments']['properties']['reference_chain']['enum']
            arguments['reference_chain']=next((x for x in choices if x and x[-1] in runtime.WANTED),choices[0])
        return {'message':{'content':json.dumps({'name':name,'arguments':arguments})}}
    def execute(name,args,messages,**kwargs):
        assert kwargs['force_read_only'] is True and kwargs['action_policy']=='confirm_mutations'
        calls.append((name,args))
        if name=='knowledge_search':return {'results':[{'source':runtime.RECIPE,'content':' '.join(sorted(runtime.WANTED))}]}
        assert name=='api_inspect_contract_page' and args['method']=='GET' and args['path']==runtime.PATH
        chain=args['reference_chain'];ref=chain[-1] if chain else None
        result={'contract_observation_status':'observed','source_id':runtime.SOURCE,'method':'GET',
            'path_template':runtime.PATH,'reference_chain':chain,'schema_reference':ref,
            'schema_sha256':('c' if change_pin and chain else 'a')*64,'projection_sha256':'b'*64,
            'direct_schema_references':[]}
        if not chain:result['direct_schema_references']=['#/components/schemas/HTTPValidationError','#/components/schemas/TaskFull']
        elif ref=='#/components/schemas/TaskFull':
            result.update(schema={'required':['id'],'properties':{'result':{}}},
                direct_schema_references=['#/components/schemas/CommandAdditionalParams'])
        else:result['schema']={'required':['programm'],'properties':{'programm':{'type':'string'}}}
        return result
    def save(*args,**kwargs):
        assert kwargs['usable_for_pass'] is False and kwargs['usable_for_verdict'] is False
        saved.append(json.loads(args[3]));return {'evidence_id':'fixture-trace'}
    api=SimpleNamespace(SYSTEM_PROMPT='generic',get_job=lambda _:deepcopy(job),ask_ollama=ask,
        execute_tool_with_policy=execute,record_tool_observations=lambda *args:[],
        record_tool_evidence=lambda *args,**kwargs:{'evidence_id':'fixture-read'},add_evidence=save,
        update_test_case=lambda *args,**kwargs:None,set_job_status=lambda *args:None)
    with patch.object(runtime,'list_operations',return_value=[]):
        outcome=runtime.run(api,[{'role':'system','content':'generic'},{'role':'user','content':job['request']}],
                            'fixture','case','confirm_mutations')
    return outcome,saved,calls
outcome,saved,calls=execute_fixture()
assert outcome['completed'] and len(calls)==4 and saved[0]['normal_core_entry']
assert saved[0]['canonical_declarations']['command_required_fields']==['programm']
assert saved[0]['canonical_declarations']['task_result_schema']=={} and not saved[0]['business_execution_verified']
assert saved[0]['canonical_declarations']['snapshot_recency']=='unknown'
report=runtime.source_report(saved[0]['canonical_declarations'],True,'fixture-trace',None)
assert 'programm' in report and 'не проверена (unknown); устаревание не доказано' in report
assert 'Схема TaskFull.result: {}' in report and 'не бизнес-PASS' in report
assert 'Чтение: неполное' in runtime.source_report(None,False,'fixture-trace','ValueError')
outcome,saved,calls=execute_fixture(change_pin=True)
assert not outcome['completed'] and outcome['error_type']=='ValueError' and len(calls)==3
import uqa
with patch.object(uqa,'get_job',return_value=deepcopy(job)),patch.object(runtime,'run',return_value={'started':True,'completed':True}) as dispatch:
    assert uqa.run_turn([{'role':'system','content':uqa.SYSTEM_PROMPT}],job_id='fixture',case_id='case',action_policy='confirm_mutations')['completed']
    assert dispatch.call_count==1
print('PASS bounded schema reader fixture: caller lock, exposed full paths, unique tool names, independent decode, source-pin stability, forced read-only, canonical source-only final; not model acceptance')

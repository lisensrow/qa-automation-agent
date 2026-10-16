"""Pure immutable stage/profile tests; no Core wiring, POST or model acceptance."""
from copy import deepcopy
from command_probe_contract import target,PROFILE_ID
from command_stage_profile import requirement,stages_for,validate_context,admitted_write,metadata_payload,CREATE

def reject(fn,*args,**kwargs):
    try:fn(*args,**kwargs)
    except (ValueError,TypeError):return
    raise AssertionError('unbound command stage admitted')

for name in ['windows','astra']:
    t=target(name);r=requirement(name,'uqa-command-v360')
    request=' '.join([t['ci_name'],t['ci_id'],t['agent_id'],'1.3.27','executeCommand','1.4.0',PROFILE_ID])
    job={'stand':'lab','job_type':'manual','status':'running','resources':[],'request':request,
        'test_cases':[{'case_id':'case','status':'running','requirement':r,'evidence':[]}]}
    validate_context(job,'case',starting=True)
    stages=stages_for(name)
    assert len(stages)==4 and len({s['stage_id'] for s in stages})==4
    assert len({str(s['arguments']) for s in stages})==4
    assert stages[0]['arguments']!=stages[2]['arguments']
    assert metadata_payload(stages[0]['stage_id'])==metadata_payload(stages[2]['stage_id'])
    for stage in stages:
        assert stage['tool']==CREATE and admitted_write(job,'case',stage['arguments'])==stage
        reject(admitted_write,job,'case',{**stage['arguments'],'programm':'whoami'})
        reject(admitted_write,job,'case',{**stage['arguments'],'target':'other'})
    reject(admitted_write,job,'case',{'target':name,'stage_id':'unknown'})
    reject(metadata_payload,'execute_command')
    for key,value in [('locked',False),('action_profile','read_only'),('core_version','latest'),
        ('plugin_version','1.3.3'),('source_manifest',{}),('expected_profile',{}),('operation_stages',[]),
        ('extra',True),('ci_id','other')]:
        bad=deepcopy(job);bad['test_cases'][0]['requirement'][key]=value;reject(validate_context,bad,'case')
    for key,value in [('status','blocked'),('stand','other'),('job_type','advisory'),('resources',[{}]),('request','short')]:
        reject(validate_context,{**job,key:value},'case')
    bad=deepcopy(job);bad['test_cases'][0]['evidence']=[{'type':'closed_command_runtime_started'}]
    reject(validate_context,bad,'case',starting=True)
    delivery=metadata_payload('deliver_command_plugin')
    assert delivery['plugins_to_delete']==[] and delivery['check_endpoint_os_version'] is True
    assert delivery['plugins_to_update']==[{'plugin_name':'executeCommand','plugin_version':'1.4.0'}]
    delivery['plugins_to_delete'].append('other')
    assert metadata_payload('deliver_command_plugin')['plugins_to_delete']==[]
print('PASS command stage profile fixtures: distinct journal args, exact workbook/scope/oracle, no replay/overrides; '
      'pure preparation only, no execution authority or native acceptance')

"""Offline intrinsic contract checks; no live API/model or business acceptance."""
from copy import deepcopy
import json
from unittest.mock import patch
import plugin_result_review as p

def run():
    net={'name':'fixture','macAddress':'02:00:00:00:00:01','isDefault':True,
         'ipAddresses':['192.0.2.1','2001:db8::1']}
    r=p.content_checks('defaultNetworkDeviceAudit',net)
    assert r['intrinsic_status']=='PASS' and r['business_pass'] is False
    assert r['independent_os_correctness']=='BLOCKED' and '192.0.2.1' not in json.dumps(r)
    for key,value in [('isDefault',False),('macAddress','bad'),('ipAddresses',['broken']),('name','')]:
        changed=deepcopy(net);changed[key]=value
        assert p.content_checks('defaultNetworkDeviceAudit',changed)['intrinsic_status']=='FAIL'
    for values in [['192.0.2.1','192.0.2.1'],[]]:
        changed=deepcopy(net);changed['ipAddresses']=values
        assert p.content_checks('defaultNetworkDeviceAudit',changed)['intrinsic_status']=='FAIL'
    changed=deepcopy(net);changed['ipAddresses']=['fe80::1%fixture']
    assert p.content_checks('defaultNetworkDeviceAudit',changed)['intrinsic_status']=='BLOCKED'
    disk=[{'device_id':'fixture','size':'4096','disk':{'partitions_quantity':1,
           'partitions':[{'partition_length':1024}]}}]
    out=p.content_checks('storageAudit',disk)
    assert out['intrinsic_status']=='BLOCKED' and all(c['status']=='PASS' for c in out['checks'][:5])
    assert all(c['status']=='BLOCKED' for c in out['checks'][5:])
    disk[0]['disk']['partitions_quantity']=2
    assert p.content_checks('storageAudit',disk)['intrinsic_status']=='FAIL'
    for bad in [True,-1,float('nan'),float('inf'),'','1e3','-1',1.5,2**65]:
        try:p.integer(bad)
        except ValueError:pass
        else:raise AssertionError('accepted invalid integer')
    for good in [0,4096,4096.0,'4096']:assert p.integer(good)==int(good)
    for target in ['windows','astra']:
        req=p.requirement(target,'offline-v418');case={'case_id':'fixture','requirement':req,'status':'running'}
        job={'stand':'lab','job_type':'manual','status':'running','test_cases':[case],
             'request':' '.join(req[k] for k in ['ci_id','agent_id','ci_name','profile_id'])}
        args={'target':target,'plugin_name':'storageAudit'}
        assert p.validate_context(job,'fixture',args)==req
        for key,value in [('core_version','latest'),('business_pass',True),('historical_only',False)]:
            altered=deepcopy(job);altered['test_cases'][0]['requirement'][key]=value
            try:p.validate_context(altered,'fixture',args)
            except ValueError:pass
            else:raise AssertionError('accepted altered contract')
    # Native GET/proof path, digest tamper and Core fail-closed, entirely offline.
    name='windows';plugin='defaultNetworkDeviceAudit';req=p.requirement(name,'offline-native-v418')
    job={'stand':'lab','job_type':'manual','status':'running','test_cases':[
        {'case_id':'fixture','requirement':req,'status':'running'}],
        'request':' '.join(req[k] for k in ['ci_id','agent_id','ci_name','profile_id'])}
    sj,sc,version=p.REFS[name,plugin];task='00000000-0000-4000-8000-000000000001'
    report={'task_id':task,'read_evidence_id':'own-proof','response_shape':p.shape(net)}
    source={'test_cases':[{'case_id':sc,'requirement':{'target':name,'plugin_name':plugin,'plugin_version':version},
      'evidence':[{'type':'model_plugin_discovery_cycle','evidence_id':'runtime-proof',
        'value':json.dumps({'completed':True,'canonical_report':report})}]}]}
    ops=[{'status':'verified','verification':{'identifier_value':task,'evidence_id':'own-proof'}}]
    full={'id':task,'agent_id':req['agent_id'],'name':plugin,'status':'success',
          'result':{'machine_uid':req['ci_id'],'result':'success','data':net}}
    with patch.object(p.job_store,'get_job',side_effect=lambda j:source if j==sj else job), \
         patch.object(p,'list_operations',return_value=ops), \
         patch.object(p,'context',return_value=({}, {}, ['tasks','agent','plugin'])), \
         patch.object(p,'validate_target_state'), \
         patch.object(p,'read_json',side_effect=lambda s,url:{} if url=='agent' else full):
        native=p.inspect(object(),name,plugin,'fixture-job','fixture')
        assert native['intrinsic_status']=='PASS' and native['new_agent_tasks']==0
        assert native['historical_only'] and native['business_pass'] is False
        full['result']['data']={**net,'name':'changed'}
        assert p.inspect(object(),name,plugin,'fixture-job','fixture')['error']=='result_review_unavailable'
    import uqa
    sample={**p.content_checks(plugin,net),'target':name,'plugin_name':plugin,'plugin_version':version,
        'source_job_id':sj,'source_case_id':sc,'same_recorded_payload':True,'historical_only':True,
        'raw_secret':'do-not-copy','url':'https://private.invalid/secret'}
    messages=[{'role':'tool','tool_name':p.TOOL,'content':json.dumps(sample)},
        {'role':'tool','tool_name':'browser_get_state','content':'{}'}]
    history=json.loads(uqa.messages_for_model(messages)[0]['content'])
    assert history['intrinsic_status']=='PASS' and history['full_source_case_status']=='BLOCKED'
    assert history['business_pass'] is False and history['historical_projection_not_permission'] is True
    assert 'raw_secret' not in history and 'private.invalid' not in json.dumps(history)
    for key,value in [('intrinsic_status','FAIL'),('business_pass',True),('source_case_id','foreign')]:
        changed={**sample,key:value};assert p.compact_review(changed)=={}
    blocked=uqa.execute_tool_with_policy(p.TOOL,{'target':'windows','plugin_name':plugin},[],
        job_id=None,case_id=None,force_read_only=True,action_policy='confirm_mutations')
    assert blocked.get('error')=='locked_result_review_scope_required'
    print('PASS plugin_result_review offline contracts')
if __name__=='__main__':run()

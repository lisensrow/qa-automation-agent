"""Value comparison is independent of row-count/schema success and never full PASS."""
from copy import deepcopy
import drive_result_comparison as d
os=[{'mount_point':'/','fs_type':'ext4','size_bytes':100},{'mount_point':None,'fs_type':None,'size_bytes':200}]
plugin=[{'mountPoint':'/','fsType':'ext4','size':100},{'mountPoint':'','fsType':'','size':200}]
x=d.compare_values(os,plugin);assert x['mounted_value_comparison_status']=='MATCH' and x['mounted_records_compared']==1
assert not x['business_pass'] and not x['unit_semantics_verified'] and not x['all_disks_completeness_verified'] and not x['live_current_state_verified']
for field,value in [('size',101),('size',True),('size',float('nan')),('fsType','xfs'),('mountPoint','/elsewhere')]:
    bad=deepcopy(plugin);bad[0][field]=value
    assert d.compare_values(os,bad)['mounted_value_comparison_status']=='MISMATCH'
assert d.compare_values(os,plugin+[plugin[0]])['mounted_value_comparison_status']=='BLOCKED'
for bad in [[],[{'mount_point':'/','fs_type':None,'size_bytes':100}],os+[os[0]]]:
    try:d.compare_values(bad,plugin);raise AssertionError('invalid OS accepted')
    except ValueError:pass
r=d.requirement('fixture-comparison');c={'case_id':'tc-test','status':'running','requirement':r}
j={'stand':'lab','status':'running','test_cases':[c],'request':' '.join(r[k] for k in ['ci_id','agent_id','ci_name','profile_id'])}
assert d.validate_context(j,'tc-test',{'target':'astra'})==r
for args in [{'target':'windows'},{'target':'astra','task_id':'other'},{}]:
    try:d.validate_context(j,'tc-test',args);raise AssertionError('scope admitted')
    except ValueError:pass
print('PASS owned recorded drive values: numeric mismatch/ambiguity/unknown/scope/no full PASS; fixture only')

from contextlib import ExitStack
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch
import hashlib,json
import job_store as store,uqa
from command_probe_contract import ORIGIN,target
from operation_journal import list_operations
from tools.registry import execute_tool
assert execute_tool(d.TOOL,{'target':'astra'})['error']=='trusted_Core_job_case_context_required'
with TemporaryDirectory() as tmp,ExitStack() as stack:
    stack.enter_context(patch.object(store,'JOBS_DIR',Path(tmp)))
    req=d.requirement('fixture-drive-value-core');request='Прочитай сравнение '+' '.join(req[k] for k in ['ci_id','agent_id','ci_name','profile_id'])
    job=store.create_job(request,stand='lab',job_type='manual');jid=job['job_id']
    cid=store.add_test_case(jid,'Fixture recorded comparison',requirement=req)['case_id']
    store.set_job_status(jid,'running');store.update_test_case(jid,cid,status='running')
    t=target('astra');base=ORIGIN+'/api/v1/agents/'+t['agent_id'];gets=[]
    op={'summary':{'os_disk_rows':os},'processed_at':'2026-10-17T00:00:00+00:00'}
    pp={'task_id':'00000000-0000-4000-8000-000000000001','processed_at':'2026-10-17T00:00:01+00:00',
        'server_created_at':'2026-10-17T00:00:00+00:00','audit_data_summary':{
            'data_sha256':hashlib.sha256(json.dumps(plugin,sort_keys=True,ensure_ascii=False).encode()).hexdigest()}}
    full={'id':pp['task_id'],'agent_id':t['agent_id'],'name':'driveDeviceAudit','status':'success','created_at':pp['server_created_at'],
        'result':{'machine_uid':t['ci_id'],'result':'success','processed_at':pp['processed_at'],'data':deepcopy(plugin)}}
    ci={'id':t['ci_id'],'agent_id':t['agent_id'],'name':t['ci_name'],'detail':{'os':{'name':'Astra Linux','architecture':'x86_64'}}}
    class Response:
        status=200
        def __init__(self,b):self.b=b
        def json(self):return deepcopy(self.b)
    def get(url,params=None,timeout=None):
        gets.append(url)
        if url==base:return Response({'id':t['agent_id'],'version':'1.3.27','status':'online'})
        assert url==base+'/tasks/'+pp['task_id']+'/full'
        return Response(full)
    session=SimpleNamespace(_ensure_started=lambda:None,_observed_agent_task_context=lambda n:(ci,{},base+'/tasks',None),
        _same_https_origin_url=lambda observed,path:ORIGIN+path,context=SimpleNamespace(request=SimpleNamespace(get=get)))
    stack.enter_context(patch('tools.browser._session',session))
    stack.enter_context(patch.object(d,'source_proof',side_effect=lambda ref,kind:deepcopy(op if kind=='os' else pp)))
    messages=[{'role':'user','content':request}];ctx={'job_id':jid,'case_id':cid,'force_read_only':True,'action_policy':'confirm_mutations'}
    out=uqa.execute_tool_with_policy(d.TOOL,{'target':'astra'},messages,**ctx)
    assert not out.get('error'),out
    assert out['mounted_value_comparison_status']=='MATCH' and out['same_recorded_payload'] and out['recorded_pair_only']
    assert not out['business_pass'] and not out['mutation_executed'] and out['new_agent_tasks']==0 and not list_operations(jid)
    model=uqa.tool_result_for_model(d.TOOL,out)
    assert model['mounted_value_comparison_status']=='MATCH' and model['comparisons']==out['comparisons']
    forged=deepcopy(out);forged['unit_semantics_verified']=True;assert not d.compact(forged)
    count=len(gets)
    bad=uqa.execute_tool_with_policy(d.TOOL,{'target':'windows'},messages,**ctx)
    assert bad.get('error') and len(gets)==count and not list_operations(jid)
    full['result']['data'][0]['size']=101
    bad=uqa.execute_tool_with_policy(d.TOOL,{'target':'astra'},messages,**ctx)
    assert bad.get('error') and bad['business_pass'] is False
    full['result']['data']=deepcopy(plugin);pp['processed_at']='2026-10-17T01:00:00+00:00'
    count=len(gets);bad=uqa.execute_tool_with_policy(d.TOOL,{'target':'astra'},messages,**ctx)
    assert bad.get('error') and len(gets)==count
print('PASS drive value Core observe/locked scope/same payload/recorded time gap/no new operations; fixtures only')

"""Exact full recorded rows, not count equality/normalization/full-case proof."""
from copy import deepcopy
from contextlib import ExitStack
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch
import hashlib,json
import software_result_comparison as g
import software_os_baseline as baseline
import job_store as store,uqa
from operation_journal import list_operations
from tools.registry import execute_tool
from command_probe_contract import ORIGIN,target
rows=[{'name':'libc6:amd64','version':'1.2','record_ref':'libc6:amd64','architecture':'amd64'}]
plugin=[{'name':'libc6:amd64','version':'1.2'}]
assert g.compare_values(rows,plugin)['comparison_status']=='MATCH'
assert g.compare_values(rows,[{'name':'libc6','version':'1.2'}])['comparison_status']=='MISMATCH'
assert g.compare_values(rows,[{'name':'libc6:amd64','version':'1.3'}])['version_mismatches']==1
assert g.compare_values(rows,[{'name':'libc6:amd64','version':''}])['comparison_status']=='BLOCKED'
assert g.compare_values(rows,plugin+plugin)['comparison_status']=='BLOCKED'
assert g.compare_values(rows+rows,plugin)['comparison_status']=='BLOCKED'
assert g.compare_values(rows,[])['comparison_status']=='MISMATCH'
assert g.compare_values([],[])['comparison_status']=='BLOCKED'
for bad in [[{'name':True,'version':'1'}],[{'name':'x','version':True}],[{'name':'x'*513,'version':'1'}],plugin*10001]:
    try:g.compare_values(rows,bad);raise AssertionError('invalid software rows accepted')
    except ValueError:pass
many=[{'name':'pkg'+str(i),'version':'1'} for i in range(200)]
sample=g.compare_values(many,[]);assert sample['differences_total']==200 and len(sample['difference_sample'])<=12 and not sample['difference_sample_is_full']
assert execute_tool(g.TOOL,{'target':'astra'})['error']=='trusted_Core_job_case_context_required'
assert uqa.classify_tool_action(g.TOOL,{'target':'astra'})=='observe'
with TemporaryDirectory() as tmp,ExitStack() as stack:
    stack.enter_context(patch.object(store,'JOBS_DIR',Path(tmp)))
    req=g.requirement('fixture-software-value-comparison');request='Прочитай сверку '+' '.join(req[k] for k in ['ci_id','agent_id','ci_name','profile_id'])
    j=store.create_job(request,stand='lab',job_type='manual');jid=j['job_id']
    cid=store.add_test_case(jid,'Recorded software values',requirement=req)['case_id'];store.set_job_status(jid,'running');store.update_test_case(jid,cid,status='running')
    t=target('astra');base=ORIGIN+'/api/v1/agents/'+t['agent_id'];gets=[]
    obj={'probe_version':1,'platform':'astra','query_complete':True,'error':'','rows':rows}
    stdout=json.dumps(obj,sort_keys=True,separators=(',',':'))
    os={'task_id':'00000000-0000-4000-8000-000000000001','summary':baseline.summarize(obj,'astra'),
        'processed_at':'2026-10-17T00:00:00+00:00','server_created_at':'2026-10-17T00:00:00+00:00','result_sha256':hashlib.sha256(stdout.encode()).hexdigest()}
    pp={'task_id':'00000000-0000-4000-8000-000000000002','processed_at':'2026-10-17T00:00:01+00:00','server_created_at':'2026-10-17T00:00:00+00:00',
        'audit_data_summary':{'data_sha256':hashlib.sha256(json.dumps(plugin,sort_keys=True,ensure_ascii=False).encode()).hexdigest()}}
    ofull={'id':os['task_id'],'agent_id':t['agent_id'],'name':'executeCommand','status':'success','created_at':os['server_created_at'],
        'result':{'machine_uid':t['ci_id'],'processed_at':os['processed_at'],'data':{'stdout':stdout,'errorlevel':0,'stderr':''}}}
    pfull={'id':pp['task_id'],'agent_id':t['agent_id'],'name':'softAudit','status':'success','created_at':pp['server_created_at'],
        'result':{'machine_uid':t['ci_id'],'result':'success','processed_at':pp['processed_at'],'data':deepcopy(plugin)}}
    ci={'id':t['ci_id'],'agent_id':t['agent_id'],'name':t['ci_name'],'detail':{'os':{'name':'Astra Linux','architecture':'x86_64'}}}
    class Response:
        status=200
        def __init__(self,b):self.b=b
        def json(self):return deepcopy(self.b)
    def get(url,params=None,timeout=None):
        gets.append(url)
        if url==base:return Response({'id':t['agent_id'],'version':'1.3.27','status':'online'})
        if url==base+'/tasks/'+os['task_id']+'/full':return Response(ofull)
        assert url==base+'/tasks/'+pp['task_id']+'/full'
        return Response(pfull)
    session=SimpleNamespace(_ensure_started=lambda:None,_observed_agent_task_context=lambda n:(ci,{},base+'/tasks',None),
        _same_https_origin_url=lambda observed,path:ORIGIN+path,context=SimpleNamespace(request=SimpleNamespace(get=get)))
    stack.enter_context(patch('tools.browser._session',session));stack.enter_context(patch.object(g,'source_proofs',side_effect=lambda:(deepcopy(os),deepcopy(pp))))
    ctx={'job_id':jid,'case_id':cid,'force_read_only':True,'action_policy':'confirm_mutations'};messages=[{'role':'user','content':request}]
    out=uqa.execute_tool_with_policy(g.TOOL,{'target':'astra'},messages,**ctx);assert not out.get('error'),out
    assert out['comparison_status']=='MATCH' and out['matched_names']==1 and out['new_agent_tasks']==0 and not out['full_case_passed'] and not list_operations(jid)
    view=uqa.tool_result_for_model(g.TOOL,out);assert view['comparison_status']=='MATCH' and view['software_tab_verified'] is False
    extra=deepcopy(out);extra['raw_inventory_should_not_be_emitted']=['private'];assert 'raw_inventory_should_not_be_emitted' not in g.compact(extra)
    for key,value in [('full_case_passed',True),('normalization_applied',True),('matched_names',2),('comparison_status','MISMATCH'),('os_payload_sha256','bad')]:
        forged=deepcopy(out);forged[key]=value;assert not g.compact(forged)
    count=len(gets);assert uqa.execute_tool_with_policy(g.TOOL,{'target':'windows'},messages,**ctx).get('error') and len(gets)==count
    ofull['result']['data']['stdout']+=' ';assert uqa.execute_tool_with_policy(g.TOOL,{'target':'astra'},messages,**ctx).get('error')
    ofull['result']['data']['stdout']=stdout;pfull['result']['data'][0]['version']='changed';assert uqa.execute_tool_with_policy(g.TOOL,{'target':'astra'},messages,**ctx).get('error')
    pfull['result']['data']=deepcopy(plugin);pp['processed_at']='2026-10-17T01:00:00+00:00';count=len(gets)
    assert uqa.execute_tool_with_policy(g.TOOL,{'target':'astra'},messages,**ctx).get('error') and len(gets)==count
print('Software recorded-value comparison: PASS (all exact rows not count, ambiguity/unknown, Core READ, both payload hashes/time, sample/projection scope; no new tasks)')

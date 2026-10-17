"""GPU-name hypothesis cannot turn subset/format matching into full acceptance."""
from copy import deepcopy
import gpu_result_comparison as g
os_rows=[{'vendor_name':'VMware','device_name':'SVGA II Adapter'}]
plugin=[{'name':'VMware SVGA II Adapter','note':'Not an independently verified oracle'}]
assert g.compare_values(os_rows,plugin)['name_hypothesis_status']=='MATCH'
assert g.compare_values(os_rows,[{'name':'SVGA II Adapter'}])['name_hypothesis_status']=='MISMATCH'
assert g.compare_values(os_rows,plugin+plugin)['name_hypothesis_status']=='BLOCKED'
assert g.compare_values(os_rows,[])['name_hypothesis_status']=='MISMATCH'
for bad in [[],os_rows+os_rows,[{'vendor_name':None,'device_name':'test'}]]:
    try:g.compare_values(bad,plugin);raise AssertionError('OS ambiguity admitted')
    except ValueError:pass
for bad in [[{'name':True}],[{'name':'a'*2049}],plugin*17]:
    try:g.compare_values(os_rows,bad);raise AssertionError('bad names admitted')
    except ValueError:pass
from contextlib import ExitStack
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch
import hashlib,json
import job_store as store,uqa
from operation_journal import list_operations
from tools.registry import execute_tool
from command_probe_contract import ORIGIN,target
assert execute_tool(g.TOOL,{'target':'astra'})['error']=='trusted_Core_job_case_context_required'
with TemporaryDirectory() as tmp,ExitStack() as stack:
    stack.enter_context(patch.object(store,'JOBS_DIR',Path(tmp)))
    req=g.requirement('fixture-gpu-name-comparison');request='Прочитай сверку '+' '.join(req[k] for k in ['ci_id','agent_id','ci_name','profile_id'])
    job=store.create_job(request,stand='lab',job_type='manual');jid=job['job_id']
    cid=store.add_test_case(jid,'GPU-name hypothesis',requirement=req)['case_id'];store.set_job_status(jid,'running');store.update_test_case(jid,cid,status='running')
    t=target('astra');base=ORIGIN+'/api/v1/agents/'+t['agent_id'];gets=[]
    os={'summary':{'os_gpu_rows':os_rows},'processed_at':'2026-10-17T00:00:00+00:00'}
    pp={'task_id':'00000000-0000-4000-8000-000000000001','processed_at':'2026-10-17T00:00:01+00:00','server_created_at':'2026-10-17T00:00:00+00:00',
        'audit_data_summary':{'data_sha256':hashlib.sha256(json.dumps(plugin,sort_keys=True,ensure_ascii=False).encode()).hexdigest()}}
    full={'id':pp['task_id'],'agent_id':t['agent_id'],'name':'gpuDeviceAudit','status':'success','created_at':pp['server_created_at'],
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
    stack.enter_context(patch('tools.browser._session',session));stack.enter_context(patch.object(g,'source_proofs',side_effect=lambda:(deepcopy(os),deepcopy(pp))))
    messages=[{'role':'user','content':request}];ctx={'job_id':jid,'case_id':cid,'force_read_only':True,'action_policy':'confirm_mutations'}
    out=uqa.execute_tool_with_policy(g.TOOL,{'target':'astra'},messages,**ctx);assert not out.get('error'),out
    assert out['name_hypothesis_status']=='MATCH' and out['hypothesis_only'] and not out['general_name_mapping_verified'] and not list_operations(jid)
    model=uqa.tool_result_for_model(g.TOOL,out);assert model['name_hypothesis_status']=='MATCH' and model['note_semantics_verified'] is False
    forged=deepcopy(out);forged['note_semantics_verified']=True;assert not g.compact(forged)
    forged=deepcopy(out);forged['plugin_name_observations']=['different'];assert not g.compact(forged)
    count=len(gets);assert uqa.execute_tool_with_policy(g.TOOL,{'target':'windows'},messages,**ctx).get('error') and len(gets)==count
    full['result']['data'][0]['name']='changed';assert uqa.execute_tool_with_policy(g.TOOL,{'target':'astra'},messages,**ctx).get('error')
    full['result']['data']=deepcopy(plugin);pp['processed_at']='2026-10-17T01:00:00+00:00';count=len(gets)
    assert uqa.execute_tool_with_policy(g.TOOL,{'target':'astra'},messages,**ctx).get('error') and len(gets)==count
print('GPU recorded-name comparison: PASS (strict hypothesis/mismatch/ambiguity/scope/READ/hash/time/bounded model; no new tasks/full PASS)')

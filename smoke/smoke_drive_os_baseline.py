from copy import deepcopy
import drive_os_baseline as p
from contextlib import ExitStack
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4
import json

def core_fixture(name,body,summary_check=None):
    import uqa,job_store as store,endpoint_metadata as ep,endpoint_metadata_runtime as rt
    from operation_journal import list_operations,reconcile_operation
    r=ep.requirement(name,'fixture-drive-os-baseline',p.PROFILE)
    assert rt.catalog([],r)[0]['function']['parameters']['properties']['query']=={'enum':[p.PROFILE]}
    assert r['payload_sha256']==p.sha(name) and r['supported_os']==name
    with TemporaryDirectory() as tmp,ExitStack() as stack:
        stack.enter_context(patch.object(store,'JOBS_DIR',Path(tmp)))
        request='Запусти фиксированную агентскую задачу '+' '.join(r[k] for k in ['ci_id','agent_id','ci_name','core_version','profile_id'])
        j=store.create_job(request,stand='lab',job_type='manual');jid=j['job_id']
        cid=store.add_test_case(jid,'Fixture OS disk baseline',requirement=r)['case_id']
        store.set_job_status(jid,'running');store.update_test_case(jid,cid,status='running')
        ci={'id':r['ci_id'],'agent_id':r['agent_id'],'name':r['ci_name'],'detail':{'os':{'name':'Windows 10' if name=='windows' else 'Astra Linux','architecture':'64'}}}
        base=ep.ORIGIN+'/api/v1/agents/'+r['agent_id'];tasks={};posts=[]
        class Response:
            def __init__(self,status,body):self.status,self.body=status,body
            def json(self):return deepcopy(self.body)
        def get(url,params=None,timeout=None):
            if url==base:return Response(200,{'id':r['agent_id'],'version':'1.3.27','status':'online'})
            if url==base+'/plugin':return Response(200,{})
            if url==base+'/tasks':return Response(200,{'items':list(tasks.values()),'total':len(tasks),'offset':0})
            if url.endswith('/full'):return Response(200,tasks[url.split('/')[-2]])
            raise AssertionError('unexpected GET')
        def post(url,data,timeout=None):
            assert url==base+'/tasks' and data==p.payload(name)
            posts.append(url);tid=str(uuid4());at=ep.now();b={**deepcopy(data),'id':tid,'agent_id':r['agent_id'],'created_at':at}
            tasks[tid]={**b,'status':'success','result':{'machine_uid':r['ci_id'],'processed_at':at,'data':{'stdout':json.dumps(body),'stderr':'','errorlevel':0}}}
            return Response(201,b)
        session=SimpleNamespace(session_id='fixture-drive-os',_ensure_started=lambda:None,
            _observed_agent_task_context=lambda name:(ci,{},base+'/tasks',None),_same_https_origin_url=lambda observed,path:ep.ORIGIN+path,
            context=SimpleNamespace(request=SimpleNamespace(get=get,post=post)))
        stack.enter_context(patch('tools.browser._session',session))
        stack.enter_context(patch.object(ep,'validate_preflight',return_value={'ready':True}))
        stack.enter_context(patch.object(ep,'validate_release_source',return_value=True))
        args={'target':name};ctx={'job_id':jid,'case_id':cid,'action_policy':'confirm_mutations'};messages=[{'role':'user','content':request}]
        assert uqa.execute_tool_with_policy(ep.CREATE,args,messages,force_read_only=True,**ctx)['error']=='tool_policy_blocked'
        assert not posts and not list_operations(jid)
        stack.enter_context(patch.object(uqa,'managed_action_policy_decision',return_value={'allow':True,'status':'fixture_only'}))
        out=uqa.execute_tool_with_policy(ep.CREATE,args,messages,**ctx);assert out.get('executed'),out
        uqa.record_tool_evidence(jid,cid,ep.CREATE,args,out)
        out=uqa.execute_tool_with_policy(ep.READ,args,messages,**ctx);assert out.get('native_result_verified'),out
        ev=uqa.record_tool_evidence(jid,cid,ep.READ,args,out);op=list_operations(jid)[0]
        assert reconcile_operation(jid,op['operation_id'],ev['evidence_id'])['verified']
        if summary_check is None:
            assert out['summary']['row_count']==1 and not out['summary']['plugin_result_compared']
        else:
            summary_check(out['summary'])
        assert not uqa.execute_tool_with_policy(ep.CREATE,args,messages,**ctx).get('executed') and len(posts)==1

def main():
    for name in ['windows','astra']:
        body={'probe_version':1,'platform':name,'query_complete':True,'error':'','rows':[
            {'device_name':'C:' if name=='windows' else 'sda1','mount_point':'C:' if name=='windows' else '/',
             'fs_type':'NTFS' if name=='windows' else 'ext4','size_bytes':123456,'device_kind':'logical' if name=='windows' else 'part','drive_type':3 if name=='windows' else None}]}
        s=p.summarize(body,name);assert s['os_query_complete'] and s['row_count']==1 and not s['business_pass'] and not s['plugin_result_compared']
        bad=deepcopy(body);bad['rows'][0]['size_bytes']=-1
        try:p.summarize(bad,name);raise AssertionError('invalid size accepted')
        except ValueError:pass
        bad=deepcopy(body);bad['query_complete']=False;bad['error']='native_disk_query_failed';bad['rows']=[]
        s=p.summarize(bad,name);assert s['row_count'] is None and s['observation_status']=='BLOCKED'
        bad=deepcopy(body);bad['rows']*=2
        try:p.summarize(bad,name);raise AssertionError('duplicate accepted')
        except ValueError:pass
        for field,value in [('probe_version',True)]:
            bad=deepcopy(body);bad[field]=value
            try:p.summarize(bad,name);raise AssertionError('bool version accepted')
            except ValueError:pass
        payload=p.payload(name);assert payload['name']=='executeCommand' and payload['period'] is None and payload['run_as_user']==''
        assert len(p.sha(name))==64
        core_fixture(name,body)
    print('drive OS baseline: PASS')

if __name__=='__main__':main()

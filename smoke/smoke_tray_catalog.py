"""Fixture-only catalogue/source/closed Core checks, no real HTTP/model acceptance."""
from contextlib import ExitStack
from copy import deepcopy
from datetime import datetime,timezone,timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch
import json,hashlib
import uqa,job_store as store,tray_catalog as p
from operation_journal import list_operations
from tools.registry import execute_tool

def rejected(fn,*args):
    try:fn(*args)
    except (ValueError,KeyError,TypeError):return
    raise AssertionError('invalid catalogue accepted')

versions=[{'version':'1.2.3','trays_info':[{'os':'windows'},{'os':'debian'}]}]
deps=[{'trays_version':'1.2.3','dependency':[{'os':'windows','files':['dependency.dll']}]}]
assert p.project(versions,'versions')==versions and p.project(deps,'dependencies')==deps
for value in [None,{},versions*2,[{'version':'1.2.3','trays_info':[{'os':'windows','extra':'secret'}]}],
    [{'version':'1.2.3','trays_info':[{'os':'windows'},{'os':'windows'}]}]]:rejected(p.project,value,'versions')
rejected(p.project,[{'trays_version':'1.2.3','dependency':[{'os':'windows','files':['token=private']}]}],'dependencies')
rejected(p.project,[{'trays_version':'1.2.3','dependency':[{'os':'windows','files':['a','a']}]}],'dependencies')
now=datetime.now(timezone.utc)
raw=json.dumps({'source':{'schema_sha256':p.SCHEMA_SHA,'openapi':'3.1.0','read_at_utc':now.isoformat()}})
witness={'job_id':p.WITNESS_JOB,'stand':'lab','test_cases':[{'case_id':p.WITNESS_CASE,'evidence':[
    {'evidence_id':p.WITNESS_EVIDENCE,'type':'operator_installed_agent_task_profile','source':'operator_installed_schema_read',
     'execution_status':'observed','usable_for_pass':False,'usable_for_verdict':False,'value':raw}]}]}
with patch.object(p,'WITNESS_SHA',hashlib.sha256(raw.encode()).hexdigest()):
    assert p.validate_witness(witness,now)==now.isoformat()
    rejected(p.validate_witness,witness,now+timedelta(hours=2))
    bad=deepcopy(witness);bad['test_cases'][0]['evidence'][0]['value']+=' ';rejected(p.validate_witness,bad,now)
    bad=deepcopy(witness);bad['test_cases'][0]['evidence'][0]['source']='model';rejected(p.validate_witness,bad,now)
    for name in ['windows','astra']:
      with TemporaryDirectory() as tmp,ExitStack() as stack:
        stack.enter_context(patch.object(store,'JOBS_DIR',Path(tmp)))
        r=p.requirement(name,'fixture-catalog')
        request='Read '+' '.join(r[k] for k in ['ci_id','agent_id','ci_name','profile_id'])
        j=store.create_job(request,stand='lab',job_type='manual');jid=j['job_id']
        c=store.add_test_case(jid,'Catalog fixture',requirement=r);cid=c['case_id']
        store.set_job_status(jid,'running');store.update_test_case(jid,cid,status='running')
        get_job=store.get_job
        stack.enter_context(patch.object(p.job_store,'get_job',side_effect=lambda key:witness if key==p.WITNESS_JOB else get_job(key)))
        t=p.target(name);base=p.ORIGIN+'/api/v1/u-auth/u-sys/api/v1/agents/'+t['agent_id']
        ci={'id':t['ci_id'],'name':t['ci_name'],'agent_id':t['agent_id'],
            'detail':{'os':{'name':'Windows' if name=='windows' else 'Astra Linux','architecture':'64'}}}
        gets=[];bad_os=[False];bad_catalog=[False]
        class Response:
            status=200
            def __init__(self,body):self.body=body
            def json(self):return deepcopy(self.body)
        def get(url,timeout,params=None):
            gets.append(url)
            if url==base:return Response({'id':t['agent_id'],'version':'1.3.27','status':'online'})
            if url==p.ORIGIN+'/api/v1/u-auth/u-sys/api/v1/agents/tray/versions':return Response({} if bad_catalog[0] else versions)
            if url==p.ORIGIN+'/api/v1/u-auth/u-sys/api/v1/agents/tray/version/dependency':return Response(deps)
            raise AssertionError('unexpected GET')
        def observed(name):
            found=deepcopy(ci)
            if bad_os[0]:found['detail']['os']['name']='Ubuntu'
            return found,{},base+'/tasks?limit=25',None
        session=SimpleNamespace(session_id='fixture-session',_ensure_started=lambda:None,
            _observed_agent_task_context=observed,_same_https_origin_url=lambda observed,path:p.ORIGIN+path,
            context=SimpleNamespace(request=SimpleNamespace(get=get,post=lambda *a,**kw:(_ for _ in ()).throw(AssertionError('POST forbidden')))))
        stack.enter_context(patch('tools.browser._session',session))
        assert uqa.classify_tool_action(p.TOOL,{})=='observe' and execute_tool(p.TOOL,{})['executed'] is False
        args={'target':name,'kind':'versions'};ctx={'job_id':jid,'case_id':cid,'force_read_only':True,'action_policy':'confirm_mutations'}
        out=uqa.execute_tool_with_policy(p.TOOL,args,[{'role':'user','content':request}],**ctx)
        assert out.get('catalog')==versions and out['mutation_executed'] is False,out
        assert out['installation_verified'] is False and out['core_plugin_compatibility_verified'] is False and out['remote_session_executed'] is False
        assert uqa.execute_tool_with_policy(p.TOOL,{'target':name,'kind':'dependencies'},[],**ctx)['catalog']==deps
        before=len(gets)
        for invalid in [{'target':'ubuntu','kind':'versions'},dict(args,kind='vnc'),dict(args,url='arbitrary')]:
            assert uqa.execute_tool_with_policy(p.TOOL,invalid,[],**ctx).get('error')=='locked_tray_catalog_scope_required'
        assert len(gets)==before
        bad_os[0]=True;assert uqa.execute_tool_with_policy(p.TOOL,args,[],**ctx).get('error');bad_os[0]=False
        bad_catalog[0]=True;assert uqa.execute_tool_with_policy(p.TOOL,args,[],**ctx).get('error')
        assert not list_operations(jid)
print('PASS Tray catalogue fixture: source pin/time, exact two lab targets, GET-only origin-prefix binding, strict schema/budgets, no installation/session/PASS claims')

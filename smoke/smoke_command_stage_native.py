"""Fake native HTTP/storage/journal only. No lab reads/writes or model acceptance."""
from copy import deepcopy
from datetime import datetime,timezone,timedelta
import hashlib
from types import SimpleNamespace
from unittest.mock import patch
import command_stage_native as n
from command_probe_contract import target
from command_stage_profile import requirement,stages_for,metadata_payload
from operation_journal import _fingerprint
from command_stage_recovery import evaluate

for name in ['windows','astra']:
    t=target(name);r=requirement(name,'uqa-command-v360');caseid='fixture-case';jid='fixture-job'
    job={'stand':'lab','job_type':'manual','status':'running','resources':[],
        'request':' '.join([r[k] for k in ['ci_id','agent_id','ci_name','core_version','plugin_name','plugin_version','profile_id']]),
        'test_cases':[{'case_id':caseid,'status':'running','requirement':r}]}
    ci={'id':t['ci_id'],'agent_id':t['agent_id'],'name':t['ci_name'],'os_name':'Windows 10 Pro' if name=='windows' else 'Astra Linux',
        'detail':{'os':{'architecture':'64'}}}
    agent={'id':t['agent_id'],'version':'1.3.27','status':'online'}
    audit={'agent_id':t['agent_id'],'last_audit_at':(datetime.now(timezone.utc)-timedelta(hours=2)).isoformat(),
        'detail':[{'plugin_name':'executeCommand','plugin_version':'1.2.25','load_status':True,'load_error':''}]}
    ledger=[];posts=[];created={};binary_version=['1.2.25'];fail_dispatch=[False]
    periodic_full=[False];bad_receipt=[False]
    class Response:
        def __init__(self,status,body):self.status=status;self.body=body
        def json(self):return deepcopy(self.body)
    def get(url,params=None,**kwargs):
        if url.endswith('/tasks'):return Response(200,{'total':0,'items':[],'offset':0})
        if url.endswith('/plugin'):return Response(200,audit)
        if url.endswith('/'+t['agent_id']):return Response(200,agent)
        if url.endswith('/full'):
            tid=url.split('/')[-2];body=deepcopy(created[tid]);task=body['name']
            envelope={'machine_uid':t['ci_id'],'processed_at':datetime.now(timezone.utc).isoformat(),'result':'success','data':{}}
            if task=='pluginAudit':
                audit['last_audit_at']=envelope['processed_at'];audit['detail'][0]['plugin_version']=binary_version[0]
            elif task=='managePlugin':
                binary_version[0]='1.4.0';envelope['data']={'plugins_downloaded':[{'plugin_name':'executeCommand','size_bytes':123}],
                    'plugins_scheduled_for_deletion':[]}
            else:
                marker=body['additional_params']['arguments'][-1]
                envelope['data']={'stdout':marker+('\r\n' if name=='windows' else ''),'stderr':'','errorlevel':0}
            body.update(status='success',result=envelope)
            if periodic_full[0]:body['period']=30
            return Response(200,body)
        raise AssertionError('Unexpected GET')
    def post(url,data,**kwargs):
        posts.append((url,deepcopy(data)))
        if fail_dispatch[0]:raise TimeoutError('synthetic after-send uncertainty')
        tid='12345678-1234-4234-9234-'+str(len(posts)).zfill(12)
        body={**deepcopy(data),'id':tid,'agent_id':t['agent_id'],'created_at':datetime.now(timezone.utc).isoformat()}
        if url.endswith('/update'):body.update(name='managePlugin',period=None)
        if bad_receipt[0] and body.get('name')=='executeCommand':body['additional_params']['programm']='sh'
        created[tid]=body;return Response(202 if url.endswith('/update') else 201,body)
    session=SimpleNamespace(session_id='fixture-session',_ensure_started=lambda:None,
        _observed_agent_task_context=lambda ci_name:(ci,{},'https://uc.lab.local/api/v1/agents/'+t['agent_id']+'/tasks',None),
        _same_https_origin_url=lambda observed,path:'https://uc.lab.local'+path,
        context=SimpleNamespace(request=SimpleNamespace(get=get,post=post)))
    def ready(*args):
        checked=n.summarize_plugin_audit(ci,audit,'executeCommand','1.4.0')
        return {'ci_id':t['ci_id'],'agent_id':t['agent_id'],'core_version':'1.3.27','agent_status':'online',
            'plugin_audit':checked,'ready':checked['observation_result']=='PASS'}
    session.inspect_pinned_agent_readiness_semantic=ready
    with patch.object(n.job_store,'get_job',return_value=job),patch.object(n,'list_operations',side_effect=lambda jid:deepcopy(ledger)),\
         patch.object(n,'Path') as path,patch.object(n,'BOOK_SHA',hashlib.sha256(b'fixture-workbook').hexdigest()):
        path.return_value.read_bytes.return_value=b'fixture-workbook'
        assert n.create_stage(session,name,'initial_inventory',jid,caseid)['mutation_executed'] is False
        assert not posts  # No durable claim -> no GET/POST authority.
        for i,s in enumerate(stages_for(name)):
            op={'operation_id':'op-'+str(i),'case_id':caseid,'status':'sending',
                **{k:s[k] for k in ['workflow_id','stage_id','resource_key','tool']},
                'arguments_fingerprint':_fingerprint(s['arguments']),
                'verification_fingerprint':_fingerprint(s['verification'])}
            ledger.append(op)
            if i==0:
                for key,value in [('version','1.2.25'),('status','offline')]:
                    saved=agent[key];agent[key]=value
                    assert n.create_stage(session,name,s['stage_id'],jid,caseid)['mutation_executed'] is False
                    assert not posts;agent[key]=saved
                saved=ci['detail']['os']['architecture'];ci['detail']['os']['architecture']='32'
                assert n.create_stage(session,name,s['stage_id'],jid,caseid)['mutation_executed'] is False
                assert not posts;ci['detail']['os']['architecture']=saved
                ledger.append(dict(op,operation_id='old-uncertain',status='uncertain'))
                assert n.create_stage(session,name,s['stage_id'],jid,caseid)['mutation_executed'] is False
                assert not posts;ledger.pop()
            assert n.create_stage(session,'other',s['stage_id'],jid,caseid)['mutation_executed'] is False
            out=n.create_stage(session,name,s['stage_id'],jid,caseid)
            assert out.get('executed') is True,(s,out)
            assert 'expected_marker' not in out
            assert len(posts)==i+1
            tid=out['task_id'];op['status']='awaiting_verification'
            assert not n.inspect_stage(session,name,'unknown',jid,caseid)['native_result_verified']
            periodic_full[0]=True
            assert not n.inspect_stage(session,name,tid,jid,caseid)['native_result_verified']
            periodic_full[0]=False
            result=n.inspect_stage(session,name,tid,jid,caseid)
            assert result['native_result_verified'] is True,(s,result)
            assert result['business_pass'] is False
            op.update(receipt={'acknowledged':True},created_at=(datetime.now(timezone.utc)-timedelta(seconds=5)).isoformat())
            def evidence(eid,tool,args,body):
                import json
                return {'evidence_id':eid,'source':'uqa_tool','execution_status':'observed',
                    'created_at':datetime.now(timezone.utc).isoformat(),
                    'value':json.dumps({'tool':tool,'arguments':args,'result':body})}
            from command_stage_profile import CREATE,READ
            create_ev=evidence('create-'+str(i),CREATE,s['arguments'],out)
            read_ev=evidence('read-'+str(i),READ,{'target':name,'task_id':tid},result)
            job['test_cases'][0]['evidence']=[create_ev,read_ev]
            assert evaluate(job,op,read_ev['evidence_id'],s['verification'])['verified'] is True,(s,result)
            import json
            for key,value in [('task_id','other'),('session_id','other'),('ci_id','other'),('fresh_result',False),
                              ('stage_id','other'),('business_pass',True)]:
                bad=deepcopy(job);b=json.loads(bad['test_cases'][0]['evidence'][1]['value']);b['result'][key]=value
                bad['test_cases'][0]['evidence'][1]['value']=json.dumps(b)
                assert evaluate(bad,op,read_ev['evidence_id'],s['verification'])['verified'] is False
            bad=deepcopy(job);bad['test_cases'][0]['evidence'][1]['source']='model_text'
            assert not evaluate(bad,op,read_ev['evidence_id'],s['verification'])['verified']
            assert not evaluate(job,op,'invented',s['verification'])['verified']
            op['status']='verified'
            if s['stage_id']=='execute_command':
                assert result['technical_execution_verified'] is True
                assert result['expected_marker_sha256']==out['expected_marker_sha256']
            else:assert posts[-1][1]==metadata_payload(s['stage_id'])
            count=len(posts)
            assert n.create_stage(session,name,s['stage_id'],jid,caseid)['mutation_executed'] is False
            assert len(posts)==count
        session.session_id='new-session'
        assert not n.inspect_stage(session,name,tid,jid,caseid)['native_result_verified']
        session.session_id='fixture-session'
        # A missing/changed workbook cannot send even with a fresh intent.
        session._closed_command_tasks={};ledger[:]=[dict(op,status='sending')]
        path.return_value.read_bytes.return_value=b'changed'
        before=len(posts);assert n.create_stage(session,name,'execute_command',jid,caseid)['mutation_executed'] is False
        assert len(posts)==before
        path.return_value.read_bytes.return_value=b'fixture-workbook';bad_receipt[0]=True
        out=n.create_stage(session,name,'execute_command',jid,caseid)
        assert out['dispatch_may_have_occurred'] is True and out['observed_task_id']
        assert out['observed_identifier_is_owned_verified_receipt'] is False and not session._closed_command_tasks
        bad_receipt[0]=False;fail_dispatch[0]=True
        out=n.create_stage(session,name,'execute_command',jid,caseid)
        assert out.get('dispatch_may_have_occurred') is True and out.get('executed') is False
print('PASS fake closed native stages: actual claimed intent required; metadata/update/own-marker path; '
      'workbook/target/session/replay guards; uncertain sends never not-sent; NO lab/model acceptance')

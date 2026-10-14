"""Real local journal + mocked sends; abrupt process exit; zero stand actions."""
import json
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import job_store
import operation_journal as journal
import uqa

def fixture():
    j=job_store.create_job('Isolated operation fixture',job_type='regression')
    c=job_store.add_test_case(j['job_id'],'Fixture',requirement={})
    return j['job_id'],c['case_id']

def context(jid,cid):
    return dict(job_id=jid,case_id=cid,workflow_id='fixture-workflow',stage_id='create',
                resource_key='owned-fixture',tool='fixture_send',arguments={'text':'private-fixture-value'})

with TemporaryDirectory(prefix='uqa-operations-') as directory, patch.object(job_store,'JOBS_DIR',Path(directory)):
    jid,cid=fixture();ctx=context(jid,cid);sends=[]
    def send():
        assert journal.list_operations(jid)[0]['status']=='sending'
        sends.append(1)
        return {'executed':True,'status':'ok'}
    result=journal.execute_journaled(ctx,send)
    assert result['operation_status']=='awaiting_verification' and sends==[1]
    assert not journal.execute_journaled(ctx,send)['allowed'] and sends==[1]
    altered=dict(ctx,arguments={'text':'different'})
    assert journal.execute_journaled(altered,send)['error']=='operation_arguments_changed' and sends==[1]
    other=dict(ctx,stage_id='rename',workflow_id='different-workflow')
    assert journal.execute_journaled(other,send)['error']=='operation_reconciliation_required' and sends==[1]
    assert 'private-fixture-value' not in json.dumps(journal.list_operations(jid))
    snapshot=job_store.get_job(jid);snapshot['request']='Legacy whole-Job save'
    job_store.save_job(snapshot)
    assert journal.list_operations(jid)[0]['status']=='awaiting_verification'

    jid2,cid2=fixture();ctx2=context(jid2,cid2)
    with ThreadPoolExecutor(max_workers=8) as pool:
        claims=list(pool.map(lambda _:journal.begin_operation(**ctx2),range(16)))
    assert sum(c['allowed'] for c in claims)==1 and len(journal.list_operations(jid2))==1

    jid3,cid3=fixture();ctx3=context(jid3,cid3)
    child='''import os,sys;from pathlib import Path;import job_store,operation_journal as j
job_store.JOBS_DIR=Path(sys.argv[1]);claim=j.begin_operation(job_id=sys.argv[2],case_id=sys.argv[3],workflow_id='fixture-workflow',stage_id='create',resource_key='owned-fixture',tool='fixture_send',arguments={'text':'private-fixture-value'});assert claim['allowed'];os._exit(23)'''
    crashed=subprocess.run([sys.executable,'-c',child,directory,jid3,cid3],capture_output=True,timeout=30)
    assert crashed.returncode==23
    assert journal.list_operations(jid3)[0]['status']=='sending'
    assert journal.execute_journaled(ctx3,lambda: (_ for _ in ()).throw(AssertionError('must not resend')))['error']=='operation_replay_blocked'

    jid4,cid4=fixture();ctx4=context(jid4,cid4)
    try:journal.execute_journaled(ctx4,lambda: (_ for _ in ()).throw(TimeoutError('private-fixture-error')))
    except TimeoutError:pass
    else:raise AssertionError('timeout expected')
    assert journal.list_operations(jid4)[0]['status']=='uncertain'
    assert 'private-fixture-error' not in json.dumps(journal.list_operations(jid4))

    # Integration: normal policy denial writes NO intent; a permitted mock send
    # is durably claimed, then replay is stopped before the approval callback.
    jid5,cid5=fixture();calls=[];decisions=[]
    def deny(*args):decisions.append(1);return {'allow':False,'status':'blocked'}
    def allow(*args):decisions.append(1);return {'allow':True,'status':'confirmed'}
    def tool(*args):
        calls.append(1);assert journal.list_operations(jid5)[0]['status']=='sending'
        return {'executed':True,'click_status':'executed'}
    args={'name':'Save','exact':True}
    with patch.object(uqa,'managed_action_policy_decision',deny),patch.object(uqa,'execute_tool',tool):
        assert uqa.execute_tool_with_policy('browser_click_semantic',args,[],job_id=jid5,case_id=cid5,action_policy='confirm_mutations')['executed'] is False
    assert not journal.list_operations(jid5) and not calls
    with patch.object(uqa,'managed_action_policy_decision',allow),patch.object(uqa,'execute_tool',tool):
        first=uqa.execute_tool_with_policy('browser_click_semantic',args,[],job_id=jid5,case_id=cid5,action_policy='confirm_mutations')
        assert first.get('operation_status')=='awaiting_verification',first.get('error')
        repeat=uqa.execute_tool_with_policy('browser_click_semantic',args,[],job_id=jid5,case_id=cid5,action_policy='confirm_mutations')
        assert repeat['action_policy_status']=='blocked_by_operation_journal' and len(calls)==1 and len(decisions)==2
print('PASS operation journal: pre-send intent, concurrent claim, process crash, timeout, replay barrier, unchanged approval policy')

"""Local Playwright disabled-button refusal and isolated durable journal tests."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from playwright.sync_api import sync_playwright
import job_store
import operation_journal as journal
import uqa
from native_dispatch import DisabledBeforeDispatch
from tools.browser import BrowserSession

with sync_playwright() as p:
    browser=p.chromium.launch(headless=True)
    page=browser.new_page()
    page.set_content('<button disabled onclick="window.clicked=true">Save</button>')
    session=BrowserSession()
    session.page=page
    with patch.object(session,'_ensure_started'), patch.object(session,'_reset_diagnostics'), \
         patch.object(session,'_capture_state',return_value={}), patch.object(session,'_begin_action_execution') as begin:
        refusal=session.click_semantic(name='Save',exact=True)
        assert type(refusal) is DisabledBeforeDispatch
        assert refusal['error']=='element_disabled' and refusal['click_status']=='not_executed'
        assert not begin.called and page.evaluate('Boolean(window.clicked)') is False
    browser.close()

with TemporaryDirectory(prefix='uqa-not-sent-') as directory, patch.object(job_store,'JOBS_DIR',Path(directory)):
    def fixture():
        j=job_store.create_job('Isolated native presend fixture',job_type='regression')
        c=job_store.add_test_case(j['job_id'],'Fixture',requirement={})
        return dict(job_id=j['job_id'],case_id=c['case_id'],workflow_id='fixture',stage_id='create',
                    resource_key='owned-fixture',tool='browser_click_semantic',arguments={'name':'Save','exact':True},
                    verification_contract={'version':1,'fixture':True})
    ctx=fixture()
    first=journal.execute_journaled(ctx,lambda:refusal)
    assert first['operation_status']=='not_sent'
    assert journal.inspect_operation(**ctx)['allowed']
    for changed in (dict(ctx,tool='different_tool'),dict(ctx,arguments={'name':'Other'}),
                    dict(ctx,verification_contract={'version':1,'fixture':False})):
        assert not journal.begin_operation(**changed)['allowed']
    assert not journal.reconcile_operation(ctx['job_id'],first['operation_id'],'fixture')['verified']
    second=journal.execute_journaled(ctx,lambda:{'click_status':'executed'})
    assert second['operation_status']=='awaiting_verification'
    assert second['operation_id']!=first['operation_id']
    assert [o['status'] for o in journal.list_operations(ctx['job_id'])]==['not_sent','awaiting_verification']
    assert not journal.inspect_operation(**ctx)['allowed']
    for untrusted in (dict(refusal),json.loads(json.dumps(refusal)),{'executed':False},
                      {'error':'click_failed','click_status':'not_executed'}):
        c=fixture()
        assert journal.execute_journaled(c,lambda:untrusted)['operation_status']=='uncertain'
        assert not journal.inspect_operation(**c)['allowed']
    c=fixture()
    try:
        journal.execute_journaled(c,lambda:(_ for _ in ()).throw(TimeoutError()))
    except TimeoutError:
        pass
    else:
        raise AssertionError('timeout expected')
    assert journal.list_operations(c['job_id'])[0]['status']=='uncertain'
    c=fixture();decisions=[];results=iter([refusal,{'click_status':'executed'}])
    def allow(*args):
        decisions.append(1)
        return {'allow':True,'status':'confirmed'}
    with patch.object(uqa,'managed_action_policy_decision',allow), \
         patch.object(uqa,'execute_tool',lambda *args:next(results)):
        args={'name':'Save','exact':True}
        first=uqa.execute_tool_with_policy('browser_click_semantic',args,[],job_id=c['job_id'],case_id=c['case_id'],action_policy='confirm_mutations')
        assert first['operation_status']=='not_sent'
        second=uqa.execute_tool_with_policy('browser_click_semantic',args,[],job_id=c['job_id'],case_id=c['case_id'],action_policy='confirm_mutations')
        assert second['operation_status']=='awaiting_verification' and len(decisions)==2
        third=uqa.execute_tool_with_policy('browser_click_semantic',args,[],job_id=c['job_id'],case_id=c['case_id'],action_policy='confirm_mutations')
        assert third['action_policy_status']=='blocked_by_operation_journal' and len(decisions)==2
print('PASS native no dispatch: actual disabled control, no click, retained attempts, same-context retry, JSON/error/timeout fail closed')

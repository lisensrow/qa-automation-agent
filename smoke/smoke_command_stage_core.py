"""Core/journal fixture, no native HTTP, LLM or lab objects."""
from contextlib import ExitStack
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import uqa,job_store,command_stage_native
from command_stage_profile import requirement,CREATE,READ
from operation_journal import list_operations
from tools.registry import execute_tool

r=requirement('windows','uqa-command-v360')
request='Проверь безопасный closed marker: '+' '.join(r[k] for k in ['ci_id','agent_id','ci_name','core_version','plugin_name','plugin_version','profile_id'])
assert uqa.classify_tool_action(CREATE,{})=='write'
assert uqa.classify_tool_action(READ,{})=='observe'
assert execute_tool(CREATE,{'target':'windows','stage_id':'initial_inventory'})['executed'] is False
assert uqa.execute_tool_with_policy(CREATE,{},[],action_policy='confirm_mutations')['executed'] is False
with TemporaryDirectory() as tmp,ExitStack() as stack:
    stack.enter_context(patch.object(job_store,'JOBS_DIR',Path(tmp)))
    j=job_store.create_job(request,stand='lab',job_type='manual');jid=j['job_id']
    c=job_store.add_test_case(jid,'Closed command fixture',requirement=r);cid=c['case_id']
    job_store.set_job_status(jid,'running');job_store.update_test_case(jid,cid,status='running')
    messages=[{'role':'user','content':request}];args={'target':'windows','stage_id':'initial_inventory'}
    ctx={'job_id':jid,'case_id':cid,'action_policy':'confirm_mutations'}
    assert uqa.execute_tool_with_policy(CREATE,args,messages,force_read_only=True,**ctx).get('error')=='tool_policy_blocked'
    assert not list_operations(jid)
    assert uqa.execute_tool_with_policy(CREATE,{**args,'target':'astra'},messages,**ctx).get('error')=='locked_closed_command_scope_required'
    assert not list_operations(jid)
    decision=stack.enter_context(patch.object(uqa,'managed_action_policy_decision',return_value={'allow':True,'status':'fixture_only'}))
    def native(session,target,stage_id,job_id,case_id):
        assert command_stage_native.claimed_stage(job_id,case_id,target,stage_id)[1]
        return command_stage_native.refusal('fixture_preflight_no_dispatch')
    invoke=stack.enter_context(patch.object(command_stage_native,'create_stage',side_effect=native))
    out=uqa.execute_tool_with_policy(CREATE,args,messages,**ctx)
    assert out.get('operation_status')=='not_sent',out
    decision.assert_called_once();invoke.assert_called_once()
    ledger=list_operations(jid);assert len(ledger)==1 and ledger[0]['stage_id']=='initial_inventory'
    assert ledger[0]['status']=='not_sent' and ledger[0]['verification_fingerprint']
    j2=job_store.create_job(request,stand='lab',job_type='manual');jid2=j2['job_id']
    c2=job_store.add_test_case(jid2,'Uncertain dispatch fixture',requirement=r);cid2=c2['case_id']
    job_store.set_job_status(jid2,'running');job_store.update_test_case(jid2,cid2,status='running')
    invoke.side_effect=lambda *args:{'error':'synthetic_after_send','executed':False,'dispatch_may_have_occurred':True}
    ctx2={'job_id':jid2,'case_id':cid2,'action_policy':'confirm_mutations'}
    out=uqa.execute_tool_with_policy(CREATE,args,messages,**ctx2)
    assert out.get('operation_status')=='uncertain',out
    before=invoke.call_count
    blocked=uqa.execute_tool_with_policy(CREATE,args,messages,**ctx2)
    assert blocked.get('executed') is False and invoke.call_count==before
    assert len(list_operations(jid2))==1 and list_operations(jid2)[0]['status']=='uncertain'
print('PASS closed command Core fixture: unchanged policy call, exact scope, strict readonly, durable claim before native; '
      'preflight refusal not-sent, no legacy dispatcher authority or real execution')

from copy import deepcopy
from diagnostic_scope import scope_diagnostic_arguments, DIAGNOSTIC_TOOLS
import uqa

job={'job_type':'regression','stand':'fixture','request':'Inspect only.',
     'test_cases':[{'case_id':'case','requirement':{'stand':'fixture'}}]}
for tool in DIAGNOSTIC_TOOLS:
    original={'method':'GET'}
    args,error=scope_diagnostic_arguments(tool,original,job,'case')
    assert error is None and args['stand']=='fixture' and original=={'method':'GET'}
    assert scope_diagnostic_arguments(tool,{'stand':'fixture'},job,'case')[1] is None
    for wrong in ('other','https://fixture.invalid','',42):
        assert scope_diagnostic_arguments(tool,{'stand':wrong},job,'case')[1]=='diagnostic_stand_mismatch'
    assert scope_diagnostic_arguments(tool,{},job,'missing')[1]=='diagnostic_case_scope_missing'
    inconsistent=deepcopy(job)
    inconsistent['test_cases'][0]['requirement']['stand']='other'
    assert scope_diagnostic_arguments(tool,{},inconsistent,'case')[1]=='diagnostic_case_scope_inconsistent'
assert scope_diagnostic_arguments('browser_get_state',{},None,None)==({},None)
saved=uqa.get_job,uqa.execute_tool
calls=[]
try:
    uqa.get_job=lambda _:deepcopy(job)
    uqa.execute_tool=lambda name,args: calls.append((name,args)) or {'status':'ok'}
    for tool in DIAGNOSTIC_TOOLS:
        result=uqa.execute_tool_with_policy(tool,{'stand':'other'},[],action_policy='confirm_mutations',job_id='job',case_id='case')
        assert result['executed'] is False and result['error']=='diagnostic_stand_mismatch'
    assert calls==[]
    result=uqa.execute_tool_with_policy('ssh_docker_ps',{},[],action_policy='confirm_mutations',job_id='job',case_id='case')
    assert calls==[('ssh_docker_ps',{'stand':'fixture'})]
    assert result['action_policy_status']=='auto_allowed'
finally:
    uqa.get_job,uqa.execute_tool=saved
print('diagnostic scope: PASS (wrong stand never executed, absent stand bound, policy retained)')

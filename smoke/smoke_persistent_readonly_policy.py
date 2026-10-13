"""Internal reminders cannot replace the user's persistent read-only scope."""
import uqa
from copy import deepcopy
saved={k:getattr(uqa,k) for k in ('get_job','execute_tool','_confirm_managed_action')}
job={'job_id':'job','job_type':'manual','stand':'fixture','request':'Read-only. Inspect the table only.',
     'test_cases':[{'case_id':'case','requirement':{'stand':'fixture'}}]}
messages=[{'role':'user','content':'Read-only. Inspect the table only.'},
          {'role':'user','content':'[UQA CORE: CONTINUE NAVIGATION] Continue to the next step.'}]
calls=[]
scope_key=('job','case')
previous=uqa._PENDING_NAVIGATION_CANDIDATES.get(scope_key)
try:
    uqa.get_job=lambda _:deepcopy(job)
    def forbidden(*args,**kwargs):
        calls.append('unexpected')
        raise AssertionError('write executed or confirmation requested for prohibited action')
    uqa.execute_tool=uqa._confirm_managed_action=forbidden
    uqa._PENDING_NAVIGATION_CANDIDATES[scope_key]={'tool':'browser_click_semantic',
        'arguments':{'name':'CMDB','exact':True}}
    for label in ('plus','+','Add','Save','Update','Rename','Delete','Purge'):
        result=uqa.execute_tool_with_policy('browser_click_semantic',{'name':label,'exact':True},messages,
            job_id='job',case_id='case',action_policy='confirm_mutations')
        assert result['executed'] is False and result['action_policy_status']=='blocked_by_request_policy',label
    assert calls==[]
    uqa.execute_tool=lambda name,args:{'status':'ok'}
    result=uqa.execute_tool_with_policy('browser_click_semantic',{'name':'CMDB','exact':True},messages,
        job_id='job',case_id='case',action_policy='confirm_mutations')
    assert result['action_class']=='interact' and result['action_policy_status']=='auto_allowed'
    allowed=[{'role':'user','content':'Create a test record; do not modify existing objects.'}]
    assert uqa.tool_policy_check('browser_click_semantic',{'name':'Add'},allowed) is None
    assert uqa.classify_tool_action('browser_click_semantic',{'name':'Add'})=='write'
    assert uqa.classify_tool_action('browser_click_semantic',{'name':'Delete'})=='destructive'
finally:
    if previous is None:
        uqa._PENDING_NAVIGATION_CANDIDATES.pop(scope_key,None)
    else:
        uqa._PENDING_NAVIGATION_CANDIDATES[scope_key]=previous
    for k,value in saved.items():
        setattr(uqa,k,value)
print('persistent read-only policy: PASS (Core reminders cannot enable writes; normal navigation retained)')

"""No UC: explicit locked runtime, policy callbacks, fail-closed and once-only."""
from copy import deepcopy
from unittest.mock import patch
import json
import condition_draft_profiles as profiles
from condition_draft_runtime import run,validate_context
import uqa

plan={'logic':'AND','conditions':[{'field':'Archived','operator':'Equal','value':'No'},
    {'field':'CI class','operator':'Equal','value':'Endpoint'},{'field':'OS name','operator':'Wildcard','value':'*fixture*'}]}
req=profiles.requirement_for_plan(plan,'ck-phase')
base={'job_id':'fixture-job','job_type':'regression','status':'running','stand':'lab','resources':[],
      'request':'Создай новую коллекцию, только условия, без сохранения.',
      'test_cases':[{'case_id':'fixture-case','status':'running','requirement':req,
                     'planned_checks':[{'check_id':'ck-phase','title':'Three conditions'}],'evidence':[],'observations':[]}]}

class Fake:
    def __init__(self):self.job=deepcopy(base);self.calls=[];self.path='/cmdb';self.wrong_plan=False;self.redirect=False;self.login=False;self.auth_candidate=False
    def get_job(self,jid):return deepcopy(self.job)
    def get_stand(self,stand):return {'web_url':'https://fixture.test'}
    def save(self,job):self.job=deepcopy(job)
    def add_evidence(self,*args,**kwargs):self.job['test_cases'][0]['evidence'].append({'type':args[2],'value':args[3]})
    def execute_tool_with_policy(self,tool,args,messages,**kwargs):
        assert kwargs['action_policy']=='confirm_mutations' and kwargs['require_compatibility_probe'] is True
        self.calls.append(tool)
        if tool=='knowledge_search':return {'results':[]}
        if tool=='browser_open_page' and self.login:
            result={'current_url':'https://fixture.test/cmdb','session_id':'fixture-session',
                    'interactive_elements':[{'type':'password','enabled':True}]}
            if self.auth_candidate:result['required_action_candidate']={'tool':'browser_authenticate_saved_stand','arguments':{'stand':'lab'}}
            return result
        if tool=='browser_authenticate_saved_stand':self.login=False
        if tool=='browser_click_semantic':
            if args['name']=='Add collection':self.path='/cmdb/collections/new/settings/composition'
            elif args['name']=='Conditions':self.path=profiles.EDITOR_PATH
        if self.redirect:self.path='/unexpected'
        return {'current_url':'https://fixture.test'+self.path,'session_id':'fixture-session',
            'click_status':'executed','tree_row_status':'applied','grid_value_status':'observed'}
    def record_tool_observations(self,*args,**kwargs):return []
    def record_tool_evidence(self,*args,**kwargs):pass
    def tool_result_for_model(self,tool,result):return result
    def ask_ollama(self,messages,**kwargs):
        assert kwargs['tools']==[] and kwargs['response_schema']
        stored=self.job['test_cases'][0]['requirement']
        assert stored['bindings']['grid_session']=='fixture-session'
        assert stored['expected_plan']==profiles.requirement_for_plan(plan,'ck-phase')['expected_plan']
        proposed=deepcopy(plan)
        if self.wrong_plan:proposed['conditions'][0]['value']='Changed'
        return {'message':{'content':json.dumps(proposed)}}

def exercise(fake,**kwargs):
    with patch.object(profiles,'source_current',return_value=True), \
         patch('operation_journal.list_operations',return_value=[]), \
         patch('job_store.save_job',side_effect=fake.save), \
         patch('job_store.add_evidence',side_effect=fake.add_evidence):
        return run(fake,[],'fixture-job','fixture-case','confirm_mutations',**kwargs)

fake=Fake();assert exercise(fake)['status']=='observed_ui_draft'
assert fake.calls.count('browser_add_tree_row_semantic')==3
assert fake.calls[-1]=='browser_inspect_labeled_grid_values_semantic'
assert fake.job['test_cases'][0]['condition_draft_state']['phase']=='observed'
previous=len(fake.calls);assert exercise(fake)['reason']=='condition_draft_already_attempted' and len(fake.calls)==previous
fake=Fake();assert exercise(fake,force_read_only=True)['status']=='blocked' and not fake.calls
fake=Fake();fake.wrong_plan=True
assert exercise(fake)['reason']=='condition_plan_expected_mismatch'
assert 'browser_add_tree_row_semantic' not in fake.calls
assert any(e['type']=='condition_logical_proposal' for e in fake.job['test_cases'][0]['evidence'])
fake=Fake();fake.redirect=True
assert exercise(fake)['reason']=='condition_draft_editor_changed'
assert fake.calls==['browser_open_page']
fake=Fake();fake.login=True
assert exercise(fake)['reason']=='condition_draft_authentication_required' and fake.calls==['browser_open_page']
fake=Fake();fake.login=True;fake.auth_candidate=True
assert exercise(fake)['status']=='observed_ui_draft'
assert fake.calls[:3]==['browser_open_page','browser_authenticate_saved_stand','browser_probe_capabilities']
for change in ('unlocked','manual','resource','expected','stand','profile_pin'):
    fake=Fake()
    if change=='unlocked':fake.job['test_cases'][0]['requirement']['locked']=False
    elif change=='manual':fake.job['job_type']='manual'
    elif change=='resource':fake.job['resources']=[{'resource_id':'existing'}]
    elif change=='expected':fake.job['test_cases'][0]['requirement']['bindings']['grid_expected']='[]'
    elif change=='stand':fake.job['stand']='other'
    else:fake.job['test_cases'][0]['requirement']['condition_profile_sha256']='0'*64
    assert exercise(fake)['status']=='blocked' and not fake.calls,change
fake=Fake()
with patch.object(profiles,'preparation',return_value=[('browser_click_semantic',{'name':'Save'},'/new')]):
    assert exercise(fake)['status']=='blocked' and not fake.calls
pending=deepcopy(base);pending['status']='created';pending['test_cases'][0]['status']='pending'
with patch.object(profiles,'source_current',return_value=True), \
     patch.object(uqa,'get_job',return_value=pending), \
     patch.object(uqa,'get_stand',return_value={'web_url':'https://fixture.test'}):
    validate_context(pending,'fixture-case',preparing=True)
    prepared=uqa._prepared_regression_case('fixture-job')
    assert prepared[2]['requirement']['type']=='bounded_condition_draft'
    assert prepared[2]['requirement']['check_contracts']==req['check_contracts']
print('PASS bounded condition runtime: explicit caller contract/source/pins, normal policy callbacks, no Save, proposal before compile, redirect/read-only/expected/replay denial')

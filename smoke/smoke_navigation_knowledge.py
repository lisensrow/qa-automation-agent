"""Navigation candidates are Core-proven hints, not verified memory."""
from copy import deepcopy
from navigation_knowledge import derive_navigation_candidates, TOOL
from run_uconnect_manual_frontend_benchmark import build_job_spec, load_and_validate_manifest
from observation_extractor import extract_observations

spec=build_job_spec(load_and_validate_manifest(),'uc-front-002','fixture',{
    'exact_ci_name':'private-ci-fixture','requested_tab_names':'["Agent","Monitoring"]'})
records=[{'tab':name,'selected_tab':name,'selected_count':1,'panel_exists':True,'panel_visible':True,
    'controls':'panel-'+name,'details_identity_preserved':True} for name in ('Agent','Monitoring')]
observation=extract_observations(TOOL,{'name':'private-ci-fixture','tabs':['Agent','Monitoring']},{
    'name':'private-ci-fixture','requested_tabs':['Agent','Monitoring'],'tabs_verified':records,
    'details_identity_passed':True,'details_identity_preserved':True,
    'current_url':'https://fixture.test/items/private-id'})[0]
observation['observation_id']='obs'
case=dict(spec['case'],case_id='case',status='passed',observations=[observation],
          evidence=[{'evidence_id':'ev','type':TOOL,'observation_ids':['obs'],'usable_for_verdict':True}],
          memory_context={'identity_checked_at':'fresh'})
job={'job_id':'job','stand':'fixture','stand_identity':{'status':'ok','installation_architecture':'ansible',
     'server_version':'1.0','frontend_status':'ok','frontend_version':'2.0','checked_at':'fresh'},'test_cases':[case]}
facts=derive_navigation_candidates(job,'case','https://fixture.test/items')
assert len(facts)==1 and facts[0]['fact_type']=='ui_navigation'
assert facts[0]['usage']=='candidate_only_not_PASS_evidence'
assert 'private-ci-fixture' not in str(facts) and 'private-id' not in str(facts)
assert facts[0]['data']['ui_path']=='/items'
assert derive_navigation_candidates(job,'case','https://other.test/items')==[]
for mutate in (lambda j:j['test_cases'][0].update(status='blocked'),
               lambda j:j['stand_identity'].update(frontend_status='unknown'),
               lambda j:j['stand_identity'].update(deployment_partial=True),
               lambda j:j['test_cases'][0]['memory_context'].update(identity_checked_at='stale'),
               lambda j:j['test_cases'][0]['evidence'][0].update(usable_for_verdict=False),
               lambda j:j['test_cases'][0]['observations'][0]['data']['tabs_verified'][0].update(panel_visible=False)):
    bad=deepcopy(job)
    mutate(bad)
    assert derive_navigation_candidates(bad,'case','https://fixture.test/items')==[]
print('navigation knowledge candidates: PASS (Core contracts, fresh scope, no CI identity or false verification)')

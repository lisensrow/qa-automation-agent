"""Simulated fetch only; same-name replacement must never be deleted/archived."""
from tools.browser import BrowserSession
from uqa import _cleanup_exact_rest_target

s=BrowserSession()
try:
    s._ensure_started()
    s.page.route('https://fixture.test/**',lambda route:route.fulfill(status=200,body='<html><body>Fixture</body></html>'))
    s.page.goto('https://fixture.test/')
    def seed():
        s.page.evaluate('''()=>{
            window.fixtureItems=[{id:'replacement',name:'owned-fixture'}];
            window.fixtureWrites=[];
            window.fetch=async (url,args={})=>{
                const method=args.method||'GET';
                if(method!=='GET'){
                    window.fixtureWrites.push({url,method});
                    if(method==='DELETE')window.fixtureItems=[];
                    else window.fixtureItems[0].archived=true;
                    return {status:204,json:async()=>null};
                }
                return {status:200,json:async()=>JSON.parse(JSON.stringify(window.fixtureItems))};
            };
        }''')
    for archive in (False,True):
        seed()
        operation=s.archive_json_resource if archive else s.delete_json_resource
        blocked=operation('/fixture-members','owned-fixture',expected_identifier='original-owned-id')
        assert blocked.get('error')=='json_resource_identifier_mismatch',blocked.get('error')
        assert blocked['mutation_executed'] is False
        assert s.page.evaluate('fixtureWrites.length')==0
        ok=operation('/fixture-members','owned-fixture',expected_identifier='replacement')
        assert ok['status']=='ok' and ok['post_delete_verified'],ok.get('error')
        assert s.page.evaluate('fixtureWrites.length')==1
        suffix='/replacement/archive' if archive else '/replacement'
        assert s.page.evaluate('(suffix)=>fixtureWrites[0].url.endsWith(suffix)',suffix)
    resource={'name':'owned-fixture','external_id':'ledger-id','created_by_case':'case',
              'metadata':{'cleanup_http':{'method':'DELETE'}}}
    job={'test_cases':[{'case_id':'case','observations':[{'data':{
        'tool':'browser_click_semantic','input':{'name':'Save'},
        'network_requests':[{'method':'POST','url':'/fixture-members','status':201}]}}]}]}
    assert _cleanup_exact_rest_target(job,resource)['arguments']['expected_identifier']=='ledger-id'
    resource['external_id']=None
    assert 'expected_identifier' not in _cleanup_exact_rest_target(job,resource)['arguments']
    print('PASS cleanup ledger identity: same-name replacement rejected before DELETE/archive, matching ID verified, Core binding')
finally:
    s.close()

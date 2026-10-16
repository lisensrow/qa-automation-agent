"""Fake GETs only, no actual lab or model acceptance."""
from copy import deepcopy
from datetime import datetime,timezone,timedelta
from types import SimpleNamespace
from unittest.mock import patch
import lab_plugin_inventory as m
from command_probe_contract import target
import uqa
from tools.registry import execute_tool,TOOLS

assert uqa.classify_tool_action('browser_inspect_lab_plugin_inventory_semantic',{})=='observe'
schema=next(x['function'] for x in TOOLS if x['function']['name']=='browser_inspect_lab_plugin_inventory_semantic')
assert schema['parameters']['additionalProperties'] is False
for name in ['windows','astra']:
    t=target(name);ci={'id':t['ci_id'],'name':t['ci_name'],'agent_id':t['agent_id'],
        'detail':{'os':{'name':'Windows 10' if name=='windows' else 'Astra Linux','architecture':'64'}}}
    agent={'id':t['agent_id'],'status':'online','version':'1.3.27'}
    audit={'agent_id':t['agent_id'],'last_audit_at':datetime.now(timezone.utc).isoformat(),
        'detail':[{'plugin_name':'initRemoteDesktopConnectionTCP','plugin_version':'1.2.25','load_status':True,'load_error':''},
                  {'plugin_name':'checkAlive','plugin_version':'1.2.25','load_status':True}]}
    session=SimpleNamespace(session_id='fake-only')
    def run(a=None,g=None,c=None):
        def get(s,url):return deepcopy(g if g is not None else agent) if url=='agent' else deepcopy(a if a is not None else audit)
        with patch.object(m,'context',return_value=(t,c if c is not None else ci,['tasks','agent','plugins'])),patch.object(m,'read_json',side_effect=get):
            return m.inspect(session,name)
    r=run();assert r['audit_fresh'] and len(r['plugins'])==6 and not r['dispatch_authorized'] and not r['business_pass']
    assert r['plugins'][5]['name_source']=='historical_server_catalog_v295' and r['plugins'][0]['name_source']=='user_guide_appendix4'
    tcp=r['plugins'][2];assert tcp['observed'][0]['name']=='initRemoteDesktopConnectionTCP' and tcp['expected_version'] is None
    check=r['plugins'][4];assert check['observed'][0]['load_error_present'] is None
    assert not r['plugins'][0]['observed'] and r['plugins'][0]['match_count']==0
    bad=deepcopy(audit);bad['detail']*=2;assert run(bad)['plugins'][4]['match_count']==2
    for field,value in [('detail',None),('detail',[None]),('agent_id','other'),('detail',[{}]*201)]:
        bad=deepcopy(audit);bad[field]=value;assert run(bad).get('error')
    for field,value in [('version','1.2.25'),('status','offline'),('id','other')]:
        bad=deepcopy(agent);bad[field]=value;assert run(g=bad).get('error')
    bad=deepcopy(audit);bad['last_audit_at']=(datetime.now(timezone.utc)-timedelta(hours=2)).isoformat()
    assert run(bad)['audit_fresh'] is False
    bad=deepcopy(ci);bad['detail']['os']['name']='Ubuntu';assert run(c=bad).get('error')
assert execute_tool('browser_inspect_lab_plugin_inventory_semantic',{'target':'windows','post':True}).get('error')
assert m.inspect(None,'redos').get('error')
print('PASS lab inventory GET-only exact2targets/core/OS, bounded rows, case spelling, duplicate/missing/error unknown, no authorization')

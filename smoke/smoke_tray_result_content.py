"""Intrinsic reported counts, NOT independent process/desktop oracle."""
from copy import deepcopy
import plugin_result_review as p
for name in ['windows','astra']:
 r=p.requirement(name,'fixture',p.TRAY_PROFILE)
 assert set(r['expected_invariants'])=={'trayControl'} and r['business_pass'] is False
 assert set(p.requirement(name,'fixture')['expected_invariants'])=={'storageAudit','defaultNetworkDeviceAudit'}
empty={'action':'start','started':[],'already_running':[],'user':''}
out=p.content_checks('trayControl',empty)
assert [x['status'] for x in out['checks']]==['PASS','PASS','FAIL']
assert out['intrinsic_status']=='FAIL' and out['full_source_case_status']=='BLOCKED' and out['business_pass'] is False
assert p.content_checks('trayControl',{})['intrinsic_status']=='BLOCKED'
assert p.content_checks('trayControl',{'action':'start','started':None,'already_running':[]})['intrinsic_status']=='FAIL'
present=deepcopy(empty);present['already_running']=['private-fixture-user']
good=p.content_checks('trayControl',present)
assert good['intrinsic_status']=='PASS' and good['independent_os_correctness']=='BLOCKED' and good['business_pass'] is False
assert 'private-fixture-user' not in str(good)
for name in ['windows','astra']:
 sj,sc,v=p.REFS[name,'trayControl']
 parsed={**out,'target':name,'plugin_name':'trayControl','plugin_version':v,'source_job_id':sj,'source_case_id':sc,
  'historical_only':True,'same_recorded_payload':True,'replay_gate':deepcopy(p.TRAY_REPLAY_GATE)}
 assert p.compact_review(parsed)['intrinsic_status']=='FAIL'
 bad=deepcopy(parsed);bad['business_pass']=True;assert p.compact_review(bad)=={}
 bad=deepcopy(parsed);bad['checks'][-1]['status']='PASS';assert p.compact_review(bad)=={}
 bad=deepcopy(parsed);bad['replay_gate']['same_start_admitted']=True;assert p.compact_review(bad)=={}
 bad=deepcopy(parsed);del bad['replay_gate'];assert p.compact_review(bad)=={}
print('PASS Tray own historical report counts/empty vs missing/privacy/profile isolation/no desktop promotion')

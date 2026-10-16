"""No plugin/task invocation: native error/version checks never become full PASS."""
import plugin_result_review as p
from copy import deepcopy
baseline=p.requirement('windows','fixture-old')
assert set(baseline['source_refs'])=={'storageAudit','defaultNetworkDeviceAudit'}
r=p.requirement('windows','fixture-vnc-review',p.VNC_PROFILE)
assert set(r['source_refs'])=={'vncServer'} and r['historical_only'] and not r['business_pass']
try:p.requirement('astra','fixture',p.VNC_PROFILE)
except ValueError:pass
else:raise AssertionError('unbound Astra startup accepted')
data={'plugin':'VncServer','version':'1.3.2','result':'error','error':'VNC not installed yet'}
out=p.content_checks('vncServer',data)
assert out['intrinsic_status']=='FAIL' and all(x['status']=='FAIL' for x in out['checks'])
assert not out['business_pass'] and out['full_source_case_status']=='BLOCKED'
good=p.content_checks('vncServer',{'plugin':'VncServer','version':'1.5.5','result':'success','error':''})
assert good['intrinsic_status']=='BLOCKED' and not good['business_pass'] and good['independent_os_correctness']=='BLOCKED'
missing=p.content_checks('vncServer',{})
assert missing['intrinsic_status']=='BLOCKED' and not missing['business_pass']
parsed={**out,'target':'windows','plugin_name':'vncServer','plugin_version':'1.5.5',
 'source_job_id':r['source_refs']['vncServer'][0],'source_case_id':r['source_refs']['vncServer'][1],
 'historical_only':True,'same_recorded_payload':True}
assert p.compact_review(parsed)['intrinsic_status']=='FAIL'
assert not p.compact_review({**parsed,'intrinsic_status':'PASS'})
print('PASS historical VNC native error/version/empty-error invariants, old profiles unchanged, no task/full-PASS promotion; fixture only')

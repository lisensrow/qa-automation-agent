"""Separate measurement contract; old five-second oracle is unchanged."""
from copy import deepcopy
from unittest.mock import patch
import endpoint_metadata as p
b=p.LOG_BASELINE
file={'id':'a'*64,'size':4000,'mtime_ns':b['latest_log_mtime_ns']+1}
raw={'probe_version':1,'sample_interval_seconds':5,
 'first':{'status':'ok','bounded':True,'files':[file]},'second':{'status':'ok','bounded':True,'files':[file]},
 'tray':{'autostart_entry_present':True,'declared_script_present':True,'process_candidates':0,'process_scan_complete':True}}
assert p.summarize(raw)['logging_status']=='BLOCKED'
s=p.summarize_post_logs(raw);assert s['logging_status']=='PASS' and not s['write_between_samples']
assert not s['tray_desktop_verified'] and not s['file_writes'] and not s['business_pass']
bad=deepcopy(raw);bad['second']['files'][0]['mtime_ns']=b['latest_log_mtime_ns']
assert p.summarize_post_logs(bad)['logging_status']=='BLOCKED'
bad=deepcopy(raw);bad['second']['bounded']=False
assert p.summarize_post_logs(bad)['logging_status']=='BLOCKED'
bad=deepcopy(raw);bad['second']['files'][0]['mtime_ns']=999999999999999999999
try:p.summarize_post_logs(bad)
except ValueError:pass
else:raise AssertionError('future metadata')
r=p.requirement('astra','fixture',p.POST_LOG)
assert r['baseline']==p.LOG_BASELINE and r['payload_sha256']==p.SHA
assert r['operation_stages'][0]['workflow_id']==p.POST_LOG
assert r!=p.requirement('astra','fixture')
from endpoint_metadata_runtime import catalog
assert catalog([],r)[0]['function']['parameters']['properties']['query']['enum']==[p.POST_LOG]
print('PASS post-event log observation separate baseline/old oracle intact/no future mtime/write/desktop claims')

"""Exact supplied Tray preparation only; cannot start/stop any user client."""
from copy import deepcopy
from unittest.mock import patch
import json,hashlib
import plugin_preparation as p,plugin_discovery as d
for target in ['windows','astra']:
 r=p.requirement(target,'trayControl','fixture')
 assert r['plugin_version']=='1.0.1' and r['source_manifest']['workbook_target_version']=='unknown'
 assert r['expected_profile']['plugin_case_executed'] is False
 try:d.requirement(target,'trayControl','fixture')
 except ValueError:pass
 else:raise AssertionError('main Tray dispatch admitted')
files=[{'plugin':'trayControl','version':'1.0.1','platform':s,'vendor_checksum_matches':True,'sha256':'a'*64}
 for s in ['windows_x64','debian_x64']]
body={'facts':{'supplied_directory_version':'1.3.1','displayMonitoring_present_in_original_archive':True,
 'vnc_minimum_1_3_2_proven':False,'trayControl_supplied_version':'1.0.1'},
 'sources':{'catalog_hash':{'stdout':p.RELEASE_CATALOG_SHA+'  catalogue'},'release_catalog':{'stdout':json.dumps({'files':files})}}}
def check(b):
 raw=json.dumps(b);e={'evidence_id':p.RELEASE_EVIDENCE,'source':'operator_release_archive_catalog_package_review',
  'type':'operator_complete_release_search','execution_status':'observed','usable_for_pass':False,'usable_for_verdict':False,'value':raw}
 j={'job_id':p.RELEASE_JOB,'stand':'lab','test_cases':[{'evidence':[e]}]}
 with patch.object(p,'RELEASE_WITNESS_SHA',hashlib.sha256(raw.encode()).hexdigest()):return p.validate_tray_release_source(j)
assert check(body)
bad=deepcopy(body);bad['facts']['trayControl_supplied_version']='latest'
try:check(bad)
except ValueError:pass
else:raise AssertionError('guessed version')
bad=deepcopy(body);bad['sources']['release_catalog']['stdout']=json.dumps({'files':files[:1]})
try:check(bad)
except ValueError:pass
else:raise AssertionError('missing OS binary')
print('PASS supplied Tray 1.0.1/source/platform/checksum/preparation only, no start/stop/session permission')

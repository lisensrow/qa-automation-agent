"""Source authority separation, no runtime/HTTP/model or compatibility claim."""
from copy import deepcopy
from unittest.mock import patch
import hashlib,json
import plugin_preparation as p
import plugin_discovery as d

for name in ['windows','astra']:
 r=p.requirement(name,'displayMonitoring','supplied-release-fixture')
 assert r['plugin_version']=='1.3.1' and r['source_manifest']['kind']=='reviewed_supplied_release'
 assert r['source_manifest']['workbook_target_version']=='1.3.2'
 assert r['source_manifest']['workbook_target_satisfied'] is False
 assert r['expected_profile']['business_pass'] is False and r['expected_profile']['supplied_release_only'] is True
 for plugin in ['displayMonitoring','vncServer','trayControl']:
  try:d.requirement(name,plugin,'forbidden-main')
  except ValueError:pass
  else:raise AssertionError('unsafe main discovery admitted')

body={'facts':{'supplied_directory_version':'1.3.1','displayMonitoring_present_in_original_archive':True,
              'vnc_minimum_1_3_2_proven':False},
      'sources':{'catalog_hash':{'stdout':p.RELEASE_CATALOG_SHA+'  fixture-catalog\n'}}}
value=json.dumps(body)
ev={'evidence_id':p.RELEASE_EVIDENCE,'type':'operator_complete_release_search',
    'source':'operator_release_archive_catalog_package_review','execution_status':'observed',
    'usable_for_pass':False,'usable_for_verdict':False,'value':value}
job={'job_id':p.RELEASE_JOB,'stand':'lab','test_cases':[{'evidence':[ev]}]}
with patch.object(p,'RELEASE_WITNESS_SHA',hashlib.sha256(value.encode()).hexdigest()):
 assert p.validate_release_source(job) is True
 for key,bad in [('source','declaration'),('usable_for_pass',True),('value',value+' '),('type','other')]:
  j=deepcopy(job);j['test_cases'][0]['evidence'][0][key]=bad
  try:p.validate_release_source(j)
  except ValueError:pass
  else:raise AssertionError('forged witness accepted')
print('PASS supplied release source pin, workbook discrepancy retained, no main/VNC/session admission')

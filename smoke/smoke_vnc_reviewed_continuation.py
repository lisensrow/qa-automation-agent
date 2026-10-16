"""Exact reviewed failure only; no server, journal edit or real session."""
from copy import deepcopy
from unittest.mock import patch
import hashlib,json
import vnc_session as p
assert len(p.REPAIR_REVIEW['sha256'])==64 and all(c in '0123456789abcdef' for c in p.REPAIR_REVIEW['sha256'])
for name in ['windows','astra']:
 r=p.requirement(name,'new-authorized',p.REPAIR_REVIEW)
 old={'job_id':'old','test_cases':[]};c={'case_id':'case','requirement':p.requirement(name,'uqa-vnc-v442')}
 op={'case_id':'case','operation_id':'op','tool':p.CREATE,'status':'uncertain','created_at':'2026-10-16T09:20:00+00:00'}
 row={'target':name,'prior_job_id':'old','prior_case_id':'case','prior_operation_id':'op',
  'prior_operation_status':'uncertain','prior_created_at':op['created_at'],'no_tasks_in_prior_window':True,
  'ci_id':r['ci_id'],'agent_id':r['agent_id']}
 b={'schema':'uqa.authorized-vnc-url-repair-review.v1','rows':[row],
  **{k:True for k in ['user_authorized_url_repair_and_continuation','old_ledger_unchanged','public_DSN_unchanged',
   'exact_live_environment_preserved_except_internal_url','images_security_mounts_ports_unchanged',
   'backend_healthy','guacamole_api_authenticated','operator_prepared_continuation_not_uninterrupted_autonomy']},
  'internal_API_path':'/guacamole/','configuration_after_sha256':'ac67fc2f2bb98b98b3c896d8d142fee9dd5272cd336300c4769938444f92151d',
  'continuation_scope':'one_new_attempt_per_exact_target_after_fresh_native_absence_check','new_agent_tasks':0,'business_pass':False}
 e={'evidence_id':p.REPAIR_REVIEW['evidence_id'],'type':'operator_guacamole_repair_review',
  'source':'operator_authorized_environment_repair_review','execution_status':'observed',
  'usable_for_pass':False,'usable_for_verdict':False,'value':json.dumps(b)}
 pin={**p.REPAIR_REVIEW,'sha256':hashlib.sha256(e['value'].encode()).hexdigest()}
 r['prior_attempt_review']=pin;before={t:{'items':[],'total':0} for t in p.TASKS}
 def check(evidence=e,req=r,operation=op,previous=c,lists=before):
  with patch.object(p,'REPAIR_REVIEW',pin),patch.object(p.job_store,'get_job',return_value={'test_cases':[{'evidence':[evidence]}]}):
   return p.reviewed_attempt_allows(req,old,previous,[operation],lists)
 assert check()
 assert not check(req=p.requirement(name,'new-no-review'))
 for key,value in [('source','model'),('usable_for_pass',True),('value',e['value']+' ')]:
  assert not check(evidence={**e,key:value})
 for key,value in [('operation_id','another'),('status','verified'),('created_at','2026-10-16T09:21:00+00:00')]:
  assert not check(operation={**op,key:value})
 assert not check(previous={**c,'requirement':p.requirement(name,'different')})
 task={'id':'b52055e5-e13a-40a9-826e-479e44a3f3a0','name':p.TASKS[0],
   'agent_id':r['agent_id'],'period':None,'created_at':op['created_at']}
 changed=deepcopy(before);changed[p.TASKS[0]]={'items':[task],'total':1}
 assert not check(lists=changed)
 assert not check(lists={**before,p.TASKS[0]:{'items':[],'total':1}})
assert 'prior_attempt_review' not in p.requirement('astra','old-default')
print('PASS VNC exact operator review hash/target/attempt/fresh absence, no unreviewed rekey; fixture only')

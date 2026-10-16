"""Pure fixture only: narrowly pinned retirement cannot hide other pending tasks."""
from copy import deepcopy
from datetime import datetime,timezone
import json,hashlib
from unittest.mock import patch
import historical_command_retirement as m
from command_probe_contract import validate_task_list
at=datetime(2026,10,16,14,tzinfo=timezone.utc)
items=[{'id':tid,'agent_id':m.AGENT,'name':'executeCommand','period':None,'status':'progress','enabled':0,
 'end_ts':'2026-10-16T13:05:32Z','additional_params':{'programm':'cmd.exe','arguments':['fixture']}} for tid in sorted(m.IDS)]
b={'schema':'uqa.exact-legacy-command-retirement.v1','target':'windows','ci_id':m.CI,'agent_id':m.AGENT,
 'core_version':'1.3.27','fingerprint_keys':m.KEYS,'all_eight_expired_disabled_and_agent_not_running':True,
 'terminal_status_not_forged':True,'card_result_preservation_verified':True,'rows':[
  {'task_id':x['id'],'agent_id':m.AGENT,'agent_reports_not_running':True,'card_retained':True,
   'prior_result_preserved':True,'enabled':0,'server_status':'progress','end_ts':x['end_ts'],
   'task_fingerprint':m.fingerprint(x),'changed_fields':['end_ts','updated_at']} for x in items]}
raw=json.dumps(b);sha=hashlib.sha256(raw.encode()).hexdigest()
ev={'evidence_id':m.EVIDENCE,'source':'operator_native_retirement_review','type':'operator_exact_legacy_retirement_review',
 'execution_status':'observed','value':raw}
job={'test_cases':[{'case_id':m.CASE,'evidence':[ev]}]}
with patch.object(m,'SHA',sha),patch.object(m.job_store,'get_job',return_value=job):
 for x in items:assert m.validate_retired_item('windows',x,at)
 assert not m.validate_retired_item('astra',items[0],at)
 for k,v in [('id','new-task'),('agent_id','other'),('name','managePlugin'),('period',30),('enabled',1),
  ('status','created'),('end_ts','9999-12-31T00:00:00Z'),('additional_params',{}),('updated_at','changed')]:
  assert not m.validate_retired_item('windows',{**items[0],k:v},at)
 assert not m.validate_retired_item('windows',items[0],datetime(2026,10,16,12,tzinfo=timezone.utc))
 assert not m.validate_retired_item('windows',items[0],at.replace(tzinfo=None))
 with patch.object(m,'SHA','0'*64):assert not m.validate_retired_item('windows',items[0],at)
 with patch.object(m.job_store,'get_job',return_value=None):assert not m.validate_retired_item('windows',items[0],at)
 # No proof changes the unknown unresolved-command rejection.
 try:validate_task_list('windows',{'total':1,'items':[{**items[0],'id':'unrelated'}]},'executeCommand')
 except ValueError:pass
 else:raise AssertionError('Unknown pending command admitted')
 terminal={**items[0],'id':'unrelated','status':'terminated'}
 assert validate_task_list('windows',{'total':1,'items':[terminal]},'executeCommand')==[terminal]
print('PASS exact8 immutable retirement, expired/not-running/intact proof, unknown pending still blocked; fixture only')

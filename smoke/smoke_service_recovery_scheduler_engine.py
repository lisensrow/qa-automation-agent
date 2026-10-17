"""Actual Core with fake native receipts; no real Scheduler/service mutation."""
from unittest.mock import patch
import service_recovery_scheduler_engine as p
import service_recovery_dry_run as old
from smoke import smoke_service_recovery_dry_run as fixture
original_sample=fixture.sample
def sample(profile):
 b=original_sample(profile)
 if profile==p.OBSERVE:b['data'].update(scheduler_engine_pid=333,scheduler_instance='12345678-1234-4234-8234-123456789abc',scheduler_instance_verified=True)
 return b
def main():
 import endpoint_metadata as ep
 assert p.REGISTER not in ep.RETIRED_RECOVERY_PROFILES and p.OBSERVE not in ep.RETIRED_RECOVERY_PROFILES
 text=p.code('windows',p.REGISTER)
 assert 'GetRunningTasks(0)' in text and 'EnginePID' in text and 'InstanceGuid' in text
 assert 'Stop-Service' not in text and 'Restart-Service' not in text
 assert 'if($taskCursor -eq 0){$taskReachedRoot=$true' not in text
 assert 'if($taskCursor -eq $taskProof.scheduler_engine_pid)' in text
 with patch.object(fixture,'p',p):
  b=sample(p.OBSERVE);assert p.summarize(b,'windows',p.OBSERVE)['independent_callback_execution_verified']
  b['data']['scheduler_instance_verified']=False
  try:p.summarize(b,'windows',p.OBSERVE)
  except ValueError as e:assert str(e)=='scheduler_engine_unverified_success'
  else:raise AssertionError('missing instance accepted')
  b=sample(p.OBSERVE);b['data']['scheduler_engine_pid']=b['data']['service_pid']
  try:p.summarize(b,'windows',p.OBSERVE)
  except ValueError as e:assert str(e)=='scheduler_instance_identity'
  else:raise AssertionError('agent as scheduler engine accepted')
 p.CALLBACK=old.CALLBACK;p.REGISTER_BODY=old.REGISTER_BODY
 with patch.object(fixture,'p',p),patch.object(fixture,'sample',sample):fixture.main()
 print('PASS native running-instance anchor/negative PID0/agent/instance/own Core/no replay; no OS actions')
if __name__=='__main__':main()

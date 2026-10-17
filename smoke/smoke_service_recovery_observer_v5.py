"""No OS changes. Own antecedent, retired writers and unchanged dry scope."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import endpoint_metadata as ep,service_recovery_observer_v5 as p,service_recovery_diagnostic as d
from smoke.smoke_service_recovery_dry_run import sample
import service_recovery_dry_run as old

def main():
 code=p.code('windows',p.PROFILE)
 assert 'Register-ScheduledTask' not in code and 'Stop-Service' not in code and 'Restart-Service' not in code
 assert 'Translate([Security.Principal.SecurityIdentifier]).Value' in code
 assert "-ceq 'S-1-5-18'" in code
 assert p.ARGUMENT_SHA=='7162fc6ee1aecb1b458a35eb95a5aa9f2cfac759164bdffba46762f24c2eedbd'
 assert p.summarize(sample(old.OBSERVE),'windows',p.PROFILE)['independent_callback_execution_verified'] is True
 b=sample(old.OBSERVE);b['data'].update(started_at='2026-10-17T00:00:00.1234567+00:00',finished_at='2026-10-17T00:01:00.1234567+00:00')
 assert p.summarize(b,'windows',p.PROFILE)['independent_callback_execution_verified'] is True
 b['data']['finished_at']='2026-10-17T00:01:00.1234568+00:00'
 try:p.summarize(b,'windows',p.PROFILE)
 except ValueError as e:assert str(e)=='recovery_time'
 else:raise AssertionError('60s plus100ns accepted')
 b=sample(old.OBSERVE);b['data']['outside_agent_tree']=False
 assert not p.summarize(b,'windows',p.PROFILE)['independent_callback_execution_verified']
 for profile in ep.RETIRED_RECOVERY_PROFILES:
  r=ep.requirement('windows','retired-safety-test',profile)
  request=' '.join(r[k] for k in ['ci_id','agent_id','ci_name','profile_id','core_version'])
  job={'stand':'lab','job_type':'manual','status':'running','request':request,'test_cases':[{'case_id':'fixture','status':'running','requirement':r}]}
  try:ep.admit(job,'fixture',{'target':'windows'})
  except ValueError as e:assert str(e)=='dry_recovery_attempt_retired_history_only_no_new_command'
  else:raise AssertionError('retired attempt admitted')
 assert p.PROFILE not in ep.RETIRED_RECOVERY_PROFILES and d.PROFILE in ep.RETIRED_RECOVERY_PROFILES
 print('PASS own SID observer scope/negative independence/retired historical writers; no OS execution')

if __name__=='__main__':main()

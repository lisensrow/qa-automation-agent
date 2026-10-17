"""Exact scope/pagination/own-proof refusal tests; no product HTTP or writes."""
from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import patch
import software_change_review as p
from software_change_fixture import PACKAGE,VERSION

def main():
 r=p.requirement('fixture-review',['source','case'],['install','case'],['audit','case'])
 c={'case_id':'case','status':'running','requirement':r,'evidence':[]}
 j={'stand':'lab','job_type':'manual','status':'running','resources':[],
    'request':' '.join(r[k] for k in ['ci_id','agent_id','package']),'test_cases':[c]}
 assert p.validate(j,'case',{'phase':'before'})[1]==r
 for field,value in [('locked',False),('package','existing-package'),('action_profile','write_resource'),('artifact_sha256','0'*64),('ci_id','other')]:
  bad=deepcopy(j);bad['test_cases'][0]['requirement'][field]=value
  try:p.validate(bad,'case',{'phase':'before'});raise AssertionError('forged scope')
  except ValueError:pass
 session=SimpleNamespace(_same_https_origin_url=lambda observed,path:'https://uc.lab.local'+path)
 row={'id':'new-software','name':None,'detail':{'name':PACKAGE,'version':VERSION},
      'detected_at_id':r['agent_id'],'parent_id':r['ci_id'],'ci_class':'software','is_archived':False}
 ctx=(None,None,['https://uc.lab.local/api/v1/agents/'+r['agent_id']+'/tasks'])
 with patch.object(p,'context',return_value=ctx),patch.object(p,'read_json',return_value={'items':[row],'total':1,'offset':0}):
  found=p._read_software(session,r['ci_id'],r['agent_id'])
  assert found['matches']==[row] and not found['fixture_absence_proved']
  # A null display name is not absence; a nested software match must be seen.
  assert found['matches'][0]['detail']['version']==VERSION
  for broken in [{'items':[row],'total':2,'offset':0},{'items':[row,row],'total':2,'offset':0},{'items':[row],'total':None}]:
   with patch.object(p,'read_json',return_value=broken):
    try:p._read_software(session,r['ci_id'],r['agent_id']);raise AssertionError('invalid pagination')
    except ValueError:pass
 import uqa
 from tools.registry import execute_tool
 assert execute_tool(p.TOOL,{'phase':'before'})=={'error':'trusted_Core_job_case_context_required','executed':False}
 assert uqa.classify_tool_action(p.TOOL,{'phase':'before'})=='observe'
 out=uqa.execute_tool_with_policy(p.TOOL,{'phase':'before'},[],force_read_only=True,action_policy='confirm_mutations')
 assert out.get('error')=='locked_software_change_review_required' and not out.get('executed')
 print('software change review: PASS (locked scope, nested name, exact pagination, contextless Core refusal; fixture only)')

if __name__=='__main__':main()

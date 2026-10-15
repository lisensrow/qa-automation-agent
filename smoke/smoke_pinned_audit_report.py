"""Reporting trusts same-case native records, not model prose/status/IDs."""
import json
from tools.agent_update import build_pinned_audit_report
from uqa import classify_tool_action
expected={'host_name':'host','machine_uid':'ci','os':{'architecture':'64','current_build_os':'1','family':'windows','name':'windows','version':'edition'}}
actual={'task_id':'task','agent_id':'agent','task_name':'osAudit','native_result_verified':True,'host_name':'host','machine_uid':'ci',
        'os_subset':{**expected['os'],'name':'Windows 10 Pro'}}
def evidence(tool,result,eid,source='uqa_tool'):
    return {'source':source,'execution_status':'observed','evidence_id':eid,'observation_ids':['real-observation'],
            'value':json.dumps({'tool':tool,'result':result})}
receipt=evidence('browser_create_pinned_agent_audit_semantic',{'task_id':'task','agent_id':'agent','task_name':'osAudit','mutation_executed':True},'native-create')
read=evidence('browser_inspect_pinned_agent_audit_semantic',actual,'native-read')
case={'case_id':'case','requirement':{'locked':True,'pinned_audit_task':{'task_name':'osAudit','ci_name':'host','agent_id':'agent'},
    'expected_subset':expected},'evidence':[receipt,read]}
job={'job_id':'job','test_cases':[case]}
report=build_pinned_audit_report(job,'case','task')
assert report['verdict']=='BLOCKED' and report['source_evidence_ids']==['native-create','native-read']
assert report['observation_ids']==['real-observation'] and report['zephyr_written'] is False
assert 'Вердикт: BLOCKED' in report['report_markdown'] and 'Task ID: task' in report['report_markdown']
assert report['rows'][-2]['status']=='BLOCKED'
assert build_pinned_audit_report(job,'case','other').get('error')
assert build_pinned_audit_report(job,'other','task').get('error')
case['evidence']=[receipt,{**read,'source':'local_model_generated_report'}]
assert build_pinned_audit_report(job,'case','task').get('error')
case['evidence']=[read]
assert build_pinned_audit_report(job,'case','task').get('error')
assert classify_tool_action('agent_build_pinned_audit_report',{})=='interact'
print('pinned_audit_report: PASS (fixture only; no invented evidence or verdict)')

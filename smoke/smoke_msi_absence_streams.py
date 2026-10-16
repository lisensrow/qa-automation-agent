"""Read-only follow-up/CLIXML semantics; fixtures, no MSI or endpoint action."""
from copy import deepcopy
import base64
import powershell_streams as s,windows_legacy_msi as m,endpoint_metadata as p,uqa
from endpoint_metadata_runtime import catalog
from tools.registry import execute_tool
ns=s.NS
progress='#< CLIXML\r\n<Objs Version="1.1.0.1" xmlns="'+ns+'"><Obj S="progress"><MS><PR>fixture</PR></MS></Obj></Objs>'
assert s.inspect_stderr(progress)=={'kind':'progress_only','progress_records':1}
assert s.inspect_stderr('')['kind']=='empty'
for bad in [progress.replace('S="progress"','S="error"'),progress.replace('S="progress"','S="warning"'),
 progress.replace('S="progress"',''),progress+'junk',progress.replace(ns,'unknown'),
 progress.replace('<Obj S="progress">','<Obj S="progress"><S S="error">error</S>'),
 '#< CLIXML <!DOCTYPE x><Objs/>','plain error',progress*1000]:
 assert s.inspect_stderr(bad)['kind'] not in {'empty','progress_only'}
body={'profile':m.POST_PROFILE,'product_code':m.PRODUCT,'registry_absent':True,'legacy_service_absent':True,
 'legacy_process_absent':True,'uninstall_performed':False,'error':''}
assert m.summarize_absence(body)['absence_status']=='PASS'
assert not m.summarize_absence(body)['original_uninstall_cycle_completed']
for k,v in [('registry_absent',False),('legacy_service_absent',False),('legacy_process_absent',False),('error','denied')]:
 assert m.summarize_absence({**body,k:v})['absence_status']=='BLOCKED'
for bad in [{**body,'uninstall_performed':True},{**body,'registry_absent':1},{**body,'product_code':'other'}]:
 try:m.summarize_absence(bad)
 except ValueError:pass
 else:raise AssertionError('Invalid absence body accepted')
code=base64.b64decode(m.POST_PAYLOAD['additional_params']['arguments'][-1]).decode('utf-16le')
assert code==m.POST_CODE
assert not any(x in code.lower() for x in ['msiexec','start-process','remove-item','restart-computer','stop-process','executionpolicy','writeall'])
assert "$ProgressPreference='SilentlyContinue'" in code
r=p.requirement('windows','fixture-absence',m.POST_PROFILE)
assert r['action_profile']=='write_resource' and r['operation_stages'][0]['tool']==p.CREATE
assert uqa.classify_tool_action(p.CREATE,{})=='write' and uqa.classify_tool_action(m.REMOVE,{})=='destructive'
assert catalog([],r)[0]['function']['parameters']['properties']['query']['enum']==[m.POST_PROFILE]
assert not execute_tool(p.CREATE,{'target':'windows'}).get('executed')
try:p.requirement('astra','fixture-absence',m.POST_PROFILE)
except ValueError:pass
else:raise AssertionError('Wrong OS admitted')
assert p.requirement('windows','fixture-msi',m.PROFILE)['operation_stages'][0]['tool']==m.REMOVE
print('PASS read-only exact absence separate from original cycle, CLIXML progress only/error denial, old payload preserved; fixture only')

"""Pure identity fixture: never scans a host or grants uninstall authority."""
from copy import deepcopy
from unittest.mock import patch
from types import SimpleNamespace
import ast
import legacy_vnc_identity as p
import endpoint_metadata as e

ast.parse(p.CODE)
empty={'probe_version':1,'packages':[],'processes':[],'package_query_complete':True,
 'process_scan_complete':True,'uninstall_executed':False}
assert not p.summarize(empty)['legacy_absence_proved']
b=deepcopy(empty);b['packages']=[{'name':'tightvncserver','version':'1.3.10','status':'installed'}]
assert p.summarize(b)['legacy_standalone_package_observed']
assert not p.summarize(b)['uninstall_authorized_by_probe']
b['packages'][0]['name']='tightvnc-java';assert not p.summarize(b)['legacy_standalone_package_observed']
b=deepcopy(empty);b['processes']=[{'name':'Xtightvnc','executable':'/opt/usystem/usagent/bin/Xtightvnc',
 'package_owner':None,'plugin_path':True}]
assert not p.summarize(b)['legacy_standalone_package_observed']
for change in [{'uninstall_executed':True},{'package_query_complete':'yes'},{'unexpected':True},
 {'packages':[{'name':'other','version':'1','status':'installed'}]},
 {'processes':[{**b['processes'][0],'plugin_path':False}]}]:
 try:p.summarize({**empty,**change})
 except (ValueError,TypeError,KeyError):pass
 else:raise AssertionError('unsafe identity accepted')
# Execute fixed probe only with every host access mocked.
fake=SimpleNamespace(run=lambda argv,**kw:SimpleNamespace(returncode=0,stdout='tightvncserver\t1.3\tinstalled\n'))
outputs=[]
with patch.dict('sys.modules',{'subprocess':fake}),patch('os.listdir',return_value=[]),patch('builtins.print',outputs.append):
 exec(p.CODE,{})
import json
assert p.summarize(json.loads(outputs[0]))['legacy_standalone_package_observed']
for name in ['windows','astra']:
 old=e.requirement(name,'fixture');new=e.requirement(name,'fixture',p.PROFILE)
 assert old['profile_id']==e.PROFILE and new['payload_sha256']==p.SHA
 assert new['operation_stages'][0]['workflow_id']==p.PROFILE
 assert old['operation_stages']!=new['operation_stages']
 assert new['expected_profile']['uninstall_executed'] is False
try:e.requirement('astra','fixture','arbitrary-shell')
except ValueError:pass
else:raise AssertionError('unknown profile')
assert not any(s in p.CODE for s in ['shell=True','os.remove','unlink(','apt-get','dpkg --remove','chmod('])
print('PASS legacy identity closed argv/package ownership/plugin separation/unknown absence/no uninstall; fixture only')

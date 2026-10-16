"""Native softAudit projection only; no new payload or removal authority."""
from plugin_audit_profiles import summarize
rows=[{'name':'TightVNC 2.8','version':'2.8','exePath':'C:\\Program Files\\TightVNC',
 'uninstallString':'private unrelated command'}, {'name':'another program','version':'private'}]
s=summarize('softAudit',rows)['legacy_vnc_software_observation']
assert len(s['matches'])==1 and set(s['matches'][0])=={'name','version','exePath'}
assert not s['package_ownership_verified'] and not s['absence_proved'] and not s['uninstall_authorized']
assert summarize('softAudit',[])['legacy_vnc_software_observation']['matches']==[]
assert summarize('softAudit',None)['legacy_vnc_software_observation']['matches']==[]
assert not summarize('softAudit',[{}]*10001)['legacy_vnc_software_observation']['bounded']
assert 'legacy_vnc_software_observation' not in summarize('serviceAudit',[])
guid='{11111111-2222-3333-4444-555555555555}'
for switch in ['/I','/X']:
 x={'name':'TightVNC','version':'2.8','uninstallString':'MsiExec.exe '+switch+guid}
 m=summarize('softAudit',[x])['legacy_vnc_software_observation']['matches'][0]
 assert m['msi_metadata']['product_code']==guid and m['msi_metadata']['observed_switch']==switch
 assert not m['msi_metadata']['uninstall_executed'] and not m['msi_metadata']['raw_command_disclosed']
for raw in ['cmd.exe /c remove', 'MsiExec.exe /I'+guid+' & arbitrary','MsiExec.exe /I{invalid}',
 'MsiExec.exe /I'+guid+' /password secret','https://uninstaller.invalid']:
 m=summarize('softAudit',[{'name':'TightVNC','uninstallString':raw}])['legacy_vnc_software_observation']['matches'][0]
 assert 'msi_metadata' not in m and 'uninstallString' not in m
print('PASS legacy software TightVNC-only projection, no unrelated inventory/uninstall string/absence authority')

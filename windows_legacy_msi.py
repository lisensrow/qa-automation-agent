"""One human-authorized legacy TightVNC MSI identity, no arbitrary uninstall.

Fixed PowerShell, no execution-policy bypass, registry command execution, manual
file deletion, plugin removal or reboot. Agent-side fresh identity preflight is
mandatory immediately before MSI. Independent postconditions remain required.
"""
import base64,hashlib
PROFILE='windows-legacy-tightvnc-msi-v1'
REMOVE='browser_remove_exact_legacy_msi_semantic'
PRODUCT='{78CA3586-0715-4862-B091-200565E3BC87}'
VERSION='2.8.85.0'
PROGRAM=r'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe'
CODE=r"""$ErrorActionPreference='Stop'
$g='{78CA3586-0715-4862-B091-200565E3BC87}'
$roots=@('HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\','HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\')
$o=[ordered]@{profile='windows-legacy-tightvnc-msi-v1';product_code=$g;expected_version='2.8.85.0';identity_verified=$false;uninstall_started=$false;msi_exit_code=$null;registry_absent=$false;legacy_service_absent=$false;legacy_process_absent=$false;reboot_required=$false;error=''}
try {
 if (-not [Environment]::Is64BitOperatingSystem) {throw 'architecture_preflight'}
 $keys=@($roots | ForEach-Object {if(Test-Path -LiteralPath ($_+$g)){Get-ItemProperty -LiteralPath ($_+$g)}})
 if ($keys.Count -ne 1) {throw 'exact_installed_product_required'}
 $k=$keys[0]
 if ($k.DisplayName -cne 'TightVNC' -or $k.DisplayVersion -cne '2.8.85.0' -or $k.WindowsInstaller -ne 1) {throw 'msi_identity_mismatch'}
 $u=[string]$k.UninstallString
 if ($u -notmatch ('(?i)^\s*"?msiexec(?:\.exe)?"?\s+/[ix]\s*'+[regex]::Escape($g)+'\s*$')) {throw 'msi_registration_mismatch'}
 $services=@(Get-CimInstance -ClassName Win32_Service -Filter "Name='tvnserver'")
 foreach($s in $services){if([string]$s.PathName -notmatch '(?i)\\TightVNC\\tvnserver\.exe(?:"|\s|$)'){throw 'service_ownership_unknown'}}
 $o.identity_verified=$true
 $o.uninstall_started=$true
 $p=Start-Process -FilePath 'C:\Windows\System32\msiexec.exe' -ArgumentList @('/x',$g,'/qn','/norestart') -WindowStyle Hidden -PassThru -Wait
 $o.msi_exit_code=[int]$p.ExitCode
 $o.reboot_required=($p.ExitCode -eq 3010 -or $p.ExitCode -eq 1641)
 $remaining=@($roots | Where-Object {Test-Path -LiteralPath ($_+$g)})
 $o.registry_absent=($remaining.Count -eq 0)
 $o.legacy_service_absent=(@(Get-CimInstance -ClassName Win32_Service -Filter "Name='tvnserver'").Count -eq 0)
 $processes=@(Get-CimInstance -ClassName Win32_Process -Filter "Name='tvnserver.exe'")
 $legacy=@($processes | Where-Object {[string]$_.ExecutablePath -match '(?i)\\TightVNC\\tvnserver\.exe$'})
 if (@($processes | Where-Object {[string]::IsNullOrWhiteSpace($_.ExecutablePath)}).Count -gt 0){throw 'process_ownership_unknown'}
 $o.legacy_process_absent=($legacy.Count -eq 0)
} catch {
 $known=@('architecture_preflight','exact_installed_product_required','msi_identity_mismatch','msi_registration_mismatch','service_ownership_unknown','process_ownership_unknown')
 $o.error=if($known -contains $_.Exception.Message){$_.Exception.Message}else{'native_msi_preflight_or_postcheck_error'}
}
$o | ConvertTo-Json -Compress
"""
SHA=hashlib.sha256(CODE.encode()).hexdigest()
PAYLOAD={'name':'executeCommand','period':None,'ttl':None,'run_as_user':'',
 'additional_params':{'programm':PROGRAM,'arguments':['-NoLogo','-NoProfile','-NonInteractive','-EncodedCommand',base64.b64encode(CODE.encode('utf-16le')).decode()]}}
KEYS={'profile','product_code','expected_version','identity_verified','uninstall_started','msi_exit_code',
 'registry_absent','legacy_service_absent','legacy_process_absent','reboot_required','error'}
def summarize(body):
 if not isinstance(body,dict) or set(body)!=KEYS or body['profile']!=PROFILE or body['product_code']!=PRODUCT or body['expected_version']!=VERSION:
  raise ValueError('exact_legacy_msi_result_required')
 for k in ['identity_verified','uninstall_started','registry_absent','legacy_service_absent','legacy_process_absent','reboot_required']:
  if type(body[k]) is not bool:raise ValueError('msi_boolean_required')
 if body['msi_exit_code'] is not None and type(body['msi_exit_code']) is not int:raise ValueError('msi_exit_code_required')
 if not isinstance(body['error'],str) or len(body['error'])>100:raise ValueError('msi_error_shape')
 passed=(body['identity_verified'] and body['uninstall_started'] and body['msi_exit_code']==0
  and body['registry_absent'] and body['legacy_service_absent'] and body['legacy_process_absent']
  and not body['reboot_required'] and not body['error'])
 return {**body,'removal_status':'PASS' if passed else 'BLOCKED','removal_postconditions_verified':bool(passed),
  'reboot_performed_by_uqa':False,'arbitrary_uninstall_allowed':False,'plugin_deletion_performed':False,
  'full_source_case_passed':False,'desktop_verified':False}

# A separate read-only follow-up, never an MSI retry or changed old payload.
POST_PROFILE='windows-legacy-tightvnc-absence-v1'
POST_CODE=r"""$ErrorActionPreference='Stop'
$ProgressPreference='SilentlyContinue'
$g='{78CA3586-0715-4862-B091-200565E3BC87}'
$o=[ordered]@{profile='windows-legacy-tightvnc-absence-v1';product_code=$g;registry_absent=$false;legacy_service_absent=$false;legacy_process_absent=$false;uninstall_performed=$false;error=''}
try {
 if(-not [Environment]::Is64BitOperatingSystem){throw 'architecture_preflight'}
 $roots=@('HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\','HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\')
 $o.registry_absent=(@($roots | Where-Object {Test-Path -LiteralPath ($_+$g)}).Count -eq 0)
 $o.legacy_service_absent=(@(Get-CimInstance -ClassName Win32_Service -Filter "Name='tvnserver'").Count -eq 0)
 $p=@(Get-CimInstance -ClassName Win32_Process -Filter "Name='tvnserver.exe'")
 if(@($p | Where-Object {[string]::IsNullOrWhiteSpace($_.ExecutablePath)}).Count -gt 0){throw 'process_ownership_unknown'}
 $o.legacy_process_absent=(@($p | Where-Object {[string]$_.ExecutablePath -match '(?i)\\TightVNC\\tvnserver\.exe$'}).Count -eq 0)
} catch { $o.error='native_absence_check_incomplete' }
$o | ConvertTo-Json -Compress
"""
POST_SHA=hashlib.sha256(POST_CODE.encode()).hexdigest()
POST_PAYLOAD={'name':'executeCommand','period':None,'ttl':None,'run_as_user':'',
 'additional_params':{'programm':PROGRAM,'arguments':['-NoLogo','-NoProfile','-NonInteractive','-EncodedCommand',base64.b64encode(POST_CODE.encode('utf-16le')).decode()]}}
def summarize_absence(body):
 keys={'profile','product_code','registry_absent','legacy_service_absent','legacy_process_absent','uninstall_performed','error'}
 if not isinstance(body,dict) or set(body)!=keys or body['profile']!=POST_PROFILE or body['product_code']!=PRODUCT:
  raise ValueError('exact_legacy_absence_result_required')
 for k in ['registry_absent','legacy_service_absent','legacy_process_absent','uninstall_performed']:
  if type(body[k]) is not bool:raise ValueError('absence_boolean_required')
 if body['uninstall_performed'] or not isinstance(body['error'],str) or len(body['error'])>100:raise ValueError('read_only_absence_required')
 passed=all(body[k] for k in ['registry_absent','legacy_service_absent','legacy_process_absent']) and not body['error']
 return {**body,'absence_status':'PASS' if passed else 'BLOCKED','full_source_case_passed':False,
  'original_uninstall_cycle_completed':False,'reboot_performed_by_uqa':False}

param([Parameter(Mandatory=$true)][string]$Python)
$ErrorActionPreference='Stop'
$taskRepoRoot=Split-Path $PSScriptRoot -Parent
$taskPrograms=& $Python -c "import sys,json,base64;sys.path.insert(0,sys.argv[1]);import agent_log_presence as a,windows_agent_log_presence_v2 as b;print(json.dumps([base64.b64encode(x.encode()).decode() for x in [a.WINDOWS,b.WINDOWS]]))" $taskRepoRoot
if($LASTEXITCODE -ne 0){throw 'probe_import'}
$taskPrograms=ConvertFrom-Json $taskPrograms
# Pure mocks in this PowerShell process. No guest or local service/files touched.
function Get-CimInstance {
 param($ClassName,$Filter)
 [pscustomobject]@{PathName=('"'+$env:ProgramFiles+'\USystem\agentServer\bin\usAgent.exe"')}
}
function Get-Item {
 param($LiteralPath,[switch]$Force)
 $taskExpected=Join-Path $env:ProgramFiles 'USystem\agentServer\var\log\usagent'
 if($LiteralPath -ine $taskExpected){throw 'fixture_wrong_log_root'}
 [pscustomobject]@{PSIsContainer=$true;Attributes=[IO.FileAttributes]::Directory;Parent=$null}
}
function Get-ChildItem {
 param($LiteralPath,[switch]$Force)
 [pscustomobject]@{PSIsContainer=$false;Attributes=[IO.FileAttributes]::Archive;Name='usagent.log';Length=42;LastWriteTimeUtc=[DateTime]::UtcNow}
}
$taskOutputs=@()
foreach($taskEncoded in $taskPrograms){
 $taskCode=[Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($taskEncoded))
 $taskOutputs+=(& ([scriptblock]::Create($taskCode)) | ConvertFrom-Json)
}
if($taskOutputs[0].query_complete -or $taskOutputs[0].error -ne 'log_metadata_unavailable'){throw 'v1_wrong_root_not_reproduced'}
if(-not $taskOutputs[1].query_complete -or $taskOutputs[1].files.Count -ne 1 -or $taskOutputs[1].files[0].size -ne 42){throw 'v2_source_root_not_verified'}
'PASS mocked Windows probe execution: original bin/var/log fails, corrected product/var/log succeeds; no real OS mutation'

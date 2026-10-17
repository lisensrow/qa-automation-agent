param([Parameter(Mandatory=$true)][string]$Python)
$ErrorActionPreference='Stop'
$taskRepo=Split-Path $PSScriptRoot -Parent
$taskEncoded=& $Python -c "import sys,base64;sys.path.insert(0,sys.argv[1]);import service_recovery_dry_run as p;print(base64.b64encode(p.COMMON.split(chr(36)+'taskOut=@')[0].replace('__ENCODED__',p.ENCODED).encode()).decode())" $taskRepo
if($LASTEXITCODE -ne 0){throw 'import_failed'}
# Only variable/function declarations, no scheduling, service call or file I/O.
$taskPrefix=[Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($taskEncoded))
. ([scriptblock]::Create($taskPrefix))
$taskFake=[pscustomobject]@{TaskName=$taskName;TaskPath='\';Actions=@([pscustomobject]@{Execute=$taskProgram;Arguments=$taskArgs});Triggers=@([pscustomobject]@{});Principal=[pscustomobject]@{UserId='SYSTEM';LogonType='ServiceAccount';RunLevel='Limited'}}
if(-not (Exact-Task $taskFake)){throw 'correct_definition_rejected'}
$taskFake.Principal.UserId='Administrator'
if(Exact-Task $taskFake){throw 'wrong_identity_accepted'}
$taskFake.Principal.UserId='SYSTEM';$taskFake.Actions[0].Arguments+=' extra'
if(Exact-Task $taskFake){throw 'wrong_action_accepted'}
'PASS dry scheduled-task definition guards in real PowerShell; no task/service/file changes'

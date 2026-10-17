"""Real cmd bootstrap: exact decoded hash + parse, never invoke scheduler script."""
import sys,subprocess
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import service_recovery_observer_v5 as p
for profile in p.PROFILES:
 check="$t=$null;$e=$null;if(-not $s){exit 3};[void][Management.Automation.Language.Parser]::ParseInput($s,[ref]$t,[ref]$e);if($e.Count){exit 2};$h=[BitConverter]::ToString([Security.Cryptography.SHA256]::Create().ComputeHash([Text.Encoding]::UTF8.GetBytes($s))).Replace('-','').ToLower();Write-Output $h"
 text=p.wrapper('windows',profile).replace('([ScriptBlock]::Create($s)).Invoke()',check)
 assert check in text
 line='C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\powershell.exe -NoLogo -NoProfile -NonInteractive -Command '+text
 assert len(line)<8000
 result=subprocess.run(['cmd.exe','/d','/s','/c',line],capture_output=True,text=True,timeout=30)
 assert result.returncode==0 and result.stderr=='' and result.stdout.strip()==p.sha('windows',profile),(result.returncode,result.stdout,result.stderr)
 print(profile,len(line),'exact SHA256 roundtrip + real cmd/decompress/parse PASS; no scheduler invoked')

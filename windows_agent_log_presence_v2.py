"""Source-root correction; immutable v1 commands and receipts remain untouched."""
import hashlib,base64
import agent_log_presence as old
PROFILE='owned-windows-agent-log-presence-source-root-v2'
OLD_ROOT="$root=Join-Path ([IO.Path]::GetDirectoryName($exe)) 'var\\log\\usagent'"
NEW_ROOT=r'''$bin=[IO.Path]::GetDirectoryName($exe)
 if([IO.Path]::GetFileName($bin) -ine 'bin'){throw 'binary_directory'}
 $product=[IO.Path]::GetDirectoryName($bin)
 $expected=@()
 foreach($prefix in @($env:ProgramFiles,${env:ProgramFiles(x86)})){
  if($prefix){$expected+=([IO.Path]::GetFullPath((Join-Path $prefix 'USystem\agentServer'))).TrimEnd('\')}
 }
 if($product.TrimEnd('\') -notin $expected){throw 'source_product_root'}
 $root=Join-Path $product 'var\log\usagent' '''
assert old.WINDOWS.count(OLD_ROOT)==1
WINDOWS=old.WINDOWS.replace(OLD_ROOT,NEW_ROOT)
LIMITS=old.LIMITS

def code(name):
 if name!='windows':raise ValueError('source_root_probe_windows_only')
 return WINDOWS

def sha(name):return hashlib.sha256(code(name).encode()).hexdigest()

def payload(name):
 text=code(name)
 return {'name':'executeCommand','period':None,'ttl':None,'run_as_user':'',
  'additional_params':{'programm':r'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe',
   'arguments':['-NoLogo','-NoProfile','-NonInteractive','-EncodedCommand',base64.b64encode(text.encode('utf-16-le')).decode()]}}

def summarize(obj,name):
 code(name)
 return old.summarize(obj,name)

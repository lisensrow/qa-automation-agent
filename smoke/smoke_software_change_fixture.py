"""No host installation: immutable archive, strict output, Core scope/no replay."""
import gzip,io,json,tarfile
from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import patch
import software_change_fixture as p

def main():
 raw=p.artifact();assert raw==p.artifact() and len(raw)<16384 and raw.startswith(b'!<arch>\n')
 offset=8;files={}
 while offset<len(raw):
  h=raw[offset:offset+60];n=int(h[48:58]);name=h[:16].decode().strip().rstrip('/')
  files[name]=raw[offset+60:offset+60+n];offset+=60+n+n%2
 assert set(files)=={'debian-binary','control.tar.gz','data.tar.gz'} and files['debian-binary']==b'2.0\n'
 with tarfile.open(fileobj=io.BytesIO(gzip.decompress(files['control.tar.gz']))) as t:
  assert t.getnames()==['./control'];control=t.extractfile('./control').read().decode()
  assert 'Depends:' not in control and 'Triggers:' not in control and p.PACKAGE in control
 with tarfile.open(fileobj=io.BytesIO(gzip.decompress(files['data.tar.gz']))) as t:
  assert t.getnames()==['.'+p.PREFIX+'/probe'];m=t.getmembers()[0]
  assert m.isfile() and m.mode==0o755 and t.extractfile(m).read()==p.PROBE
 assert 'apt ' not in p.CODE and 'dnf ' not in p.CODE and '--force' not in p.CODE
 compile(p.CODE,'fixed-owned-install','exec')
 b={'probe_version':1,'package':p.PACKAGE,'version':p.VERSION,'artifact_sha256':p.ARTIFACT_SHA,
    'absent_before':True,'install_attempted':True,'installed_after':True,'probe_output_matches':True,'dpkg_exit':0,'error':None}
 assert p.summarize(b)['fixture_install_verified'] and not p.summarize(b)['full_case_passed']
 for key in ['absent_before','installed_after','probe_output_matches']:
  bad=deepcopy(b);bad[key]=False;assert not p.summarize(bad)['fixture_install_verified']
 bad=dict(b,probe_version=True)
 try:p.summarize(bad);raise AssertionError('boolean version')
 except ValueError:pass
 failed=dict(b,absent_before=False,install_attempted=False,installed_after=False,probe_output_matches=False,dpkg_exit=None,error='package_must_be_absent_no_reinstall')
 assert p.summarize(failed)['observation_status']=='BLOCKED' and not p.summarize(failed)['fixture_install_verified']
 wrong=dict(b,package='other-package')
 try:p.summarize(wrong);raise AssertionError('wrong identity')
 except ValueError:pass
 # A pre-existing package or non-root agent must never open a path or call dpkg install.
 outputs=[]
 with patch('os.geteuid',return_value=0,create=True),patch('subprocess.run',return_value=SimpleNamespace(returncode=0,stdout='installed\t0.0.1\n',stderr='')) as run,patch('os.open',side_effect=AssertionError('must not write')),patch('builtins.print',side_effect=outputs.append):
  exec(compile(p.CODE,'owned-install','exec'),{})
 assert len(run.call_args_list)==1 and json.loads(outputs[0])['install_attempted'] is False
 import endpoint_metadata as em
 r=em.requirement('astra','test-owned-software-change',p.PROFILE)
 assert r['action_profile']=='write_resource' and r['payload_sha256']==p.SHA
 try:em.requirement('windows','test-owned-software-change',p.PROFILE);raise AssertionError('wrong OS')
 except ValueError:pass
 import smoke_drive_os_baseline as fixture
 # Existing Core fixture exercises policy, journal, own full and durable no-rekey guard.
 retired_case={'case_id':'retired','status':'running','requirement':r,'evidence':[]}
 retired_job={'test_cases':[retired_case],'stand':'lab','status':'running','job_type':'manual','resources':[],
  'request':' '.join(r[k] for k in ['ci_id','agent_id','ci_name','profile_id','core_version'])}
 try:em.admit(retired_job,'retired',{'target':'astra'});raise AssertionError('retired fixture dispatched')
 except ValueError as exc:assert str(exc)=='fixture_v1_retired_history_only_use_v2'
 import software_change_fixture_v2 as v2
 vraw=v2.artifact();voffset=8;vfiles={}
 while voffset<len(vraw):
  h=vraw[voffset:voffset+60];n=int(h[48:58]);vfiles[h[:16].decode().strip().rstrip('/')]=vraw[voffset+60:voffset+60+n];voffset+=60+n+n%2
 with tarfile.open(fileobj=io.BytesIO(gzip.decompress(vfiles['data.tar.gz']))) as t:
  assert t.getnames()==['.'+v2.PREFIX,'.'+v2.PREFIX+'/probe']
  assert t.getmembers()[0].isdir() and t.getmembers()[0].mode==0o755
  assert t.getmembers()[1].isfile() and t.extractfile(t.getmembers()[1]).read()==v2.PROBE
 vb=dict(b,package=v2.PACKAGE,artifact_sha256=v2.ARTIFACT_SHA)
 assert v2.summarize(vb)['fixture_install_verified']
 bad=dict(vb,installed_after=False);assert not v2.summarize(bad)['fixture_install_verified']
 proxy2=SimpleNamespace(PROFILE=v2.PROFILE,payload=lambda name:v2.PAYLOAD,sha=lambda name:v2.SHA)
 with patch.object(fixture,'p',proxy2):fixture.core_fixture('astra',vb,lambda s:(_ for _ in ()).throw(AssertionError('not complete')) if not s['fixture_install_verified'] else None)
 print('software change fixture: PASS (archive/no scripts, exact additive scope, Core/policy/own full/no replay; no host install)')

if __name__=='__main__':main()

"""Corrected NEW owned fixture; never replays/reinstalls the failed v1 object.

The v1 payload/hash stays immutable. Directory records are required by dpkg;
only the NEW owned prefix is in the archive, not the existing /opt parent.
"""
import base64,gzip,hashlib,io,tarfile
import software_change_fixture as old
PROFILE='owned-astra-software-change-20261017-v2'
PACKAGE=old.PACKAGE+'-v2'
VERSION=old.VERSION
PREFIX='/opt/'+PACKAGE
STAGING='/var/tmp/'+PACKAGE+'.deb'
MARKER=old.MARKER
PROBE=old.PROBE

def artifact():
 raw=old.artifact();offset=8;members={}
 while offset<len(raw):
  h=raw[offset:offset+60];n=int(h[48:58]);name=h[:16].decode().strip().rstrip('/')
  members[name]=raw[offset+60:offset+60+n];offset+=60+n+n%2
 with tarfile.open(fileobj=io.BytesIO(gzip.decompress(members['control.tar.gz']))) as t:
  control=t.extractfile('./control').read().replace(old.PACKAGE.encode(),PACKAGE.encode())
 data=io.BytesIO()
 with tarfile.open(fileobj=data,mode='w',format=tarfile.USTAR_FORMAT) as t:
  directory=tarfile.TarInfo('.'+PREFIX);directory.type=tarfile.DIRTYPE
  directory.mode=0o755;directory.uid=directory.gid=directory.mtime=0
  t.addfile(directory)
  f=tarfile.TarInfo('.'+PREFIX+'/probe');f.mode=0o755;f.size=len(PROBE);f.uid=f.gid=f.mtime=0
  t.addfile(f,io.BytesIO(PROBE))
 out=b'!<arch>\n'
 for name,body in [('debian-binary',b'2.0\n'),('control.tar.gz',old._tar([('./control',control,0o644)])),('data.tar.gz',gzip.compress(data.getvalue(),mtime=0))]:
  header=(name+'/').ljust(16)+'0'.ljust(12)+'0'.ljust(6)+'0'.ljust(6)+'100644'.ljust(8)+str(len(body)).ljust(10)+'`\n'
  assert len(header)==60
  out+=header.encode()+body+(b'\n' if len(body)%2 else b'')
 return out

ARTIFACT_SHA=hashlib.sha256(artifact()).hexdigest()
CODE=(old.CODE.replace(base64.b64encode(old.artifact()).decode(),base64.b64encode(artifact()).decode())
 .replace(old.ARTIFACT_SHA,ARTIFACT_SHA).replace(old.PACKAGE,PACKAGE))
SHA=hashlib.sha256(CODE.encode()).hexdigest()
PAYLOAD={'name':'executeCommand','period':None,'ttl':None,'run_as_user':'',
 'additional_params':{'programm':'/usr/bin/python3','arguments':['-c',CODE]}}

def summarize(raw):
 # Reuse the same strict original success/failure predicate with the new exact
 # identity. Never normalize a failing boolean/exit/error to success.
 if not isinstance(raw,dict) or raw.get('package')!=PACKAGE or raw.get('artifact_sha256')!=ARTIFACT_SHA:raise ValueError('software_change_v2_identity')
 mapped=dict(raw,package=old.PACKAGE,artifact_sha256=old.ARTIFACT_SHA)
 summary=old.summarize(mapped)
 return {**summary,'package':PACKAGE,'artifact_sha256':ARTIFACT_SHA}

"""One additive Astra software-change fixture, not a general package installer.

Operator prepares this immutable artifact/oracle. UQA must select dispatch and
fetch through Core/journal. Never reinstall, repair, remove or execute scripts
from an existing package. No apt/DNF, dependency download or trigger processing.
"""
import base64
import gzip
import hashlib
import io
import json
import tarfile

PROFILE = 'owned-astra-software-change-20261017-v1'
PACKAGE = 'uqa-regression-probe-20261017'
VERSION = '0.0.1'
PREFIX = '/opt/uqa-regression-probe-20261017'
MARKER = 'UQA-SOFTWARE-CHANGE-20261017-V1'
STAGING = '/var/tmp/uqa-regression-probe-20261017.deb'
PROBE = ('#!/bin/sh\nprintf "%s\\n" "' + MARKER + '"\n').encode()


def _tar(files):
    stream = io.BytesIO()
    with tarfile.open(fileobj=stream, mode='w', format=tarfile.USTAR_FORMAT) as archive:
        for name, data, mode in files:
            info = tarfile.TarInfo(name)
            info.size, info.mode, info.uid, info.gid, info.mtime = len(data), mode, 0, 0, 0
            info.uname = info.gname = 'root'
            archive.addfile(info, io.BytesIO(data))
    return gzip.compress(stream.getvalue(), mtime=0)


def artifact():
    control = ('Package: ' + PACKAGE + '\nVersion: ' + VERSION + '\nArchitecture: all\n'
               'Maintainer: UQA lab <uqa@example.invalid>\nSection: misc\nPriority: optional\n'
               'Description: Isolated harmless UQA software audit fixture\n').encode()
    members = [('debian-binary', b'2.0\n'),
               ('control.tar.gz', _tar([('./control', control, 0o644)])),
               ('data.tar.gz', _tar([('.' + PREFIX + '/probe', PROBE, 0o755)]))]
    out = b'!<arch>\n'
    for name, data in members:
        header = (name + '/').ljust(16) + '0'.ljust(12) + '0'.ljust(6) + '0'.ljust(6)
        header += '100644'.ljust(8) + str(len(data)).ljust(10) + '`\n'
        assert len(header) == 60
        out += header.encode() + data + (b'\n' if len(data) % 2 else b'')
    return out


ARTIFACT_SHA = hashlib.sha256(artifact()).hexdigest()
CODE = r'''import base64,hashlib,json,os,subprocess
PACKAGE=__PACKAGE__
VERSION=__VERSION__
PREFIX=__PREFIX__
STAGING=__STAGING__
MARKER=__MARKER__
DATA=base64.b64decode(__DATA__,validate=True)
EXPECTED_SHA=__SHA__
out={'probe_version':1,'package':PACKAGE,'version':VERSION,'artifact_sha256':EXPECTED_SHA,
     'absent_before':False,'install_attempted':False,'installed_after':False,
     'probe_output_matches':False,'dpkg_exit':None,'error':None}
def run(args):
 p=subprocess.run(args,capture_output=True,text=True,timeout=60,env=dict(os.environ,LC_ALL='C',LANG='C'))
 if len(p.stdout.encode())+len(p.stderr.encode())>32768:raise ValueError('output_budget')
 return p
try:
 if os.geteuid()!=0:raise ValueError('existing_agent_root_required_no_escalation')
 if hashlib.sha256(DATA).hexdigest()!=EXPECTED_SHA:raise ValueError('artifact_hash')
 q=run(['/usr/bin/dpkg-query','-W','-f=${db:Status-Status}\t${Version}\n',PACKAGE])
 if q.returncode!=1 or q.stdout.strip():raise ValueError('package_must_be_absent_no_reinstall')
 if os.path.lexists(PREFIX) or os.path.lexists(STAGING):raise ValueError('owned_paths_must_be_absent')
 out['absent_before']=True
 fd=os.open(STAGING,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
 with os.fdopen(fd,'wb') as f:f.write(DATA);f.flush();os.fsync(f.fileno())
 # Exclusive owned path is retained even on failure; never overwrite/clean/retry.
 with open(STAGING,'rb') as f:
  if hashlib.sha256(f.read(16385)).hexdigest()!=EXPECTED_SHA:raise ValueError('staged_hash')
 out['install_attempted']=True
 p=run(['/usr/bin/dpkg','--no-triggers','--install',STAGING]);out['dpkg_exit']=p.returncode
 if p.returncode!=0:raise ValueError('dpkg_install_failed_no_repair')
 q=run(['/usr/bin/dpkg-query','-W','-f=${db:Status-Status}\t${Version}\n',PACKAGE])
 out['installed_after']=q.returncode==0 and q.stdout=='installed\t'+VERSION+'\n'
 p=run([PREFIX+'/probe'])
 out['probe_output_matches']=p.returncode==0 and not p.stderr and p.stdout==MARKER+'\n'
except Exception as e:
 out['error']=str(e)[:160] if isinstance(e,ValueError) else type(e).__name__
print(json.dumps(out,sort_keys=True))
'''
for key, value in {'PACKAGE': PACKAGE, 'VERSION': VERSION, 'PREFIX': PREFIX,
                   'STAGING': STAGING, 'MARKER': MARKER, 'SHA': ARTIFACT_SHA,
                   'DATA': base64.b64encode(artifact()).decode()}.items():
    CODE = CODE.replace('__' + key + '__', repr(value))
SHA = hashlib.sha256(CODE.encode()).hexdigest()
PAYLOAD = {'name': 'executeCommand', 'period': None, 'ttl': None, 'run_as_user': '',
           'additional_params': {'programm': '/usr/bin/python3', 'arguments': ['-c', CODE]}}


def summarize(raw):
    expected = {'probe_version': 1, 'package': PACKAGE, 'version': VERSION,
                'artifact_sha256': ARTIFACT_SHA, 'absent_before': True,
                'install_attempted': True, 'installed_after': True,
                'probe_output_matches': True, 'dpkg_exit': 0, 'error': None}
    if not isinstance(raw, dict) or set(raw) != set(expected):
        raise ValueError('software_change_output_shape')
    if (any(type(raw[k]) is not type(v) for k, v in expected.items() if k not in {'dpkg_exit', 'error'})
            or raw['dpkg_exit'] is not None and type(raw['dpkg_exit']) is not int
            or raw['error'] is not None and (not isinstance(raw['error'], str) or not 1 <= len(raw['error']) <= 160)):
        raise ValueError('software_change_output_types')
    if any(raw[k] != expected[k] for k in ['probe_version', 'package', 'version', 'artifact_sha256']):
        raise ValueError('software_change_output_identity')
    complete = raw == expected
    return {**raw, 'observation_status': 'COMPLETE' if complete else 'BLOCKED',
            'fixture_install_verified': complete, 'existing_software_modified': False,
            'artifact_retained': True, 'softaudit_verified': False,
            'cmdb_verified': False, 'full_case_passed': False, 'business_pass': False}

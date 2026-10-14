"""Abrupt child-process exit and durable ledger resume; no browser/server action."""
import os
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import job_store

child = '''
import os, sys
from pathlib import Path
import job_store
job_store.JOBS_DIR = Path(sys.argv[1])
job_id, resource_id, mode = sys.argv[2:5]
resource = job_store.get_test_resource(job_id, resource_id)
assert resource['name'] == 'fixture-resource'
assert resource['cleanup_required'] is True
attempt = job_store.start_cleanup_attempt(job_id, resource_id)
if mode == 'crash':
    os._exit(23)
resource = job_store.get_test_resource(job_id, resource_id)
assert [a['status'] for a in resource['cleanup_attempts']] == ['interrupted', 'running']
assert resource['cleanup_attempts'][0]['reason'] == 'superseded_by_resumed_cleanup'
job_store.finish_cleanup_attempt(job_id, resource_id, attempt['attempt_id'],
    'pending', reason='fixture_resume_without_remote_action')
assert len(job_store.list_cleanup_candidates(job_id)) == 1
'''

root = Path(__file__).resolve().parents[1]
environment = dict(os.environ, PYTHONPATH=str(root))
with TemporaryDirectory(prefix='uqa-ledger-process-') as directory, \
        patch.object(job_store, 'JOBS_DIR', Path(directory)):
    job = job_store.create_job('Isolated ledger process recovery', job_type='regression')
    case = job_store.add_test_case(job['job_id'], 'Fixture only')
    resource = job_store.add_test_resource(job['job_id'], 'fixture', name='fixture-resource',
        created_by_case=case['case_id'], cleanup_required=True)
    arguments = [sys.executable, '-c', child, directory, job['job_id'], resource['resource_id']]
    crashed = subprocess.run(arguments + ['crash'], cwd=root, env=environment, capture_output=True, timeout=30)
    assert crashed.returncode == 23, 'child did not reach the deliberate fixture crash'
    restored = job_store.get_test_resource(job['job_id'], resource['resource_id'])
    assert restored['status'] == 'cleanup_in_progress' and len(restored['cleanup_attempts']) == 1
    resumed = subprocess.run(arguments + ['resume'], cwd=root, env=environment, capture_output=True, timeout=30)
    assert resumed.returncode == 0, 'isolated resume assertions failed'
    restored = job_store.get_test_resource(job['job_id'], resource['resource_id'])
    assert restored['status'] != 'cleaned' and restored['cleanup_required'] is True
    assert len(restored['cleanup_attempts']) == 2
print('resource process recovery: PASS (durable ledger, interrupted attempt, resumed pending; no remote mutation)')

"""Temporary fixture snapshots only, not the real jobs directory."""
import json
import os
import stat
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from job_store import _atomic_write

with TemporaryDirectory(prefix='uqa-atomic-snapshot-') as directory:
    path=Path(directory)/'fixture.json'
    original={'fixture':'initial'}
    with patch('job_store.os.fsync', wraps=os.fsync) as sync:
        _atomic_write(path,original)
        assert sync.call_count >= (2 if os.name=='posix' else 1)
    assert json.loads(path.read_text())==original
    if os.name=='posix':assert stat.S_IMODE(path.stat().st_mode)==0o660
    for target in ('replace','fsync'):
        ctx=patch.object(Path,'replace',side_effect=OSError('fixture rename failure')) if target=='replace' else patch('job_store.os.fsync',side_effect=OSError('fixture sync failure'))
        with ctx:
            try:_atomic_write(path,{'fixture':'must-not-replace'})
            except OSError:pass
            else:raise AssertionError('expected fixture failure')
        assert json.loads(path.read_text())==original
        assert not list(Path(directory).glob('*.tmp'))
    def write(index):
        value={'index':index,'payload':str(index)*2048}
        _atomic_write(path,value)
        # A concurrent reader sees a whole snapshot, not half of another JSON.
        read=json.loads(path.read_text())
        assert read['payload']==str(read['index'])*2048
    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(write,range(80)))
    assert not list(Path(directory).glob('*.tmp'))
    read=json.loads(path.read_text())
    assert 0<=read['index']<80
print('PASS Job atomic snapshots: unique concurrent writers, file/rename sync, failure cleanup; no real jobs')

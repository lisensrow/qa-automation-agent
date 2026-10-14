"""Temporary input files only, never execute/extract a package."""
import hashlib
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import distribution_catalog as catalog

with TemporaryDirectory(prefix='uqa-distribution-catalog-') as root,patch.object(catalog,'INPUT_ROOT',Path(root)):
    directory=Path(root)/'plugins';directory.mkdir();payload=b'fixture-package-not-executable'
    package=directory/'fixture.bin';package.write_bytes(payload)
    result=catalog.inspect_distribution('plugins','fixture.bin',hashlib.sha256(payload).hexdigest())
    assert result['size_bytes']==len(payload) and not result['installation_performed']
    def refused(call):
        try:call()
        except ValueError:return
        raise AssertionError('unsafe distribution selection accepted')
    refused(lambda:catalog.inspect_distribution('plugins','../fixture.bin'))
    refused(lambda:catalog.inspect_distribution('plugins','fixture.bin','0'*64))
    refused(lambda:catalog.inspect_distribution('unknown','fixture.bin'))
    (directory/'alias.bin').symlink_to(package)
    refused(lambda:catalog.inspect_distribution('plugins','alias.bin'))
print('PASS distribution catalog: checksum, fixed selection, symlink/path rejection; no unpack, install or execution')

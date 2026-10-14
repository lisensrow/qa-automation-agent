"""Read-only inventory/checksum of input files; no extraction or execution."""
import hashlib
from pathlib import Path
import stat

INPUT_ROOT=Path('/home/adminacc/uqa-input/distributions')
KINDS={'core','agents','plugins'}
MAX_BYTES=100*1024*1024

def inspect_distribution(kind,filename,expected_sha256=None):
    if kind not in KINDS or not isinstance(filename,str) or Path(filename).name!=filename or filename in {'','.','..'}:
        raise ValueError('invalid distribution selection')
    directory=INPUT_ROOT/kind;path=directory/filename
    if INPUT_ROOT.is_symlink() or directory.is_symlink() or path.is_symlink():raise ValueError('distribution symlink refused')
    root=INPUT_ROOT.resolve(strict=True)
    if path.resolve(strict=True).parent!=root/kind:raise ValueError('distribution outside input')
    before=path.stat()
    if not stat.S_ISREG(before.st_mode) or not 0<before.st_size<=MAX_BYTES:raise ValueError('distribution size/type refused')
    digest=hashlib.sha256();size=0
    with path.open('rb') as stream:
        while chunk:=stream.read(1024*1024):
            size+=len(chunk)
            if size>MAX_BYTES:raise ValueError('distribution grew during read')
            digest.update(chunk)
    after=path.stat()
    if (before.st_ino,before.st_size,before.st_mtime_ns)!=(after.st_ino,after.st_size,after.st_mtime_ns) or size!=before.st_size:
        raise ValueError('distribution changed during read')
    actual=digest.hexdigest()
    if expected_sha256 is not None and actual!=expected_sha256:raise ValueError('distribution checksum mismatch')
    return {'kind':kind,'filename':filename,'size_bytes':size,'sha256':actual,
            'compatibility':'not_verified','installation_performed':False,'bookkeeping_only':True,'product_evidence':False}

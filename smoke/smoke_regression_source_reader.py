"""Source-only reader: exact provenance, complete windows, no authority or truncation."""
import hashlib,json,tempfile
from pathlib import Path
from unittest.mock import patch
import regression_source_reader as r

def main():
    with tempfile.TemporaryDirectory() as tmp:
        root=Path(tmp)
        obj={'key':'US-T116','title':'Case 1','updated_on':'2026-10-16','precondition_html':'source only',
            'objective_html':'','steps':[{'number':n,'description_html':'source action '+str(n),'test_data_html':'data',
            'expected_html':'expected '+str(n)} for n in range(1,6)]}
        raw=json.dumps(obj).encode();(root/'US-T116.json').write_bytes(raw)
        manifest={'cycles':[{'key':'US-C346','cases':[{'key':'US-T116','number':1,'steps':5,'json_sha256':hashlib.sha256(raw).hexdigest()}]}]}
        raw_manifest=json.dumps(manifest).encode();(root/'manifest.json').write_bytes(raw_manifest)
        with patch.object(r,'ROOT',root),patch.object(r,'MANIFEST_SHA',hashlib.sha256(raw_manifest).hexdigest()):
            first=r.read_case('US-T116',1,3);assert first['next_step']==4 and not first['window_contains_full_case']
            last=r.read_case('US-T116',4,3);assert last['next_step'] is None and not last['window_contains_full_case']
            assert first['steps']+last['steps']==obj['steps']
            assert first['steps'][0]['expected_html']=='expected 1'
            for result in [first,last]:
                assert result['source_only'] and not result['executed'] and not result['business_pass'] and not result['execution_permission_granted'] and result['truncated'] is False
            for args in [('../secrets',1,1),('US-T116',0,1),('US-T116',True,1),('US-T116',1,4),('US-T116',6,1)]:
                assert r.read_case(*args).get('error')
            with patch.object(r,'MAX_RESULT_CHARS',10):
                blocked=r.read_case('US-T116');assert blocked['status']=='blocked_source_window_budget' and 'steps' not in blocked and blocked['truncated'] is False
            (root/'US-T116.json').write_bytes(raw+b' ')
            assert r.read_case('US-T116')['error']=='source_case_hash_mismatch'
            (root/'manifest.json').write_bytes(raw_manifest+b' ')
            assert r.read_case('US-T116')['error']=='source_manifest_hash_mismatch'
    print('regression source reader: PASS')

if __name__=='__main__':main()

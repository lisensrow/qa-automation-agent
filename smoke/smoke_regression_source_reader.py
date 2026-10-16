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
    with tempfile.TemporaryDirectory() as tmp:
        root=Path(tmp);text='<p>Полный исторический expected\\n</p>'*300
        obj={'key':'US-T102','steps':[{'number':1,'description_html':'drive','test_data_html':'','expected_html':text}],
            'title':'Large case','updated_on':'2026-10-16','precondition_html':'source','objective_html':''}
        raw=json.dumps(obj).encode();(root/'US-T102.json').write_bytes(raw)
        manifest={'cycles':[{'key':'US-C347','cases':[{'key':'US-T102','number':2,'steps':1,'json_sha256':hashlib.sha256(raw).hexdigest()}]}]}
        mr=json.dumps(manifest).encode();(root/'manifest.json').write_bytes(mr)
        with patch.object(r,'ROOT',root),patch.object(r,'MANIFEST_SHA',hashlib.sha256(mr).hexdigest()):
            assert r.read_case('US-T102')['status']=='blocked_source_window_budget'
            offset=0;pages=[]
            while True:
                p=r.read_step_cell('US-T102',1,'expected_html',offset,1500)
                assert p['status']=='source_cell_page_observed' and p['char_offset']==offset
                assert p['source_only'] and not p['executed'] and not p['execution_permission_granted']
                assert not p['truncated'] and not p['page_contains_full_step'] and not p['page_contains_full_case']
                assert p['cell_sha256']==hashlib.sha256(text.encode()).hexdigest()
                assert len(json.dumps(p,ensure_ascii=False))<=r.MAX_RESULT_CHARS
                pages.append(p['content']);offset=p['next_char_offset']
                if offset is None:break
            assert ''.join(pages)==text and len(pages)>1
            empty=r.read_step_cell('US-T102',1,'test_data_html');assert empty['page_contains_full_cell'] and empty['content']==''
            for args in [('US-T102',1,'expected_html',True,100),('US-T102',1,'expected_html',0,2001),
                         ('US-T102',True,'expected_html',0,100),('US-T102',1,'unknown',0,100),
                         ('US-T102',1,'expected_html',len(text),100),('../secrets',1,'expected_html',0,100)]:
                assert r.read_step_cell(*args).get('error')
            (root/'US-T102.json').write_bytes(raw+b' ')
            assert r.read_step_cell('US-T102',1,'expected_html')['error']=='source_case_hash_mismatch'
    print('regression source reader: PASS (whole windows and lossless explicit cell pages)')

if __name__=='__main__':main()

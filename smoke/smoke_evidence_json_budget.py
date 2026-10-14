"""Isolated Job evidence budget: valid JSON, full normal snapshots, fail-closed overflow."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import job_store
import uqa
from tools.browser import BrowserSession
class Request:
    method='GET';resource_type='xhr';post_data=None
    def all_headers(self):return {'authorization':'fixture-auth','cookie':'fixture-cookie'}
class Response:
    url='https://fixture.local/api/items';status=200
    def __init__(self,padding):self.padding=padding
    def all_headers(self):return {'content-type':'application/json','set-cookie':'fixture-cookie'}
    def text(self):return json.dumps({'offset':0,'count':1,'total':1,'items':[{'id':'fixture','padding':self.padding,'password':'fixture-private'}]})
session=BrowserSession();session._ensure_started=lambda:None
session.network_details={'n1':{'request':Request(),'response':Response('x'*12000),'session_id':'fixture'}}
native=session.get_network_detail('n1')
assert native['response_body_truncated'] is False
assert len(json.loads(native['response_body'])['items'][0]['padding'])==12000
assert 'fixture-private' not in native['response_body']
assert not native['request_headers'] and 'set-cookie' not in native['response_headers']
session.network_details['n1']['response']=Response('x'*70000)
truncated=session.get_network_detail('n1')
assert truncated['response_body_truncated'] is True
assert json.loads(truncated['response_body'])['_body_truncated'] is True
with TemporaryDirectory(prefix='uqa-evidence-budget-') as d,patch.object(job_store,'JOBS_DIR',Path(d)):
    job=job_store.create_job('Isolated evidence JSON fixture',job_type='manual')
    case=job_store.add_test_case(job['job_id'],'Budget fixture')
    def record(tool,result):
        return uqa.record_tool_evidence(job['job_id'],case['case_id'],tool,{},result)
    result={'status':'ok','text_preview':'fixture '*1300}
    e=record('browser_get_state',result)
    assert json.loads(e['value'])['result']==result
    body=json.dumps({'offset':0,'count':1,'total':1,'items':[{'id':'fixture','name':'x'*20000}]})
    result={'status':200,'method':'GET','response_body':body,'request_id':'n1','session_id':'fixture'}
    e=record('browser_get_network_detail',result)
    assert json.loads(e['value'])['result']['response_body']==body
    for result in ({'status':'ok','text_preview':'x'*270000},{'status':'ok','text_preview':'Ж'*140000}):
        e=record('browser_get_state',result);payload=json.loads(e['value'])
        assert payload['result']['evidence_truncated'] is True
        assert len(payload['result']['original_payload_sha256'])==64
        assert not e['usable_for_pass'] and not e['usable_for_verdict']
        assert e['eligibility_reason']=='evidence_payload_over_budget'
        assert len(e['value'].encode('utf-8'))<1000
    e=record('browser_get_network_detail',truncated)
    assert not e['usable_for_verdict'] and e['eligibility_reason']=='native_response_body_truncated'
print('PASS evidence JSON budget: ordinary and API snapshots retained, UTF8 limit, valid overflow envelope, no truncated PASS')

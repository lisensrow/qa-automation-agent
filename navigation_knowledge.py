"""Derive navigation candidates from Core contracts, never from model prose.

Candidates are not verified knowledge. Promotion/retrieval needs a separate
type-specific validator; the existing API-binding validator must not accept them.
"""
import hashlib
import json
import re
from urllib.parse import urlsplit
from frontend_check_contracts import evaluate_contract, normalized_origin

TOOL = 'browser_verify_exact_table_row_tabs_semantic'


def derive_navigation_candidates(job, case_id, saved_url):
    case = next((c for c in job.get('test_cases',[]) if c.get('case_id')==case_id),{})
    identity = job.get('stand_identity') or {}
    context = case.get('memory_context') or {}
    if (case.get('status')!='passed' or identity.get('status')!='ok'
            or identity.get('deployment_partial') or identity.get('frontend_status')!='ok'
            or not identity.get('frontend_version') or not identity.get('server_version')
            or not identity.get('installation_architecture') or not identity.get('checked_at')
            or context.get('identity_checked_at')!=identity['checked_at']
            or not normalized_origin(saved_url)):
        return []
    requirement = case.get('requirement') or {}
    contracts = requirement.get('check_contracts') or {}
    if not contracts or any(c.get('tool')!=TOOL for c in contracts.values()):
        return []
    fields = set()
    references = set()
    for check_id, contract in contracts.items():
        result,_ = evaluate_contract(case,requirement,{'check_id':check_id,'status':'blocked'},saved_url)
        if result.get('status')!='passed':
            return []
        fields.update(a['field'] for a in result.get('assertions',[]))
        references.update(result.get('observations',[]))
    if not {'tab_selection','panels_visible','details_identity_preserved'} <= fields or len(references)!=1:
        return []
    observation = next((o for o in case.get('observations',[]) if o.get('observation_id') in references),{})
    tabs = (observation.get('data') or {}).get('requested_tabs')
    if not isinstance(tabs,list) or not 1<=len(tabs)<=20:
        return []
    for tab in tabs:
        if (not isinstance(tab,str) or not 1<=len(tab)<=128
                or re.search(r'password|passwd|secret|token|authorization|cookie|bearer|[\x00-\x1f]',tab,re.I)
                or any(c in tab for c in ('@','?','/','\\'))):
            return []
    # Route starts at the configured page, not a CI-specific details URL.
    path = urlsplit(saved_url).path or '/'
    if re.search(r'password|token|secret|[\x00-\x1f]',path,re.I) or len(path)>256:
        return []
    data={'ui_path':path,'ui_tool':TOOL,'ui_action':'exact_row_then_named_tabs','tab_names':list(tabs)}
    digest=hashlib.sha256(json.dumps(data,sort_keys=True,separators=(',',':')).encode()).hexdigest()[:20]
    return [{'fact_key':'ui_navigation:'+digest,'fact_type':'ui_navigation',
             'subject_key':'ui_navigation_subject:'+digest,
             'statement':'Exact table row details support the observed named-tab navigation.',
             'data':data,'source_observation_ids':sorted(references),
             'verification':{'runtime_exact_row_tabs_observed':True,'runtime_panels_visible':True,
                             'runtime_details_identity_preserved':True},
             'usage':'candidate_only_not_PASS_evidence'}]

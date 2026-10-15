"""Operator-registered historical contract sources. Read-only, never HTTP or PASS.

The model selects neither paths, pins nor evidence IDs. Registration is private
runtime state, separate from source evidence and from current-runtime trust.
"""
import hashlib
import json
import re
from copy import deepcopy
from pathlib import Path
from urllib.parse import urlsplit
import job_store
from stands import get_stand
from api_contract_projection import inspect_api_contract_page, FLAGS, MAX_BYTES, MAX_OUTPUT_BYTES

TOKEN=re.compile(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,159}\Z')
PIN=re.compile(r'[0-9a-f]{64}\Z')
FIELDS={'source_id','stand','origin','job_id','case_id','evidence_id','projection_sha256','schema_sha256'}

def schema_tools_for_case(job, case_id):
    """Expose reader schemas for an explicitly source-bound read-only QA case.

    Availability is not a call, grant, source validity claim or business oracle.
    Every eventual call still passes the ordinary stand/source/policy checks.
    """
    if not isinstance(job,dict) or job.get('job_type') not in {'manual','regression'}:return set()
    case=next((c for c in job.get('test_cases',[]) if c.get('case_id')==case_id),{})
    req=case.get('requirement') or {};source=req.get('api_contract_source_id')
    stand=job.get('stand')
    if (req.get('action_profile')!='read_only' or not isinstance(source,str) or not TOKEN.fullmatch(source)
            or not isinstance(stand,str) or not TOKEN.fullmatch(stand) or req.get('stand') not in (None,stand)):
        return set()
    return {'api_inspect_contract_page','api_inspect_request_contract'}


def bind_reader_catalog(catalog, job, case_id):
    """Do not ask the model to invent context IDs already owned by the caller."""
    names=schema_tools_for_case(job,case_id)
    if not names:return catalog
    result=deepcopy(catalog)
    for item in result:
        fn=item.get('function') or {}
        if fn.get('name') not in names:continue
        params=fn['parameters']
        for key in ('stand','source_id'):params['properties'].pop(key,None)
        params['required']=[key for key in params.get('required',[]) if key not in {'stand','source_id'}]
        fn['description']=('Context-bound: stand and source_id are injected from this QA case. Omit both. '
            'Schema availability grants no permission. '+fn.get('description',''))
    return result

def _pairs(pairs):
    result={}
    for k,v in pairs:
        if k in result:raise ValueError('duplicate key')
        result[k]=v
    return result

def _origin(value):
    p=urlsplit(value)
    if (p.scheme not in {'http','https'} or not p.hostname or p.username or p.password
        or p.path not in ('','/') or p.query or p.fragment):raise ValueError('origin')
    return p.scheme,p.hostname.lower(),p.port or (443 if p.scheme=='https' else 80)

def inspect_registered_contract_page(stand, method, path, reference_chain=(), source_id=None):
    """Load a registered same-stand evidence value, recheck pins, then pure lookup."""
    denied={'contract_observation_status':'unavailable',**FLAGS}
    try:
        if not isinstance(stand,str) or not TOKEN.fullmatch(stand):raise ValueError('stand')
        if source_id is not None and (not isinstance(source_id,str) or not TOKEN.fullmatch(source_id)):
            raise ValueError('source')
        manifest=Path(job_store.JOBS_DIR).parent/'api_contract_sources.json'
        if manifest.is_symlink() or not manifest.is_file() or manifest.stat().st_size>32768:
            return dict(denied,reason='registered_contract_sources_unavailable')
        raw_manifest=manifest.read_bytes()
        if len(raw_manifest)>32768:raise ValueError('manifest budget')
        doc=json.loads(raw_manifest,object_pairs_hook=_pairs)
        if (not isinstance(doc,dict) or set(doc)!={'version','sources'} or type(doc['version']) is not int
            or doc['version']!=1 or not isinstance(doc['sources'],list) or not 1<=len(doc['sources'])<=20):
            raise ValueError('manifest')
        identities=set()
        for entry in doc['sources']:
            if not isinstance(entry,dict) or set(entry)!=FIELDS:raise ValueError('entry')
            for k in FIELDS-{'origin','projection_sha256','schema_sha256'}:
                if not isinstance(entry[k],str) or not TOKEN.fullmatch(entry[k]):raise ValueError('identity')
            for k in ('projection_sha256','schema_sha256'):
                if not isinstance(entry[k],str) or not PIN.fullmatch(entry[k]):raise ValueError('pin')
            _origin(entry['origin'])
            identity=(entry['stand'],entry['source_id'])
            if identity in identities:raise ValueError('duplicate source')
            identities.add(identity)
        matches=[e for e in doc['sources'] if e['stand']==stand and (source_id is None or e['source_id']==source_id)]
        if len(matches)!=1:
            return dict(denied,reason='registered_contract_source_not_unique',
                available_source_ids=sorted(e['source_id'] for e in doc['sources'] if e['stand']==stand))
        entry=matches[0]
        if _origin(get_stand(stand)['web_url'])!=_origin(entry['origin']):
            return dict(denied,reason='registered_contract_stand_origin_mismatch')
        source_job=job_store.get_job(entry['job_id'])
        if not isinstance(source_job,dict) or source_job.get('stand')!=stand:
            raise ValueError('source job stand')
        cases=[c for c in source_job.get('test_cases',[]) if c.get('case_id')==entry['case_id']]
        if len(cases)!=1:raise ValueError('case')
        receipts=[e for e in cases[0].get('evidence',[]) if e.get('evidence_id')==entry['evidence_id']]
        if len(receipts)!=1:raise ValueError('evidence')
        evidence=receipts[0]
        if (evidence.get('type')!='operator_installed_schema_projection'
            or evidence.get('source')!='operator_installed_schema_read'
            or evidence.get('execution_status')!='observed'
            or evidence.get('usable_for_pass') is not False or evidence.get('usable_for_verdict') is not False):
            raise ValueError('unsupported source provenance')
        raw=evidence.get('value')
        if not isinstance(raw,str) or len(raw)>MAX_BYTES or len(raw.encode())>MAX_BYTES:raise ValueError('source budget')
        if hashlib.sha256(raw.encode()).hexdigest()!=entry['projection_sha256']:
            return dict(denied,reason='registered_contract_evidence_hash_mismatch')
        result=inspect_api_contract_page(raw,expected_projection_sha256=entry['projection_sha256'],
            expected_schema_sha256=entry['schema_sha256'],method=method,path=path,reference_chain=reference_chain)
        if result['contract_observation_status']=='observed':
            result.update(source_id=entry['source_id'],source_job_id=entry['job_id'],
                source_case_id=entry['case_id'],source_evidence_id=entry['evidence_id'],
                execution_mode='registered_historical_operator_schema_snapshot',
                stand=stand,source_registration_verified=True,current_schema_recency_verified=False)
            if len(json.dumps(result,ensure_ascii=False).encode())>MAX_OUTPUT_BYTES:
                return dict(denied,reason='registered_contract_output_budget')
        return result
    except (OSError,ValueError,TypeError,KeyError,UnicodeError,AttributeError,RecursionError):
        return dict(denied,reason='registered_contract_source_invalid')


def inspect_registered_request_contract(stand, method, path, source_id=None):
    """Two bounded historical reads: operation + its direct JSON request root.

    No recursive closure, guessed ref, HTTP, freshness promotion or execution.
    Both reads must independently validate the same registered source and pins.
    """
    refused={'contract_observation_status':'unavailable',**FLAGS}
    root=inspect_registered_contract_page(stand,method,path,source_id=source_id)
    if root.get('contract_observation_status')!='observed':return root
    try:
        media=(root['operation'].get('request_body') or {}).get('content',{}).get('application/json')
        if not isinstance(media,dict) or set(media)!={'$ref'}:
            return dict(refused,reason='registered_json_request_root_not_single_reference')
        ref=media['$ref']
        if ref not in root['direct_schema_references']:
            return dict(refused,reason='registered_request_reference_not_exposed')
        page=inspect_registered_contract_page(stand,method,path,[ref],source_id=root['source_id'])
        if page.get('contract_observation_status')!='observed':return page
        keys=('source_id','source_job_id','source_case_id','source_evidence_id','stand',
              'schema_sha256','projection_sha256','method','path_template')
        if any(page.get(k)!=root.get(k) for k in keys) or page.get('schema_reference')!=ref:
            return dict(refused,reason='registered_request_revision_changed')
        result={k:root[k] for k in keys}
        result.update(contract_observation_status='observed',observation_kind='bounded_registered_request_contract',
            operation_id=root['operation']['operation_id'],
            request_body_required=root['operation']['request_body']['required'],media_type='application/json',
            request_schema_reference=ref,request_schema=page['schema'],
            direct_schema_references=page['direct_schema_references'],
            observed_page_count=2,reference_path_verified=True,complete_reference_closure=False,
            defaults_exported=False,examples_exported=False,descriptions_exported=False,
            source_registration_verified=True,current_schema_recency_verified=False,
            execution_mode='registered_historical_operator_request_contract',**FLAGS)
        if len(json.dumps(result,ensure_ascii=False).encode())>MAX_OUTPUT_BYTES:
            return dict(refused,reason='registered_request_output_budget')
        return result
    except (KeyError,TypeError,ValueError,AttributeError):
        return dict(refused,reason='registered_request_contract_invalid')

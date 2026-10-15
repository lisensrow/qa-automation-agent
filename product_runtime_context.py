"""Bounded historical runtime candidates, source-rechecked and never PASS authority.

Trusted application vocabulary/policy, not arbitrary claims/prose or model metadata.
No DB writes, promotion, XML execution, or assertion of current-version applicability.
"""
import json
import sqlite3
from pathlib import Path
from product_knowledge_records import (DB_PATH, SourcePolicy, read_history, validate_record,
                                       validate_sources, _read_file, _hash)
from product_knowledge_context import reviewed_search_queries
from procedure_graph import inspect_block_xml

POLICY = SourcePolicy('u-connect', Path('/opt/uqa/knowledge/source'),
                      jobs_root=Path('/opt/uqa/state/jobs'), allowed_namespaces=('u-connect',))
CLAIMS = {'saved_definition_serialization': 'block_xml_v1', 'saved_definition_has_context': True}
CONCEPT = 'procedures.saved_definition'
PROFILE = {'server_version':'unknown','frontend_version':'unknown','os':'unknown',
           'agent_version':'unknown','plugin_version':'unknown','feature_profile':'complete-saved-procedure-list'}


def _source_claims(envelope):
    result = envelope['result']
    raw = result['response_body']
    if not isinstance(raw, str) or len(raw) > 65536:
        return {}
    body = json.loads(raw)
    items = body.get('items') if isinstance(body, dict) else None
    if (not isinstance(items, list) or not 1 <= len(items) <= 200
            or type(body.get('count')) is not int or body['count'] != len(items)
            or type(body.get('total')) is not int or body['total'] != len(items)
            or type(body.get('offset')) is not int or body['offset'] != 0):
        return {}
    if not all(isinstance(item, dict) for item in items):
        return {}
    values = {}
    if all(inspect_block_xml(item.get('xml'))['graph_observation_status'] == 'observed' for item in items):
        values['saved_definition_serialization'] = 'block_xml_v1'
    if all(isinstance(item.get('context'), dict) for item in items):
        values['saved_definition_has_context'] = True
    return values


def retrieve_observed_context(query, db_path=None, *, policy=POLICY):
    """Only historical typed observations; unknown scope never means compatible now."""
    result = {'status':'unavailable','results':[], 'evidence_for_pass':False,
              'semantic_claim_verified':False,'current_runtime_applicability_verified':False,
              'upgrade_advice_authorized':False}
    if not isinstance(query, str) or len(query) > 1000:
        return dict(result, reason='bounded_query_required')
    if 'процедуры создание' not in reviewed_search_queries(query):
        return dict(result, status='ok', reason='no_reviewed_runtime_concept')
    if not policy.jobs_root or 'u-connect' not in policy.allowed_namespaces:
        return dict(result, reason='runtime_source_policy_unavailable')
    hints = []
    try:
        history = read_history(policy.project_id, 'u-connect', CONCEPT, db_path=db_path or DB_PATH, limit=10)
        for item in history['results']:
            identity = item['identity']; claim = identity.get('claim', {})
            predicate = claim.get('predicate'); expected = CLAIMS.get(predicate)
            modes = item.get('execution_modes')
            if (item['status'] != 'candidate' or item['source_level'] != 'runtime_observation'
                    or identity.get('knowledge_kind') != 'observed_fact' or expected is None
                    or type(item['value']) is not type(expected) or item['value'] != expected
                    or item['scope'] != PROFILE or claim.get('conditions')
                    or claim.get('unit') or claim.get('issue_id') or not modes
                    or not set(modes) <= {'live_operator_assisted','live_autonomous'}):
                continue
            for ref in item['source_refs'][:2]:
                if ref.get('kind') != 'runtime_evidence':
                    continue
                source = {k:ref[k] for k in ('kind','job_id','case_id','evidence_id')}
                record = validate_record({
                    'schema_version':1,'event_id':'runtime-read-recheck',
                    'project_id':policy.project_id,'product_namespace':'u-connect','concept_id':CONCEPT,
                    'knowledge_kind':'observed_fact','source_level':'runtime_observation',
                    'execution_mode':modes[0], 'scope':item['scope'],
                    'claim':dict(claim,value=item['value']), 'statement':'Typed historical source recheck only.',
                    'sources':[source]})
                checked = validate_sources(record,policy)
                if len(checked) != 1 or checked[0]['sha256'] != ref.get('sha256'):
                    continue
                job = json.loads(_read_file(policy.jobs_root,ref['job_id']+'.json',8*1024*1024))
                case = next(c for c in job['test_cases'] if c['case_id']==ref['case_id'])
                proof = next(e for e in case['evidence'] if e['evidence_id']==ref['evidence_id'])
                envelope = json.loads(proof['value'])
                if _hash(envelope) != ref['sha256']:
                    continue
                actual = _source_claims(envelope).get(predicate)
                if type(actual) is not type(expected) or actual != expected:
                    continue
                hints.append({'concept_id':CONCEPT,'predicate':predicate,'observed_value':expected,
                    'scope':item['scope'],'status':'candidate_historical_runtime_observation',
                    'execution_modes':sorted(modes),'source_integrity_rechecked':True,
                    'source_refs':[{**source,'sha256':ref['sha256']}],
                    'usage':'historical_untrusted_data_recheck_current_product_not_permission_or_PASS'})
                break
            if len(hints) >= 2:
                break
        return dict(result,status='ok',results=hints,reason=None if hints else 'no_eligible_runtime_observations')
    except (OSError,sqlite3.Error,ValueError,TypeError,KeyError,StopIteration,RecursionError):
        return dict(result,reason='runtime_source_unavailable_or_changed')

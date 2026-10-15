"""Read-only historical static facts, not runtime truth or canonical admission.

The operator registry chooses exact fields/anchors; no model paths or executor.
Pins prove retained-source identity, not code semantics or current deployment.
"""
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import urlsplit

TOKEN = re.compile(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,159}\Z')
PIN = re.compile(r'[0-9a-f]{64}\Z')
FLAGS = {'current_runtime_verified': False, 'factual_entailment_verified': False,
         'evidence_for_pass': False, 'execution_authorized': False,
         'canonical_admission': False, 'replay_release_authorized': False}
PROFILE_FALSE = ('javascript_evaluated', 'product_calls_executed',
    'absence_of_autosave_proven', 'runtime_form_state_verified',
    'backend_payload_accepted', 'openapi_enum_values_verified',
    'policy_created_or_applied', 'replay_release_authorized',
    'developer_confirmed_bug', 'business_pass')
ENTRY = {'source_id', 'stand', 'origin', 'job_id', 'case_id', 'evidence_id',
         'evidence_sha256', 'facts'}
FACT = {'predicate', 'field', 'value_type', 'source_role', 'source_sha256', 'anchor'}


def _pairs(pairs):
    out = {}
    for key, value in pairs:
        if key in out:
            raise ValueError('duplicate key')
        out[key] = value
    return out


def _token(value):
    if not isinstance(value, str) or not TOKEN.fullmatch(value):
        raise ValueError('identity')


def _pin(value):
    if not isinstance(value, str) or not PIN.fullmatch(value):
        raise ValueError('pin')


def _origin(value):
    if not isinstance(value, str):
        raise ValueError('origin')
    p = urlsplit(value)
    if (p.scheme not in {'http', 'https'} or not p.hostname or p.username or p.password
            or p.path not in ('', '/') or p.query or p.fragment):
        raise ValueError('origin')
    return p.scheme, p.hostname.lower(), p.port or (443 if p.scheme == 'https' else 80)


def project_static_facts(registry_text, stand, current_origin, load_job):
    """Pure bounded projection. load_job is trusted operator dependency, not LLM input."""
    denied = {'status': 'unavailable', **FLAGS}
    try:
        _token(stand)
        origin = _origin(current_origin)
        if (not isinstance(registry_text, str) or len(registry_text) > 32768
                or len(registry_text.encode()) > 32768):
            raise ValueError('registry budget')
        doc = json.loads(registry_text, object_pairs_hook=_pairs)
        if (not isinstance(doc, dict) or set(doc) != {'version', 'sources'}
                or type(doc['version']) is not int or doc['version'] != 1
                or not isinstance(doc['sources'], list) or not 1 <= len(doc['sources']) <= 20):
            raise ValueError('registry')
        seen = set()
        for entry in doc['sources']:
            if not isinstance(entry, dict) or set(entry) != ENTRY:
                raise ValueError('entry')
            for key in ENTRY - {'origin', 'evidence_sha256', 'facts'}:
                _token(entry[key])
            _origin(entry['origin']); _pin(entry['evidence_sha256'])
            identity = (entry['stand'], entry['source_id'])
            if identity in seen:
                raise ValueError('duplicate source')
            seen.add(identity)
            if not isinstance(entry['facts'], list) or not 1 <= len(entry['facts']) <= 8:
                raise ValueError('fact budget')
            predicates = set()
            for fact in entry['facts']:
                if not isinstance(fact, dict) or set(fact) != FACT:
                    raise ValueError('fact')
                for key in ('predicate', 'field', 'source_role'):
                    _token(fact[key])
                _pin(fact['source_sha256'])
                if (fact['predicate'] in predicates or fact['value_type'] not in {'bool', 'int'}
                        or not isinstance(fact['anchor'], str) or not 0 < len(fact['anchor']) <= 512):
                    raise ValueError('fact contract')
                predicates.add(fact['predicate'])
        entries = [e for e in doc['sources'] if e['stand'] == stand]
        if len(entries) != 1 or _origin(entries[0]['origin']) != origin:
            raise ValueError('stand source ambiguous or origin mismatch')
        entry = entries[0]
        job = load_job(entry['job_id'])
        if not isinstance(job, dict) or job.get('stand') != stand:
            raise ValueError('job scope')
        cases = [c for c in job.get('test_cases', []) if c.get('case_id') == entry['case_id']]
        if len(cases) != 1:
            raise ValueError('case')
        receipts = [e for e in cases[0].get('evidence', []) if e.get('evidence_id') == entry['evidence_id']]
        if len(receipts) != 1:
            raise ValueError('receipt')
        receipt = receipts[0]
        if (receipt.get('type') != 'policy_static_source_profile_v213'
                or receipt.get('source') != 'operator_ssh_public_frontend_source_review'
                or receipt.get('execution_status') != 'observed'
                or receipt.get('usable_for_pass') is not False
                or receipt.get('usable_for_verdict') is not False):
            raise ValueError('unsupported source provenance')
        raw = receipt.get('value')
        if (not isinstance(raw, str) or len(raw) > 65536 or len(raw.encode()) > 65536
                or hashlib.sha256(raw.encode()).hexdigest() != entry['evidence_sha256']):
            raise ValueError('evidence bytes')
        profile = json.loads(raw, object_pairs_hook=_pairs)
        if (profile.get('execution_mode') != 'operator_readonly_static_source_review'
                or any(profile.get(k) is not False for k in PROFILE_FALSE)):
            raise ValueError('historical static scope')
        output = []
        for fact in entry['facts']:
            role = fact['source_role']
            source = profile['sources'][role]
            markers = profile['selected_static_markers'][role]
            if (source['sha256'] != fact['source_sha256']
                    or type(source['bytes']) is not int or not 0 < source['bytes'] <= 1048576
                    or not isinstance(markers, list) or not 1 <= len(markers) <= 32
                    or any(not isinstance(m, str) or not 0 < len(m) <= 1024 for m in markers)
                    or fact['anchor'] not in markers):
                raise ValueError('anchor pin')
            value = profile['static_observations'][fact['field']]
            expected_type = bool if fact['value_type'] == 'bool' else int
            if type(value) is not expected_type or (type(value) is int and abs(value) > 2**53):
                raise ValueError('scalar type')
            output.append({'predicate': fact['predicate'], 'value': value,
                'value_type': fact['value_type'], 'source_role': role,
                'source_sha256': fact['source_sha256'], **FLAGS})
        return {'status': 'historical_candidate', 'stand': stand,
            'source_id': entry['source_id'], 'source_job_id': entry['job_id'],
            'source_case_id': entry['case_id'], 'source_evidence_id': entry['evidence_id'],
            'evidence_sha256': entry['evidence_sha256'], 'facts': output,
            'execution_mode': 'registered_historical_static_profile', **FLAGS}
    except (ValueError, TypeError, KeyError, AttributeError, OSError, UnicodeError, RecursionError):
        return dict(denied, reason='static_source_invalid_or_unavailable')


def read_registered_static_facts(stand):
    """No configurable path exposed to models; no network calls or writes."""
    import job_store
    from stands import get_stand
    try:
        path = Path(job_store.JOBS_DIR).parent / 'static_fact_sources.json'
        if path.is_symlink() or not path.is_file() or path.stat().st_size > 32768:
            raise ValueError('registry unavailable')
        return project_static_facts(path.read_text(encoding='utf-8'), stand,
                                    get_stand(stand)['web_url'], job_store.get_job)
    except (OSError, ValueError, TypeError, AttributeError, KeyError, UnicodeError, RecursionError):
        return {'status': 'unavailable', 'reason': 'static_source_invalid_or_unavailable', **FLAGS}


def render_static_fact_brief(result):
    """Only typed retained values, never free model prose. Not a current-default assertion."""
    if result.get('status') != 'historical_candidate':
        return 'Исторические статические факты недоступны; значение не определено.'
    lines = ['Исторический статический источник; текущий UI/API не проверен.']
    for fact in result['facts']:
        lines.append(f"{fact['predicate']} = {json.dumps(fact['value'])} ({fact['value_type']}); "
                     f"source SHA256 {fact['source_sha256']}")
    lines.append(f"Job {result['source_job_id']}; evidence {result['source_evidence_id']}; "
                 f"evidence SHA256 {result['evidence_sha256']}. Это не разрешение на исполнение и не PASS.")
    return '\n'.join(lines)


def bind_static_facts_to_chunks(result, sources):
    """Caller supplies source-rechecked chunks. Exact retained references, not fuzzy intent.

    This links provenance only, NOT factual agreement with the source or model.
    """
    if result.get('status') != 'historical_candidate':
        return None
    linked = []
    for source in sources[:4]:
        content = source.get('content', '')
        if (not isinstance(content, str) or len(content) > 8192
                or source.get('source_bytes_rechecked') is not True):
            continue
        def exact_reference(value):
            return re.search(r'(?<![A-Za-z0-9_-])' + re.escape(value) + r'(?![A-Za-z0-9_-])', content)
        # Retained reviewed notes also use the explicit legacy Job<ID>/<case>/<evidence> notation.
        # Require the whole exact triple, never an arbitrary substring or omitted case.
        legacy = ('Job' + result['source_job_id'] + '/' + result['source_case_id']
                  + '/' + result['source_evidence_id'])
        if (exact_reference(legacy) or all(exact_reference(result[key])
                for key in ('source_job_id', 'source_evidence_id'))):
            linked.append({key: source[key] for key in
                           ('citation_id', 'source', 'chunk_no', 'source_sha256', 'chunk_sha256')})
    return {**result, 'linked_chunks': linked} if linked else None

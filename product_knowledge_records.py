"""v1 candidate knowledge: bounded contracts, trusted source checks, additive storage.

Not a model tool, promotion engine, exporter, or replacement for legacy facts.
All input narratives remain untrusted. Source integrity is not semantic proof.
"""
from dataclasses import dataclass
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import re
import sqlite3
import unicodedata

DB_PATH = Path('/opt/uqa/product_knowledge/product_knowledge.db')
KINDS = {'contract', 'observed_fact', 'limitation', 'test_experience'}
LEVELS = {'declared_spec', 'runtime_observation', 'hypothesis', 'developer_confirmation'}
MODES = {'document_review', 'live_operator_assisted', 'live_autonomous', 'isolated_fixture'}
SCOPE_FIELDS = {'installation_architecture', 'server_version', 'frontend_version',
                'agent_version', 'plugin_version', 'os', 'os_version', 'agent_architecture',
                'feature_profile', 'document_revision'}
TOKEN = re.compile(r'[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}\Z')
SECRET = re.compile(r'(?i)(-----BEGIN .*PRIVATE KEY|\bbearer\s+\S+|\b(?:password|passwd|token|secret|cookie|authorization)\s*[:=]\s*\S+|://[^/\s]+:[^/@\s]+@)')

def _json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)

def _hash(value):
    return hashlib.sha256(_json(value).encode('utf-8')).hexdigest()

def _text(value, maximum=1024):
    if not isinstance(value, str):
        raise ValueError('string required')
    value = ' '.join(unicodedata.normalize('NFC', value).split())
    if not value or len(value) > maximum or SECRET.search(value) or any(ord(c) < 32 for c in value):
        raise ValueError('invalid or sensitive text')
    return value

def _token(value):
    value = _text(value, 128)
    if not TOKEN.fullmatch(value):
        raise ValueError('stable token required')
    return value

def _keys(value, required, optional=()):
    if not isinstance(value, dict) or not set(required) <= set(value) or set(value) - set(required) - set(optional):
        raise ValueError('invalid contract fields')

def _scalar(value):
    if value is None or type(value) is bool:
        return value
    if type(value) in {int, float}:
        if abs(value) > 2**63 or not math.isfinite(value):
            raise ValueError('invalid number')
        return int(value) if type(value) is float and value.is_integer() else value
    return _text(value, 512)

def _value(value):
    if isinstance(value, list):
        if not 1 <= len(value) <= 16:
            raise ValueError('bounded scalar list required')
        return [_scalar(v) for v in value]
    return _scalar(value)

def validate_record(record):
    """Closed v1 atomic-claim format. Does not declare semantic truth."""
    _keys(record, {'schema_version', 'event_id', 'project_id', 'product_namespace',
                   'concept_id', 'knowledge_kind', 'source_level', 'execution_mode',
                   'scope', 'claim', 'statement', 'sources'})
    if type(record['schema_version']) is not int or record['schema_version'] != 1:
        raise ValueError('unsupported knowledge schema')
    r = {k: _token(record[k]) for k in ('event_id', 'project_id', 'product_namespace', 'concept_id')}
    for field, allowed in [('knowledge_kind', KINDS), ('source_level', LEVELS), ('execution_mode', MODES)]:
        if not isinstance(record[field], str) or record[field] not in allowed:
            raise ValueError('unsupported knowledge classification')
        r[field] = record[field]
    if r['execution_mode'] == 'isolated_fixture' and (r['product_namespace'] != 'uqa' or r['knowledge_kind'] != 'test_experience'):
        raise ValueError('fixture cannot claim product behavior')
    if r['knowledge_kind'] == 'test_experience' and r['product_namespace'] != 'uqa':
        raise ValueError('technical experience must use uqa namespace')
    if r['knowledge_kind'] == 'contract' and r['source_level'] != 'declared_spec':
        raise ValueError('contract requires declared specification')
    if r['source_level'] == 'runtime_observation' and r['execution_mode'] == 'document_review':
        raise ValueError('document review is not runtime observation')
    scope = record['scope']
    if not isinstance(scope, dict) or not scope or set(scope) - SCOPE_FIELDS:
        raise ValueError('explicit bounded scope required')
    r['scope'] = {k: _text(v, 128) for k, v in scope.items()}
    if any(v.casefold() in {'latest', 'main', 'master', '*'} for v in r['scope'].values()):
        raise ValueError('floating scope prohibited; use explicit unknown')
    if 'installation_architecture' in r['scope']:
        r['scope']['installation_architecture'] = r['scope']['installation_architecture'].lower()
    claim = record['claim']
    _keys(claim, {'predicate', 'conditions', 'value'}, {'unit', 'issue_id'})
    if claim['predicate'] in {'issue_classification', 'declared_fix_version'}:
        if r['source_level'] != 'developer_confirmation' or r['knowledge_kind'] != 'limitation' or 'issue_id' not in claim:
            raise ValueError('issue classification/fix declaration requires developer source and issue identity')
        if claim['predicate'] == 'issue_classification' and claim['value'] not in {'confirmed_bug', 'not_a_bug', 'needs_information'}:
            raise ValueError('explicit developer issue decision required')
        if claim['predicate'] == 'declared_fix_version' and (not isinstance(claim['value'], str)
                or claim['value'].casefold() in {'unknown','latest','main','*'}):
            raise ValueError('explicit declared fix version required')
    if claim['predicate'] == 'fix_verification' and (r['source_level'] != 'runtime_observation' or 'issue_id' not in claim):
        raise ValueError('fix verification requires runtime source and issue identity')
    if not isinstance(claim['conditions'], list) or len(claim['conditions']) > 16:
        raise ValueError('bounded conditions required')
    conditions = []
    for c in claim['conditions']:
        _keys(c, {'field', 'operator', 'value'}, {'unit'})
        if c['operator'] not in {'eq', 'ne', 'lt', 'lte', 'gt', 'gte', 'in'}:
            raise ValueError('unsupported condition operator')
        v = _value(c['value'])
        if c['operator'] == 'in':
            if not isinstance(v, list):
                raise ValueError('in requires a list')
            v = sorted({_json(x): x for x in v}.values(), key=_json)
        elif isinstance(v, list):
            raise ValueError('only in accepts condition lists')
        conditions.append({'field': _token(c['field']), 'operator': c['operator'], 'value': v,
                           **({'unit': _token(c['unit'])} if 'unit' in c else {})})
    conditions = sorted({_json(c): c for c in conditions}.values(), key=_json)
    r['claim'] = {'predicate': _token(claim['predicate']), 'conditions': conditions,
                  'value': _value(claim['value']), **({'unit': _token(claim['unit'])} if 'unit' in claim else {}),
                  **({'issue_id': _token(claim['issue_id'])} if 'issue_id' in claim else {})}
    r['statement'] = _text(record['statement'])
    if not isinstance(record['sources'], list) or not 1 <= len(record['sources']) <= 4:
        raise ValueError('one to four source references required')
    r['sources'] = record['sources']
    r['schema_version'] = 1
    if len(_json(r).encode('utf-8')) > 16384:
        raise ValueError('knowledge record over budget')
    return r

@dataclass(frozen=True)
class DocumentSource:
    """Trusted operator registry entry, NEVER supplied as model metadata."""
    source_id: str
    relative_path: str
    sha256: str
    source_type: str  # official_document or curated_note
    publisher: str
    revision: str
    applicability: tuple = ()  # Trusted explicit (scope_field, value) declarations.
    approval_role: str | None = None

@dataclass(frozen=True)
class SourcePolicy:
    project_id: str
    document_root: Path
    documents: tuple = ()
    jobs_root: Path | None = None
    allowed_namespaces: tuple = ()

def _read_file(root, relative, maximum):
    root = Path(root).resolve(strict=True)
    relative = Path(relative)
    if relative.is_absolute() or '..' in relative.parts:
        raise ValueError('source path escaped root')
    path = (root / relative).resolve(strict=True)
    path.relative_to(root)
    if not path.is_file() or path.stat().st_size > maximum:
        raise ValueError('invalid or oversized source')
    data = path.read_bytes()
    if len(data) > maximum:
        raise ValueError('source changed beyond budget')
    return data

def validate_sources(record, policy):
    """Checks provenance integrity/eligibility only, NOT entailment of a claim."""
    if not isinstance(policy, SourcePolicy) or record['project_id'] != policy.project_id:
        raise ValueError('trusted source policy project mismatch')
    if not policy.allowed_namespaces or record['product_namespace'] not in policy.allowed_namespaces:
        raise ValueError('product namespace not approved by source policy')
    checked = []
    registry = {d.source_id: d for d in policy.documents}
    if len(registry) != len(policy.documents):
        raise ValueError('ambiguous source registry')
    for ref in record['sources']:
        if not isinstance(ref, dict):
            raise ValueError('source reference required')
        if ref.get('kind') == 'document':
            _keys(ref, {'kind', 'source_id', 'sha256'})
            spec = registry.get(ref['source_id'])
            if spec is None or spec.source_type not in {'official_document', 'curated_note', 'developer_confirmation'}:
                raise ValueError('unregistered source')
            if Path(spec.relative_path).suffix.lower() not in {'.docx', '.pdf', '.xlsx', '.md', '.txt'}:
                raise ValueError('unsupported source type')
            raw = _read_file(policy.document_root, spec.relative_path, 32 * 1024 * 1024)
            digest = hashlib.sha256(raw).hexdigest()
            if digest != spec.sha256 or digest != ref['sha256']:
                raise ValueError('source revision/hash mismatch')
            if record['source_level'] == 'declared_spec' and spec.source_type != 'official_document':
                raise ValueError('declared specification requires approved official source')
            if spec.source_type == 'developer_confirmation' and spec.approval_role != 'developer':
                raise ValueError('developer attribution must be approved in trusted registry')
            if record['scope'].get('document_revision') != spec.revision:
                raise ValueError('document revision scope mismatch')
            applicability = dict(spec.applicability)
            for field, value in record['scope'].items():
                if field != 'document_revision' and value != 'unknown' and applicability.get(field) != value:
                    raise ValueError('document does not establish this applicability')
            checked.append({'kind': 'document', 'source_id': _token(spec.source_id), 'sha256': digest,
                            'source_type': spec.source_type, 'publisher': _text(spec.publisher, 256),
                            'revision': _text(spec.revision, 128), 'applicability': applicability,
                            'approval_role': spec.approval_role,
                            'confirmation_group': 'doc:' + digest})
        elif ref.get('kind') == 'runtime_evidence':
            _keys(ref, {'kind', 'job_id', 'case_id', 'evidence_id'})
            if policy.jobs_root is None or not re.fullmatch(r'\d{8}-\d{6}-[0-9a-f]{8}', str(ref['job_id'])):
                raise ValueError('runtime source not permitted')
            job = json.loads(_read_file(policy.jobs_root, ref['job_id'] + '.json', 8 * 1024 * 1024))
            if job.get('job_id') != ref['job_id']:
                raise ValueError('job identity mismatch')
            cases = [c for c in job.get('test_cases', []) if c.get('case_id') == ref['case_id']]
            if len(cases) != 1:
                raise ValueError('exact source case required')
            case = cases[0]
            evidence = [e for e in case.get('evidence', []) if e.get('evidence_id') == ref['evidence_id']]
            if len(evidence) != 1 or evidence[0].get('usable_for_verdict') is not True:
                raise ValueError('eligible runtime evidence required')
            e = evidence[0]
            envelope = json.loads(e['value'])
            result = envelope.get('result', {})
            if not isinstance(result, dict) or result.get('response_body_truncated') or result.get('evidence_truncated'):
                raise ValueError('truncated evidence prohibited')
            if (envelope.get('tool') != 'browser_get_network_detail' or result.get('method') != 'GET'
                    or type(result.get('status')) is not int or not 200 <= result['status'] < 300
                    or not result.get('session_id') or not result.get('request_id')
                    or envelope.get('arguments', {}).get('request_id') != result['request_id']):
                raise ValueError('supported native read receipt required')
            body = json.loads(result['response_body'])
            if not isinstance(body, (dict, list)):
                raise ValueError('structured native response required')
            if not isinstance(e.get('observation_ids'), list) or not e['observation_ids']:
                raise ValueError('runtime observations required')
            observations = {o.get('observation_id') for o in case.get('observations', [])}
            if not set(e['observation_ids']) <= observations:
                raise ValueError('missing linked observation')
            identity = job.get('stand_identity') or {}
            if any(record['scope'].get(k, 'unknown') != 'unknown' for k in ('installation_architecture', 'server_version', 'frontend_version')):
                if identity.get('status') != 'ok' or identity.get('deployment_partial'):
                    raise ValueError('usable runtime identity required')
            if record['scope'].get('frontend_version', 'unknown') != 'unknown' and identity.get('frontend_status') != 'ok':
                raise ValueError('usable frontend identity required')
            for key in ('installation_architecture', 'server_version', 'frontend_version'):
                requested = record['scope'].get(key, 'unknown')
                if requested != 'unknown' and identity.get(key) != requested:
                    raise ValueError('runtime version identity mismatch')
            # Existing passports do not prove per-agent/plugin/OS identity here.
            if any(record['scope'].get(k, 'unknown') != 'unknown' for k in ('agent_version', 'plugin_version', 'os', 'os_version', 'agent_architecture')):
                raise ValueError('specialized runtime scope validator not implemented')
            if record['execution_mode'] == 'isolated_fixture':
                raise ValueError('fixture sources require separate future adapter')
            checked.append({'kind': 'runtime_evidence', 'job_id': _token(ref['job_id']),
                            'case_id': _token(ref['case_id']), 'evidence_id': _token(ref['evidence_id']),
                            'sha256': _hash(envelope), 'confirmation_group': 'run:' + ref['job_id']})
        else:
            raise ValueError('unsupported source adapter')
    if record['source_level'] == 'runtime_observation' and not any(s['kind'] == 'runtime_evidence' for s in checked):
        raise ValueError('runtime claim requires checked runtime evidence')
    if record['source_level'] == 'declared_spec' and not any(s.get('source_type') == 'official_document' for s in checked):
        raise ValueError('declared specification requires checked official document')
    if record['source_level'] == 'developer_confirmation' and not any(s.get('source_type') == 'developer_confirmation' for s in checked):
        raise ValueError('developer assertion requires approved developer confirmation')
    return sorted({_json(s): s for s in checked}.values(), key=_json)

DDL = (
    'CREATE TABLE IF NOT EXISTS knowledge_v1_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)',
    'CREATE TABLE IF NOT EXISTS knowledge_v1_claims (claim_id TEXT PRIMARY KEY, identity_json TEXT NOT NULL)',
    '''CREATE TABLE IF NOT EXISTS knowledge_v1_variants (variant_id TEXT PRIMARY KEY,
       claim_id TEXT NOT NULL REFERENCES knowledge_v1_claims(claim_id), value_json TEXT NOT NULL,
       statement TEXT NOT NULL, created_at TEXT NOT NULL)''',
    '''CREATE TABLE IF NOT EXISTS knowledge_v1_scopes (variant_id TEXT NOT NULL REFERENCES knowledge_v1_variants(variant_id),
       scope_id TEXT NOT NULL, scope_json TEXT NOT NULL, source_level TEXT NOT NULL,
       status TEXT NOT NULL CHECK(status IN ('candidate','conflict')), PRIMARY KEY(variant_id,scope_id,source_level))''',
    '''CREATE TABLE IF NOT EXISTS knowledge_v1_sources (source_revision_id TEXT PRIMARY KEY,
       manifest_json TEXT NOT NULL, created_at TEXT NOT NULL)''',
    '''CREATE TABLE IF NOT EXISTS knowledge_v1_supports (variant_id TEXT NOT NULL, scope_id TEXT NOT NULL,
       source_level TEXT NOT NULL, source_revision_id TEXT NOT NULL REFERENCES knowledge_v1_sources(source_revision_id),
       confirmation_group TEXT NOT NULL, first_seen_at TEXT NOT NULL, last_seen_at TEXT NOT NULL,
       PRIMARY KEY(variant_id,scope_id,source_level,source_revision_id))''',
    '''CREATE TABLE IF NOT EXISTS knowledge_v1_events (event_id TEXT PRIMARY KEY, input_sha256 TEXT NOT NULL,
       variant_id TEXT NOT NULL, scope_id TEXT NOT NULL, source_level TEXT NOT NULL,
       execution_mode TEXT NOT NULL, created_at TEXT NOT NULL)''',
    'CREATE INDEX IF NOT EXISTS knowledge_v1_variants_claim ON knowledge_v1_variants(claim_id)',
    """CREATE INDEX IF NOT EXISTS knowledge_v1_claim_lookup ON knowledge_v1_claims(
       json_extract(identity_json,'$.project_id'),json_extract(identity_json,'$.product_namespace'),
       json_extract(identity_json,'$.concept_id'))""",
)

@contextmanager
def _connect(db_path):
    con = sqlite3.connect(db_path, timeout=10)
    try:
        con.execute('PRAGMA foreign_keys=ON')
        with con:
            yield con
    finally:
        con.close()

def initialize_schema(db_path=DB_PATH):
    """Explicit additive migration. Never updates or reclassifies legacy tables."""
    with _connect(db_path) as con:
        con.execute('BEGIN IMMEDIATE')
        for sql in DDL:
            con.execute(sql)
        version = con.execute("SELECT value FROM knowledge_v1_meta WHERE key='schema_version'").fetchone()
        if version is not None and version != ('1',):
            raise ValueError('incompatible knowledge schema')
        con.execute("INSERT OR IGNORE INTO knowledge_v1_meta VALUES('schema_version','1')")

def ingest_record(record, policy, db_path=DB_PATH):
    """Atomic candidate-only sink; no legacy writes, index updates, or stand actions."""
    r = validate_record(record)
    sources = validate_sources(r, policy)
    fingerprint = _hash(r)
    identity = {k: r[k] for k in ('project_id', 'product_namespace', 'concept_id', 'knowledge_kind')}
    identity['claim'] = {k: v for k, v in r['claim'].items() if k != 'value'}
    claim_id = 'kc-' + _hash(identity)
    variant_id = 'kv-' + _hash({'claim_id': claim_id, 'value': r['claim']['value']})
    scope_id = _hash(r['scope'])
    event_id = _json([r['project_id'], r['event_id']])
    now = datetime.now(timezone.utc).isoformat()
    with _connect(db_path) as con:
        con.execute('BEGIN IMMEDIATE')
        if con.execute("SELECT value FROM knowledge_v1_meta WHERE key='schema_version'").fetchone() != ('1',):
            raise ValueError('explicit schema initialization required')
        previous = con.execute('SELECT input_sha256 FROM knowledge_v1_events WHERE event_id=?', (event_id,)).fetchone()
        if previous:
            if previous[0] != fingerprint:
                raise ValueError('event replay payload mismatch; new outcome revision required')
            return {'duplicate_event': True, 'claim_id': claim_id, 'variant_id': variant_id, 'evidence_for_pass': False}
        con.execute('INSERT OR IGNORE INTO knowledge_v1_claims VALUES(?,?)', (claim_id, _json(identity)))
        con.execute('INSERT OR IGNORE INTO knowledge_v1_variants VALUES(?,?,?,?,?)',
                    (variant_id, claim_id, _json(r['claim']['value']), r['statement'], now))
        con.execute('INSERT OR IGNORE INTO knowledge_v1_scopes VALUES(?,?,?,?,?)',
                    (variant_id, scope_id, _json(r['scope']), r['source_level'], 'candidate'))
        variants = con.execute('''SELECT s.variant_id FROM knowledge_v1_scopes s JOIN knowledge_v1_variants v
                    ON v.variant_id=s.variant_id WHERE v.claim_id=? AND s.scope_id=? AND s.source_level=?''',
                    (claim_id, scope_id, r['source_level'])).fetchall()
        if len(variants) > 1:
            con.executemany("UPDATE knowledge_v1_scopes SET status='conflict' WHERE variant_id=? AND scope_id=? AND source_level=?",
                            [(v[0], scope_id, r['source_level']) for v in variants])
        for source in sources:
            source_id = 'ks-' + _hash({'project_id': r['project_id'], 'manifest': source})
            con.execute('INSERT OR IGNORE INTO knowledge_v1_sources VALUES(?,?,?)', (source_id, _json(source), now))
            con.execute('''INSERT INTO knowledge_v1_supports VALUES(?,?,?,?,?,?,?)
                ON CONFLICT(variant_id,scope_id,source_level,source_revision_id) DO UPDATE SET last_seen_at=excluded.last_seen_at''',
                (variant_id, scope_id, r['source_level'], source_id, source['confirmation_group'], now, now))
        con.execute('INSERT INTO knowledge_v1_events VALUES(?,?,?,?,?,?,?)',
                    (event_id, fingerprint, variant_id, scope_id, r['source_level'], r['execution_mode'], now))
        status = con.execute('SELECT status FROM knowledge_v1_scopes WHERE variant_id=? AND scope_id=? AND source_level=?',
                             (variant_id, scope_id, r['source_level'])).fetchone()[0]
        independent = con.execute('''SELECT COUNT(DISTINCT confirmation_group) FROM knowledge_v1_supports
                   WHERE variant_id=? AND scope_id=? AND source_level=?''', (variant_id, scope_id, r['source_level'])).fetchone()[0]
    return {'duplicate_event': False, 'claim_id': claim_id, 'variant_id': variant_id, 'scope_id': scope_id,
            'status': status, 'confirmation_group_count': independent, 'evidence_for_pass': False,
            'semantic_claim_verified': False, 'search_published': False}

def read_history(project_id, product_namespace, concept_id, db_path=DB_PATH, limit=20):
    """Bounded read-only operator history; not model retrieval or upgrade advice."""
    project_id, product_namespace, concept_id = map(_token, (project_id, product_namespace, concept_id))
    if type(limit) is not int or not 1 <= limit <= 50:
        raise ValueError('bounded history limit required')
    path = Path(db_path).resolve(strict=True)
    con = sqlite3.connect(path.as_uri() + '?mode=ro', uri=True, timeout=2)
    try:
        rows = con.execute('''SELECT c.identity_json,v.variant_id,v.value_json,v.statement,
             s.scope_json,s.source_level,s.status,MIN(p.first_seen_at),MAX(p.last_seen_at),
             COUNT(DISTINCT p.confirmation_group)
             FROM knowledge_v1_claims c JOIN knowledge_v1_variants v ON v.claim_id=c.claim_id
             JOIN knowledge_v1_scopes s ON s.variant_id=v.variant_id
             JOIN knowledge_v1_supports p ON p.variant_id=s.variant_id AND p.scope_id=s.scope_id AND p.source_level=s.source_level
             WHERE json_extract(c.identity_json,'$.project_id')=?
               AND json_extract(c.identity_json,'$.product_namespace')=?
               AND json_extract(c.identity_json,'$.concept_id')=?
             GROUP BY v.variant_id,s.scope_id,s.source_level ORDER BY MAX(p.last_seen_at) DESC,v.variant_id LIMIT ?''',
             (project_id,product_namespace,concept_id,limit+1)).fetchall()
        results = []
        for r in rows[:limit]:
            scope = json.loads(r[4])
            refs = con.execute('''SELECT a.manifest_json FROM knowledge_v1_sources a JOIN knowledge_v1_supports p
               ON p.source_revision_id=a.source_revision_id WHERE p.variant_id=? AND p.scope_id=? AND p.source_level=?
               ORDER BY p.last_seen_at DESC,p.source_revision_id LIMIT 4''', (r[1], _hash(scope), r[5])).fetchall()
            results.append({'identity':json.loads(r[0]), 'variant_id':r[1], 'value':json.loads(r[2]),
                  'statement':r[3], 'scope':scope, 'source_level':r[5], 'status':r[6],
                  'first_seen_at':r[7], 'last_seen_at':r[8], 'confirmation_group_count':r[9],
                  'source_refs':[json.loads(s[0]) for s in refs[:3]], 'source_refs_limited':len(refs)>3,
                  'execution_modes':[mode[0] for mode in con.execute(
                      'SELECT DISTINCT execution_mode FROM knowledge_v1_events WHERE variant_id=? AND scope_id=? AND source_level=? ORDER BY execution_mode LIMIT 5',
                      (r[1],_hash(scope),r[5])).fetchall()]})
        return {'status':'ok','results':results,
                'has_more':len(rows)>limit, 'evidence_for_pass':False, 'upgrade_advice_authorized':False}
    finally:
        con.close()

"""Bounded read-only retrieval; remembered facts are hints, never evidence."""
import json
import re
import sqlite3
from pathlib import Path
from knowledge_fact_contracts import FIELDS, sanitize_memory_fact, confirmation_matches_frontend

DB_PATH = Path('/opt/uqa/product_knowledge/product_knowledge.db')


def retrieve_product_knowledge(query, identity, limit=3, db_path=None):
    result = {'status': 'unavailable', 'results': [], 'evidence_for_pass': False}
    identity = identity if isinstance(identity, dict) else {}
    architecture = identity.get('installation_architecture')
    version = identity.get('server_version')
    frontend = identity.get('frontend_version')
    frontend_required = 'frontend_status' in identity or 'frontend_version' in identity
    if frontend_required and (identity.get('frontend_status') != 'ok' or not isinstance(frontend, str)
                              or not frontend.strip() or frontend.casefold() in {'latest','dev','main','master'}):
        return dict(result, reason='usable_frontend_identity_required')
    if (identity.get('status') != 'ok' or identity.get('deployment_partial')
            or not isinstance(architecture, str) or not architecture.strip()
            or not isinstance(version, str) or not version.strip()):
        return dict(result, reason='usable_version_identity_required')
    tokens = set(re.findall(r'[\w-]{2,}', str(query or '')[:1000].casefold()))
    if not tokens:
        return dict(result, reason='query_required')
    path = Path(db_path) if db_path is not None else DB_PATH
    try:
        # Do not invoke store APIs here: they perform migrations and WAL writes.
        with sqlite3.connect(path.resolve().as_uri() + '?mode=ro', uri=True, timeout=2) as connection:
            connection.row_factory = sqlite3.Row
            rows = connection.execute('''
                SELECT f.fact_key, f.fact_type, f.data_json, s.verified_at
                FROM facts f JOIN fact_scopes s ON s.fact_key=f.fact_key
                WHERE s.status='verified' AND s.installation_architecture=?
                  AND s.server_version=? AND s.conflict_at IS NULL
                  AND s.deprecated_at IS NULL AND s.verified_at IS NOT NULL
                ORDER BY s.last_seen_at DESC, f.fact_key LIMIT 201
            ''', (architecture.strip().lower(), version.strip())).fetchall()
            ranked = []
            frontend_recheck = 0
            for row in rows[:200]:
                kind = row['fact_type']
                if kind not in FIELDS or (kind == 'ui_navigation' and not frontend_required):
                    continue  # No unvalidated arbitrary fact payloads in a prompt.
                data = json.loads(row['data_json'])
                if not isinstance(data, dict):
                    continue
                safe = sanitize_memory_fact(kind,data)
                terms = set(re.findall(r'[\w-]{2,}', ' '.join(
                    ' '.join(v) if isinstance(v,list) else v for v in safe.values()).casefold()))
                score = len(tokens & terms)
                if not score:
                    continue
                source_fields = 'job_id, case_id' + (', stand_identity_json, verification_json, source_observation_ids_json' if frontend_required else '')
                sources = connection.execute(f'''
                    SELECT {source_fields} FROM confirmations WHERE fact_key=?
                      AND installation_architecture=? AND server_version=?
                      AND COALESCE(deployment_partial,0)=0
                    ORDER BY created_at DESC LIMIT 12
                ''', (row['fact_key'], architecture.strip().lower(), version.strip())).fetchall()
                if frontend_required:
                    compatible = [source for source in sources if confirmation_matches_frontend(source,kind,identity)]
                    if kind == 'ui_navigation' and len({s['job_id'] for s in compatible if s['job_id']}) < 2:
                        compatible = []
                    if not compatible:
                        frontend_recheck += 1
                    sources = compatible
                if not sources:
                    continue
                ranked.append((score, {
                    'fact_key': row['fact_key'], 'fact_type': row['fact_type'],
                    'data': safe, 'scope': {'installation_architecture': architecture.strip().lower(),
                                          'server_version': version.strip(),
                                          **({'frontend_version': frontend} if frontend_required else {})},
                    'source_cases': [{k:source[k] for k in ('job_id','case_id')} for source in sources[:3]],
                    'usage': 'untrusted_navigation_hint_recheck_in_current_UI',
                }))
        ranked.sort(key=lambda item: (-item[0], item[1]['fact_key']))
        return dict(result, status='ok', results=[item[1] for item in ranked[:max(1, min(int(limit), 5))]],
                    candidate_scan_complete=len(rows) <= 200,
                    scope_excludes_frontend_version=not frontend_required,
                    frontend_version=frontend if frontend_required else None,
                    frontend_recheck_needed_count=frontend_recheck,
                    reason='frontend_scope_not_confirmed' if frontend_recheck and not ranked else None)
    except (sqlite3.Error, OSError, ValueError, TypeError):
        return dict(result, reason='memory_store_unavailable_or_invalid')

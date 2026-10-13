"""Navigation requires repeated Core proof for the same frontend tag."""
import json
import re
import sqlite3
from pathlib import Path
from knowledge_fact_contracts import sanitize_memory_fact, confirmation_matches_frontend

DB_PATH=Path('/opt/uqa/product_knowledge/product_knowledge.db')


def evaluate_navigation_scope(fact_key,identity,db_path=None):
    identity=identity if isinstance(identity,dict) else {}
    result={'decision':'insufficient_evidence','fact_key':fact_key,'distinct_job_count':0}
    if (identity.get('status')!='ok' or identity.get('deployment_partial')
            or identity.get('frontend_status')!='ok' or not identity.get('frontend_version')
            or not re.fullmatch(r'\d+\.\d+\.\d+(?:[-+][A-Za-z0-9.-]+)?',str(identity.get('frontend_version')))
            or not identity.get('installation_architecture') or not identity.get('server_version')):
        return dict(result,decision='identity_unavailable')
    try:
        path=Path(db_path or DB_PATH)
        with sqlite3.connect(path.resolve().as_uri()+'?mode=ro',uri=True,timeout=2) as connection:
            connection.row_factory=sqlite3.Row
            fact=connection.execute('''SELECT f.fact_type,f.data_json,s.status,s.conflict_at,s.deprecated_at
                FROM facts f JOIN fact_scopes s ON s.fact_key=f.fact_key
                WHERE f.fact_key=? AND s.installation_architecture=? AND s.server_version=?''',
                (fact_key,identity['installation_architecture'],identity['server_version'])).fetchone()
            if (not fact or fact['fact_type']!='ui_navigation' or fact['status'] not in ('candidate','verified')
                    or fact['conflict_at'] or fact['deprecated_at']
                    or not sanitize_memory_fact('ui_navigation',json.loads(fact['data_json']))):
                return dict(result,decision='fact_or_scope_ineligible')
            rows=connection.execute('''SELECT job_id,case_id,stand_identity_json,verification_json,
                source_observation_ids_json FROM confirmations WHERE fact_key=?
                AND installation_architecture=? AND server_version=? AND COALESCE(deployment_partial,0)=0
                ORDER BY created_at DESC LIMIT 2001''',
                (fact_key,identity['installation_architecture'],identity['server_version'])).fetchall()
        if len(rows)>2000:
            return dict(result,decision='bounded_confirmation_scan_incomplete')
        jobs={r['job_id'] for r in rows if r['job_id'] and r['case_id']
              and confirmation_matches_frontend(r,'ui_navigation',identity)}
        return dict(result,decision='eligible' if len(jobs)>=2 else 'insufficient_evidence',
                    distinct_job_count=len(jobs),scope_status=fact['status'],frontend_version=identity['frontend_version'])
    except (sqlite3.Error,OSError,ValueError,TypeError):
        return dict(result,decision='memory_store_unavailable_or_invalid')


def promote_navigation_scope(fact_key,identity,db_path=None,setter=None):
    decision=evaluate_navigation_scope(fact_key,identity,db_path)
    if decision['decision']!='eligible':
        return {'action':'not_eligible','changed':False,'decision':decision}
    if decision['scope_status']=='verified':
        return {'action':'already_verified','changed':False,'decision':decision}
    if setter is None:
        from product_knowledge_store import set_fact_scope_status
        setter=set_fact_scope_status
    setter(fact_key=fact_key,installation_architecture=identity['installation_architecture'],
           server_version=identity['server_version'],status='verified',source='navigation_runtime_validator',
           reason='Two distinct Core-proven Jobs for frontend '+identity['frontend_version'],decision=decision)
    return {'action':'promoted','changed':True,'decision':decision}

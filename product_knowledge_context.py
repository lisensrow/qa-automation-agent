"""Source-rechecked, bounded specification hints; never verdict evidence.

Product vocabulary belongs to this adapter, not execution Core. Only the
operator-reviewed subset of declarations is exposed. No mutations/migrations.
"""
import hashlib
from pathlib import Path
import sqlite3

from product_knowledge_records import DocumentSource, SourcePolicy, read_history

GUIDE = DocumentSource(
    'uc.user-guide.2026-07-06',
    'UQA-docs/UC Руководство пользователя от 06.07.2026.docx',
    '41bfa19668d6ac1550477fe78b4773f560c1c655dfd4f21df58b71e1fd1a5a6e',
    'official_document', 'U-Connect user guide', '2026-07-06')
POLICY = SourcePolicy('u-connect', Path('/opt/uqa/knowledge/source'), (GUIDE,),
                      allowed_namespaces=('u-connect',))
CONCEPTS = {
    'collections.membership': {
        'terms': ('коллекц', 'collection'),
        'search_query': 'коллекции создание',
        'experience_query': 'коллекция Manual Table fields',
        'claims': {'composition_formula': 'automatic_plus_manual_minus_exclusions',
                   'clear_on_update_semantics': 'recompute_not_accumulate'},
    },
    'policies.configuration': {
        'terms': ('политик', 'policy', 'policies'),
        'search_query': 'политики создание',
        'claims': {'supported_types': ['agent_configuration', 'agent_task_update', 'agent_plugin_management'],
                   'condition_logic': 'same_as_collection_conditions'},
    },
    'procedures.execution': {
        'terms': ('процедур', 'procedure'),
        'search_query': 'процедуры создание',
        'claims': {'definition_kind': 'template_not_execution_instance',
                   'target_kind': 'collection',
                   'target_membership_time': 'snapshot_at_launch',
                   'minimum_blocks': 2},
    },
}


def reviewed_search_queries(task):
    """Bounded product vocabulary; does not authorize an action or route."""
    if not isinstance(task, str):
        return []
    # Restrictions are not requests to explore those product surfaces.
    import re
    positive = ' '.join(re.split(r'(?iu)\b(?:не|без|никаких|нельзя|never|without|do not|no)\b', clause, 1)[0]
                        for clause in re.split(r'[.!?;\n]+', task[:12000])).casefold()
    queries = []
    for spec in CONCEPTS.values():
        if any(term in positive for term in spec['terms']):
            queries.append(spec['search_query'])
            if spec.get('experience_query'):
                queries.append(spec['experience_query'])
    return queries[:3]


def retrieve_declared_context(query, db_path=None, *, policy=POLICY, concepts=None):
    """Trusted policy/vocabulary are application configuration, never tool input."""
    result = {'status': 'unavailable', 'results': [], 'evidence_for_pass': False,
              'semantic_claim_verified': False, 'upgrade_advice_authorized': False,
              'current_runtime_applicability_verified': False}
    if not isinstance(query, str) or not query.strip():
        return dict(result, reason='query_required')
    vocabulary = CONCEPTS if concepts is None else concepts
    matches = [key for key, spec in vocabulary.items()
               if any(term.casefold() in query[:1000].casefold() for term in spec['terms'])]
    if not matches:
        return dict(result, status='ok', reason='no_reviewed_concept')
    try:
        # Recheck approved bytes, not just the manifest stored at admission.
        approved = {}
        root = Path(policy.document_root).resolve(strict=True)
        for source in policy.documents:
            if source.source_type != 'official_document':
                continue
            path = (root / source.relative_path).resolve(strict=True)
            if not path.is_relative_to(root) or path.stat().st_size > 32 * 1024 * 1024:
                continue
            if hashlib.sha256(path.read_bytes()).hexdigest() == source.sha256:
                approved[source.source_id] = source
        if not approved:
            return dict(result, reason='approved_source_unavailable_or_changed')
        hints = []
        for concept in matches[:3]:
            for namespace in policy.allowed_namespaces[:3]:
                kwargs = {'db_path': db_path} if db_path is not None else {}
                history = read_history(policy.project_id, namespace, concept, limit=20, **kwargs)
                for item in history['results']:
                    identity = item['identity']
                    claim = identity.get('claim', {})
                    expected = vocabulary[concept]['claims'].get(claim.get('predicate'))
                    if (item['status'] != 'candidate' or item['source_level'] != 'declared_spec'
                            or identity.get('knowledge_kind') != 'contract'
                            or expected is None or item['value'] != expected
                            or claim.get('conditions') or claim.get('issue_id') or claim.get('unit')):
                        continue
                    refs = []
                    for ref in item['source_refs']:
                        source = approved.get(ref.get('source_id'))
                        if (source and ref.get('kind') == 'document'
                                and ref.get('source_type') == 'official_document'
                                and ref.get('sha256') == source.sha256
                                and ref.get('revision') == source.revision
                                and item['scope'] == {'document_revision': source.revision}):
                            refs.append({'source_id': source.source_id, 'sha256': source.sha256,
                                         'document_revision': source.revision})
                    if not refs:
                        continue
                    # Do not pass arbitrary stored prose or issue assertions to the model.
                    hints.append({'concept_id': concept, 'predicate': claim['predicate'],
                                  'declared_value': expected, 'scope': item['scope'],
                                  'status': 'candidate_declared_spec', 'source_refs': refs[:2],
                                  'usage': 'untrusted_spec_hint_read_manual_and_recheck_current_product'})
        return dict(result, status='ok', results=hints[:5],
                    reason=None if hints else 'no_eligible_declarations')
    except (OSError, sqlite3.Error, ValueError, TypeError, KeyError):
        return dict(result, reason='declaration_store_unavailable_or_invalid')

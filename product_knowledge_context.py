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
        'experience_query': 'наблюдённый маршрут поля коллекции',
        'read_query': 'просмотр существующей коллекции привязка таблицы',
        'read_intent': r'\b(?:откр\w*|прочит\w*|прочест\w*|просмотр\w*|open|read|inspect|view)\b',
        'create_intent': r'\b(?:созда\w*|нов\w*|create|creation|new)\b',
        'layout_intent': r'\b(?:колон\w*|столбц\w*|column\w*|layout|table\s+(?:fields|headers)|поля\s+таблиц\w*)\b',
        'layout_query': 'колонки коллекции каталог полей',
        'task_facets': (
            (r'\bram\b|оперативн\w*\s+памят', 'RAM агрегаты единицы отсутствие данных'),
            (r'\bcpu\b|процессор\w*|\bядр\w*', 'CPU не спутать CI ядра текущую нагрузку'),
        ),
        'facet_base_query': 'логика условий состава коллекций',
        'claims': {'composition_formula': 'automatic_plus_manual_minus_exclusions',
                   'clear_on_update_semantics': 'recompute_not_accumulate'},
    },
    'collections.form': {
        'terms': ('коллекц', 'collection'),
        'claims': {'name_field_panel': 'Settings', 'filter_panel': 'Conditions',
                   'table_layout_panel': 'Table fields'},
    },
    'policies.configuration': {
        'terms': ('политик', 'policy', 'policies'),
        'search_query': 'политики создание',
        'experience_query': 'наблюдённый маршрут формы политики',
        'task_facets': (
            (r'по\s+умолчан\w*|\bdefaults?\b|активн\w*|\b(?:activation|active|inactive)\b|\bsubmit\b|\blauncher\b|сохранени\w*',
             'политика открытие редактора отдельный submit активность по умолчанию'),
        ),
        'claims': {'supported_types': ['agent_configuration', 'agent_task_update', 'agent_plugin_management'],
                   'condition_logic': 'same_as_collection_conditions'},
    },
    'procedures.execution': {
        'terms': ('процедур', 'procedure'),
        'search_query': 'процедуры создание',
        'experience_query': 'наблюдённый маршрут формы процедуры',
        'claims': {'definition_kind': 'template_not_execution_instance',
                   'target_kind': 'collection',
                   'target_membership_time': 'snapshot_at_launch',
                   'minimum_blocks': 2},
    },
}

PLUGIN_REVIEWED_TOPIC = {
    'terms': ('плагин', 'plugin'),
    'search_query': 'плагины агента инвентаризация обновление полный результат задачи',
    'task_facets': (
        (r'верси\w*|\bversions?\b|загруз\w*|\bload\w*', 'версия и загрузка плагина разные проверки'),
        (r'задач\w*|результат\w*|\btasks?\b|\bresults?\b|\bfetch\b', 'создание задания не является проверкой его результата'),
    ),
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
    def first_mention(spec):
        positions = [positive.find(term) for term in spec['terms'] if term in positive]
        return min(positions) if positions else len(positive) + 1
    # User topic order, not dictionary order, decides which domain gets the
    # bounded budget first. A collection used as scope must not hide a policy.
    # Reviewed plugin experience is not an official-guide declaration or claim allowlist.
    for spec in sorted([*CONCEPTS.values(), PLUGIN_REVIEWED_TOPIC], key=first_mention):
        if any(term in positive for term in spec['terms']):
            facets = [query for pattern, query in spec.get('task_facets', ())
                      if re.search(pattern, positive)]
            creating = bool(re.search(spec.get('create_intent', r'(?!)'), positive))
            layout = bool(spec.get('layout_query') and
                          re.search(spec['layout_intent'], positive))
            read_intent = (bool(spec.get('read_query')) and bool(re.search(spec['read_intent'], positive))
                           and not creating)
            if read_intent:
                queries.append(spec['read_query'])
            elif spec.get('search_query') and (not layout or creating):
                queries.append(spec.get('facet_base_query',spec['search_query'])
                               if facets and not layout else spec['search_query'])
            # Keep the same three-query budget. Explicit subject matter takes
            # priority over a generic entry-route recipe; never supply answers.
            if layout:
                queries.append(spec['layout_query'])
            queries.extend(facets)
            if not (read_intent or layout) and spec.get('experience_query'):
                queries.append(spec['experience_query'])
    return queries[:3]


def retrieve_control_location_hint(task, field, db_path=None):
    """Small source-gated location data, not an instruction or permission."""
    aliases = {'name': 'name_field_panel', 'имя': 'name_field_panel',
               'ci class': 'filter_panel', 'archived': 'filter_panel',
               'os name': 'filter_panel', 'класс ке': 'filter_panel'}
    predicate = aliases.get(str(field or '').strip().casefold())
    if (not predicate or CONCEPTS['collections.membership']['search_query']
            not in reviewed_search_queries(task)):
        return {'status':'unavailable','evidence_for_pass':False}
    context = retrieve_declared_context(task, db_path)
    rows = [row for row in context['results'] if row['concept_id']=='collections.form'
            and row['predicate']==predicate]
    if len(rows)!=1:
        return {'status':'unavailable','evidence_for_pass':False}
    row=rows[0]
    return {'status':'candidate_location_hint','requested_control_label':str(field)[:160],
            'document_panel_name':row['declared_value'],'scope':row['scope'],
            'source_refs':row['source_refs'],'evidence_for_pass':False,
            'current_runtime_applicability_verified':False,
            'usage':'Untrusted location hint. Inspect the currently visible panel before navigation; do not repeat input on an unchanged page. A panel hint does not establish an actual control role or business validity.'}


def compact_control_location_hint(hint):
    """Keep bounded location data across observations; drop prose/commands/authority."""
    if (not isinstance(hint,dict) or hint.get('status')!='candidate_location_hint'
            or hint.get('evidence_for_pass') is not False
            or hint.get('current_runtime_applicability_verified') is not False):
        return None
    from product_knowledge_records import _text, _token
    import re
    try:
        refs=[]
        for ref in hint.get('source_refs',[])[:2]:
            if not isinstance(ref,dict) or not re.fullmatch(r'[0-9a-f]{64}',str(ref.get('sha256',''))):
                return None
            refs.append({'source_id':_token(ref['source_id']),'sha256':ref['sha256'],
                         'document_revision':_text(ref['document_revision'],128)})
        if not refs:
            return None
        return {'status':'candidate_location_hint',
                'requested_control_label':_text(hint['requested_control_label'],160),
                'document_panel_name':_text(hint['document_panel_name'],160),
                'source_refs':refs,'evidence_for_pass':False,
                'current_runtime_applicability_verified':False}
    except (ValueError,TypeError,KeyError):
        return None


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

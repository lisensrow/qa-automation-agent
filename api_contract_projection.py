"""Pure bounded structural lookup in a hash-pinned installed-schema projection.

No files, HTTP, credentials, dispatch, permission, promotion, or payload validation.
Pins are supplied by the trusted caller, not proof that the caller is trustworthy.
"""
import hashlib
import json
import re

MAX_BYTES = 1048576
MAX_NODES = 100000
MAX_DEPTH = 24
MAX_OUTPUT_BYTES = 32768
MAX_REFERENCED_SCHEMAS = 20
METHODS = {'get', 'post', 'put', 'patch', 'delete', 'head', 'options', 'trace'}
FLAGS = {'permission_granted': False, 'evidence_for_pass': False,
         'enum_values_exported': False,
         'operation_execution_verified': False, 'business_semantics_verified': False,
         'current_runtime_applicability_verified': False,
         'complete_payload_validation': False, 'authentication_contract_available': False}
IDENTIFIER = re.compile(r'[A-Za-z0-9_.:$-]{1,300}\Z')
HASH = re.compile(r'[0-9a-f]{64}\Z')
REF = re.compile(r'#/components/(schemas|parameters|responses|requestBodies)/([A-Za-z0-9_.-]+)\Z')
MIME = re.compile(r'[A-Za-z0-9.*+-]+/[A-Za-z0-9.*+-]+\Z')


class _Refusal(ValueError):
    pass


def _need(condition, reason):
    if not condition:
        raise _Refusal(reason)


def _keys(value, required, optional=()):
    _need(isinstance(value, dict) and set(required) <= set(value)
          and not set(value) - set(required) - set(optional), 'unsupported_projection_shape')


def _identifier(value):
    _need(isinstance(value, str) and bool(IDENTIFIER.fullmatch(value)), 'invalid_identifier')


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        _need(key not in result, 'duplicate_json_key')
        result[key] = value
    return result


def _walk(root):
    stack = [(root, 0)]
    count = 0
    while stack:
        value, depth = stack.pop()
        count += 1
        _need(count <= MAX_NODES and depth <= MAX_DEPTH, 'projection_node_or_depth_budget')
        yield value
        if isinstance(value, dict):
            _need(all(isinstance(k, str) and len(k) <= 500 for k in value), 'invalid_json_key')
            stack.extend((v, depth + 1) for v in value.values())
        elif isinstance(value, list):
            stack.extend((v, depth + 1) for v in value)
        elif isinstance(value, str):
            _need(len(value) <= 512 and not any(ord(c) < 32 for c in value), 'invalid_projection_string')
        else:
            _need(value is None or type(value) in (bool, int), 'invalid_projection_scalar')


def _schema(value):
    _keys(value, (), ('type', 'format', 'required', 'properties', 'items', 'anyOf', 'allOf',
                      'oneOf', 'enum_count', '$ref', 'projection_truncated'))
    if 'projection_truncated' in value:
        _need(set(value) == {'projection_truncated'} and value['projection_truncated'] is True,
              'invalid_truncation_marker')
        return
    if 'type' in value:
        types = value['type'] if isinstance(value['type'], list) else [value['type']]
        _need(1 <= len(types) <= 8 and all(isinstance(t, str) and t in
              {'object', 'array', 'string', 'number', 'integer', 'boolean', 'null'} for t in types), 'invalid_schema_type')
    if 'format' in value:
        _need(isinstance(value['format'], str) and bool(re.fullmatch(r'[A-Za-z0-9_.-]{1,80}', value['format'])), 'invalid_schema_format')
    if '$ref' in value:
        _need(isinstance(value['$ref'], str) and bool(REF.fullmatch(value['$ref'])), 'external_or_invalid_reference')
    if 'enum_count' in value:
        _need(type(value['enum_count']) is int and 0 <= value['enum_count'] <= 10000, 'invalid_enum_count')
    if 'required' in value:
        _need(isinstance(value['required'], list) and len(value['required']) <= 200, 'invalid_required_fields')
        for item in value['required']:
            _identifier(item)
        _need(len(value['required']) == len(set(value['required'])), 'duplicate_required_field')
    if 'properties' in value:
        _need(isinstance(value['properties'], dict) and len(value['properties']) <= 500, 'invalid_schema_properties')
        for key, child in value['properties'].items():
            _identifier(key)
            _schema(child)
    if 'items' in value:
        _schema(value['items'])
    for key in ('anyOf', 'allOf', 'oneOf'):
        if key in value:
            _need(isinstance(value[key], list) and 1 <= len(value[key]) <= 100, 'invalid_schema_union')
            for child in value[key]:
                _schema(child)


def _content(value):
    _need(isinstance(value, dict) and len(value) <= 16, 'invalid_content_map')
    for mime, item in value.items():
        _need(bool(MIME.fullmatch(mime)), 'invalid_media_type')
        _schema(item)


def _schema_nodes(root):
    """Walk typed schema nodes, never mistake a property named $ref for a reference."""
    stack = [root]
    while stack:
        node = stack.pop()
        yield node
        stack.extend(node.get('properties', {}).values())
        if 'items' in node:
            stack.append(node['items'])
        for key in ('anyOf', 'allOf', 'oneOf'):
            stack.extend(node.get(key, []))


def _operation(value):
    _keys(value, ('operation_id', 'parameters', 'tags', 'response_codes', 'responses'), ('request_body',))
    _identifier(value['operation_id'])
    _need(isinstance(value['tags'], list) and len(value['tags']) <= 30, 'invalid_tags')
    for tag in value['tags']:
        _need(isinstance(tag, str) and bool(re.fullmatch(r'[A-Za-z0-9_.:$ -]{1,120}', tag)), 'invalid_tag')
    _need(isinstance(value['parameters'], list) and len(value['parameters']) <= 100, 'invalid_parameters')
    parameters = set()
    for parameter in value['parameters']:
        if isinstance(parameter, dict) and set(parameter) == {'$ref'}:
            _schema(parameter)
            continue
        _keys(parameter, ('name', 'in', 'required', 'schema'))
        _identifier(parameter['name'])
        _need(isinstance(parameter['in'], str) and parameter['in'] in {'path', 'query', 'header', 'cookie'}
              and type(parameter['required']) is bool, 'invalid_parameter_location')
        identity = (parameter['in'], parameter['name'])
        _need(identity not in parameters, 'duplicate_parameter')
        parameters.add(identity)
        _schema(parameter['schema'])
    if 'request_body' in value:
        _keys(value['request_body'], ('required', 'content'))
        _need(type(value['request_body']['required']) is bool, 'invalid_body_required')
        _content(value['request_body']['content'])
    _need(isinstance(value['responses'], dict) and len(value['responses']) <= 100, 'invalid_responses')
    _need(isinstance(value['response_codes'], list)
          and value['response_codes'] == sorted(value['responses']), 'response_code_mismatch')
    for code, content in value['responses'].items():
        _need(bool(re.fullmatch(r'(?:[1-5][0-9X]{2}|default)', code)), 'invalid_response_code')
        _content(content)


def inspect_api_contract(raw, *, expected_projection_sha256, expected_schema_sha256, method, path):
    return _inspect_projection(raw, expected_projection_sha256=expected_projection_sha256,
        expected_schema_sha256=expected_schema_sha256, method=method, path=path)


def inspect_api_contract_page(raw, *, expected_projection_sha256, expected_schema_sha256,
                              method, path, reference_chain=()):
    """Read one operation/schema page along a bounded, verified local reference path.

    Empty chain selects operation roots. Each next reference must be exposed by
    the preceding page, not merely exist somewhere in the snapshot. No traversal
    of siblings, closure expansion, HTTP or claim of complete schema validation.
    """
    return _inspect_projection(raw, expected_projection_sha256=expected_projection_sha256,
        expected_schema_sha256=expected_schema_sha256, method=method, path=path,
        page_mode=True, reference_chain=reference_chain)


def _direct_page_refs(nodes, schemas):
    refs = set()
    for root in nodes:
        for node in _schema_nodes(root):
            _need(node.get('projection_truncated') is not True, 'selected_schema_truncated')
            if '$ref' not in node:
                continue
            match = REF.fullmatch(node['$ref'])
            _need(match and match[1] == 'schemas', 'unsupported_selected_reference')
            _need(match[2] in schemas, 'missing_schema_reference')
            refs.add(node['$ref'])
            _need(len(refs) <= MAX_REFERENCED_SCHEMAS, 'page_reference_budget')
    return sorted(refs)


def _inspect_projection(raw, *, expected_projection_sha256, expected_schema_sha256, method, path,
                        page_mode=False, reference_chain=()):
    """Inspect a method+path template and flat reference closure; never dispatch."""
    refused = {'contract_observation_status': 'unavailable', **FLAGS}
    try:
        _need(isinstance(raw, (str, bytes)), 'projection_bytes_required')
        _need(len(raw) <= MAX_BYTES, 'projection_byte_budget')
        encoded = raw.encode('utf-8') if isinstance(raw, str) else raw
        _need(len(encoded) <= MAX_BYTES, 'projection_byte_budget')
        _need(isinstance(expected_projection_sha256, str) and bool(HASH.fullmatch(expected_projection_sha256))
              and isinstance(expected_schema_sha256, str) and bool(HASH.fullmatch(expected_schema_sha256)), 'explicit_hash_pins_required')
        _need(hashlib.sha256(encoded).hexdigest() == expected_projection_sha256, 'projection_hash_mismatch')
        _need(isinstance(method, str) and method.lower() in METHODS and method == method.strip(), 'method_required')
        _need(isinstance(path, str) and bool(re.fullmatch(r'/[A-Za-z0-9/_.{}-]*', path))
              and len(path) <= 500, 'exact_path_template_required')
        def nonfinite(_value):
            raise _Refusal('nonfinite_json_forbidden')
        document = json.loads(encoded, object_pairs_hook=_pairs, parse_constant=nonfinite)
        list(_walk(document))
        _keys(document, ('source', 'counts', 'paths', 'schemas', 'limits'))
        source = document['source']
        _keys(source, ('execution_mode', 'schema_path', 'schema_sha256', 'schema_bytes', 'openapi',
                       'source_kind', 'backend_container_image', 'frontend_container_image', 'product_release'))
        _need(source['schema_sha256'] == expected_schema_sha256, 'schema_hash_mismatch')
        _need(source['openapi'] == '3.1.0' and source['execution_mode'] == 'operator_installed_schema_read'
              and source['source_kind'] == 'installed_contract_not_operation_execution', 'unsupported_source_profile')
        _need(type(source['schema_bytes']) is int and 0 < source['schema_bytes'] <= 2097152, 'invalid_schema_size')
        _need(all(isinstance(source[k], str) for k in ('schema_path', 'backend_container_image',
                  'frontend_container_image', 'product_release'))
              and bool(re.fullmatch(r'/[A-Za-z0-9/_.-]+', source['schema_path'])), 'invalid_source_metadata')
        _need(document['limits'] == {'descriptions_exported': False, 'defaults_exported': False,
              'examples_exported': False, 'operation_execution_verified': False, 'evidence_for_pass': False}
              and all(type(v) is bool for v in document['limits'].values()), 'invalid_projection_limits')
        _need(isinstance(document['paths'], dict) and 0 < len(document['paths']) <= 1000
              and isinstance(document['schemas'], dict) and len(document['schemas']) <= 2000, 'projection_catalog_budget')
        identifiers = []
        counts = {}
        for template, operations in document['paths'].items():
            _need(bool(re.fullmatch(r'/[A-Za-z0-9/_.{}-]*', template)), 'invalid_catalog_path')
            _need(isinstance(operations, dict) and set(operations) <= METHODS, 'invalid_catalog_method')
            for verb, operation in operations.items():
                _operation(operation)
                identifiers.append(operation['operation_id'])
                counts[verb] = counts.get(verb, 0) + 1
        _need(len(identifiers) <= 2000, 'operation_budget')
        _keys(document['counts'], ('paths', 'operations', 'method_counts', 'component_schemas', 'duplicate_operation_ids'))
        actual = {'paths': len(document['paths']), 'operations': len(identifiers), 'method_counts': counts,
                  'component_schemas': len(document['schemas']), 'duplicate_operation_ids': len(identifiers) - len(set(identifiers))}
        _need(document['counts'] == actual and all(type(document['counts'][k]) is int for k in
              ('paths', 'operations', 'component_schemas', 'duplicate_operation_ids'))
              and all(type(v) is int for v in document['counts']['method_counts'].values()), 'catalog_count_mismatch')
        for key, value in document['schemas'].items():
            _identifier(key)
            _schema(value)
        selected = document['paths'].get(path, {}).get(method.lower())
        _need(selected is not None, 'operation_not_in_snapshot')
        closure = {}
        queue = [p if '$ref' in p else p['schema'] for p in selected['parameters']]
        queue.extend(selected.get('request_body', {}).get('content', {}).values())
        for content in selected['responses'].values():
            queue.extend(content.values())
        if page_mode:
            _need(isinstance(reference_chain, (tuple, list)) and len(reference_chain) <= 8,
                  'reference_path_budget')
            _need(all(isinstance(r, str) and REF.fullmatch(r) for r in reference_chain),
                  'invalid_reference_path')
            _need(len(reference_chain) == len(set(reference_chain)), 'cyclic_reference_path')
            refs = _direct_page_refs(queue, document['schemas'])
            page = {'operation': selected}
            for reference in reference_chain:
                _need(reference in refs, 'reference_not_exposed_by_previous_page')
                schema = document['schemas'][REF.fullmatch(reference)[2]]
                refs = _direct_page_refs([schema], document['schemas'])
                page = {'schema_reference': reference, 'schema': schema}
            result = {'contract_observation_status': 'observed', 'observation_kind': 'bounded_reference_page',
                'method': method.upper(), 'path_template': path,
                'schema_sha256': expected_schema_sha256, 'projection_sha256': expected_projection_sha256,
                'reference_chain': list(reference_chain), 'direct_schema_references': refs,
                'reference_path_verified': True, 'complete_reference_closure': False,
                'duplicate_operation_id_in_snapshot': identifiers.count(selected['operation_id']) > 1,
                'integrity_matches_supplied_pins': True, **page, **FLAGS}
            _need(len(json.dumps(result, ensure_ascii=False).encode()) <= MAX_OUTPUT_BYTES, 'contract_output_budget')
            return result
        while queue:
            item = queue.pop()
            for node in _schema_nodes(item):
                _need(node.get('projection_truncated') is not True, 'selected_schema_truncated')
                if '$ref' not in node:
                    continue
                match = REF.fullmatch(node['$ref'])
                _need(match and match[1] == 'schemas', 'unsupported_selected_reference')
                key = match[2]
                _need(key in document['schemas'], 'missing_schema_reference')
                if key not in closure:
                    _need(len(closure) < MAX_REFERENCED_SCHEMAS, 'reference_closure_budget')
                    closure[key] = document['schemas'][key]
                    queue.append(closure[key])
        result = {'contract_observation_status': 'observed', 'method': method.upper(), 'path_template': path,
                  'schema_sha256': expected_schema_sha256, 'projection_sha256': expected_projection_sha256,
                  'openapi': source['openapi'], 'operation': selected, 'referenced_schemas': closure,
                  'duplicate_operation_id_in_snapshot': identifiers.count(selected['operation_id']) > 1,
                  'integrity_matches_supplied_pins': True, 'reference_graph_flat_not_expanded': True, **FLAGS}
        _need(len(json.dumps(result, ensure_ascii=False).encode()) <= MAX_OUTPUT_BYTES, 'contract_output_budget')
        return result
    except _Refusal as exc:
        return dict(refused, reason=str(exc))
    except (ValueError, TypeError, UnicodeError, RecursionError, OverflowError, KeyError, AttributeError):
        return dict(refused, reason='invalid_projection')

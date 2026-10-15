"""Bounded block-XML structure observation. No dispatch, evaluation or PASS oracle.

Private parsed values must never be logged/exported. Public APIs return only counts,
fixed reason codes and equality booleans; not IDs, types, names or field contents.
Unsupported constructs fail closed instead of silently disappearing in comparison.
"""
import re
from xml.etree import ElementTree as ET

MAX_BYTES = 65536
MAX_NODES = 2000
MAX_DEPTH = 32
NAMESPACE = 'https://developers.google.com/blockly/xml'
ATTRS = {
    'xml': set(), 'variables': set(), 'variable': {'id', 'type'},
    'block': {'id', 'type', 'x', 'y', 'disabled', 'inline', 'collapsed', 'deletable', 'movable', 'editable'},
    'shadow': {'id', 'type'}, 'field': {'name', 'id'},
    'value': {'name'}, 'next': set(),
}
BOOL_ATTRS = {'disabled', 'inline', 'collapsed', 'deletable', 'movable', 'editable'}
FLAGS = {'business_semantics_verified': False, 'execution_verified': False,
         'evidence_for_pass': False, 'permission_granted': False}


class _Refusal(ValueError):
    pass


def _require(condition, reason):
    if not condition:
        raise _Refusal(reason)


def _parse(xml):
    _require(isinstance(xml, str), 'xml_string_required')
    _require(len(xml) <= MAX_BYTES, 'xml_byte_budget')
    try:
        encoded = xml.encode('utf-8')
    except UnicodeError:
        raise _Refusal('invalid_unicode') from None
    _require(len(encoded) <= MAX_BYTES, 'xml_byte_budget')
    # No DTD, entities, comments, XInclude, or processing instructions.
    stripped = re.sub(r'^\s*<\?xml\s+[^?]{0,200}\?>', '', xml, count=1)
    _require('<!' not in stripped and '<?' not in stripped, 'xml_declaration_forbidden')
    try:
        root = ET.fromstring(xml)
    except (ET.ParseError, ValueError):
        raise _Refusal('invalid_xml') from None
    prefix = '{' + NAMESPACE + '}'
    namespace = prefix if root.tag == prefix + 'xml' else ''
    _require(root.tag == namespace + 'xml', 'unsupported_root_namespace')
    nodes = []
    stack = [(root, 0)]
    while stack:
        node, depth = stack.pop()
        _require(depth <= MAX_DEPTH, 'xml_depth_budget')
        _require(len(nodes) < MAX_NODES, 'xml_node_budget')
        _require(node.tag.startswith(namespace), 'mixed_namespace')
        tag = node.tag[len(namespace):]
        _require(tag in ATTRS and node.tag == namespace + tag, 'unsupported_element')
        _require(set(node.attrib) <= ATTRS[tag], 'unsupported_attribute')
        for key, value in node.attrib.items():
            _require(len(value) <= 256 and all(ord(c) >= 32 for c in value), 'invalid_attribute')
            if key in BOOL_ATTRS:
                _require(value in {'true', 'false'}, 'invalid_boolean_attribute')
            if key in {'x', 'y'}:
                _require(re.fullmatch(r'-?\d{1,7}(?:\.\d{1,6})?', value) is not None, 'invalid_coordinate')
        _require(not node.tail or not node.tail.strip(), 'unexpected_tail_text')
        if tag not in {'field', 'variable'}:
            _require(not node.text or not node.text.strip(), 'unexpected_structural_text')
        _require(len(node.text or '') <= 8192, 'field_text_budget')
        nodes.append((node, tag))
        stack.extend((child, depth + 1) for child in reversed(list(node)))
    block_ids = set()
    variable_ids = set()
    for node, tag in nodes:
        if tag in {'block', 'shadow', 'variable'}:
            identifier = node.get('id')
            _require(bool(identifier), 'missing_identifier')
            ids = variable_ids if tag == 'variable' else block_ids
            _require(identifier not in ids, 'duplicate_identifier')
            ids.add(identifier)
        if tag in {'block', 'shadow'}:
            _require(bool(node.get('type')), 'missing_block_type')
        if tag in {'field', 'value'}:
            _require(bool(node.get('name')), 'missing_input_name')
    for node, tag in nodes:
        children = list(node)
        tags = [child.tag[len(namespace):] for child in children]
        if tag == 'xml':
            _require(tags.count('variables') <= 1 and set(tags) <= {'variables', 'block'}, 'invalid_root_children')
        elif tag == 'variables':
            _require(set(tags) <= {'variable'}, 'invalid_variable_children')
        elif tag in {'variable', 'field'}:
            _require(not children, 'invalid_leaf_children')
            if tag == 'field' and node.get('id') is not None:
                _require(node.get('id') in variable_ids, 'dangling_variable_reference')
        elif tag in {'block', 'shadow'}:
            _require(set(tags) <= {'field', 'value', 'next'} and tags.count('next') <= 1, 'invalid_block_children')
            names = [(child.tag, child.get('name')) for child in children if child.tag != namespace + 'next']
            _require(len(names) == len(set(names)), 'duplicate_input_name')
        elif tag == 'next':
            _require(tags == ['block'], 'invalid_next_link')
        elif tag == 'value':
            _require(tags in (['block'], ['shadow'], ['shadow', 'block']), 'invalid_value_link')
    structure = []
    values = []
    layout = []
    for node, tag in nodes:
        structure.append((tag, tuple(sorted((k, v) for k, v in node.attrib.items() if k not in {'x', 'y'})), len(node)))
        values.append(node.text or '' if tag in {'field', 'variable'} else '')
        layout.append((node.get('x'), node.get('y')))
    counts = {tag: sum(t == tag for _, t in nodes) for tag in ATTRS}
    return tuple(structure), tuple(values), tuple(layout), counts


def inspect_block_xml(xml):
    """Describe a supported saved graph without returning sensitive XML values."""
    try:
        _, _, _, counts = _parse(xml)
    except _Refusal as exc:
        return {'graph_observation_status': 'refused', 'reason': str(exc), **FLAGS}
    return {'graph_observation_status': 'observed', 'format': 'block_xml_v1',
            'counts': counts, **FLAGS}


def compare_block_xml(expected, actual):
    """Strict identities/order; layout separated. Equality never proves business PASS."""
    parsed = []
    for side, xml in (('expected', expected), ('actual', actual)):
        try:
            parsed.append(_parse(xml))
        except _Refusal as exc:
            return {'graph_comparison_status': 'refused', 'side': side, 'reason': str(exc), **FLAGS}
    left, right = parsed
    structure_equal = left[0] == right[0]
    values_equal = left[1] == right[1]
    return {'graph_comparison_status': 'compared', 'structure_equal': structure_equal,
            'field_values_equal': values_equal, 'layout_equal': left[2] == right[2],
            'exact_semantic_equal': structure_equal and values_equal, **FLAGS}

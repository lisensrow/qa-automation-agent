"""Isolated block XML parser/comparator; no browser, model, files, or UC mutation."""
import json
from procedure_graph import inspect_block_xml, compare_block_xml, NAMESPACE

fixture = '<xml><variables><variable id="v">private fixture value</variable></variables><block id="a" type="fixture" x="1" y="2"><field name="VAR" id="v">private fixture value</field><next><block id="b" type="fixture"><value name="V"><shadow id="s" type="fixture"><field name="TEXT">token=fixture-sensitive</field></shadow><block id="c" type="fixture"/></value></block></next></block></xml>'
def observed(xml):
    result = inspect_block_xml(xml)
    assert result['graph_observation_status'] == 'observed', result
    assert result['business_semantics_verified'] is False and result['evidence_for_pass'] is False
    assert 'fixture-sensitive' not in json.dumps(result) and 'private fixture value' not in json.dumps(result)
    return result
def refused(xml):
    result = inspect_block_xml(xml)
    assert result['graph_observation_status'] == 'refused', result
    assert 'fixture-sensitive' not in json.dumps(result)

r = observed(fixture)
assert r['counts']['block'] == 3 and r['counts']['shadow'] == 1 and r['counts']['next'] == 1
observed(fixture.replace('<xml>', '<xml xmlns="'+NAMESPACE+'">'))
observed('<xml/>')  # empty draft is structural only, not business PASS
same = compare_block_xml(fixture, fixture)
assert same['exact_semantic_equal'] is True and same['layout_equal'] is True
pretty = fixture.replace('><', '>\n  <')
assert compare_block_xml(fixture, pretty)['exact_semantic_equal'] is True
assert compare_block_xml(fixture, fixture.replace('x="1"', 'x="3"'))['layout_equal'] is False
assert compare_block_xml(fixture, fixture.replace('x="1"', 'x="3"'))['exact_semantic_equal'] is True
value_change = compare_block_xml(fixture, fixture.replace('token=fixture-sensitive', 'different private fixture'))
assert value_change['structure_equal'] is True and value_change['field_values_equal'] is False
assert value_change['exact_semantic_equal'] is False
assert compare_block_xml(fixture, fixture.replace('id="c"', 'id="changed"'))['structure_equal'] is False
assert compare_block_xml(fixture, fixture.replace('type="fixture"', 'type="other"', 1))['structure_equal'] is False
for xml in (None, b'<xml/>', '\ud800', 'x'*65537, '<xml>',
            '<!DOCTYPE xml [<!ENTITY x SYSTEM "file:///fixture-sensitive">]><xml>&x;</xml>',
            '<xml><!-- fixture-sensitive --></xml>', '<xml><?fixture-sensitive x?></xml>',
            '<xml xmlns="urn:unknown"/>', '<xml><unexpected/></xml>',
            '<xml><block id="a" type="x"><mutation/></block></xml>',
            '<xml><block type="x"/></xml>', '<xml><block id="a"/></xml>',
            '<xml><block id="a" type="x"/><block id="a" type="x"/></xml>',
            '<xml><variables><variable id="v">a</variable><variable id="v">b</variable></variables></xml>',
            '<xml><block id="a" type="x"><field name="V" id="missing">fixture-sensitive</field></block></xml>',
            '<xml><block id="a" type="x"><field name="V"/><field name="V"/></block></xml>',
            '<xml><block id="a" type="x"><next/></block></xml>',
            '<xml><block id="a" type="x"><value name="V"/></block></xml>',
            '<xml><block id="a" type="x" disabled="yes"/></xml>',
            '<xml><block id="a" type="x" x="nan"/></xml>',
            '<xml><block id="a" type="x" unknown="fixture-sensitive"/></xml>',
            '<xml><block id="a" type="x"><field name="V"><block id="b" type="x"/></field></block></xml>',
            '<xml><block id="a" type="x">fixture-sensitive</block></xml>',
            '<xml><block id="a" type="x"/>fixture-sensitive</xml>',
            '<xml>'+''.join('<block id="b'+str(i)+'" type="x"/>' for i in range(2001))+'</xml>',
            '<xml>'+''.join('<block id="b'+str(i)+'" type="x"><next>' for i in range(18))+'<block id="last" type="x"/>'+'</next></block>'*18+'</xml>'):
    refused(xml)
assert compare_block_xml('<bad/>', fixture)['side'] == 'expected'
assert compare_block_xml(fixture, '<bad/>')['side'] == 'actual'
print('procedure graph: PASS (bounded grammar, private values, strict comparison, no execution or PASS authority)')

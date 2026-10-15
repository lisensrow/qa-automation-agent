"""Pure contract observer: pins, closed grammar, closure and no permission/PASS."""
import copy
import hashlib
import json
import api_contract_projection as observer

schema_pin='a'*64
operation={'operation_id':'read_item','tags':['match product process'],'parameters':[
    {'name':'uid','in':'path','required':True,'schema':{'type':'string','format':'uuid'}}],
    'response_codes':['200','422'],'responses':{'200':{'application/json':{'$ref':'#/components/schemas/Item'}},'422':{}}}
base={'source':{'execution_mode':'operator_installed_schema_read','source_kind':'installed_contract_not_operation_execution',
    'schema_path':'/api/v1/docs/openapi.json','schema_sha256':schema_pin,'schema_bytes':1024,'openapi':'3.1.0',
    'backend_container_image':'unknown','frontend_container_image':'unknown','product_release':'unknown'},
    'counts':{'paths':1,'operations':2,'method_counts':{'get':1,'head':1},'component_schemas':1,'duplicate_operation_ids':1},
    'paths':{'/items/{uid}':{'get':copy.deepcopy(operation),'head':copy.deepcopy(operation)}},
    'schemas':{'Item':{'type':'object','required':['id'],'properties':{'id':{'type':'string'},
        'children':{'type':'array','items':{'$ref':'#/components/schemas/Item'}},'mode':{'type':'string','enum_count':2}}}},
    'limits':{'descriptions_exported':False,'defaults_exported':False,'examples_exported':False,
        'operation_execution_verified':False,'evidence_for_pass':False}}

def inspect(document=base,method='GET',path='/items/{uid}',**kwargs):
    raw=document if isinstance(document,(str,bytes)) else json.dumps(document).encode()
    pins={'expected_projection_sha256':hashlib.sha256(raw.encode() if isinstance(raw,str) else raw).hexdigest(),
          'expected_schema_sha256':schema_pin}
    pins.update(kwargs)
    return observer.inspect_api_contract(raw,method=method,path=path,**pins)

def refused(document,reason=None,**kwargs):
    result=inspect(document,**kwargs)
    assert result['contract_observation_status']=='unavailable',result
    if reason: assert result['reason']==reason,result
    assert all(result[k] is False for k in observer.FLAGS)
    assert set(result)<=set(observer.FLAGS)|{'reason','contract_observation_status'}
    return result

result=inspect()
assert result['contract_observation_status']=='observed'
assert result['method']=='GET' and result['path_template']=='/items/{uid}'
assert result['duplicate_operation_id_in_snapshot'] is True
assert set(result['referenced_schemas'])=={'Item'}
assert result['referenced_schemas']['Item']['properties']['children']['items']['$ref'].endswith('/Item')
assert all(result[k] is False for k in observer.FLAGS)
assert inspect(method='HEAD')['contract_observation_status']=='observed'
named=copy.deepcopy(base)
named['schemas']['Item']['properties']['$ref']={'type':'string'}
named['schemas']['Item']['properties']['projection_truncated']={'type':'boolean'}
assert inspect(named)['contract_observation_status']=='observed'
refused(base,'operation_not_in_snapshot',method='DELETE')
refused(base,'operation_not_in_snapshot',path='/items/real-id')
refused(base,'exact_path_template_required',path='https://example.test/items')
refused(base,'exact_path_template_required',path='/items/{uid}?token=secret')
refused(base,'projection_hash_mismatch',expected_projection_sha256='0'*64)
refused(base,'schema_hash_mismatch',expected_schema_sha256='0'*64)
refused(base,'explicit_hash_pins_required',expected_schema_sha256='latest')
refused(b'{"x":1,"x":2}','duplicate_json_key')
refused(b'{"x":NaN}','nonfinite_json_forbidden')
refused(b'\xff','invalid_projection')
refused(b'x'*(observer.MAX_BYTES+1),'projection_byte_budget')

bad=copy.deepcopy(base);bad['paths']['/items/{uid}']['get']['examples']={'password':'private-value'}
r=refused(bad,'unsupported_projection_shape');assert 'private-value' not in json.dumps(r)
bad=copy.deepcopy(base);bad['schemas']['Item']['properties']['id']['$ref']='https://example.test/schema'
refused(bad,'external_or_invalid_reference')
bad=copy.deepcopy(base);bad['schemas']['Item']['properties']['id']['$ref']='#/components/schemas/Missing'
refused(bad,'missing_schema_reference')
bad=copy.deepcopy(base);bad['schemas']['Item']['properties']['id']={'projection_truncated':True}
refused(bad,'selected_schema_truncated')
bad=copy.deepcopy(base);bad['schemas']['Item']['properties']['id']={'projection_truncated':1}
refused(bad,'invalid_truncation_marker')
bad=copy.deepcopy(base);bad['schemas']['Item']['properties']['id']['examples']=['private-value']
refused(bad,'unsupported_projection_shape')
bad=copy.deepcopy(base);bad['limits']['evidence_for_pass']=True
refused(bad,'invalid_projection_limits')
bad=copy.deepcopy(base);bad['limits']['evidence_for_pass']=0
refused(bad,'invalid_projection_limits')
bad=copy.deepcopy(base);bad['counts']['method_counts']['get']=True
refused(bad,'catalog_count_mismatch')
bad=copy.deepcopy(base);bad['counts']['operations']=3
refused(bad,'catalog_count_mismatch')
bad=copy.deepcopy(base);bad['paths']['/items/{uid}']['get']['parameters']*=2
refused(bad,'duplicate_parameter')
bad=copy.deepcopy(base);bad['paths']['/items/{uid}']['get']['response_codes']=['200']
refused(bad,'response_code_mismatch')

old_output=observer.MAX_OUTPUT_BYTES
old_closure=observer.MAX_REFERENCED_SCHEMAS
old_nodes=observer.MAX_NODES
old_depth=observer.MAX_DEPTH
try:
    observer.MAX_OUTPUT_BYTES=64;refused(base,'contract_output_budget')
    observer.MAX_OUTPUT_BYTES=old_output
    observer.MAX_REFERENCED_SCHEMAS=0;refused(base,'reference_closure_budget')
    observer.MAX_REFERENCED_SCHEMAS=old_closure
    observer.MAX_NODES=10;refused(base,'projection_node_or_depth_budget')
    observer.MAX_NODES=old_nodes
    observer.MAX_DEPTH=2;refused(base,'projection_node_or_depth_budget')
finally:
    observer.MAX_OUTPUT_BYTES=old_output;observer.MAX_REFERENCED_SCHEMAS=old_closure
    observer.MAX_NODES=old_nodes;observer.MAX_DEPTH=old_depth
assert inspect()['contract_observation_status']=='observed'

def page(document=base,chain=(),**kwargs):
    raw=json.dumps(document).encode()
    pins={'expected_projection_sha256':hashlib.sha256(raw).hexdigest(),'expected_schema_sha256':schema_pin}
    pins.update(kwargs)
    return observer.inspect_api_contract_page(raw,method='GET',path='/items/{uid}',reference_chain=chain,**pins)

p=page()
assert p['observation_kind']=='bounded_reference_page' and 'operation' in p and 'schema' not in p
assert p['direct_schema_references']==['#/components/schemas/Item']
p=page(chain=['#/components/schemas/Item'])
assert p['schema']['required']==['id'] and p['reference_path_verified']
assert p['enum_values_exported'] is False
assert p['complete_reference_closure'] is False and all(p[k] is False for k in observer.FLAGS)
assert page(chain=['#/components/schemas/Item']*2)['reason']=='cyclic_reference_path'
assert page(chain=['#/components/schemas/Unknown'])['reason']=='reference_not_exposed_by_previous_page'
assert page(chain=['#/components/schemas/Item']*9)['reason']=='reference_path_budget'
assert page(chain=True)['reason']=='reference_path_budget'
assert page(chain=['https://example.test/private'])['reason']=='invalid_reference_path'
assert page(expected_projection_sha256='0'*64)['reason']=='projection_hash_mismatch'
assert page(expected_schema_sha256='0'*64)['reason']=='schema_hash_mismatch'

large=copy.deepcopy(base)
large['schemas']={}
for i in range(31):
    children=[{'$ref':'#/components/schemas/N'+str(n)} for n in (2*i+1,2*i+2) if n<31]
    large['schemas']['N'+str(i)]={'anyOf':children} if children else {'type':'string'}
large['counts']['component_schemas']=31
for op in large['paths']['/items/{uid}'].values():
    op['responses']['200']['application/json']={'$ref':'#/components/schemas/N0'}
refused(large,'reference_closure_budget')
p=page(large,['#/components/schemas/N0','#/components/schemas/N1'])
assert p['schema_reference'].endswith('/N1') and len(p['direct_schema_references'])==2
# N2 exists but is a sibling of N1: a caller cannot jump sideways by schema name.
assert page(large,['#/components/schemas/N0','#/components/schemas/N1','#/components/schemas/N2'])['reason']=='reference_not_exposed_by_previous_page'
bad=copy.deepcopy(large);bad['schemas']['N1']={'projection_truncated':True}
assert page(bad,['#/components/schemas/N0','#/components/schemas/N1'])['reason']=='selected_schema_truncated'
# An unvisited sibling remains unread, not silently declared validated/complete.
assert page(bad,['#/components/schemas/N0','#/components/schemas/N2'])['complete_reference_closure'] is False
try:
    observer.MAX_OUTPUT_BYTES=64
    assert page()['reason']=='contract_output_budget'
finally:
    observer.MAX_OUTPUT_BYTES=old_output
print('API contract projection: PASS (pins, closed grammar, cycles, budgets, no values/dispatch/permission/PASS)')

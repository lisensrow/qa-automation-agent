"""Pure caller-pinned logical condition plan -> bounded UI calls. Not an executor.

Product vocabulary, selectors and expected values belong to a trusted caller
profile, never to model metadata. Valid structure grants no execution authority.
"""
from copy import deepcopy
import hashlib
import json
import re

FLAGS = {'execution_authorized': False, 'current_runtime_verified': False,
         'saved_filter_verified': False, 'membership_verified': False, 'business_pass': False}


def _text(value, limit=160):
    if not isinstance(value, str) or not 0 < len(value) <= limit or value != value.strip():
        raise ValueError('condition_plan_bounded_label_required')
    return value


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
        separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def validate_profile(profile):
    if (not isinstance(profile, dict) or set(profile) != {'version','profile_id','logic','target','fields','source_sha256'}
            or type(profile['version']) is not int or profile['version'] != 1
            or profile['logic'] not in {'AND','OR'}
            or not re.fullmatch(r'[a-z0-9][a-z0-9_.-]{0,127}', str(profile['profile_id']))
            or not re.fullmatch(r'[0-9a-f]{64}', str(profile['source_sha256']))):
        raise ValueError('condition_profile_invalid')
    _text(profile['target'])
    fields=profile['fields']
    if not isinstance(fields, dict) or not 1 <= len(fields) <= 32:
        raise ValueError('condition_profile_fields_invalid')
    sources=[];row_labels=[]
    for field,spec in fields.items():
        _text(field)
        if not isinstance(spec, dict) or set(spec)-{'row_label'} != {'source','parents','value_column','value_action',
                                                     'operator_column','operators','default_operator'}:
            raise ValueError('condition_profile_field_shape')
        for key in ('source','value_column','operator_column','default_operator'):
            _text(spec[key])
        parents=spec['parents']
        if (not isinstance(parents,list) or len(parents)>5 or any(not isinstance(p,str) for p in parents)
                or len(set(parents))!=len(parents) or spec['source'] in parents):
            raise ValueError('condition_profile_parents_invalid')
        for parent in parents:_text(parent)
        if spec['value_action'] not in {'fill','select'} or spec['value_column']==spec['operator_column']:
            raise ValueError('condition_profile_control_invalid')
        operators=spec['operators']
        if (not isinstance(operators,dict) or not 1 <= len(operators) <= 16
                or spec['default_operator'] not in operators):
            raise ValueError('condition_profile_operators_invalid')
        for logical,visible in operators.items():_text(logical);_text(visible)
        sources.append(spec['source'])
        row_labels.append(_text(spec['row_label']) if 'row_label' in spec else spec['source'])
    if len(set(sources))!=len(sources):
        raise ValueError('condition_profile_duplicate_source')
    if len(set(row_labels))!=len(row_labels):raise ValueError('condition_profile_duplicate_row_label')
    return deepcopy(profile)


def normalize_plan(plan, profile):
    if (not isinstance(plan,dict) or set(plan)!={'logic','conditions'} or plan['logic']!=profile['logic']
            or not isinstance(plan['conditions'],list) or not 1 <= len(plan['conditions']) <= 16):
        raise ValueError('condition_plan_shape_or_logic')
    rows=[]
    for row in plan['conditions']:
        if not isinstance(row,dict) or set(row)!={'field','operator','value'}:
            raise ValueError('condition_plan_row_shape')
        if not isinstance(row['field'],str) or row['field'] not in profile['fields']:
            raise ValueError('condition_plan_unknown_field')
        spec=profile['fields'][row['field']]
        if not isinstance(row['operator'],str) or row['operator'] not in spec['operators']:
            raise ValueError('condition_plan_unknown_operator')
        if not isinstance(row['value'],str) or len(row['value'])>1000:
            raise ValueError('condition_plan_value_invalid')
        rows.append(deepcopy(row))
    if len({r['field'] for r in rows})!=len(rows):
        raise ValueError('condition_plan_duplicate_field')
    return {'logic':profile['logic'],'conditions':sorted(rows,key=lambda r:r['field'])}


def compile_condition_plan(plan, profile, expected, expected_profile_sha256):
    profile=validate_profile(profile)
    if (not isinstance(expected_profile_sha256,str) or fingerprint(profile)!=expected_profile_sha256):
        raise ValueError('condition_profile_pin_mismatch')
    # Expected is supplied and pinned by the caller before generation, not by the model.
    actual=normalize_plan(plan,profile); wanted=normalize_plan(expected,profile)
    if actual!=wanted:raise ValueError('condition_plan_expected_mismatch')
    steps=[]
    for row in actual['conditions']:
        spec=profile['fields'][row['field']]; cells=[]
        if row['operator']!=spec['default_operator']:
            cells.append({'column':spec['operator_column'],'action':'select','value':spec['operators'][row['operator']]})
        cells.append({'column':spec['value_column'],'action':spec['value_action'],'value':row['value']})
        steps.append({'tool':'browser_add_tree_row_semantic','arguments':{
            'source':spec['source'],'target':profile['target'],'parents':deepcopy(spec['parents']),'cells':cells}})
        if 'row_label' in spec:steps[-1]['arguments']['row_label']=spec['row_label']
    return {'status':'compiled_plan_only','profile_sha256':fingerprint(profile),'plan_sha256':fingerprint(actual),
            'logical_plan':actual,'ui_steps':steps,**FLAGS}


def response_schema(profile):
    profile=validate_profile(profile)
    variants=[]
    for field,spec in sorted(profile['fields'].items()):
        variants.append({'type':'object','additionalProperties':False,'properties':{
            'field':{'type':'string','enum':[field]},
            'operator':{'type':'string','enum':sorted(spec['operators'])},
            'value':{'type':'string','maxLength':1000}},'required':['field','operator','value']})
    return {'type':'object','additionalProperties':False,'properties':{
        'logic':{'type':'string','enum':[profile['logic']]},
        'conditions':{'type':'array','minItems':1,'maxItems':16,'items':{'anyOf':variants}}},
        'required':['logic','conditions']}

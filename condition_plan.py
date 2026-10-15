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
        if not isinstance(spec, dict) or set(spec)-{'row_label','value_encodings','value_type','value_labels'} != {'source','parents','value_column','value_action',
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
        encodings=spec.get('value_encodings',{})
        if (not isinstance(encodings,dict) or set(encodings)-set(operators)
                or any(not isinstance(v,str) or v not in {'literal','glob_contains'} for v in encodings.values())):
            raise ValueError('condition_profile_value_encoding_invalid')
        value_type=spec.get('value_type','string');labels=spec.get('value_labels')
        if not isinstance(value_type,str) or value_type not in {'string','boolean','enum'}:raise ValueError('condition_profile_value_type_invalid')
        if value_type=='string':
            if labels is not None:raise ValueError('condition_profile_value_labels_invalid')
        elif (not isinstance(labels,dict) or not 1<=len(labels)<=32
                or (value_type=='boolean' and set(labels)!={'true','false'}) or encodings):
            raise ValueError('condition_profile_value_labels_invalid')
        else:
            for logical,visible in labels.items():_text(logical);_text(visible)
            if len(set(labels.values()))!=len(labels):raise ValueError('condition_profile_duplicate_value_label')
        sources.append(spec['source'])
        row_labels.append(_text(spec['row_label']) if 'row_label' in spec else spec['source'])
    if len(set(sources))!=len(sources):
        raise ValueError('condition_profile_duplicate_source')
    if len(set(row_labels))!=len(row_labels):raise ValueError('condition_profile_duplicate_row_label')
    return deepcopy(profile)


def control_value(spec, operator, value):
    """Trusted profile encodes a user literal; never repairs a mismatched plan."""
    kind=spec.get('value_type','string')
    if kind=='boolean':
        if type(value) is not bool:raise ValueError('condition_plan_boolean_required')
        return spec['value_labels']['true' if value else 'false']
    if kind=='enum':
        if not isinstance(value,str) or value not in spec['value_labels']:raise ValueError('condition_plan_enum_value_unknown')
        return spec['value_labels'][value]
    if not isinstance(value,str) or len(value)>1000:raise ValueError('condition_plan_value_invalid')
    encoding=spec.get('value_encodings',{}).get(operator,'literal')
    if encoding=='literal':return value
    if (encoding!='glob_contains' or not isinstance(value,str) or not 1<=len(value)<=998
            or any(c in value for c in '*?\\') or any(ord(c)<32 for c in value)):
        raise ValueError('condition_plan_contains_literal_required')
    return '*'+value+'*'


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
        control_value(spec,row['operator'],row['value'])
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
        cells.append({'column':spec['value_column'],'action':spec['value_action'],
                      'value':control_value(spec,row['operator'],row['value'])})
        steps.append({'tool':'browser_add_tree_row_semantic','arguments':{
            'source':spec['source'],'target':profile['target'],'parents':deepcopy(spec['parents']),'cells':cells}})
        if 'row_label' in spec:steps[-1]['arguments']['row_label']=spec['row_label']
    return {'status':'compiled_plan_only','profile_sha256':fingerprint(profile),'plan_sha256':fingerprint(actual),
            'logical_plan':actual,'ui_steps':steps,**FLAGS}


def response_schema(profile):
    profile=validate_profile(profile)
    variants=[]
    for field,spec in sorted(profile['fields'].items()):
        kind=spec.get('value_type','string')
        value_schema=({'type':'boolean'} if kind=='boolean' else
            {'type':'string','enum':sorted(spec['value_labels'])} if kind=='enum' else
            {'type':'string','maxLength':1000})
        variants.append({'type':'object','additionalProperties':False,'properties':{
            'field':{'type':'string','enum':[field]},
            'operator':{'type':'string','enum':sorted(spec['operators'])},
            'value':value_schema},'required':['field','operator','value']})
    return {'type':'object','additionalProperties':False,'properties':{
        'logic':{'type':'string','enum':[profile['logic']]},
        'conditions':{'type':'array','minItems':1,'maxItems':16,'items':{'anyOf':variants}}},
        'required':['logic','conditions']}


def plan_instruction(profile):
    typed=any(s.get('value_type','string')!='string' for s in profile['fields'].values())
    contains=any('glob_contains' in s.get('value_encodings',{}).values() for s in profile['fields'].values())
    if not typed and not contains:
        return 'Extract a logical condition plan only. No tool calls, UI arguments, execution or success claims. Use exact UI field/operator/value labels from reviewed guidance. Return the typed JSON plan.'
    instruction='Extract a logical condition plan only. No tool calls, UI arguments, execution or success claims. Use exact field/operator identifiers from the typed schema. Return the typed JSON plan.'
    if contains:instruction+=' Contains takes the plain user literal, without wildcard syntax: the trusted compiler owns encoding. Do not copy UI patterns from a different logical operator.'
    if typed:instruction+=' Boolean fields use JSON true/false, enum fields use the exact logical IDs from the schema; the compiler owns UI labels. Do not substitute UI strings or backend IDs.'
    return instruction

"""Reviewed UConnect profile data, separate from generic execution Core."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from condition_plan import compile_condition_plan, fingerprint

PROFILE_ID='uc.collections.flat.v2'
SOURCE=Path('/opt/uqa/knowledge/source/UQA-experience/UQA_COLLECTIONS_KNOWLEDGE.md')
SOURCE_SHA='41fb09e9a813f56f086b7eb494ef60e2d7ef41acbe8ddc415f5adb008d0d2cac'
ROW_SOURCE=SOURCE.with_name('UQA_CONDITION_ROW_LABELS_KNOWLEDGE.md')
ROW_SOURCE_SHA='8e03a8d735ec620ad8d9dd65adda7524746733be2f5968512fe4b8ea4a837043'


def profile():
    base={'parents':['Common'],'value_column':'Value','value_action':'select','operator_column':'Operator',
          'operators':{'Equal':'Equal'},'default_operator':'Equal'}
    return {'version':1,'profile_id':PROFILE_ID,'logic':'AND','target':'And',
        'source_sha256':fingerprint({'field_source':SOURCE_SHA,'row_caption_source':ROW_SOURCE_SHA}),
        'fields':{'Archived':{**base,'source':'Archived'},'CI class':{**base,'source':'CI class'},
                  'OS name':{**base,'source':'OS name','row_label':'Endpoint.OS name','parents':['Endpoint'],'value_action':'fill',
                             'operators':{'Equal':'Equal','Wildcard':'Wildcard'}}}}


def source_current():
    try:return (hashlib.sha256(SOURCE.read_bytes()).hexdigest()==SOURCE_SHA
                and hashlib.sha256(ROW_SOURCE.read_bytes()).hexdigest()==ROW_SOURCE_SHA)
    except OSError:return False


def expectation_cells(expected):
    p=profile(); logical=compile_condition_plan(expected,p,expected,fingerprint(p))['logical_plan']
    cells=[]
    for row in logical['conditions']:
        spec=p['fields'][row['field']]
        for column,value in ((spec['operator_column'],spec['operators'][row['operator']]),
                             (spec['value_column'],row['value'])):
            cells.append({'row':spec.get('row_label',spec['source']),'column':column,'value_sha256':hashlib.sha256(value.encode()).hexdigest()})
    return cells


def requirement_for_plan(expected, check_id):
    p=profile(); logical=compile_condition_plan(expected,p,expected,fingerprint(p))['logical_plan']
    return {'type':'bounded_condition_draft','locked':True,'stand':'lab','action_profile':'write_ui_state',
        'execution_status':'ready','condition_profile_id':PROFILE_ID,'condition_profile_sha256':fingerprint(p),
        'condition_preparation_sha256':fingerprint({'steps':preparation('configured-stand-entry'),
            'auth_continuation':'core_saved_auth_candidate_same_saved_origin_only'}),
        'expected_plan':logical,'bindings':{'grid_subject':'labeled-grid','grid_session':'','grid_url':'',
            'grid_expected':json.dumps(expectation_cells(logical),ensure_ascii=False,sort_keys=True)},
        'check_contracts':{check_id:{'tool':'browser_inspect_labeled_grid_values_semantic',
            'subject_binding':'grid_subject','cells_binding':'grid_expected','session_binding':'grid_session',
            'url_binding':'grid_url','assertions':[{'field':'cell_values_match_binding','operator':'eq','expected':True}]}}}


def immutable_requirement(requirement):
    value=deepcopy(requirement)
    for key in ('grid_session','grid_url'):
        if key in (value.get('bindings') or {}):value['bindings'][key]=''
    return value


def preparation(entry_url):
    return [
        ('browser_open_page',{'url':entry_url},'/cmdb'),
        ('browser_probe_capabilities',{},'/cmdb'),
        ('browser_click_semantic',{'name':'Add','role':'button','exact':True},'/cmdb'),
        ('browser_click_semantic',{'name':'Add collection','role':'menuitem','exact':True},'/cmdb/collections/new/settings/composition'),
        ('browser_click_semantic',{'name':'Conditions','role':'tab','exact':True},'/cmdb/collections/new/settings/conditions')]

EDITOR_PATH='/cmdb/collections/new/settings/conditions'

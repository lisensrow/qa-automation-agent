"""A rechecked documented label can explain an actual entry, never grant WRITE."""
from copy import deepcopy
from unittest.mock import patch
import uqa
import product_knowledge_context as context

base=[{'role':'user','content':'Prepare a new collection with a Windows filter.'},
      {'role':'tool','tool_name':'browser_open_page','content':{
          'current_url':'https://fixture.test/cmdb','http_status':200,'session_id':'s1',
          'navigation_labels':['CMDB']}}]
hint={'status':'candidate_entry_surface_hint','section_label':'CMDB',
      'source_refs':[{'source_id':'fixture-guide','sha256':'a'*64}],
      'evidence_for_pass':False,'current_runtime_applicability_verified':False,'execution_authorized':False}
with patch.object(context,'retrieve_entry_surface_hint',return_value=hint):
    assert uqa._open_page_proves_named_route(base)
    for key,value in [('http_status',500),('executed',False),('error','failed'),
                      ('navigation_labels',[]),('navigation_labels',['CMDB','CMDB']),
                      ('navigation_labels',['CMDB','cmdb']),('session_id',None),
                      ('current_url','https://fixture.test/unknown')]:
        bad=deepcopy(base);bad[-1]['content'][key]=value
        assert not uqa._open_page_proves_named_route(bad)
    bad=deepcopy(base);bad[-1]['tool_name']='knowledge_search'
    assert not uqa._open_page_proves_named_route(bad)
    editor=deepcopy(base)+[{'role':'tool','tool_name':'browser_click_semantic','content':{
        'current_url':'https://fixture.test/cmdb/new/settings','session_id':'s1',
        'click_status':'executed','action_class':'write','action_policy_status':'confirmed'}}]
    assert uqa._confirmed_new_editor_below_named_route(editor)
    for key,value in [('session_id','other'),('current_url','https://other.test/cmdb/new/settings'),
                      ('action_policy_status','blocked'),('click_status','failed')]:
        bad=deepcopy(editor);bad[-1]['content'][key]=value
        assert not uqa._confirmed_new_editor_below_named_route(bad)
for key,value in [('status','unavailable'),('section_label','/cmdb'),('source_refs',[]),
                  ('execution_authorized',True),('evidence_for_pass',True),
                  ('current_runtime_applicability_verified',True)]:
    bad=deepcopy(hint);bad[key]=value
    with patch.object(context,'retrieve_entry_surface_hint',return_value=bad):
        assert not uqa._open_page_proves_named_route(base)
with patch.object(context,'retrieve_entry_surface_hint',return_value=None):
    assert not uqa._open_page_proves_named_route(base)
assert context.retrieve_entry_surface_hint('Do not create collections. Inspect policies.') is None
assert context.retrieve_entry_surface_hint('Create a policy for a new collection.') is None
assert context.retrieve_entry_surface_hint('Read an existing collection.') is None
print('PASS documented entry: native page+unique label+rechecked source; redirect/error/scope/flags reject; no permission or verdict grant')

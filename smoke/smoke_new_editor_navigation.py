"""Named entry -> confirmed new editor retains navigation, not permission."""
from copy import deepcopy
from unittest.mock import patch
import uqa

base=[{'role':'user','content':'Create a new item in widgets, leave existing objects unchanged.'},
      {'role':'tool','tool_name':'browser_open_page','content':{
          'current_url':'https://fixture.test/widgets','http_status':200,'session_id':'session-one'}},
      {'role':'tool','tool_name':'browser_click_semantic','content':{
          'current_url':'https://fixture.test/widgets/new/settings/composition','session_id':'session-one',
          'semantic_name':'Add item','click_status':'executed','action_class':'write',
          'action_policy_status':'confirmed','text_preview':'New item Composition Settings'}}]
assert uqa._managed_navigation_ready(base)
for key,value in [('session_id','other-session'),('action_policy_status','blocked'),
                  ('click_status','failed'),('executed',False),('error','failure'),
                  ('action_class','destructive')]:
    bad=deepcopy(base);bad[-1]['content'][key]=value
    assert not uqa._confirmed_new_editor_below_named_route(bad)
for url in ('https://other.test/widgets/new/settings','https://fixture.test/widgets/42/settings',
            'https://fixture.test/widgetsmith/new/settings','https://fixture.test/widgets/newly/settings',
            'https://fixture.test/widgets/new/../settings'):
    bad=deepcopy(base);bad[-1]['content']['current_url']=url
    assert not uqa._confirmed_new_editor_below_named_route(bad)
bad=deepcopy(base);bad[-1]['tool_name']='knowledge_search'
assert not uqa._confirmed_new_editor_below_named_route(bad)
bad=deepcopy(base);bad[0]['content']='Create a group in accounts'
assert not uqa._confirmed_new_editor_below_named_route(bad)
bad=deepcopy(base);bad[-1]['content'].pop('session_id')
assert not uqa._confirmed_new_editor_below_named_route(bad)
with patch.object(uqa,'managed_navigation_preflight_check',side_effect=AssertionError('stale resolver requested')):
    key=('fixture-job','fixture-case')
    uqa._PENDING_NAVIGATION_CANDIDATES[key]={'tool':'browser_click_semantic','arguments':{'name':'widgets'}}
    result=uqa.add_managed_navigation_preflight_advisory('browser_click_semantic',base[-1]['content'],
                                                        base[:-1],'confirm_mutations',*key)
    assert result['navigation_preflight_status']=='completed' and key not in uqa._PENDING_NAVIGATION_CANDIDATES
print('new editor navigation: PASS (same session/origin, confirmed native click, no guessed/saved editor)')

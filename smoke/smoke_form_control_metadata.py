"""Invoke readonly form observer with a fake DOM; no real browser or stand."""
from unittest.mock import patch
import re
import tools.browser as browser
from observation_extractor import extract_observations
class Scope:
    def evaluate(self,script):
        assert 'control_states: visible.map' in script
        assert not re.search(r'\bel\.value\b|dispatchEvent|\.click\(|\.focus\(',script)
        return {'visible_control_count':1,'invalid_control_count':0,'invalid_controls':[],
                'validation_passed':True,'truncated':False,'control_states_reported':True,
                'control_states':[{'index':0,'tag':'select','type':'select-one','label_hint':'',
                    'native_required':False,'native_disabled':False,'native_read_only':None,
                    'native_will_validate':True}]}
class Page:
    def locator(self,name):
        assert name=='body'
        return Scope()
session=browser._session
with patch.object(session,'_ensure_started'), patch.object(session,'_reset_diagnostics'), \
        patch.object(session,'_capture_state',return_value={'current_url':'https://fixture.test/'}), \
        patch.object(session,'page',Page()):
    result=session.inspect_form_validation_semantic()
assert result['mutation_executed'] is False
data=extract_observations('browser_inspect_form_validation_semantic',{},result)[0]['data']
assert data['control_states_reported'] is True
assert data['control_states'][0]['native_read_only'] is None
assert data['control_state_summary']['native_required_count']==0
assert data['control_state_summary']['native_read_only_unknown_count']==1
assert 'value' not in data['control_states'][0]
print('form control metadata smoke: PASS (readonly DOM, native null preserved, no values)')

"""Historical browser compaction keeps references, not secret values or invented truth."""
from copy import deepcopy
import json
import uqa
payload={'semantic_name':'Name','uqa_evidence_id':'ev-fixture','uqa_evidence_usable_for_verdict':True,
         'uqa_observation_ids':['obs-fixture','https://private.invalid','secret value'],
         'visible':True,'required':False,'value':'PRIVATE_FIELD_VALUE','text':'PRIVATE_TEXT',
         'headers':{'Authorization':'PRIVATE_TOKEN'},'validation_audit':{
            'visible_control_count':7,'invalid_control_count':0,'validation_passed':True,'truncated':False,
            'invalid_controls':[{'value':'PRIVATE_INVALID'}]}}
before=deepcopy(payload)
history=[{'role':'tool','tool_name':'browser_inspect_semantic','content':json.dumps(payload)},
         {'role':'tool','tool_name':'browser_get_state','content':'{}'}]
original=deepcopy(history)
prepared=uqa.messages_for_model(history)
summary=json.loads(prepared[0]['content'])
assert summary['uqa_observation_ids']==['obs-fixture']
assert summary['uqa_evidence_usable_for_verdict'] is True
assert summary['required'] is False and summary['visible'] is True
assert summary['validation_audit']['visible_control_count']==7
assert summary['validation_audit']['truncated'] is False
assert 'PRIVATE_' not in prepared[0]['content']
assert history==original and payload==before
bad=dict(payload,uqa_evidence_usable_for_verdict=False,required='true',visible=1)
summary=uqa._historical_browser_result_summary('browser_inspect_semantic',bad)
assert summary['uqa_evidence_usable_for_verdict'] is False
assert 'required' not in summary and 'visible' not in summary
bad['validation_audit']={'visible_control_count':True,'validation_passed':1,'truncated':None}
assert uqa._historical_browser_result_summary('browser_inspect_semantic',bad)['validation_audit']=={}
assert 'uqa_evidence_usable_for_verdict' not in uqa._historical_browser_result_summary('browser_get_state',{})
assert uqa.messages_for_model(history)[-1]==history[-1]
print('history provenance smoke: PASS (IDs and scalars retained; private values omitted)')

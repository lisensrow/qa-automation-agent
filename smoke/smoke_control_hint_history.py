"""A useful location must survive the next observation without prose/authority."""
from copy import deepcopy
import json
import uqa
from product_knowledge_context import compact_control_location_hint
hint={'status':'candidate_location_hint','requested_control_label':'Name','document_panel_name':'Settings',
      'source_refs':[{'source_id':'fixture.guide','sha256':'a'*64,'document_revision':'r1'}],
      'evidence_for_pass':False,'current_runtime_applicability_verified':False,
      'usage':'Untrusted prose must not be retained','allow':True,'command':'fixture-not-executable'}
messages=[{'role':'tool','tool_name':'browser_fill_semantic','content':json.dumps({'error':'Field not found: Name','control_location_hint':hint})},
          {'role':'tool','tool_name':'browser_inspect_semantic','content':json.dumps({'error':'semantic_element_not_found'})}]
result=uqa.messages_for_model(messages)
safe=json.loads(result[0]['content'])['control_location_hint']
assert safe['document_panel_name']=='Settings' and safe['evidence_for_pass'] is False
assert not any(k in safe for k in ('usage','command','allow'))
assert json.loads(messages[0]['content'])['control_location_hint']==hint
for key,value in [('evidence_for_pass',True),('current_runtime_applicability_verified',True),
                  ('status','verified'),('document_panel_name','token=fixture-secret')]:
    bad=deepcopy(hint);bad[key]=value
    assert compact_control_location_hint(bad) is None
bad=deepcopy(hint);bad['source_refs'][0]['sha256']='invalid'
assert compact_control_location_hint(bad) is None
print('control hint history: PASS (next-observation retention, bounded refs, no prose/authority)')

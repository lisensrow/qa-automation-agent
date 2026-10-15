"""Pure compiler: model owns logic only; caller owns profile and expected."""
from copy import deepcopy
from condition_plan import compile_condition_plan, fingerprint, response_schema, FLAGS

spec={'source':'Attribute A','parents':['Category'],'value_column':'Value','value_action':'select',
      'operator_column':'Operator','operators':{'equal':'Equal','pattern':'Wildcard'},'default_operator':'equal'}
profile={'version':1,'profile_id':'fixture.condition.v1','logic':'AND','target':'And','source_sha256':'a'*64,
         'fields':{'attribute':spec,'other':{**spec,'source':'Attribute B','value_action':'fill'}}}
plan={'logic':'AND','conditions':[{'field':'attribute','operator':'equal','value':'No'},
                                {'field':'other','operator':'pattern','value':'*fixture*'}]}
pin=fingerprint(profile)
result=compile_condition_plan(plan,profile,deepcopy(plan),pin)
assert result['status']=='compiled_plan_only' and all(result[k] is False for k in FLAGS)
assert result['ui_steps'][0]['arguments']['cells']==[{'column':'Value','action':'select','value':'No'}]
assert result['ui_steps'][1]['arguments']['cells']==[
    {'column':'Operator','action':'select','value':'Wildcard'},{'column':'Value','action':'fill','value':'*fixture*'}]
assert all('session_id' not in s['arguments'] and 'current_url' not in s['arguments'] for s in result['ui_steps'])
assert compile_condition_plan({**plan,'conditions':list(reversed(plan['conditions']))},profile,plan,pin)['plan_sha256']==result['plan_sha256']

def denied(candidate, p=profile, expected=plan, sha=pin):
    try:compile_condition_plan(candidate,p,expected,sha)
    except (ValueError,TypeError):return
    raise AssertionError('unsafe plan accepted')

for candidate in ({**plan,'logic':'OR'},{**plan,'url':'https://invented.test'},
                  {**plan,'conditions':plan['conditions']*2}, {**plan,'conditions':[]},
                  {**plan,'conditions':[{'field':'unknown','operator':'equal','value':'No'}]},
                  {**plan,'conditions':[{'field':'attribute','operator':'unknown','value':'No'}]},
                  {**plan,'conditions':[{'field':'attribute','operator':'equal','value':False}]},
                  {**plan,'conditions':[{'field':'attribute','operator':'equal','value':'different'}]},
                  {**plan,'conditions':[dict(plan['conditions'][0],tool='browser_click_semantic')]}):denied(candidate)
bad=deepcopy(profile);bad['fields']['attribute']['parents']=['Changed'];denied(plan,p=bad)
bad=deepcopy(profile);bad['fields']['other']['source']='Attribute A';denied(plan,p=bad,sha=fingerprint(bad))
bad=deepcopy(profile);bad['fields']['other']['value_action']='click';denied(plan,p=bad,sha=fingerprint(bad))
denied(plan,sha='0'*64)
schema=response_schema(profile)
variants=schema['properties']['conditions']['items']['anyOf']
assert [v['properties']['field']['enum'] for v in variants]==[['attribute'],['other']]
restricted=deepcopy(profile);restricted['fields']['attribute']['operators']={'equal':'Equal'}
restricted_variants=response_schema(restricted)['properties']['conditions']['items']['anyOf']
assert restricted_variants[0]['properties']['operator']['enum']==['equal']
assert restricted_variants[1]['properties']['operator']['enum']==['equal','pattern']
assert fingerprint(profile)==pin and plan['conditions'][0]['value']=='No'
qualified=deepcopy(profile);qualified['fields']['other']['row_label']='Category.Attribute B'
compiled=compile_condition_plan(plan,qualified,plan,fingerprint(qualified))
assert compiled['ui_steps'][1]['arguments']['source']=='Attribute B'
assert compiled['ui_steps'][1]['arguments']['row_label']=='Category.Attribute B'
assert 'row_label' not in compiled['ui_steps'][0]['arguments']
bad=deepcopy(qualified);bad['fields']['attribute']['row_label']='Category.Attribute B'
denied(plan,p=bad,sha=fingerprint(bad))
bad=deepcopy(qualified);bad['fields']['other']['row_label']=' '
denied(plan,p=bad,sha=fingerprint(bad))
denied({**plan,'conditions':[dict(plan['conditions'][0],row_label='invented')]})
print('PASS condition plan: caller pin/expected, closed logical schema, no model UI arguments, duplicates/logic/value/profile denials; not an executor')

"""Caller expected versus linked fresh grid values, including stale-read denial."""
from copy import deepcopy
import hashlib
import json
from frontend_check_contracts import evaluate_contract

h=hashlib.sha256(b'No').hexdigest()
cells=[{'row':'Attribute A','column':'Value','value_sha256':h}]
contract={'tool':'browser_inspect_labeled_grid_values_semantic','subject_binding':'subject',
    'cells_binding':'expected','session_binding':'session','url_binding':'draft',
    'assertions':[{'field':'cell_values_match_binding','operator':'eq','expected':True}]}
requirement={'bindings':{'subject':'labeled-grid','expected':json.dumps(cells),'session':'fixture',
    'draft':'https://fixture.test/new'},'check_contracts':{'ck-grid':contract}}
data={'tool':contract['tool'],'subject':'labeled-grid','session_id':'fixture','url':'https://fixture.test/new',
      'grid_value_status':'observed','requested_cells':[{'row':'Attribute A','column':'Value'}],
      'grid_values':[{**cells[0],'value_length':2}]}
case={'observations':[{'observation_id':'obs-grid','type':'ui_grid_values','data':data}],
    'evidence':[{'evidence_id':'ev-grid','type':contract['tool'],'observation_ids':['obs-grid'],
                 'usable_for_verdict':True}]}
check={'check_id':'ck-grid','status':'passed'}
def verdict(c=case,r=requirement):return evaluate_contract(c,r,check,'https://fixture.test')[0]
assert verdict()['status']=='passed'
bad=deepcopy(case);bad['observations'][0]['data']['grid_values'][0]['value_sha256']='b'*64
assert verdict(bad)['status']=='failed'
for change in ('session','url','missing','duplicate','raw_extra','requested_scope','unusable','later_write'):
    bad=deepcopy(case);d=bad['observations'][0]['data']
    if change=='session':d['session_id']='other'
    elif change=='url':d['url']='https://other.test/new'
    elif change=='missing':d['grid_values']=[]
    elif change=='duplicate':d['grid_values']*=2
    elif change=='raw_extra':d['grid_values'][0]['raw_value']='not-allowed'
    elif change=='requested_scope':d['requested_cells'][0]['row']='Other'
    elif change=='unusable':bad['evidence'][0]['usable_for_verdict']=False
    else:bad['evidence'].append({'evidence_id':'ev-write','type':'browser_fill_semantic',
        'value':json.dumps({'result':{'action_class':'write','executed':True}})})
    assert verdict(bad)['status']=='blocked',change
bad=deepcopy(case);bad['evidence'].append({'evidence_id':'ev-denied','type':'browser_fill_semantic',
    'value':json.dumps({'result':{'action_class':'write','executed':False}})})
assert verdict(bad)['status']=='passed'
print('PASS grid value contract: caller six-cell capable hashes/context, linked usable evidence, mismatch FAIL, malformed/stale/unusable BLOCKED; no tool/model match flag trusted')

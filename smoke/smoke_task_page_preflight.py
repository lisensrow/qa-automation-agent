"""Pure bounded pagination fixture, never product mutations."""
from copy import deepcopy
from unittest.mock import patch
import uuid
import task_page_preflight as p
from command_probe_contract import target

t=target('windows')
for n in [0,1,31,100,132,1000]:
  for bad in ['none','total_changed','duplicate','wrong_offset','short','pending','head_changed','overflow']:
    rows=[{'id':str(uuid.uuid4()),'agent_id':t['agent_id'],'name':'remoteConnections','period':None,'status':'success'} for _ in range(n)]
    calls=[]
    def get(session,url,params):
        offset=params['offset'];calls.append(offset);items=deepcopy(rows[offset:offset+100]);total=n
        if bad=='overflow':total=1001
        if bad=='total_changed' and offset:total=n-1
        if bad=='duplicate' and offset and items:items[0]['id']=rows[0]['id']
        if bad=='pending' and items:items[0]['status']='progress'
        if bad=='short' and items:items.pop()
        if bad=='head_changed' and offset==0 and len(calls)>1 and items:items[0]['id']=str(uuid.uuid4())
        return {'items':items,'total':total,'count':len(items),'offset':offset+1 if bad=='wrong_offset' else offset,'limit':100}
    expected_fail=(bad in {'wrong_offset','overflow'} or bad in {'pending','short'} and n>0
        or bad in {'total_changed','duplicate','head_changed'} and n>100)
    with patch.object(p,'read_json',side_effect=get):
        try:out,proof=p.complete_task_list(None,'observed-url','windows','remoteConnections')
        except ValueError:
            assert expected_fail,(n,bad)
        else:
            assert not expected_fail,(n,bad)
            assert len(out)==n and proof['unique_ids']==n and proof['complete_enumeration'] is True
            assert proof['atomic_snapshot'] is False and proof['head_rechecked'] is (n>100)
            assert calls==list(range(0,max(1,n),100))+([0] if n>100 else [])
print('PASS bounded native pagination: 0..1000, stable total/count/offset/IDs/head, pending/duplicates/budgets fail closed, no atomic claim')

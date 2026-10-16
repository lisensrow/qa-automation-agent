"""Bounded native GET pagination; no dispatch, retry permission or atomic claim."""
from uuid import UUID
from command_stage_native import read_json
from command_probe_contract import validate_task_list

def complete_task_list(session,url,target,task_name):
    rows=[];ids=set();pages=[];total=None;first_ids=None
    for offset in range(0,1000,100):
        page=read_json(session,url,{'name':task_name,'periodic':False,'limit':100,'offset':offset})
        items=page.get('items');n=page.get('total')
        if (type(n) is not int or not 0<=n<=1000 or not isinstance(items,list)
            or type(page.get('offset')) is not int or page['offset']!=offset
            or type(page.get('limit')) is not int or page['limit']!=100
            or type(page.get('count')) is not int or page['count']!=len(items)
            or len(items)!=min(100,max(0,n-offset)) or total is not None and n!=total):
            raise ValueError('task_pagination_incomplete_or_changed')
        total=n;pageids=[]
        for item in items:
            uid=item.get('id') if isinstance(item,dict) else None
            if not isinstance(uid,str) or str(UUID(uid))!=uid or uid in ids:raise ValueError('task_pagination_duplicate_or_invalid_id')
            ids.add(uid);pageids.append(uid)
        validate_task_list(target,{'items':items,'total':len(items),'offset':0},task_name)
        if first_ids is None:first_ids=pageids
        rows.extend(items);pages.append({'offset':offset,'count':len(items),'total':n})
        if len(rows)==total:break
    if total is None or len(rows)!=total:raise ValueError('task_pagination_budget_exhausted')
    # Multi-page head recheck catches insertion/reordering during enumeration.
    # This is an observed consistency window, never an atomic server snapshot.
    if len(pages)>1:
        head=read_json(session,url,{'name':task_name,'periodic':False,'limit':100,'offset':0})
        if (head.get('total')!=total or head.get('offset')!=0 or head.get('count')!=len(first_ids)
            or head.get('limit')!=100 or not isinstance(head.get('items'),list)
            or [x.get('id') for x in head['items'] if isinstance(x,dict)]!=first_ids):
            raise ValueError('task_pagination_head_changed')
        validate_task_list(target,{'items':head['items'],'total':len(head['items']),'offset':0},task_name)
    validate_task_list(target,{'items':rows,'total':total,'offset':0},task_name)
    return rows,{'total':total,'pages':pages,'unique_ids':len(ids),'complete_enumeration':True,
        'head_rechecked':len(pages)>1,'atomic_snapshot':False,'max_tasks':1000}

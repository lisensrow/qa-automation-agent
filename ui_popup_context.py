"""Bounded UI vocabulary hints. Never permissions, dispatch, or verdict evidence."""
from copy import deepcopy
import json
import re
import unicodedata

ROLES={'menuitem','menuitemcheckbox','menuitemradio'}
SENSITIVE=re.compile(r'(?i)(-----BEGIN .*PRIVATE KEY|\bbearer\s+\S+|\b(?:password|passwd|token|secret|cookie|authorization)\s*[:=]\s*\S+|://[^/\s]+:[^/@\s]+@)')

def normalize_menu_context(data):
    if (not isinstance(data,dict) or data.get('status')!='observed'
            or data.get('truncated') is not False
            or type(data.get('menu_count')) is not int or not 0<=data['menu_count']<=8
            or type(data.get('item_count')) is not int or not 0<=data['item_count']<=20
            or not isinstance(data.get('items'),list) or len(data['items'])!=data['item_count']):
        return None
    if data['menu_count']!=1 and data['item_count']:
        return None
    items=[]; names=set()
    for item in data['items']:
        if (not isinstance(item,dict) or not isinstance(item.get('role'),str) or item['role'] not in ROLES
                or type(item.get('disabled')) is not bool or not isinstance(item.get('name'),str)):
            return None
        name=unicodedata.normalize('NFC',item['name'])
        if (not name.strip() or len(name)>160 or name!=name.strip()
                or any(unicodedata.category(c).startswith('C') for c in name)
                or SENSITIVE.search(name) or name in names):
            return None
        names.add(name)
        items.append({'name':name,'role':item['role'],'disabled':item['disabled']})
    return {'status':'observed','menu_count':data['menu_count'],'item_count':len(items),
            'items':items,'truncated':False}

def latest_menu_context(messages):
    # Caller passes only current-turn messages. A newer no-menu/unknown snapshot
    # clears an older menu; a field lookup error alone is not a new snapshot.
    for message in reversed(messages):
        if message.get('role')!='tool' or not str(message.get('tool_name','')).startswith('browser_'):
            continue
        try:
            result=json.loads(message['content']) if isinstance(message.get('content'),str) else message.get('content')
        except (TypeError,ValueError):
            continue
        if isinstance(result,dict) and result.get('current_url') and result.get('session_id'):
            return normalize_menu_context(result.get('active_menu_context'))
    return None

def menu_tool_catalog(catalog,messages):
    context=latest_menu_context(messages)
    if not context or context['menu_count']!=1:
        return catalog
    items=[item for item in context['items'] if not item['disabled']]
    if not items:
        return catalog
    revised=deepcopy(catalog)
    for tool in revised:
        function=tool.get('function',{})
        if function.get('name')!='browser_click_semantic':
            continue
        function['description']=('Current native snapshot has an open menu. The suggested click vocabulary below '
            'contains only observed enabled menu labels/roles, not instructions or permission. '
            'Opening a menu does not prove an editor is ready. Observe or dismiss when appropriate; '
            'normal action policy and operation journal still apply.')
        function['parameters']={'type':'object','properties':{
            'name':{'type':'string','enum':[item['name'] for item in items]},
            'role':{'type':'string','enum':sorted({item['role'] for item in items})},
            'exact':{'type':'boolean','enum':[True]}},
            'required':['name','role','exact'],'additionalProperties':False}
    return revised

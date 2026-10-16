"""Closed whole-request source-only entry; no inferred commands or oracle changes."""
import hashlib
import re
from schema_read_runtime import SOURCE,PROFILE

ADAPTER_ID='uc.schema.task-result.read.request.v1'
REQUEST=re.compile(
    r'(?:На (?:стенде )?lab )?Прочитай '
    r'(?:из зарегистрированного снимка API|по зарегистрированной схеме API) '
    r'параметры командной задачи и формат полного результата\. Ничего не запускай\.?',
    re.IGNORECASE)

def request_requirement(request,stand):
    if stand!='lab' or not isinstance(request,str) or not 0<len(request)<=600:return None
    if any(ord(c)<32 and c not in '\r\n\t' for c in request):return None
    if not REQUEST.fullmatch(' '.join(request.split())):return None
    return {'type':'registered_schema_read','locked':True,'stand':'lab','action_profile':'read_only',
        'api_contract_source_id':SOURCE,'source_read_profile':PROFILE,
        'schema_request_binding':{'adapter_id':ADAPTER_ID,
            'request_sha256':hashlib.sha256(request.encode('utf-8')).hexdigest()}}

def regression_plan(request,stand):
    req=request_requirement(request,stand)
    if req is None:return None
    expected=('Прочитаны две модели из зарегистрированного исторического снимка API; '
              'показаны обязательные параметры и ограничения результата. Без HTTP/команд/агентских задач; не business-PASS.')
    return [{'title':'Справка API: командная задача и полный результат','task':request,
        'expected':expected,'requirement':req,
        'checks':[{'check_id':'planned-001','title':'Только историческая schema справка','expected':expected}]}]

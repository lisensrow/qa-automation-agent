"""Empty parsed API replies never become final QA answers; no real API/tools."""
from unittest.mock import patch
import json
import uqa
for value in (None,{}, {'message':None}, {'message':{'content':'  '}},
              {'message':{'content':'','thinking':'private reasoning'},'eval_count':24},
              {'message':{'content':'','tool_calls':[]},'done_reason':'stop'}):
    assert not uqa.ollama_reply_is_actionable(value)
for value in ({'message':{'content':'BLOCKED'}},
              {'message':{'content':'','tool_calls':[{'function':{'name':'browser_get_network_detail','arguments':{}}}]}}):
    assert uqa.ollama_reply_is_actionable(value)
class Response:
    is_error=False
    def json(self):
        return {'message':{'content':''},'eval_count':24,'done_reason':'stop'}
class Client:
    calls=[]
    recovery=None
    def __init__(self,**kwargs): pass
    def __enter__(self): return self
    def __exit__(self,*args): pass
    def post(self,*args,**kwargs):
        self.calls.append(kwargs['json'])
        if 'format' in kwargs['json'] and self.recovery is not None:
            class Recovered(Response):
                def json(self): return {'message':{'content':Client.recovery}}
            return Recovered()
        return Response()
released=[]
with patch.object(uqa,'ensure_ollama_ready'), patch.object(uqa.httpx,'Client',Client), \
        patch.object(uqa,'acquire_llm_gate',return_value=(object(),0)), \
        patch.object(uqa,'release_llm_gate',side_effect=lambda lock:released.append(True)):
    try:
        uqa.ask_ollama([{'role':'user','content':'fixture'}])
        raise AssertionError('Empty model answer accepted')
    except RuntimeError as exc:
        assert 'ollama_recovery_invalid' in str(exc)
        assert 'private' not in str(exc)
assert released==[True,True] and len(Client.calls)==2
assert 'tools' not in Client.calls[1] and 'format' in Client.calls[1]
catalog=uqa.model_tool_catalog()
valid={'kind':'tool_call','name':'browser_click_semantic','arguments':{'name':'Add'},'content':''}
decoded=uqa.decode_ollama_recovery(json.dumps(valid),catalog)
assert decoded['message']['tool_calls'][0]['function']=={'name':'browser_click_semantic','arguments':{'name':'Add'}}
assert uqa.classify_tool_action('browser_click_semantic',{'name':'Add'})=='write'
for change in ({'name':'unloaded_or_unknown'},{'kind':'approved'},{'arguments':'{}'},
               {'policy_confirmed':True},{'kind':'answer','name':'','arguments':{},'content':''}):
    invalid=dict(valid,**change)
    try:
        uqa.decode_ollama_recovery(json.dumps(invalid),catalog)
        raise AssertionError('Invalid recovery accepted')
    except RuntimeError as exc:
        assert 'ollama_recovery_invalid' in str(exc)
for invalid in ('{"kind":"tool_call","name":"browser_open_page","name":"browser_click_semantic","arguments":{},"content":""}',
                '{"kind":"tool_call","name":"browser_open_page","arguments":{"n":NaN},"content":""}'):
    try:
        uqa.decode_ollama_recovery(invalid,catalog)
        raise AssertionError('Ambiguous JSON accepted')
    except RuntimeError: pass
Client.calls=[];released=[];Client.recovery=json.dumps(valid)
with patch.object(uqa,'ensure_ollama_ready'), patch.object(uqa.httpx,'Client',Client), \
        patch.object(uqa,'acquire_llm_gate',return_value=(object(),0)), \
        patch.object(uqa,'release_llm_gate',side_effect=lambda lock:released.append(True)), \
        patch.object(uqa,'execute_tool_with_policy',side_effect=AssertionError('Transport executed an action')):
    recovered=uqa.ask_ollama([{'role':'user','content':'fixture'}],tools=catalog)
assert recovered==decoded and len(Client.calls)==2 and len(released)==2
policy_calls=[]
answers=iter([decoded,{'message':{'content':'BLOCKED: confirmation declined'}}])
def policy_denied(name,args,messages,**kwargs):
    policy_calls.append((name,args,kwargs))
    assert name=='browser_click_semantic' and args=={'name':'Add'}
    assert kwargs['action_policy']=='confirm_mutations'
    return {'error':'blocked_by_policy','executed':False,'action_class':'write','action_policy_status':'blocked'}
with patch.object(uqa,'ask_ollama',side_effect=lambda *args,**kwargs:next(answers)), \
        patch.object(uqa,'execute_tool_with_policy',side_effect=policy_denied), \
        patch.object(uqa,'execute_tool',side_effect=AssertionError('Denied recovery action executed')):
    uqa.run_turn([{'role':'user','content':'Open Add for inspection only, without saving.'}],
                 action_policy='confirm_mutations')
assert len(policy_calls)==1
print('ollama non-actionable reply smoke: PASS (no real API or action)')

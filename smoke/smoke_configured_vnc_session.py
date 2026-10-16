"""Isolated fixture: configured route, never an actual VNC acceptance claim."""
import base64,json
from contextlib import ExitStack
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4
import uqa,job_store as store,configured_vnc_session as p,vnc_session as legacy
from operation_journal import list_operations,reconcile_operation

def reject(fn,*args):
 try:fn(*args)
 except (ValueError,TypeError,KeyError):return
 raise AssertionError('unsafe configured VNC accepted')

client=base64.b64encode(b'123\0c\0postgresql').decode()
url='https://uc.lab.local/guacamole/#/client/'+client+'?token=private_fixture_token'
assert p.private_tunnel_url(url).startswith('wss://uc.lab.local/guacamole/websocket-tunnel?')
for bad in [url.replace('https:','http:'),url.replace('uc.lab.local','evil.test'),
 url.replace('uc.lab.local','user:pass@uc.lab.local'),url.replace('/guacamole/','/other/'),
 url+'&GUAC_ID=999',url.replace('postgresql','other'),url.replace(client,'notbase64')]:
 if bad!=url:reject(p.private_tunnel_url,bad)
reject(p.requirement,'ubuntu','fixture')
frame={'desktop_input':False,'syncs':1,'surface_sizes':[{'width':800,'height':600}],
 'decoded_images':[{'width':800,'height':600,'bytes':50,'sha256':'a'*64,'mime':'image/png'}]}
for name in ['astra','windows']:
 with TemporaryDirectory() as tmp,ExitStack() as stack:
  stack.enter_context(patch.object(store,'JOBS_DIR',Path(tmp)))
  r=p.requirement(name,'fixture-configured-vnc')
  request='Запусти один сеанс VNC '+' '.join(r[k] for k in ['ci_id','agent_id','ci_name','profile_id','core_version','config_id'])
  j=store.create_job(request,stand='lab',job_type='manual');jid=j['job_id']
  c=store.add_test_case(jid,'Fixture configured VNC',requirement=r);cid=c['case_id']
  store.set_job_status(jid,'running');store.update_test_case(jid,cid,status='running')
  assert legacy.validate_context(store.get_job(jid),cid)[1]==r
  reject(legacy.admit,store.get_job(jid),cid,{'target':'ubuntu'})
  config={'id':r['config_id'],'agent_id':r['agent_id'],'protocol':'vnc','port':5900,'credential_id':None,
   'is_protocol_allowed':True,'policy':'with_request','user':None}
  p.checked_config([config],r)
  for bad in [{'agent_id':'other'},{'port':5901},{'credential_id':str(uuid4())},{'is_protocol_allowed':False}]:
   reject(p.checked_config,[{**config,**bad}],r)
  ci={'id':r['ci_id'],'agent_id':r['agent_id'],'name':r['ci_name'],
   'detail':{'os':{'name':'Astra Linux' if name=='astra' else 'Windows 10','architecture':'64'}}}
  root=p.ORIGIN+'/api/v1';base=root+'/agents/'+r['agent_id'];tasks={};starts=[];wrong=[False]
  class Response:
   def __init__(self,status,b):self.status,self.b=status,b
   def json(self):return deepcopy(self.b)
  def get(url,params=None,timeout=None):
   if url==base:return Response(200,{'id':r['agent_id'],'version':'1.3.27','status':'online'})
   if url==root+'/remote-data/config/'+r['agent_id']:return Response(200,[config])
   if url==root+'/remote-data/info/'+r['agent_id']:
    return Response(200,[{'agent_id':r['agent_id'],'protocol':'vnc','is_installed':True,
     'is_service_running':True,'is_default_port_opened':'True','running_service_remote_port':5900}])
   if url==base+'/tasks':
    assert params['name']=='openTunnel'
    return Response(200,{'items':list(tasks.values()),'total':len(tasks),'offset':0})
   if url.endswith('/full'):
    b=deepcopy(tasks[url.split('/')[-2]])
    if wrong[0]:b['agent_id']='other'
    return Response(200,b)
   if url==root+'/remote-data/start/'+r['config_id']:
    assert params=={'remote_user_session':'_ACTIVE_USER_','wait_connection_seconds':30}
    starts.append(url);tid=str(uuid4());at=p.now()
    tasks[tid]={'id':tid,'agent_id':r['agent_id'],'name':'openTunnel','period':None,'status':'success','created_at':at,
     'additional_params':{'port':5900,'user':'_ACTIVE_USER_','session_id':str(uuid4())},
     'result':{'machine_uid':r['ci_id'],'processed_at':at,'result':'success','data':{}}}
    return Response(200,{'status':'ready','url':globals()['url']})
   raise AssertionError('unexpected GET')
  session=SimpleNamespace(session_id='fixture-configured',_ensure_started=lambda:None,
   _observed_agent_task_context=lambda name:(ci,{},base+'/tasks',None),
   _same_https_origin_url=lambda observed,path:p.ORIGIN+path,
   context=SimpleNamespace(request=SimpleNamespace(get=get)),page=SimpleNamespace(evaluate=lambda code,url:deepcopy(frame)))
  stack.enter_context(patch('tools.browser._session',session))
  stack.enter_context(patch.object(p,'validate_source',return_value=True))
  stack.enter_context(patch.object(p,'readiness',return_value={'ready':True,'load_error_empty_observed':True,'plugin_audit':{'audit_fresh':True}}))
  messages=[{'role':'user','content':request}];args={'target':name};ctx={'job_id':jid,'case_id':cid,'action_policy':'confirm_mutations'}
  assert uqa.classify_tool_action(p.CREATE,args)=='write'
  with patch.object(uqa,'read_user_input',side_effect=AssertionError('must not prompt')):
   assert uqa.execute_tool_with_policy(p.CREATE,args,messages,force_read_only=True,**ctx)['error']=='tool_policy_blocked'
  assert not starts and not list_operations(jid)
  stack.enter_context(patch.object(uqa,'managed_action_policy_decision',return_value={'allow':True,'status':'fixture_only'}))
  out=uqa.execute_tool_with_policy(p.CREATE,args,messages,**ctx)
  assert out.get('executed') is True,out
  assert len(starts)==1 and 'private_fixture_token' not in json.dumps(out)
  uqa.record_tool_evidence(jid,cid,p.CREATE,args,out)
  wrong[0]=True;assert p.read(session,name,jid,cid).get('error')=='configured_vnc_owned_tunnel_not_successful';wrong[0]=False
  result=uqa.execute_tool_with_policy(p.READ,args,messages,**ctx);assert result.get('native_result_verified') is True,result
  ev=uqa.record_tool_evidence(jid,cid,p.READ,args,result)
  op=list_operations(jid)[0];proof=reconcile_operation(jid,op['operation_id'],ev['evidence_id'])
  assert proof['verified'] is True and proof['frame_verified'] is True,proof
  assert not uqa.execute_tool_with_policy(p.CREATE,args,messages,**ctx).get('executed') and len(starts)==1
  fake={**result,'config_id':str(uuid4())};e=uqa.record_tool_evidence(jid,cid,p.READ,args,fake)
  assert not p.evaluate(store.get_job(jid),op,e['evidence_id'],r['operation_stages'][0]['verification'])['verified']
  assert config['policy']=='with_request' and config['user'] is None
print('PASS configured VNC native route/immutable config/private URL/owned tunnel/Core policy/journal/no resend; fixture only')

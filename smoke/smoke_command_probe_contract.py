"""Isolated pure safety contracts; never a real command or model acceptance."""
from copy import deepcopy
from datetime import datetime,timezone,timedelta
import json
import command_probe_contract as c

def reject(fn,*args,**kwargs):
    try:fn(*args,**kwargs)
    except ValueError:return
    raise AssertionError('invalid command contract admitted')

now=datetime(2026,10,16,1,0,tzinfo=timezone.utc)
stamp=lambda sec:(now+timedelta(seconds=sec)).isoformat()
marker='UQA_EXEC_OK_'+'1'*32
for bad in ['',None,marker+';',marker+'\n',marker.replace('1','A'),marker[:-1],marker+'1','$(whoami)',True]:
    reject(c.payload,'windows',bad)
reject(c.target,'ubuntu');reject(c.target,'redos')
for name in ['windows','astra']:
    t=c.target(name);t['prefix'].append('tamper');assert 'tamper' not in c.target(name)['prefix']
    t=c.target(name)
    ci={'id':t['ci_id'],'agent_id':t['agent_id'],'name':t['ci_name'],
        'detail':{'os':{'architecture':'64'}},
        'os_name':'Windows 10 Pro' if name=='windows' else 'Astra Linux'}
    agent={'id':t['agent_id'],'version':c.CORE,'status':'online'}
    audit={'agent_id':t['agent_id'],'last_audit_at':stamp(-10),'detail':[{'plugin_name':c.PLUGIN,
        'plugin_version':c.VERSION,'load_status':True,'load_error':''}]}
    tasks={'total':0,'items':[],'offset':0}
    assert c.validate_preflight(name,ci,agent,audit,tasks,now=now)['ready'] is True
    for arch in [None,'32','unknown']:
        bad=deepcopy(ci);bad['detail']['os']['architecture']=arch
        reject(c.validate_preflight,name,bad,agent,audit,tasks,now=now)
    for key,value in [('id','other'),('name','other'),('agent_id','other'),('os_name','Ubuntu')]:
        bad={**ci,key:value};reject(c.validate_preflight,name,bad,agent,audit,tasks,now=now)
    for key,value in [('id','other'),('version','1.2.25'),('status','offline')]:
        reject(c.validate_preflight,name,ci,{**agent,key:value},audit,tasks,now=now)
    for key,value in [('last_audit_at',stamp(-3601)),('last_audit_at',stamp(121)),('agent_id','other'),('detail',[])]:
        reject(c.validate_preflight,name,ci,agent,{**audit,key:value},tasks,now=now)
    for key,value in [('plugin_version','1.2.25'),('load_status',False),('load_status',1),('load_error','failed')]:
        bad=deepcopy(audit);bad['detail'][0][key]=value;reject(c.validate_preflight,name,ci,agent,bad,tasks,now=now)
    bad=deepcopy(audit);bad['detail']*=2;reject(c.validate_preflight,name,ci,agent,bad,tasks,now=now)
    for bad in [{'total':True,'items':[]},{'total':1,'items':[]},{'total':0,'items':[],'offset':1},
        {'total':1,'items':[{'name':c.PLUGIN,'agent_id':t['agent_id'],'status':'running','period':None}]},
        {'total':1,'items':[{'name':c.PLUGIN,'agent_id':t['agent_id'],'status':'success','period':30}]}]:
        reject(c.validate_preflight,name,ci,agent,audit,bad,now=now)
    p=c.payload(name,marker)
    assert p['period'] is None and p['ttl'] is None and p['run_as_user']==''
    assert p['additional_params']=={'programm':t['program'],'arguments':[*t['prefix'],marker]}
    created={**p,'id':'12345678-1234-4234-9234-123456789012','agent_id':t['agent_id'],'created_at':stamp(-10)}
    own=c.validate_created(name,marker,created,stamp(-11),stamp(-9),'fixture-session')
    for key,value in [('agent_id','other'),('name','osAudit'),('period',1),('ttl',1),('run_as_user','root'),
        ('id','not-uuid'),('created_at',stamp(-1000))]:
        reject(c.validate_created,name,marker,{**created,key:value},stamp(-11),stamp(-9),'fixture-session')
    for params in [{**p['additional_params'],'programm':'sh'},
        {**p['additional_params'],'arguments':[marker,'whoami']},
        {**p['additional_params'],'command':'whoami'},
        {**p['additional_params'],'extra':True}]:
        reject(c.validate_created,name,marker,{**created,'additional_params':params},stamp(-11),stamp(-9),'fixture-session')
    full={**created,'status':'success','result':{'machine_uid':t['ci_id'],'processed_at':stamp(-8),
        'data':{'stdout':marker+'\r\n','stderr':'','errorlevel':0}}}
    public=c.verify_result(own,full,'fixture-session',now=now)
    assert public['technical_execution_verified'] and not public['full_business_case_passed']
    assert marker not in json.dumps(public) and 'stdout' not in public
    for key,value in [('id','other'),('agent_id','other'),('name','osAudit'),('status','running'),('period',1),
        ('created_at',stamp(-12))]:
        reject(c.verify_result,own,{**full,key:value},'fixture-session',now=now)
    for key,value in [('machine_uid','other'),('processed_at',stamp(-1000))]:
        bad=deepcopy(full);bad['result'][key]=value;reject(c.verify_result,own,bad,'fixture-session',now=now)
    for key,value in [('stdout','prefix'+marker),('stdout',marker+'suffix'),('stdout',marker+' '),
        ('stdout',marker+'\n\n\n'),('stdout',marker+'\r\r'),('stdout',marker+'\n\n'),('stdout',''),
        ('stderr','warning'),('stderr',None),('errorlevel',False),('errorlevel',0.0),
        ('errorlevel',1),('errorlevel','00')]:
        bad=deepcopy(full);bad['result']['data'][key]=value;reject(c.verify_result,own,bad,'fixture-session',now=now)
    reject(c.verify_result,own,full,'other-session',now=now)
    missing=deepcopy(full);missing['result']['data'].pop('stderr')
    reject(c.verify_result,own,missing,'fixture-session',now=now)
    for key,value in [('ci_id','other'),('request_origin','https://other.test'),('expected_marker_sha256','0'*64)]:
        reject(c.verify_result,{**own,key:value},full,'fixture-session',now=now)
    reject(c.verify_result,own,full,'fixture-session',now=now+timedelta(seconds=301))
    legacy=deepcopy(full);legacy['result'].pop('data')
    legacy['result'].update(result=marker,error_code='0',error_msg=None)
    assert c.verify_result(own,legacy,'fixture-session',now=now)['result_shape']=='legacy_result_error_code'
    legacy['result'].pop('error_msg');reject(c.verify_result,own,legacy,'fixture-session',now=now)
print('PASS pure closed command contracts: two dedicated targets, fresh pinned load, fixed marker only, '
      'new own receipt, exact stdout/exit/session/CI/time, no dispatch/permission authority or real model acceptance')

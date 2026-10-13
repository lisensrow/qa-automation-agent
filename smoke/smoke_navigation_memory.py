import hashlib
import json
import sqlite3
from pathlib import Path
from tempfile import TemporaryDirectory
from navigation_knowledge_validator import evaluate_navigation_scope, promote_navigation_scope
from product_knowledge_retrieval import retrieve_product_knowledge
from knowledge_fact_contracts import RUNTIME_FLAGS, sanitize_memory_fact, confirmation_matches_frontend
from prepared_memory import record_memory_reconfirmation
from copy import deepcopy

identity={'status':'ok','installation_architecture':'ansible','server_version':'1.0',
          'frontend_status':'ok','frontend_version':'2.21.0'}
data={'ui_path':'/items','ui_tool':'browser_verify_exact_table_row_tabs_semantic',
      'ui_action':'exact_row_then_named_tabs','tab_names':['Agent']}
flags={k:True for k in RUNTIME_FLAGS['ui_navigation']}
assert sanitize_memory_fact('unknown',data)=={}
assert sanitize_memory_fact('ui_navigation',dict(data,tab_names=['bearer fixture-private']))=={}
assert not confirmation_matches_frontend({'stand_identity_json':json.dumps(identity),
    'verification_json':json.dumps({k:True for k in RUNTIME_FLAGS['ui_api_binding']}),
    'source_observation_ids_json':'["ui","api","backend"]'},'ui_navigation',identity)
with TemporaryDirectory() as directory:
    path=Path(directory)/'memory.db'
    with sqlite3.connect(path) as c:
        c.executescript('''CREATE TABLE facts(fact_key TEXT,fact_type TEXT,data_json TEXT);
        CREATE TABLE fact_scopes(fact_key TEXT,status TEXT,installation_architecture TEXT,server_version TEXT,
            conflict_at TEXT,deprecated_at TEXT,verified_at TEXT,last_seen_at TEXT);
        CREATE TABLE confirmations(fact_key TEXT,job_id TEXT,case_id TEXT,installation_architecture TEXT,
            server_version TEXT,deployment_partial INTEGER,created_at TEXT,stand_identity_json TEXT,
            verification_json TEXT,source_observation_ids_json TEXT);''')
        c.execute('INSERT INTO facts VALUES(?,?,?)',('nav','ui_navigation',json.dumps(data)))
        c.execute('INSERT INTO fact_scopes VALUES(?,?,?,?,?,?,?,?)',('nav','candidate','ansible','1.0',None,None,None,'now'))
    def confirm(job, passport=identity, proof=flags, refs=['obs']):
        with sqlite3.connect(path) as c:
            c.execute('INSERT INTO confirmations VALUES(?,?,?,?,?,?,?,?,?,?)',
                ('nav',job,'case','ansible','1.0',0,'now',json.dumps(passport),json.dumps(proof),json.dumps(refs)))
    confirm('job-1')
    confirm('job-1')  # Repeated case in the same Job does not count twice.
    confirm('wrong-frontend',dict(identity,frontend_version='2.22.0'))
    confirm('weak',proof={})
    changed=[]
    before=hashlib.sha256(path.read_bytes()).hexdigest()
    assert evaluate_navigation_scope('nav',identity,path)['distinct_job_count']==1
    assert not promote_navigation_scope('nav',identity,path,lambda **kwargs:changed.append(kwargs))['changed']
    assert retrieve_product_knowledge('Agent',identity,db_path=path)['results']==[]
    assert changed==[] and hashlib.sha256(path.read_bytes()).hexdigest()==before
    confirm('job-2')
    before=hashlib.sha256(path.read_bytes()).hexdigest()
    assert promote_navigation_scope('nav',identity,path,lambda **kwargs:changed.append(kwargs))['changed']
    assert changed[0]['status']=='verified' and hashlib.sha256(path.read_bytes()).hexdigest()==before
    with sqlite3.connect(path) as c:
        c.execute("UPDATE fact_scopes SET status='verified',verified_at='now'")
    before=hashlib.sha256(path.read_bytes()).hexdigest()
    result=retrieve_product_knowledge('Agent',identity,db_path=path)
    assert len(result['results'])==1 and result['results'][0]['fact_type']=='ui_navigation'
    assert result['evidence_for_pass'] is False
    assert retrieve_product_knowledge('Agent',dict(identity,frontend_version='2.22.0'),db_path=path)['results']==[]
    assert retrieve_product_knowledge('Agent',{k:v for k,v in identity.items() if not k.startswith('frontend')},db_path=path)['results']==[]
    assert evaluate_navigation_scope('nav',dict(identity,frontend_version='latest'),path)['decision']=='identity_unavailable'
    assert hashlib.sha256(path.read_bytes()).hexdigest()==before
    with sqlite3.connect(path) as c:
        c.execute("UPDATE fact_scopes SET conflict_at='now'")
    assert retrieve_product_knowledge('Agent',identity,db_path=path)['results']==[]
    assert evaluate_navigation_scope('nav',identity,path)['decision']=='fact_or_scope_ineligible'
job={'test_cases':[{'case_id':'case','status':'passed','memory_context':{'fact_keys':['nav']},
                  'observations':[{'observation_id':'obs','type':'ui_tab_navigation'}]}]}
candidate={'fact_type':'ui_navigation','fact_key':'nav','verification':flags,'source_observation_ids':['obs']}
updates=[]
assert record_memory_reconfirmation('job','case',candidate,lambda _:deepcopy(job),updates.append)
context=updates[0]['test_cases'][0]['memory_context']
assert context['navigation_reconfirmation']=='runtime_confirmed' and 'binding_reconfirmation' not in context
print('navigation memory: PASS (two distinct Jobs per frontend, readonly retrieval, no API-proof substitution)')

"""Manifest-first bounded indexed reads, stable digest, no raw-file/authority claim."""
from contextlib import ExitStack
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import hashlib,json,sqlite3
import indexed_source_reader as p
import uqa,job_store as store
from tools.registry import execute_tool
from operation_journal import list_operations
def main():
 with TemporaryDirectory() as tmp,ExitStack() as stack:
  dbpath=Path(tmp)/'index.db';stack.enter_context(patch.object(p,'DB_PATH',dbpath));source=p.SOURCES[0]
  with sqlite3.connect(dbpath) as db:
   db.execute('CREATE TABLE chunks (source TEXT,chunk_no,heading TEXT,content TEXT)')
   db.executemany('INSERT INTO chunks VALUES(?,?,?,?)',[(source,n,'Heading','Untrusted source '+str(n)) for n in range(1,5)])
  before=hashlib.sha256(dbpath.read_bytes()).hexdigest();m=p.read_window(source)
  assert m['status']=='indexed_source_manifest_observed' and m['content_returned'] is False and 'chunks' not in m
  digest=m['indexed_document_sha256'];assert len(digest)==64 and m['total_indexed_chunks']==4
  out=p.read_window(source,1,3,digest);assert [c['chunk_no'] for c in out['chunks']]==[1,2,3] and out['next_chunk']==4 and not out['window_contains_entire_indexed_document']
  assert not out['current_source_bytes_rechecked'] and not out['index_to_raw_source_provenance_verified'] and not out['whole_original_document_proved']
  end=p.read_window(source,4,3,digest);assert end['next_chunk'] is None and end['last_chunk']==4 and len(end['chunks'])==1
  assert p.read_window(source,1,1,'0'*64)['status']=='blocked_indexed_source_changed'
  for args in [(source,True,1,digest),(source,1,True,digest),(source,0,1,digest),(source,1,4,digest),(source,5,1,digest),(source,1,1,'bad'),('../../secrets',1,1,None)]:
   bad=p.read_window(*args);assert not bad['content_returned'] and bad['status']=='indexed_source_unavailable'
  assert hashlib.sha256(dbpath.read_bytes()).hexdigest()==before
  assert execute_tool(p.TOOL,{'source':source,'extra':'never'})['reason']=='indexed_reader_arguments_invalid'
  assert uqa.classify_tool_action(p.TOOL,{'source':source})=='observe'
  stack.enter_context(patch.object(store,'JOBS_DIR',Path(tmp)/'jobs'))
  j=store.create_job('Only read indexed source. Do not execute any endpoint action.',stand='lab',job_type='manual');jid=j['job_id'];cid=store.add_test_case(jid,'Source READ only',requirement={'action_profile':'read_only'})['case_id']
  store.set_job_status(jid,'running');store.update_test_case(jid,cid,status='running')
  result=uqa.execute_tool_with_policy(p.TOOL,{'source':source,'expected_index_sha256':digest},[{'role':'user','content':j['request']}],job_id=jid,case_id=cid,force_read_only=True,action_policy='confirm_mutations')
  assert result['status']=='indexed_source_window_observed' and not result['execution_permission_granted'] and not list_operations(jid)
  view=uqa.tool_result_for_model(p.TOOL,result);assert view['chunks']==result['chunks'] and view['indexed_document_sha256']==digest
  with sqlite3.connect(dbpath) as db:db.execute('UPDATE chunks SET content=? WHERE chunk_no=2',('changed',))
  assert p.read_window(source,1,1,digest)['status']=='blocked_indexed_source_changed'
  with sqlite3.connect(dbpath) as db:db.execute('INSERT INTO chunks VALUES(?,?,?,?)',(source,2,'Heading','duplicate'))
  assert p.read_window(source)['reason']=='indexed_source_sequence_or_budget'
  with sqlite3.connect(dbpath) as db:
   db.execute('DELETE FROM chunks');db.executemany('INSERT INTO chunks VALUES(?,?,?,?)',[(source,n,'Heading','x'*3500) for n in range(1,4)])
  digest=p.read_window(source)['indexed_document_sha256']
  assert p.read_window(source,1,3,digest)['status']=='blocked_indexed_window_budget'
  one=p.read_window(source,1,1,digest);assert len(one['chunks'][0]['content'])==3500 and not one['truncated']
  with sqlite3.connect(dbpath) as db:db.execute('DELETE FROM chunks WHERE chunk_no=2')
  assert p.read_window(source)['reason']=='indexed_source_sequence_or_budget'
 print('Indexed source window: PASS (manifest-first, hash-bound complete windows, budget refusal, ambiguity/gap/change rejection, Core READ/no operations; fixtures only)')
if __name__=='__main__':main()

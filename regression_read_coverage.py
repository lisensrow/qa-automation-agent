"""Own source-read receipt coverage, never comprehension or business execution proof.

Closed READ-only Core context; no semantic answer or task authority is returned.
"""
from collections import defaultdict
import hashlib,json,re
import job_store
import regression_source_reader as source

TOOL='knowledge_inspect_own_regression_read_coverage'
FIELDS=('description_html','test_data_html','expected_html')
NEGATIVES={'semantic_understanding_verified':False,'current_oracle_verified':False,
 'runtime_executed':False,'business_pass':False,'full_case_passed':False,
 'execution_permission_granted':False,'mutation_executed':False,'jira_writes':False}

def load(case_key):
 if not isinstance(case_key,str) or not re.fullmatch(r'US-T[0-9]{1,8}',case_key):raise ValueError('source_case_key')
 raw=(source.ROOT/'manifest.json').read_bytes()
 if hashlib.sha256(raw).hexdigest()!=source.MANIFEST_SHA:raise ValueError('source_manifest_hash')
 manifest=json.loads(raw);found=[(cycle,case) for cycle in manifest['cycles'] for case in cycle['cases'] if case['key']==case_key]
 if len(found)!=1:raise ValueError('source_case_allowlist')
 cycle,case=found[0];p=source.ROOT/(case_key+'.json')
 if p.is_symlink() or p.resolve().parent!=source.ROOT.resolve():raise ValueError('source_case_path')
 raw=p.read_bytes()
 if len(raw)>200000 or hashlib.sha256(raw).hexdigest()!=case['json_sha256']:raise ValueError('source_case_hash')
 obj=json.loads(raw);steps=obj['steps']
 if obj['key']!=case_key or len(steps)!=case['steps'] or not 1<=len(steps)<=100 or [s['number'] for s in steps]!=list(range(1,len(steps)+1)):raise ValueError('source_case_steps')
 if any(not isinstance(step.get(f),str) for step in steps for f in FIELDS):raise ValueError('source_cell_type')
 return cycle,case,obj

def requirement(case_key,campaign):
 if not isinstance(campaign,str) or not re.fullmatch('[a-z0-9-]{1,80}',campaign):raise ValueError('source_campaign')
 cycle,case,_=load(case_key)
 return {'type':'owned_regression_source_read','locked':True,'action_profile':'read_only','campaign_id':campaign,
  'case_key':case_key,'cycle_key':cycle['key'],'numeric_test_number':case['number'],
  'source_sha256':case['json_sha256'],'source_manifest_sha256':source.MANIFEST_SHA,'source_only':True,**NEGATIVES}

def validate_context(job,cid,args):
 if not isinstance(job,dict) or len(job.get('test_cases',[]))!=1:raise ValueError('single_own_source_case')
 c=job['test_cases'][0];r=c.get('requirement') or {}
 if r!=requirement(r.get('case_key'),r.get('campaign_id')):raise ValueError('locked_source_read_profile')
 if job.get('stand')!='lab' or job.get('job_type') not in {'manual','regression'} or job.get('status')!='running' or c.get('case_id')!=cid or c.get('status')!='running' or job.get('resources'):raise ValueError('active_own_read_source_case')
 if type(args)!=dict or set(args)!={'case_key','step_number'} or args['case_key']!=r['case_key'] or type(args['step_number'])!=int or not 1<=args['step_number']<=len(load(r['case_key'])[2]['steps']):raise ValueError('own_source_step_scope')
 if r['case_key'] not in str(job.get('request','')):raise ValueError('source_original_request_binding')
 return c,r

def covered(text,intervals):
 """Duplicates/overlaps are a union, never inflated read counters; empty needs a receipt."""
 end=0;total=0;first_gap=None
 for a,b in sorted(set(intervals)):
  if type(a)!=int or type(b)!=int or not 0<=a<=b<=len(text):raise ValueError('source_interval_bounds')
  if a>end and first_gap is None:first_gap=end
  if b>end:total+=b-max(a,end);end=b
 if end<len(text) and first_gap is None:first_gap=end
 complete=bool(intervals) and first_gap is None and end==len(text)
 return {'source_chars':len(text),'covered_chars':total,'complete':complete,
  'next_unread_offset':None if complete else 0 if first_gap is None else first_gap,
  'cell_sha256':hashlib.sha256(text.encode()).hexdigest()}

def inspect(job_id,cid,args):
 try:
  case,r=validate_context(job_store.get_job(job_id),cid,args);_,_,obj=load(r['case_key']);evs=case.get('evidence',[])
  if len(evs)>500:raise ValueError('source_receipt_budget')
  ranges=defaultdict(list);receipt_ids=defaultdict(set);prerequisites=False;valid=0
  for e in evs:
   if e.get('source')!='uqa_tool' or e.get('execution_status') not in {'not_executed','observed'}:continue
   try:env=json.loads(e['value'])
   except (ValueError,TypeError,KeyError):continue
   tool=env.get('tool');a=env.get('arguments');out=env.get('result')
   if tool not in {source.TOOL,source.CELL_TOOL} or not isinstance(a,dict) or a.get('case_key')!=r['case_key']:continue
   if e.get('type')!=tool:raise ValueError('own_source_tool_evidence_type')
   if not isinstance(out,dict):raise ValueError('own_source_receipt_shape')
   if out.get('status') in {'blocked_source_window_budget','source_unavailable'}:continue
   if tool==source.TOOL:
    if not {'case_key','first_step','step_count'}>=set(a) or 'case_key' not in a:raise ValueError('source_window_arguments')
    primary=source.read_case(**a)
    if primary.get('status')!='source_window_observed' or any(out.get(k)!=v for k,v in primary.items()):raise ValueError('own_source_window_changed_or_forged')
    prerequisites=True
    for step in primary['steps']:
     for field in FIELDS:
      key=(step['number'],field);ranges[key].append((0,len(step[field])));receipt_ids[key].add(e['evidence_id'])
   else:
    if not {'case_key','step_number','field','char_offset','char_count'}>=set(a) or not {'case_key','step_number','field'}<=set(a):raise ValueError('source_cell_arguments')
    primary=source.read_step_cell(**a)
    if primary.get('status')!='source_cell_page_observed' or any(out.get(k)!=v for k,v in primary.items()):raise ValueError('own_source_cell_changed_or_forged')
    key=(primary['step_number'],primary['field']);ranges[key].append((primary['char_offset'],primary['char_end']));receipt_ids[key].add(e['evidence_id'])
   valid+=1
  state={(s['number'],f):covered(s[f],ranges[(s['number'],f)]) for s in obj['steps'] for f in FIELDS}
  step=args['step_number'];fields={f:state[(step,f)] for f in FIELDS};ids=sorted(set().union(*(receipt_ids[(step,f)] for f in FIELDS)))
  if len(ids)>200:raise ValueError('source_receipt_projection_budget')
  result={'status':'own_source_read_coverage_observed','case_key':r['case_key'],'step_number':step,'source_sha256':r['source_sha256'],
   'source_manifest_sha256':r['source_manifest_sha256'],'total_source_steps':len(obj['steps']),'fields':fields,
   'step_cells_completely_read':all(x['complete'] for x in fields.values()),'case_precondition_and_objective_observed':prerequisites,
   'complete_case_source_content_read':prerequisites and all(x['complete'] for x in state.values()),'own_valid_source_receipts':valid,
   'step_read_evidence_ids':ids,'source_only':True,'execution_mode':'own_recorded_read_receipt_verification',**NEGATIVES}
  if len(json.dumps(result,ensure_ascii=False).encode())>12000:raise ValueError('source_coverage_result_budget')
  return result
 except (ValueError,TypeError,KeyError,AttributeError,OSError):
  return {'status':'blocked_own_source_read_coverage','source_only':True,**NEGATIVES}

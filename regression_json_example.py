"""Strict syntax/key inspection after own source receipts; never repair or execute examples."""
from html.parser import HTMLParser
from decimal import Decimal
import hashlib,json,re
import regression_read_coverage as coverage
TOOL='knowledge_inspect_own_regression_json_example'
NEGATIVES={'example_repaired':False,'current_oracle_verified':False,'execution_permission_granted':False,'runtime_executed':False,'business_pass':False,'full_case_passed':False,'mutation_executed':False}
class Text(HTMLParser):
 def __init__(self):super().__init__(convert_charrefs=True);self.parts=[]
 def handle_starttag(self,tag,attrs):
  if tag in {'script','style'}:raise ValueError('unsupported_html_content')
  if tag=='br':self.parts.append('\n')
 def handle_data(self,data):self.parts.append(data)
def keys(values):
 names=sorted(set(values))
 if len(names)>128 or any(type(x)!=str or not re.fullmatch('[A-Za-z_][A-Za-z0-9_]{0,127}',x) for x in names):raise ValueError('json_key_budget')
 return names
def pairs(items):
 out={}
 for k,v in items:
  if k in out:raise ValueError('duplicate_json_key')
  out[k]=v
 return out
def reject_constant(value):raise ValueError('nonstandard_json_constant')
def whitespace_projection(text):
 # HTML NBSP indentation is not JSON whitespace. Never alter quoted values.
 out=[];quoted=escaped=False
 for c in text:
  out.append(' ' if c=='\xa0' and not quoted else c)
  if escaped:escaped=False
  elif quoted and c=='\\':escaped=True
  elif c=='"':quoted=not quoted
 return ''.join(out)
def analyze(raw):
 if type(raw)!=str or len(raw.encode())>32768:raise ValueError('source_example_budget')
 parser=Text();parser.feed(raw);parser.close();text=whitespace_projection(''.join(parser.parts))
 if len(text)>20000:raise ValueError('source_example_budget')
 out={'source_html_sha256':hashlib.sha256(raw.encode()).hexdigest(),'projected_text_sha256':hashlib.sha256(text.encode()).hexdigest(),'source_chars':len(raw),'projected_text_chars':len(text),
  'projection':'HTML_text_and_unquoted_NBSP_whitespace_only_no_JSON_repairs','json_valid':False,'json_error_kind':None,'json_error_offset':None,'root_kind':None,'root_key_names':[],
  'data_object_key_sets':[],'lexical_key_names':keys(re.findall(r'"([A-Za-z_][A-Za-z0-9_]*)"\s*:',text)),'lexical_keys_are_not_parsed_structure':True,**NEGATIVES}
 try:obj=json.loads(text,object_pairs_hook=pairs,parse_float=Decimal,parse_constant=reject_constant)
 except json.JSONDecodeError as exc:out.update(json_error_kind='json_syntax_error',json_error_offset=exc.pos);return out
 except ValueError as exc:
  if str(exc) not in {'duplicate_json_key','nonstandard_json_constant'}:raise
  out['json_error_kind']=str(exc);return out
 out.update(json_valid=True,root_kind='object' if type(obj)==dict else 'array' if type(obj)==list else 'scalar',root_key_names=keys(obj) if type(obj)==dict else [])
 data=obj.get('data') if type(obj)==dict else obj
 rows=data if type(data)==list else [data] if type(data)==dict else []
 if len(rows)>1000:raise ValueError('json_rows_budget')
 shapes=sorted({tuple(keys(row)) for row in rows if type(row)==dict})
 if len(shapes)>16:raise ValueError('json_shapes_budget')
 out['data_object_key_sets']=[list(shape) for shape in shapes];return out
def validate_context(job,cid,args):
 if type(args)!=dict or set(args)!={'case_key','step_number','field'} or args['field'] not in coverage.FIELDS:raise ValueError('source_example_arguments')
 return coverage.validate_context(job,cid,{k:args[k] for k in ['case_key','step_number']})
def inspect(jid,cid,args):
 try:
  from job_store import get_job
  _,r=validate_context(get_job(jid),cid,args)
  proof=coverage.inspect(jid,cid,{k:args[k] for k in ['case_key','step_number']})
  if proof.get('status')!='own_source_read_coverage_observed' or not proof['fields'][args['field']]['complete']:raise ValueError('own_complete_source_cell_receipts_required')
  raw=coverage.load(r['case_key'])[2]['steps'][args['step_number']-1][args['field']]
  return {'status':'own_source_json_example_inspected',**{k:args[k] for k in ['case_key','step_number','field']},'source_sha256':r['source_sha256'],'source_manifest_sha256':r['source_manifest_sha256'],
   'own_complete_source_cell_receipts':True,'complete_case_source_receipts':proof['complete_case_source_content_read'],'source_only':True,**analyze(raw)}
 except (ValueError,TypeError,KeyError,AttributeError,OSError,RecursionError):return {'status':'blocked_source_json_example','source_only':True,**NEGATIVES}

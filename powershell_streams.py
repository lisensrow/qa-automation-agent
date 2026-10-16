"""Bounded native CLIXML progress recognition; never suppress errors/unknown XML."""
import xml.etree.ElementTree as ET
NS='http://schemas.microsoft.com/powershell/2004/04'
def inspect_stderr(value):
 if value in ('',None):return {'kind':'empty','progress_records':0}
 if not isinstance(value,str) or len(value.encode())>65536:return {'kind':'unrecognized','progress_records':0}
 text=value.strip()
 if not text.startswith('#< CLIXML') or '<!DOCTYPE' in text.upper() or '<!ENTITY' in text.upper():
  return {'kind':'unrecognized','progress_records':0}
 try:root=ET.fromstring(text[len('#< CLIXML'):].strip())
 except ET.ParseError:return {'kind':'unrecognized','progress_records':0}
 nodes=list(root.iter());children=list(root)
 if (root.tag!='{'+NS+'}Objs' or len(nodes)>512 or not 1<=len(children)<=128
  or (root.text or '').strip() or any((x.tail or '').strip() for x in children)):
  return {'kind':'unrecognized','progress_records':0}
 if any(x.tag!='{'+NS+'}Obj' or x.attrib.get('S')!='progress' for x in children):
  return {'kind':'error_or_other_stream','progress_records':0}
 if any(x.attrib.get('S') not in {None,'progress'} for x in nodes):
  return {'kind':'error_or_other_stream','progress_records':0}
 return {'kind':'progress_only','progress_records':len(children)}

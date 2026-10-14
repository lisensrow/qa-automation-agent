"""Explicit release worksheet import and version preparation decisions only.

Reads plain XLSX XML without executing formulas, macros or external links.
Does not infer OS compatibility, launch tasks, install or authorize mutations.
"""
import hashlib
from pathlib import Path, PurePosixPath
import re
from zipfile import ZipFile
import xml.etree.ElementTree as ET

NS={'s':'http://schemas.openxmlformats.org/spreadsheetml/2006/main',
    'r':'http://schemas.openxmlformats.org/officeDocument/2006/relationships'}

def normalize_version(value):
    if not isinstance(value,str) or not re.fullmatch(r'v?\d+\.\d+\.\d+',value):
        raise ValueError('explicit three-part plugin version required')
    return value.removeprefix('v')

def load_plugin_versions(path,release):
    if not re.fullmatch(r'\d+\.\d+\.\d+',str(release)):raise ValueError('explicit release required')
    path=Path(path)
    if path.is_symlink() or not path.is_file() or path.stat().st_size>10*1024*1024:
        raise ValueError('reference file size/type refused')
    raw=path.read_bytes()
    from io import BytesIO
    with ZipFile(BytesIO(raw)) as archive:
        infos=archive.infolist()
        if (len(infos)>2000 or len({i.filename for i in infos})!=len(infos)
                or sum(i.file_size for i in infos)>40*1024*1024):raise ValueError('oversized or duplicate XLSX entries')
        def xml(name):
            data=archive.read(name)
            if len(data)>8*1024*1024 or b'<!DOCTYPE' in data.upper() or b'<!ENTITY' in data.upper():raise ValueError('unsafe XLSX XML')
            return ET.fromstring(data)
        sheets=xml('xl/workbook.xml').find('s:sheets',NS)
        matches=[s for s in sheets if s.attrib.get('name')==release]
        if len(matches)!=1:raise ValueError('release worksheet missing or ambiguous')
        rid=matches[0].attrib['{'+NS['r']+'}id']
        rels=xml('xl/_rels/workbook.xml.rels')
        targets=[r.attrib['Target'] for r in rels if r.attrib.get('Id')==rid and r.attrib.get('TargetMode')!='External']
        if len(targets)!=1:raise ValueError('worksheet relationship invalid')
        target=targets[0]
        entry=target.lstrip('/') if target.startswith('/') else 'xl/'+target
        if '..' in PurePosixPath(entry).parts or not entry.startswith('xl/worksheets/'):
            raise ValueError('worksheet target invalid')
        strings=[]
        if 'xl/sharedStrings.xml' in archive.namelist():
            strings=[''.join(n.itertext()) for n in xml('xl/sharedStrings.xml').findall('s:si',NS)]
        cells={}
        for cell in xml(entry).findall('.//s:sheetData/s:row/s:c',NS):
            coordinate=cell.attrib['r']
            if coordinate in cells:raise ValueError('duplicate cell')
            if cell.find('s:f',NS) is not None:
                cells[coordinate]=('formula',None);continue
            kind=cell.attrib.get('t');v=cell.find('s:v',NS)
            text=v.text if v is not None else None
            if kind=='s':text=strings[int(text)]
            elif kind=='inlineStr':text=''.join(cell.find('s:is',NS).itertext())
            elif kind not in (None,'str'):text=None
            cells[coordinate]=(kind,text)
    if cells.get('B1',(None,None))[1]!='актуальная версия':raise ValueError('current version header missing')
    plugins={};seen=set()
    for coordinate,(kind,name) in cells.items():
        if not re.fullmatch(r'A[2-9]\d*|A1\d+',coordinate):continue
        if name is None:continue
        if kind=='formula' or not isinstance(name,str) or not re.fullmatch(r'[A-Za-z][A-Za-z0-9_.-]{0,119}',name):
            raise ValueError('invalid plugin name')
        row=coordinate[1:];vkind,version=cells.get('B'+row,(None,None))
        if vkind=='formula':raise ValueError('formula plugin version refused')
        normalized=normalize_version(version)
        if name.casefold() in seen:raise ValueError('duplicate plugin name')
        seen.add(name.casefold())
        plugins[name]={'version':normalized,'raw_version':version,'sheet':release,'name_cell':coordinate,'version_cell':'B'+row}
    if not plugins:raise ValueError('empty plugin reference')
    return {'release':release,'source_sha256':hashlib.sha256(raw).hexdigest(),'plugins':plugins,
            'compatibility_verified':False,'bookkeeping_only':True,'product_evidence':False}

def decide_plugin_preparation(reference,plugin_name,installed,compatibility_verified=False):
    base={'plugin_name':plugin_name,'action':'blocked','mutation_authorized':False,'case_pass':False}
    item=reference.get('plugins',{}).get(plugin_name)
    if not item:return {**base,'reason':'plugin_not_in_selected_reference'}
    base.update(expected_version=item['version'],source_sha256=reference['source_sha256'],source_sheet=item['sheet'],source_cell=item['version_cell'])
    if compatibility_verified is not True:return {**base,'reason':'os_architecture_compatibility_unconfirmed'}
    if not isinstance(installed,dict) or installed.get('audit_fresh') is not True:
        return {**base,'reason':'fresh_plugin_audit_required'}
    matches=installed.get('matched_plugins')
    if not isinstance(matches,list) or len(matches)>1:return {**base,'reason':'plugin_audit_ambiguous'}
    if not matches:return {**base,'action':'install_required','reason':'plugin_absent'}
    plugin=matches[0]
    if plugin.get('name')!=plugin_name:return {**base,'reason':'plugin_identity_mismatch'}
    try:actual=normalize_version(plugin.get('version'))
    except ValueError:return {**base,'reason':'installed_version_unknown'}
    base['installed_version']=actual
    if actual==item['version']:
        return {**base,'action':'ready_for_case' if plugin.get('load_status') is True else 'blocked',
                'reason':None if plugin.get('load_status') is True else 'plugin_not_loaded'}
    newer=tuple(map(int,actual.split('.')))>tuple(map(int,item['version'].split('.')))
    return {**base,'action':'version_conflict' if newer else 'install_required',
            'reason':'installed_newer_than_reference' if newer else 'installed_version_outdated'}

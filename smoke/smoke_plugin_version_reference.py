"""Synthetic XLSX version gate; no product installation or launch."""
from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZipFile
from plugin_version_reference import load_plugin_versions,decide_plugin_preparation

with TemporaryDirectory(prefix='uqa-plugin-reference-') as root:
    path=Path(root)/'versions.xlsx'
    def make(rows):
        with ZipFile(path,'w') as z:
            z.writestr('xl/workbook.xml','<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="1.3.27" r:id="r1"/></sheets></workbook>')
            z.writestr('xl/_rels/workbook.xml.rels','<Relationships><Relationship Id="r1" Target="worksheets/sheet1.xml"/></Relationships>')
            z.writestr('xl/worksheets/sheet1.xml','<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData><row><c r="B1" t="inlineStr"><is><t>актуальная версия</t></is></c></row>'+rows+'</sheetData></worksheet>')
    row='<row><c r="A2" t="inlineStr"><is><t>localNetworkAudit</t></is></c><c r="B2" t="inlineStr"><is><t>v1.3.10</t></is></c></row>'
    make(row);ref=load_plugin_versions(path,'1.3.27')
    assert ref['plugins']['localNetworkAudit']['version']=='1.3.10'
    def gate(version,loaded=True,fresh=True):
        return decide_plugin_preparation(ref,'localNetworkAudit',{'audit_fresh':fresh,'matched_plugins':[{'name':'localNetworkAudit','version':version,'load_status':loaded}]},True)
    assert gate('1.3.10')['action']=='ready_for_case'
    assert gate('v1.3.10')['action']=='ready_for_case'
    assert gate('1.3.9')['action']=='install_required'
    assert gate('1.3.11')['action']=='version_conflict'
    assert gate('1.3.10',loaded=False)['action']=='blocked'
    assert gate('1.3.10',fresh=False)['action']=='blocked'
    assert decide_plugin_preparation(ref,'localNetworkAudit',{'audit_fresh':True,'matched_plugins':[]},True)['action']=='install_required'
    assert decide_plugin_preparation(ref,'localNetworkAudit',{},False)['action']=='blocked'
    def refused(call):
        try:call()
        except ValueError:return
        raise AssertionError('unsafe reference accepted')
    refused(lambda:load_plugin_versions(path,'1.3.26'))
    make(row.replace('<is><t>v1.3.10</t></is>','<f>1+1</f><v>1.3.10</v>'));refused(lambda:load_plugin_versions(path,'1.3.27'))
    make(row+row.replace('A2','A3').replace('B2','B3'));refused(lambda:load_plugin_versions(path,'1.3.27'))
print('PASS plugin version reference: selected release, v normalization, duplicate/formula rejection, fresh loaded gate, no downgrade or mutation grant')

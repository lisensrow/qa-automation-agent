"""Source namespace filters before candidate budget; not current-source authority."""
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import knowledge_index as index,knowledge_tool as tool
from tools.registry import execute_tool,TOOLS
with TemporaryDirectory() as tmp,patch.object(index,'DB_PATH',Path(tmp)/'knowledge.db'):
    con=index._connect()
    con.executemany('INSERT INTO chunks(source,chunk_no,heading,content) VALUES(?,?,?,?)',
        [('UQA-experience/experience'+str(n)+'.md',1,'gpuDeviceAudit','gpuDeviceAudit name note '*20) for n in range(30)]+
        [('UQA-docs/guide.docx',1,'Plugin specification','gpuDeviceAudit device name')])
    con.commit();con.close();before=index.DB_PATH.read_bytes()
    assert len(index.search('gpuDeviceAudit',limit=20))==20
    docs=index.search('gpuDeviceAudit',limit=20,source_namespace='product_docs')
    assert len(docs)==1 and docs[0]['source']=='UQA-docs/guide.docx'
    assert all(x['source'].startswith('UQA-experience/') for x in index.search('gpuDeviceAudit',source_namespace='experience'))
    assert index.search('gpuDeviceAudit')==index.search('gpuDeviceAudit',source_namespace='all')
    out=execute_tool('knowledge_search',{'query':'gpuDeviceAudit','limit':5,'source_namespace':'product_docs'})
    assert out['source_namespace']=='product_docs' and out['result_count']==1 and out['indexed_excerpts_only'] and not out['execution_permission_granted'] and not out['current_source_bytes_rechecked']
    assert index.DB_PATH.read_bytes()==before
    for bad in ['../UQA-docs','UQA-docs/%',None,True,{}]:
        assert tool.knowledge_search('gpuDeviceAudit',source_namespace=bad)['status']=='invalid_source_namespace'
        try:index.search('gpuDeviceAudit',source_namespace=bad);raise AssertionError('invalid namespace accepted')
        except ValueError:pass
    with patch.object(tool,'search',side_effect=lambda query,limit:[]):
        assert tool.knowledge_search('default compatibility')['status']=='ok'
    schema=next(x['function']['parameters'] for x in TOOLS if x['function']['name']=='knowledge_search')
    assert schema['properties']['source_namespace']['enum']==['all','product_docs','experience']
print('scoped knowledge search: PASS (scope before budget/ranking, no index writes, default compatibility, invalid filters, no authority)')

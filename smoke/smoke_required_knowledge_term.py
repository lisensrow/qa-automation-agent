"""Rare exact token is conjunctive before ranking/budget, never a naming oracle."""
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import knowledge_index as index,knowledge_tool as tool
from tools.registry import execute_tool
with TemporaryDirectory() as tmp,patch.object(index,'DB_PATH',Path(tmp)/'knowledge.db'):
    db=index._connect()
    db.executemany('INSERT INTO chunks(source,chunk_no,heading,content) VALUES(?,?,?,?)',
      [('UQA-docs/noise'+str(n)+'.docx',1,'DB','name note manufacturer '*20) for n in range(25)]+
      [('UQA-docs/guide.docx',142,'Plugins','gpuDeviceAudit collects GPU information'),
       ('UQA-docs/prefix.docx',1,'Different plugin','gpuDeviceAuditExtra name note manufacturer'),
       ('UQA-experience/history.md',1,'History','gpuDeviceAudit name note manufacturer')])
    db.commit();db.close();before=index.DB_PATH.read_bytes()
    q='gpuDeviceAudit note name manufacturer'
    out=execute_tool('knowledge_search',{'query':q,'source_namespace':'product_docs','required_term':'gpuDeviceAudit','limit':3})
    assert out['result_count']==1 and out['results'][0]['source']=='UQA-docs/guide.docx'
    assert out['required_term']=='gpuDeviceAudit' and out['anchor_is_retrieval_filter_not_specification'] and not out['execution_permission_granted']
    assert len(index.search(q,source_namespace='product_docs',required_term='gpuDeviceAudit'))==1
    assert index.search(q)==index.search(q,required_term=None)
    assert len(index.search(q,required_term='gpuDeviceAudit'))==2
    assert index.DB_PATH.read_bytes()==before
    for bad in ['x','gpuDeviceAudit OR name','../secret','gpu*','a" OR "b',True,{}]:
        assert tool.knowledge_search(q,required_term=bad)['status']=='invalid_required_term'
        try:index.search(q,required_term=bad);raise AssertionError('invalid anchor accepted')
        except ValueError:pass
    with patch.object(tool,'search',side_effect=lambda query,limit:[]):
        assert tool.knowledge_search('default compatibility')['status']=='ok'
print('required knowledge term: PASS (conjunctive rare token before rank/budget, no prefix injection/index writes, default-compatible, no authority)')

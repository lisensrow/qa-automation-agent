"""Isolated FTS indexing preservation, retrieval and invalid input tests."""
import importlib
import os
from pathlib import Path
import sqlite3
import sys
import tempfile

sys.path.insert(0, os.getenv('UQA_SMOKE_ROOT', '/opt/uqa'))
index = importlib.import_module('knowledge_index')
tool = importlib.import_module('knowledge_tool')

with tempfile.TemporaryDirectory() as folder:
    root = Path(folder)
    sources = root / 'source'
    sources.mkdir()
    index.SOURCE_DIR = sources
    index.DB_PATH = root / 'index' / 'knowledge.db'
    first = sources / 'manual.md'
    first.write_text('# Fixture manual\nPreserved original manual sentinel.\n', encoding='utf-8')
    second = sources / 'experience.md'
    second.write_text('# Fixture recipe\nCollections RAM SUM verified operator-assisted, not autonomous.\n', encoding='utf-8')
    index.index_document(first)
    with sqlite3.connect(index.DB_PATH) as db:
        preserved = db.execute('SELECT rowid,* FROM chunks WHERE source=?', ('manual.md',)).fetchall()
    result = index.index_document(second)
    assert result['evidence_for_pass'] is False
    assert any(r['source'] == 'experience.md' for r in tool.knowledge_search('operator-assisted')['results'])
    index.index_document(second)
    with sqlite3.connect(index.DB_PATH) as db:
        assert db.execute('SELECT rowid,* FROM chunks WHERE source=?', ('manual.md',)).fetchall() == preserved
        old = db.execute('SELECT * FROM chunks WHERE source=?', ('experience.md',)).fetchall()
    second.write_text('', encoding='utf-8')
    try:
        index.index_document(second)
        raise AssertionError('empty source accepted')
    except ValueError:
        pass
    outside = root / 'outside.md'
    outside.write_text('outside', encoding='utf-8')
    try:
        index.index_document(outside)
        raise AssertionError('outside source accepted')
    except ValueError:
        pass
    # A source symlink escaping the source directory must also fail closed.
    escaped = sources / 'escaped.md'
    escaped.symlink_to(outside)
    try:
        index.index_document(escaped)
        raise AssertionError('escaped symlink accepted')
    except ValueError:
        pass
    with sqlite3.connect(index.DB_PATH) as db:
        assert db.execute('SELECT * FROM chunks WHERE source=?', ('experience.md',)).fetchall() == old
    print('incremental knowledge index: PASS (isolated fixtures; other sources unchanged; retrieval; empty/outside/symlink rejection)')

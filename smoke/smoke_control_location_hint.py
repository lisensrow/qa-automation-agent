"""Control recovery data cannot grant permissions or invent runtime validity."""
from unittest.mock import patch
import product_knowledge_context as c

row={'concept_id':'collections.form','predicate':'name_field_panel','declared_value':'Settings',
     'scope':{'document_revision':'fixture-r1'},'source_refs':[{'source_id':'fixture-guide'}]}
with patch.object(c,'retrieve_declared_context',return_value={'results':[row]}) as read:
    hint=c.retrieve_control_location_hint('Create a collection','Name')
    assert hint['document_panel_name']=='Settings'
    assert hint['evidence_for_pass'] is False and hint['current_runtime_applicability_verified'] is False
    assert 'arguments' not in hint and 'allow' not in hint and 'verified' not in hint
    assert c.retrieve_control_location_hint('Create a collection','password')['status']=='unavailable'
    assert c.retrieve_control_location_hint('Создай политику без коллекций','Name')['status']=='unavailable'
    assert read.call_count==1
with patch.object(c,'retrieve_declared_context',return_value={'results':[]}):
    assert c.retrieve_control_location_hint('Create a policy','Name')['status']=='unavailable'
with patch.object(c,'retrieve_declared_context',return_value={'results':[row,row]}):
    assert c.retrieve_control_location_hint('Create a collection','Name')['status']=='unavailable'
assert c.reviewed_search_queries('Создай коллекцию')==['коллекции создание','наблюдённый маршрут поля коллекции']
print('control location hint: PASS (bounded data, unknown/ambiguous unavailable, no runtime/permission claim)')

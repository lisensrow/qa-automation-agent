"""Locate one current tab from a rechecked field-panel hint. No execution or grants."""
from product_knowledge_context import compact_control_location_hint


def candidate_for_missing_field(hint, state):
    hint=compact_control_location_hint(hint)
    if not hint or not isinstance(state,dict) or not state.get('session_id') or not state.get('current_url'):
        return None
    panel=hint['document_panel_name']
    if not isinstance(state.get('navigation_labels'),list) or state['navigation_labels'].count(panel)!=1:
        return None
    tabs=[]
    for element in state.get('interactive_elements',[]):
        label=next((element.get(k) for k in ('aria_label','text','label') if element.get(k)),None)
        if (element.get('role')=='tab' and label==panel and element.get('enabled') is True
                and element.get('aria_disabled')!='true'):
            tabs.append(element)
    if len(tabs)!=1 or tabs[0].get('selected') is True or tabs[0].get('aria_selected')=='true':
        return None
    return {'tool':'browser_click_semantic','arguments':{'name':panel,'role':'tab','exact':True}}

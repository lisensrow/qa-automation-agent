"""Bounded tree-leaf -> new row -> exact cells. No routes, submit, or permissions."""
from tools.table_cell_controls import operate, visible


def validate(source, target, parents, cells, session_id, current_url):
    def label(value):
        return isinstance(value, str) and 0 < len(value) <= 160 and value == value.strip()
    if not label(source) or not label(target) or source == target:
        return False
    if not isinstance(parents, list) or len(parents) > 5 or any(not label(p) for p in parents):
        return False
    if len(set(parents)) != len(parents) or source in parents:
        return False
    if not isinstance(cells, list) or not 1 <= len(cells) <= 4:
        return False
    columns = []
    for cell in cells:
        if not isinstance(cell, dict) or set(cell) != {'column', 'action', 'value'}:
            return False
        if not label(cell['column']) or cell['action'] not in {'select', 'fill'}:
            return False
        if not isinstance(cell['value'], str) or len(cell['value']) > 1000:
            return False
        columns.append(cell['column'])
    return (len(set(columns)) == len(columns) and isinstance(session_id, str)
            and 0 < len(session_id) <= 200 and isinstance(current_url, str)
            and 0 < len(current_url) <= 2048)


def add_tree_row(session, source, target, parents, cells, session_id, current_url):
    try:
        return _add_tree_row(session, source, target, parents, cells, session_id, current_url)
    except Exception as exc:
        return {'error': 'tree_row_execution_uncertain', 'error_type': type(exc).__name__,
                'tree_row_status': 'uncertain', 'executed': None, 'automatic_retry_allowed': False,
                'saved_filter_verified': False, 'membership_verified': False}


def _add_tree_row(session, source, target, parents, cells, session_id, current_url):
    """One non-replaying UI sequence. A partial failure is never retried or undone."""
    if not validate(source, target, parents, cells, session_id, current_url):
        return {'error': 'tree_row_arguments_invalid', 'tree_row_status': 'not_started', 'executed': False}
    session._ensure_started()
    steps = []
    changed = False

    def bound():
        state = session._capture_state('tree-row-binding')
        return state, state.get('session_id') == session_id and state.get('current_url') == current_url

    def fail(reason, state=None):
        return {**(state or {}), 'error': reason, 'tree_row_status': 'partial' if changed else 'not_started',
                'executed': changed, 'child_steps': steps, 'automatic_retry_allowed': False,
                'saved_filter_verified': False, 'membership_verified': False}

    state, matched = bound()
    if not matched:
        return fail('tree_row_binding_changed', state)
    # Do not overwrite or add a duplicate row. The tree label itself is excluded.
    existing = [e for e in visible(session.page.get_by_text(source, exact=True))
                if not e.evaluate("e=>Boolean(e.closest('[role=tree]'))")]
    if existing:
        return fail('tree_row_label_already_present', state)
    for parent in parents:
        state, matched = bound()
        if not matched:
            return fail('tree_row_binding_changed', state)
        result = session.set_tree_item_expanded(parent, True, exact=True)
        changed = changed or result.get('mutation_executed') is True
        steps.append({'tool': 'browser_set_tree_item_expanded', 'status': result.get('tree_expand_status')})
        if result.get('error') or result.get('expanded') is not True:
            return fail('tree_row_parent_unavailable')
    result = session.inspect_tree_semantic(item=source, exact=True)
    leaves = [i for i in result.get('tree_items', []) if i.get('name') == source]
    if result.get('error') or len(leaves) != 1 or leaves[0].get('disabled'):
        return fail('tree_row_leaf_unconfirmed')
    leaf, strategy, error = session._pointer_target(source, True, 'treeitem')
    if error or not leaf.evaluate("e=>e.draggable===true&&!e.querySelector('[role=treeitem]')"):
        return fail('tree_row_leaf_not_draggable')
    state, matched = bound()
    if not matched:
        return fail('tree_row_binding_changed', state)
    result = session.drag_semantic(source, target, exact=True, source_role='treeitem')
    # Drag may have acted even if its post-observation failed. Never advertise replay.
    changed = True
    steps.append({'tool': 'browser_drag_semantic', 'status': result.get('drag_status')})
    if result.get('error') or result.get('drag_status') != 'performed':
        return fail('tree_row_drag_not_verified', result)
    # Check all controls before editing any value. Ambiguity stops here.
    for cell in cells:
        state, matched = bound()
        if not matched:
            return fail('tree_row_binding_changed', state)
        probe = operate(session, source, cell['column'])
        if probe.get('error') or probe.get('control_enabled') is not True:
            return fail('tree_row_cell_unavailable')
    for cell in cells:
        state, matched = bound()
        if not matched:
            return fail('tree_row_binding_changed', state)
        result = operate(session, source, cell['column'], cell['action'], cell['value'])
        steps.append({'tool': 'browser_table_cell_control_semantic', 'column': cell['column'],
                      'status': result.get('cell_control_status'), 'value_sha256': result.get('value_sha256'),
                      'value_length': result.get('value_length')})
        if result.get('error') or result.get('cell_control_status') != 'applied':
            return fail('tree_row_cell_not_verified', result)
    state, matched = bound()
    if not matched:
        return fail('tree_row_binding_changed', state)
    return {**state, 'tree_row_status': 'applied', 'executed': True, 'mutation_executed': True,
            'child_steps': steps, 'cell_row': source, 'automatic_retry_allowed': False,
            'saved_filter_verified': False, 'membership_verified': False,
            'whole_sequence_network_coverage_verified': False}

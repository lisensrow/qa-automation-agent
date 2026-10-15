"""Read bounded exact labeled-div-grid controls. No raw values or mutation."""
import hashlib
from tools.table_cell_controls import labeled_grid_cell, visible


def inspect_values(session, cells, session_id, current_url):
    if (not isinstance(cells,list) or not 1 <= len(cells) <= 32
            or any(not isinstance(c,dict) or set(c)!={'row','column'} for c in cells)
            or any(not isinstance(v,str) or not 0<len(v)<=160 for c in cells for v in c.values())
            or len({(c['row'],c['column']) for c in cells})!=len(cells)
            or not isinstance(session_id,str) or not session_id or len(session_id)>200
            or not isinstance(current_url,str) or not current_url or len(current_url)>2048):
        return {'error':'grid_readback_arguments_invalid','executed':False}
    session._ensure_started(); session._reset_diagnostics()
    values=[]
    def capture():
        state=session._capture_state('inspect-labeled-grid-values')
        if state.get('session_id')!=session_id or state.get('current_url')!=current_url:
            raise ValueError('grid_readback_binding_changed')
        # Do not export the surrounding page or its text/input values.
        return {'session_id':state['session_id'],'current_url':state['current_url']}
    try:
        capture()
        for item in cells:
            capture()
            cell,error=labeled_grid_cell(session.page,item['row'],item['column'])
            if error:raise ValueError('grid_readback_cell_absent_or_ambiguous')
            controls=visible(cell.locator('select,input:not([type=hidden]),textarea,[role=combobox]'))
            controls=[c for c in controls if not c.evaluate("e=>e.tagName.toLowerCase()==='input'&&Boolean(e.closest('[role=combobox]'))&&e.closest('[role=combobox]')!==e")]
            if len(controls)!=1:raise ValueError('grid_readback_control_absent_or_ambiguous')
            control=controls[0]; tag=control.evaluate('e=>e.tagName.toLowerCase()')
            kind=(control.get_attribute('type') or '').lower()
            if kind=='password':raise ValueError('grid_readback_sensitive_control')
            if tag=='select':
                chosen=control.locator('option:checked')
                if chosen.count()!=1:raise ValueError('grid_readback_selection_ambiguous')
                value=chosen.inner_text().strip()
            elif tag in {'input','textarea'} and kind not in {'checkbox','radio','file','range','color','button','submit','reset'}:
                value=control.input_value()
            elif control.get_attribute('role')=='combobox':
                value=control.inner_text().strip()
            else:raise ValueError('grid_readback_control_unsupported')
            if len(value)>1000:raise ValueError('grid_readback_value_limit')
            values.append({**item,'value_sha256':hashlib.sha256(value.encode()).hexdigest(),'value_length':len(value)})
        return {**capture(),'grid_value_status':'observed','subject':'labeled-grid',
                'requested_cells':cells,'grid_values':values,'mutation_executed':False,
                'raw_values_exported':False,'saved_filter_verified':False,'membership_verified':False}
    except Exception as exc:
        reason=str(exc) if isinstance(exc,ValueError) and str(exc).startswith('grid_readback_') else 'grid_readback_unavailable'
        return {'error':reason,'grid_value_status':'unavailable','executed':False,
                'mutation_executed':False,'raw_values_exported':False}

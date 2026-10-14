"""Exact row/column HTML table controls. No coordinates or product routes."""
import hashlib
import json

def visible(locator):
    if locator.count()>200:raise ValueError('cell_scope_limit_exceeded')
    return [locator.nth(i) for i in range(min(locator.count(),200)) if locator.nth(i).is_visible()]

def labeled_grid_cell(page,row,column):
    """Bind an unlabeled form grid by unique sibling header labels and row cells."""
    headers=visible(page.get_by_text(column,exact=True))
    if len(headers)!=1:return None,'grid_header_absent_or_ambiguous'
    header=headers[0];header_row=None;labels=None
    for _ in range(6):
        cells=header.locator(':scope > *')
        texts=[c.inner_text().strip() for c in cells.all()]
        if (2<=len(texts)<=20 and texts.count(column)==1 and all(0<len(t)<=160 for t in texts)
                and len(set(texts))==len(texts) and header.locator('input,select,textarea,[role=combobox]').count()==0):
            header_row=header;labels=texts;break
        header=header.locator('xpath=..')
    if header_row is None:return None,'grid_header_structure_unconfirmed'
    root=header_row.locator('xpath=..');rows=[];index=labels.index(column)
    def logical_cells(candidate):
        return [c for c in candidate.locator(':scope > *').all()
                if c.evaluate("e=>e.tagName.toLowerCase()!=='button'&&Boolean(String(e.innerText||'').trim()||e.querySelector('input,select,textarea,[role=combobox]'))")]
    for label in visible(root.get_by_text(row,exact=True)):
        candidate=label
        for _ in range(6):
            if candidate.evaluate('(e,h)=>e.contains(h)',header_row.element_handle()):break
            cells=logical_cells(candidate)
            if (len(cells)==len(labels) and candidate.locator('input,select,textarea,[role=combobox]').count()>0
                    and all(c.locator('input,select,textarea,[role=combobox]').count()<=2 for c in cells)
                    and len(visible(cells[index].locator('input,select,textarea,[role=combobox]'))) in {1,2}):
                if not any(candidate.evaluate('(e,other)=>e===other',other.element_handle()) for other in rows):rows.append(candidate)
                break
            candidate=candidate.locator('xpath=..')
    if len(rows)!=1:return None,'grid_row_absent_or_ambiguous'
    return logical_cells(rows[0])[index],None

def operate(session,row,column,action='inspect',value=None,table=None):
    session._ensure_started();session._reset_diagnostics()
    if action not in {'inspect','fill','select'}:return {'error':'unsupported_cell_action','executed':False}
    if not all(isinstance(v,str) and 0<len(v)<=160 for v in (row,column)):
        return {'error':'exact_row_and_column_required','executed':False}
    candidates=session.page.get_by_role('table',name=table,exact=True) if table else session.page.locator('table')
    eligible=[]
    for candidate in visible(candidates):
        headers=visible(candidate.get_by_role('columnheader',name=column,exact=True))
        if len(headers)==1:eligible.append((candidate,headers[0]))
    if len(eligible)>1:return {'error':'ambiguous_cell_table','executed':False}
    if not eligible:
        if table:return {'error':'named_cell_table_not_found','executed':False}
        cell,error=labeled_grid_cell(session.page,row,column)
        if error:
            labels=visible(session.page.get_by_text(column,exact=True))
            probe=labels[0].evaluate("e=>{const a=[];for(let i=0;e&&i<6;i++,e=e.parentElement)a.push({tag:e.tagName,role:e.getAttribute('role'),children:Array.from(e.children).slice(0,12).map(c=>({tag:c.tagName,role:c.getAttribute('role'),text:String(c.innerText||'').trim().slice(0,120)}))});return a}") if len(labels)==1 else []
            return {'error':error,'executed':False,'grid_probe':probe}
    else:
        root,header=eligible[0]
        layout=header.evaluate("e=>({index:Array.from(e.parentElement.children).indexOf(e),simple:Array.from(e.parentElement.children).every(c=>(Number(c.getAttribute('colspan'))||1)===1&&(Number(c.getAttribute('rowspan'))||1)===1)})")
        if not layout['simple']:return {'error':'merged_table_headers_unsupported','executed':False}
        rows=[candidate for candidate in visible(root.get_by_role('row')) if visible(candidate.get_by_text(row,exact=True))]
        if len(rows)!=1:return {'error':'ambiguous_cell_row' if rows else 'cell_row_not_found','executed':False}
        cells=rows[0].locator(':scope > td')
        if layout['index']>=cells.count():return {'error':'table_cell_missing','executed':False}
        if any((cells.nth(i).get_attribute('colspan') or '1')!='1' for i in range(cells.count())):
            return {'error':'merged_table_row_unsupported','executed':False}
        cell=cells.nth(layout['index'])
    controls=visible(cell.locator('select,input:not([type=hidden]),textarea,[role=combobox]'))
    controls=[c for c in controls if not c.evaluate("e=>e.tagName.toLowerCase()==='input'&&Boolean(e.closest('[role=combobox]'))&&e.closest('[role=combobox]')!==e")]
    if len(controls)!=1:return {'error':'ambiguous_cell_control' if controls else 'cell_control_missing','executed':False}
    control=controls[0];tag=control.evaluate('e=>e.tagName.toLowerCase()');kind=(control.get_attribute('type') or '').lower()
    if kind=='password':return {'error':'sensitive_cell_control','executed':False}
    base={'cell_row':row,'cell_column':column,'control_tag':tag,'control_type':kind,'mutation_executed':False}
    if action=='inspect':
        options=[o.inner_text() for o in control.locator('option').all()] if tag=='select' else []
        return {**session._capture_state('inspect-table-cell-control'),**base,'cell_control_status':'observed',
                'control_enabled':control.is_enabled(),'options':options[:100]}
    if not isinstance(value,str) or len(value)>1000:return {'error':'bounded_cell_value_required','executed':False}
    if not control.is_enabled() or control.get_attribute('aria-disabled')=='true':return {'error':'cell_control_disabled','executed':False}
    if action=='fill' and (tag not in {'input','textarea'} or kind in {'checkbox','radio','file'} or not control.is_editable()):
        return {'error':'cell_control_not_text_editable','executed':False}
    if action=='select' and tag!='select' and control.get_attribute('role')!='combobox':
        return {'error':'cell_control_not_selectable','executed':False}
    session._begin_action_execution()
    if action=='fill':control.fill(value);matched=control.input_value()==value
    elif tag=='select':
        options=[o for o in control.locator('option').all() if o.inner_text().strip()==value]
        if len(options)!=1:return {'error':'cell_option_absent_or_ambiguous','executed':False}
        if not options[0].is_enabled():return {'error':'cell_option_disabled','executed':False}
        control.select_option(label=value);matched=control.locator('option:checked').inner_text().strip()==value
    else:
        control.click()
        popup_id=control.get_attribute('aria-controls') or control.get_attribute('aria-owns')
        popups=visible(session.page.locator('[id='+json.dumps(popup_id)+']')) if popup_id else visible(session.page.get_by_role('listbox'))
        if len(popups)!=1:return {'error':'cell_option_popup_binding_ambiguous','executed':False}
        choices=visible(popups[0].get_by_role('option',name=value,exact=True))
        if len(choices)!=1:return {'error':'cell_option_absent_or_ambiguous','executed':False}
        choices[0].click();session.page.wait_for_timeout(150)
        matched=control.inner_text().strip()==value or control.get_attribute('aria-valuetext')==value or control.get_attribute('aria-label')==value
        if tag=='input':matched=control.input_value()==value
    result={**session._capture_state('set-table-cell-control'),**base,'mutation_executed':True,'executed':True,
            'cell_control_status':'applied' if matched else 'not_verified',
            'value_sha256':hashlib.sha256(value.encode()).hexdigest(),'value_length':len(value)}
    if not matched:result['error']='cell_control_value_not_verified'
    return result

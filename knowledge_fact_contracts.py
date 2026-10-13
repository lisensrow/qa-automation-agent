"""Closed type contracts for safe memory hints and runtime confirmations."""
import json
import re

RUNTIME_FLAGS = {
    'ui_api_binding':('runtime_ui_action_observed','runtime_api_exchange_observed','backend_request_correlated'),
    'ui_navigation':('runtime_exact_row_tabs_observed','runtime_panels_visible','runtime_details_identity_preserved'),
}
FIELDS = {
    'ui_api_binding':('ui_path','ui_field','ui_action','api_method','api_endpoint','query_parameter'),
    'ui_navigation':('ui_path','ui_tool','ui_action','tab_names'),
}


def safe_string(value):
    return (isinstance(value,str) and 0<len(value)<=256
            and not re.search(r'password|passwd|secret|token|authorization|cookie|bearer|[\x00-\x1f]',value,re.I)
            and not any(marker in value for marker in ('://','?','@')))


def sanitize_memory_fact(kind,data):
    if kind not in FIELDS or not isinstance(data,dict):
        return {}
    safe={key:data[key] for key in FIELDS[kind] if key!='tab_names' and safe_string(data.get(key))}
    if kind=='ui_navigation':
        tabs=data.get('tab_names')
        if (safe.get('ui_tool')!='browser_verify_exact_table_row_tabs_semantic'
                or safe.get('ui_action')!='exact_row_then_named_tabs'
                or not safe.get('ui_path','').startswith('/') or not isinstance(tabs,list)
                or not 1<=len(tabs)<=20 or not all(safe_string(t) and len(t)<=128 for t in tabs)
                or len(set(tabs))!=len(tabs)):
            return {}
        safe['tab_names']=list(tabs)
    return safe


def confirmation_matches_frontend(source,kind,identity):
    if kind not in RUNTIME_FLAGS:
        return False
    try:
        passport=json.loads(source['stand_identity_json'] or '{}')
        flags=json.loads(source['verification_json'] or '{}')
        refs=json.loads(source['source_observation_ids_json'] or '[]')
        return (isinstance(passport,dict) and isinstance(flags,dict)
                and passport.get('status')=='ok' and not passport.get('deployment_partial')
                and passport.get('installation_architecture')==identity.get('installation_architecture')
                and passport.get('server_version')==identity.get('server_version')
                and passport.get('frontend_status')=='ok'
                and passport.get('frontend_version')==identity.get('frontend_version')
                and all(flags.get(k) is True for k in RUNTIME_FLAGS[kind])
                and isinstance(refs,list) and all(isinstance(r,str) and r for r in refs)
                and len(set(refs)) >= (3 if kind=='ui_api_binding' else 1))
    except (ValueError,TypeError,KeyError):
        return False

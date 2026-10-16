"""Bounded native GET-only discovery; never delivery, remote session or PASS."""
from datetime import datetime,timezone
from command_stage_native import context,read_json
from command_probe_contract import validate_target_state
from tools.agent_plugins import summarize_plugin_audit

# Five guide names plus vncServer actually observed in historical server catalogue.
# Guide action names are not silently equated with installed binary/plugin names.
NAMES=('initRemoteDesktopConnectionVNC','displayMonitoring','InitRemoteDesktopConnectionTCP',
       'remoteConnections','checkAlive','vncServer')

def inspect(session,name):
    try:
        t,ci,urls=context(session,name)
        agent=read_json(session,urls[1]);validate_target_state(name,ci,agent)
        audit=read_json(session,urls[2]);details=audit.get('detail')
        if (audit.get('agent_id')!=t['agent_id'] or not isinstance(details,list)
            or len(details)>200 or any(not isinstance(x,dict) for x in details)):
            raise ValueError('complete_plugin_inventory_required')
        summary=summarize_plugin_audit(ci,audit)
        rows=[]
        for documented in NAMES:
            found=[x for x in details if isinstance(x.get('plugin_name'),str)
                and x['plugin_name'].casefold()==documented.casefold()]
            rows.append({'documented_name':documented,'match_count':len(found),
                'name_source':'historical_server_catalog_v295' if documented=='vncServer' else 'user_guide_appendix4',
                'observed':[{'name':x['plugin_name'],'version':x.get('plugin_version'),
                    'loaded':x.get('load_status') if type(x.get('load_status')) is bool else None,
                    'load_error_observed':'load_error' in x,
                    'load_error_present':bool(x.get('load_error')) if 'load_error' in x else None}
                    for x in found],
                'expected_version':None,'compatibility_verified':False,'execution_verified':False})
        return {'target':name,'ci_id':t['ci_id'],'agent_id':t['agent_id'],'core_version':agent['version'],
            'agent_status':agent['status'],'os_name':ci['detail']['os'].get('name') or ci.get('os_name'),
            'architecture':ci['detail']['os']['architecture'],'session_id':session.session_id,
            'read_at':datetime.now(timezone.utc).isoformat(),'last_audit_at':summary['last_audit_at'],
            'audit_fresh':summary['audit_fresh'],'audit_age_seconds':summary['audit_age_seconds'],
            'plugins':rows,'mutation_executed':False,'business_pass':False,'dispatch_authorized':False,
            'scope':'six_known_names_inventory_only_not_vnc_session_or_case_pass'}
    except Exception as exc:
        return {'error':str(exc)[:160] if isinstance(exc,ValueError) else 'lab_plugin_inventory_unavailable',
            'mutation_executed':False,'business_pass':False,'dispatch_authorized':False}

"""Read one exact saved graph from a native captured GET. Never request or execute."""
from datetime import datetime, timezone
import json
import re
from urllib.parse import urlsplit
from procedure_graph import inspect_block_xml, FLAGS


def _origin(value):
    if not isinstance(value, str):
        return None
    try:
        url = urlsplit(value)
        if url.scheme not in {'http', 'https'} or not url.hostname or url.username or url.password:
            return None
        port = url.port or (443 if url.scheme == 'https' else 80)
        return url.scheme, url.hostname.lower(), port
    except ValueError:
        return None


def summarize_saved_block_graph(detail, exact_name, *, current_origin,
                                current_session_id, max_age_seconds=60, now=None):
    """The detail must be native, not supplied by model arguments. Summary is not PASS."""
    def refuse(reason):
        return {'saved_graph_observation_status': 'refused', 'error': reason, **FLAGS}
    if not isinstance(exact_name, str) or not exact_name.strip() or len(exact_name) > 160:
        return refuse('saved_graph_exact_name_invalid')
    if any(ord(c) < 32 for c in exact_name):
        return refuse('saved_graph_exact_name_invalid')
    if type(max_age_seconds) is not int or not 1 <= max_age_seconds <= 3600:
        return refuse('saved_graph_age_limit_invalid')
    if not isinstance(detail, dict) or detail.get('error'):
        return refuse('saved_graph_native_source_unavailable')
    if detail.get('method') != 'GET' or type(detail.get('status')) is not int or detail['status'] != 200:
        return refuse('saved_graph_source_not_successful_get')
    request_id = detail.get('request_id')
    if not isinstance(request_id, str) or re.fullmatch(r'n[1-9][0-9]{0,8}', request_id) is None:
        return refuse('saved_graph_request_identity_invalid')
    if not current_session_id or detail.get('session_id') != current_session_id:
        return refuse('saved_graph_source_session_mismatch')
    origin = _origin(current_origin)
    if not origin or _origin(detail.get('response_origin')) != origin:
        return refuse('saved_graph_source_origin_mismatch')
    try:
        url = urlsplit(detail.get('url', ''))
    except (TypeError, ValueError):
        return refuse('saved_graph_source_url_invalid')
    if not url.path.startswith('/') or url.fragment or (url.netloc and _origin(detail['url']) != origin):
        return refuse('saved_graph_source_url_invalid')
    if url.scheme and _origin(detail['url']) != origin:
        return refuse('saved_graph_source_url_invalid')
    try:
        received = datetime.fromisoformat(detail['received_at'])
        current = now if now is not None else datetime.now(timezone.utc)
        if received.tzinfo is None or current.tzinfo is None:
            return refuse('saved_graph_source_time_invalid')
        age = (current - received).total_seconds()
    except (KeyError, TypeError, ValueError, AttributeError, OverflowError):
        return refuse('saved_graph_source_time_invalid')
    if age < -5 or age > max_age_seconds:
        return refuse('saved_graph_source_stale_or_future')
    if detail.get('response_body_truncated') is not False:
        return refuse('saved_graph_source_body_incomplete')
    raw = detail.get('response_body')
    if not isinstance(raw, str) or len(raw) > 65536:
        return refuse('saved_graph_source_body_invalid')
    try:
        payload = json.loads(raw)
    except (ValueError, RecursionError):
        return refuse('saved_graph_source_body_invalid')
    if not isinstance(payload, dict) or not isinstance(payload.get('items'), list):
        return refuse('saved_graph_collection_shape_invalid')
    items = payload['items']
    if (len(items) > 200 or type(payload.get('offset')) is not int or payload['offset'] != 0
            or type(payload.get('count')) is not int or payload['count'] != len(items)
            or type(payload.get('total')) is not int or payload['total'] != len(items)
            or type(payload.get('limit')) is not int or not len(items) <= payload['limit'] <= 10000):
        return refuse('saved_graph_collection_incomplete')
    ids = set()
    matches = []
    for item in items:
        if not isinstance(item, dict):
            return refuse('saved_graph_record_shape_invalid')
        identifier = item.get('id')
        if not isinstance(identifier, str) or not identifier or len(identifier) > 256 or identifier in ids:
            return refuse('saved_graph_record_identity_invalid')
        ids.add(identifier)
        if not isinstance(item.get('name'), str):
            return refuse('saved_graph_record_shape_invalid')
        if item['name'] == exact_name:
            matches.append(item)
    if len(matches) != 1:
        return refuse('saved_graph_record_not_unique')
    graph = inspect_block_xml(matches[0].get('xml'))
    if graph['graph_observation_status'] != 'observed':
        return {**refuse('saved_graph_xml_refused'), 'graph_reason': graph['reason']}
    return {**graph, 'saved_graph_observation_status': 'observed',
            'source_request_ids': {'saved_graph': request_id}, 'source_age_seconds': round(max(0, age), 3),
            'same_origin_source_verified': True, 'source_session_matched': True,
            'record_identity_matched': True, 'workspace_binding_verified': False,
            'record_context_verified': False}

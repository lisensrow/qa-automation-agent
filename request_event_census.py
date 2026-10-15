"""Bounded request-start accounting, not a no-side-effect or replay oracle.

Only object identities and bounded method/type counters stay in memory. No URL,
headers, body, credentials or response are read or returned. Background traffic
within the window is deliberately included; causality is not inferred.
"""
from datetime import datetime, timezone

METHODS = frozenset({'GET', 'HEAD', 'OPTIONS', 'POST', 'PUT', 'PATCH', 'DELETE', 'TRACE', 'CONNECT'})
TYPES = frozenset({'document', 'stylesheet', 'image', 'media', 'font', 'script',
                   'texttrack', 'xhr', 'fetch', 'eventsource', 'websocket', 'manifest', 'other'})


class RequestEventCensus:
    MAX_PENDING = 256

    def __init__(self):
        self._pending = {}
        self._window = None
        self._tracking_incomplete = False
        self.capture_active = False

    def mark_incomplete(self):
        # Sticky for this browser context. A later reset must not hide a loss.
        self._tracking_incomplete = True

    def begin(self, action_id):
        if not isinstance(action_id, str) or not 1 <= len(action_id) <= 200:
            raise ValueError('invalid action identity')
        replaced = self._window is not None
        if replaced:
            self.mark_incomplete()
        self._window = {'action_execution_id': action_id,
                        'started_at': datetime.now(timezone.utc).isoformat(),
                        'pending_at_begin': len(self._pending),
                        'request_started_count': 0, 'completion_event_count': 0,
                        'failed_event_count': 0, 'method_counts': {}, 'resource_type_counts': {},
                        'replaced_open_window': replaced}

    def started(self, request):
        key = id(request)
        if key in self._pending:
            self.mark_incomplete()
            return
        if len(self._pending) >= self.MAX_PENDING:
            self.mark_incomplete()
        else:
            # Keep the object alive so Python cannot recycle its id.
            self._pending[key] = request
        if self._window is None:
            return
        try:
            method = request.method
            kind = request.resource_type
            if method not in METHODS:
                method = 'OTHER'
                self.mark_incomplete()
            if kind not in TYPES:
                kind = 'other'
                self.mark_incomplete()
        except Exception:
            method, kind = 'OTHER', 'other'
            self.mark_incomplete()
        window = self._window
        window['request_started_count'] += 1
        for field, value in (('method_counts', method), ('resource_type_counts', kind)):
            counts = window[field]
            counts[value] = counts.get(value, 0) + 1

    def completed(self, request, *, failed=False):
        if self._pending.pop(id(request), None) is not request:
            self.mark_incomplete()
        if self._window is not None:
            self._window['completion_event_count'] += 1
            self._window['failed_event_count'] += int(failed)

    def finish(self, action_id):
        window = self._window
        self._window = None
        if window is None or window['action_execution_id'] != action_id:
            self.mark_incomplete()
            return None
        return {**window, 'schema_version': 1,
                'finished_at': datetime.now(timezone.utc).isoformat(),
                'capture_scope': 'browser_context_request_events_until_action_finish',
                'capture_active': self.capture_active is True,
                'tracking_incomplete': self._tracking_incomplete,
                'pending_at_finish': len(self._pending),
                'pending_capacity': self.MAX_PENDING,
                'future_traffic_covered': False, 'websocket_frames_covered': False,
                'service_worker_coverage_verified': False,
                'causal_attribution_verified': False, 'business_effect_verified': False,
                'resend_authorized': False}

"""Observed JSON response bodies support numeric IDs without guessing IDs."""
import json
from uqa import _tool_history_observed_identifier as observed

def message(**data):
    return [{'role':'tool','tool_name':'browser_get_network_detail','content':json.dumps(data)}]

assert observed(message(response_body='{"id":1,"name":"fixture"}'), '1')
assert observed(message(response_body='[{"items":[{"uid":"actual-id"}]}]'), 'actual-id')
assert not observed(message(response_body='{"id":1}'), '2')
assert not observed(message(response_body='{"name":"1"}'), '1')
assert not observed(message(request_body='{"id":1}'), '1')
assert not observed(message(text_preview='{"id":1}'), '1')
assert not observed(message(response_body='{"id":1'), '1')
assert not observed(message(response_body='"{\\"id\\":1}"'), '1')
assert not observed(message(response_body=' '*65537+'{"id":1}'), '1')
assert not observed([{'role':'user','content':json.dumps({'response_body':'{"id":1}'})}], '1')
assert observed(message(identifier_value='existing-id'), 'existing-id')
print('PASS observed response identifiers: JSON object/array, numeric ID, wrong/truncated/untrusted sources rejected')

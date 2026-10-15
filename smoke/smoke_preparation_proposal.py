"""Pure candidate plan safety fixtures; not UI or administrator acceptance."""
from copy import deepcopy
from itertools import permutations
import preparation_proposal as p

binding = {'stand': 'fixture', 'campaign_id': 'fixture-campaign', 'resource_kind': 'example',
           'resource_key': 'new-example', 'new_name': 'uqa-test-fixture',
           'scope_id': 'scope-fixture', 'target_ids': ['target-b', 'target-a']}
proposal = {'version': 1, 'mode': p.MODE, **deepcopy(binding),
            'desired_enabled': False, 'steps': list(p.STEPS)}
result = p.validate_preparation_proposal(proposal, binding)
assert all(result[k] is False for k in p.FLAGS)
assert result['status'] == 'valid_proposal_only' and result['proposal']['target_ids'] == ['target-a', 'target-b']
assert p.check_pinned_proposal(proposal, binding, result['proposal_sha256']) == result
assert result['proposal_sha256'] == p.validate_preparation_proposal(result['proposal'], binding)['proposal_sha256']


def reject(candidate, trusted=binding):
    try:
        p.validate_preparation_proposal(candidate, trusted)
    except ValueError:
        return
    raise AssertionError('unsafe proposal accepted')


for steps in permutations(p.STEPS):
    if steps != p.STEPS:
        reject({**proposal, 'steps': list(steps)})
for key in binding:
    changed = deepcopy(proposal)
    changed[key] = ['other-target'] if key == 'target_ids' else 'other'
    reject(changed)
for value in (True, 0, 1, None, 'false'):
    reject({**proposal, 'desired_enabled': value})
for version in (True, '1', 0, 2):
    reject({**proposal, 'version': version})
for ids in ([], ['a'] * 2, ['a'] * 33, ['all'], ['*'], ['unknown'], [1], [True], 'target-a'):
    changed = {**proposal, 'target_ids': ids}
    reject(changed, {**binding, 'target_ids': ids})
for scope in ('all', 'any', 'latest', '*', 'unknown', '', '../scope'):
    reject({**proposal, 'scope_id': scope}, {**binding, 'scope_id': scope})
for extra in ('tool', 'endpoint', 'payload', 'execute', 'secret', 'policy_override'):
    reject({**proposal, extra: 'not allowed'})
for steps in (list(p.STEPS[:-1]), list(p.STEPS) + ['activate'], ['commit_create'] * 5,
              list(p.STEPS[:-1]) + ['run'], 'prepare then save'):
    reject({**proposal, 'steps': steps})
reject('Natural language plan is not executable')
reject({k: v for k, v in proposal.items() if k != 'desired_enabled'})
for candidate in ('0' * 64, 'invalid', None):
    try: p.check_pinned_proposal(proposal, binding, candidate)
    except ValueError: pass
    else: raise AssertionError('wrong pin accepted')
changed = deepcopy(proposal); changed['new_name'] = 'uqa-test-other'
try: p.check_pinned_proposal(changed, {**binding, 'new_name': changed['new_name']}, result['proposal_sha256'])
except ValueError: pass
else: raise AssertionError('changed binding bypassed pin')
proposal['steps'][0] = 'commit_create'
assert result['proposal']['steps'][0] == 'prepare_disabled_draft'  # Independent snapshot.
schema = p.proposal_response_schema()
assert schema['additionalProperties'] is False and len(str(schema)) < 8192
outline = {'version': 1, 'mode': p.MODE, 'desired_enabled': False, 'steps': list(p.STEPS)}
compiled = p.compile_preparation_outline(outline, binding)
assert compiled == result
for extra in binding:
    try: p.compile_preparation_outline({**outline, extra: binding[extra]}, binding)
    except ValueError: pass
    else: raise AssertionError('model-supplied binding accepted in outline')
for order in permutations(p.STEPS):
    if order == p.STEPS: continue
    try: p.compile_preparation_outline({**outline, 'steps': list(order)}, binding)
    except ValueError: pass
    else: raise AssertionError('unsafe outline accepted')
assert set(p.outline_response_schema()['properties']) == set(outline)
diagnostic = p.safe_outline_diagnostic({'credential-private': 'never echo',
    'desired_enabled': 'private', 'steps': ['commit_create', 'private']})
assert 'private' not in str(diagnostic) and diagnostic['unexpected_field_count'] == 1
assert diagnostic['known_steps'] == ['commit_create', '<unsupported>']
assert p.safe_outline_diagnostic('never echo') == {'object_received': False}
skeleton = p.build_disabled_scoped_skeleton(binding)
assert skeleton['proposal'] == result['proposal'] and skeleton['proposal_sha256'] == result['proposal_sha256']
assert skeleton['generation_mode'] == 'deterministic_supported_profile' and skeleton['model_plan_accepted'] is False
assert all(skeleton[k] is False for k in p.FLAGS)
try: p.build_disabled_scoped_skeleton({**binding, 'target_ids': []})
except ValueError: pass
else: raise AssertionError('skeleton invented broad or missing scope')
print('preparation_proposal: PASS (119 unsafe permutations, exact binding, disabled/type/scope/pin; no execution authority)')

"""Pure disabled/scoped creation proposal contract. Not a workflow or executor.

Binding is supplied by trusted caller, NEVER inferred from model metadata.
Valid structure proves neither ownership, freshness, UI lifecycle nor permission.
"""
from copy import deepcopy
import hashlib
import json
import re

MODE = 'disabled_scoped_create_proposal'
STEPS = ('prepare_disabled_draft', 'verify_disabled_draft', 'verify_exact_scope',
         'commit_create', 'verify_saved_disabled_scope')
BINDING_FIELDS = {'stand', 'campaign_id', 'resource_kind', 'resource_key',
                  'new_name', 'scope_id', 'target_ids'}
TOKEN = re.compile(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,159}\Z')
FLAGS = {'execution_authorized': False, 'current_runtime_verified': False,
         'ownership_verified': False, 'preconditions_verified': False,
         'ui_lifecycle_verified': False, 'payload_schema_verified': False,
         'business_pass': False, 'replay_release_authorized': False}


def _token(value):
    if not isinstance(value, str) or not TOKEN.fullmatch(value):
        raise ValueError('proposal_identity')
    return value


def _binding(value):
    if not isinstance(value, dict) or set(value) != BINDING_FIELDS:
        raise ValueError('proposal_binding_fields')
    out = {k: _token(value[k]) for k in BINDING_FIELDS - {'target_ids'}}
    if not out['new_name'].startswith('uqa-test-'):
        raise ValueError('proposal_test_name_required')
    ids = value['target_ids']
    if not isinstance(ids, list) or not 1 <= len(ids) <= 32:
        raise ValueError('proposal_explicit_targets_required')
    ids = [_token(i) for i in ids]
    if len(set(ids)) != len(ids):
        raise ValueError('proposal_duplicate_target')
    # Broad natural-language selectors are not identifiers in this contract.
    if any(i.casefold() in {'all', 'any', 'unknown', 'latest'} for i in [out['scope_id'], *ids]):
        raise ValueError('proposal_exact_scope_required')
    out['target_ids'] = sorted(ids)
    return out


def validate_preparation_proposal(proposal, binding):
    """Closed five-stage proposal. No tools, endpoints, expressions or product payloads."""
    expected = _binding(binding)
    if not isinstance(proposal, dict) or set(proposal) != BINDING_FIELDS | {
            'version', 'mode', 'desired_enabled', 'steps'}:
        raise ValueError('proposal_fields')
    if type(proposal['version']) is not int or proposal['version'] != 1 or proposal['mode'] != MODE:
        raise ValueError('proposal_mode_version')
    if proposal['desired_enabled'] is not False:
        raise ValueError('proposal_explicit_disabled_required')
    if _binding({k: proposal[k] for k in BINDING_FIELDS}) != expected:
        raise ValueError('proposal_scope_or_resource_changed')
    if not isinstance(proposal['steps'], list) or proposal['steps'] != list(STEPS):
        raise ValueError('proposal_unsafe_or_unsupported_order')
    normalized = {'version': 1, 'mode': MODE, **expected,
                  'desired_enabled': False, 'steps': list(STEPS)}
    raw = json.dumps(normalized, sort_keys=True, separators=(',', ':'), ensure_ascii=False)
    return {'status': 'valid_proposal_only', 'proposal': normalized,
            'proposal_sha256': hashlib.sha256(raw.encode()).hexdigest(), **FLAGS}


def check_pinned_proposal(proposal, binding, expected_sha256):
    """Integrity check only. Deliberately never usable by the operation journal as authority."""
    if not isinstance(expected_sha256, str) or not re.fullmatch(r'[0-9a-f]{64}', expected_sha256):
        raise ValueError('proposal_pin_required')
    result = validate_preparation_proposal(proposal, binding)
    if result['proposal_sha256'] != expected_sha256:
        raise ValueError('proposal_changed')
    return deepcopy(result)


def proposal_response_schema():
    """Model transport grammar is intentionally weaker than the independent order validator."""
    fields = {key: {'type': 'string'} for key in BINDING_FIELDS - {'target_ids'}}
    fields.update(version={'type': 'integer', 'enum': [1]}, mode={'type': 'string', 'enum': [MODE]},
        desired_enabled={'type': 'boolean'}, target_ids={'type': 'array', 'minItems': 1,
        'maxItems': 32, 'items': {'type': 'string'}}, steps={'type': 'array', 'minItems': 5,
        'maxItems': 5, 'items': {'type': 'string', 'enum': list(STEPS)}})
    return {'type': 'object', 'properties': fields, 'required': sorted(fields), 'additionalProperties': False}


def compile_preparation_outline(outline, binding):
    """Compile logical model outline with caller-owned identity, never model-supplied IDs."""
    keys = {'version', 'mode', 'desired_enabled', 'steps'}
    if not isinstance(outline, dict) or set(outline) != keys:
        raise ValueError('proposal_outline_fields')
    expected = _binding(binding)
    return validate_preparation_proposal({**deepcopy(outline), **expected}, expected)


def outline_response_schema():
    full = proposal_response_schema()
    keys = ['version', 'mode', 'desired_enabled', 'steps']
    return {'type': 'object', 'properties': {k: full['properties'][k] for k in keys},
            'required': keys, 'additionalProperties': False}


def safe_outline_diagnostic(outline):
    """Bounded shape/type/known-stage diagnostic; never echo arbitrary model values/keys."""
    if not isinstance(outline, dict):
        return {'object_received': False}
    keys = {'version', 'mode', 'desired_enabled', 'steps'}
    enabled = outline.get('desired_enabled')
    steps = outline.get('steps')
    return {'object_received': True, 'missing_fields': sorted(keys - set(outline)),
        'unexpected_field_count': len(set(outline) - keys),
        'desired_enabled': enabled if type(enabled) is bool else '<not_boolean>',
        'known_steps': [s if isinstance(s, str) and s in STEPS else '<unsupported>'
                        for s in steps[:8]] if isinstance(steps, list) else [],
        'step_count': len(steps) if isinstance(steps, list) else None}


def build_disabled_scoped_skeleton(binding):
    """Deterministic supported-profile proposal, NOT a repair/acceptance of a rejected LLM plan.

    Caller must explicitly choose this narrow profile. Mandatory dependencies do
    not depend on LLM order; no precondition is executed or claimed satisfied.
    """
    expected = _binding(binding)
    result = compile_preparation_outline({'version': 1, 'mode': MODE,
        'desired_enabled': False, 'steps': list(STEPS)}, expected)
    return {**result, 'generation_mode': 'deterministic_supported_profile', 'model_plan_accepted': False}

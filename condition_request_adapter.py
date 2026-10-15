"""Narrow whole-request UC adapter; no model-authored oracle or permissions."""
import hashlib
import re
from condition_draft_profiles import requirement_for_plan, TYPED_FAMILY_PROFILE_ID

ADAPTER_ID = 'uc.unsaved.os-family.request.v1'
# Deliberately closed: do not discard extra user criteria or reinterpret Save.
REQUEST = re.compile(
    r'(?:На стенде lab )?Проверь (?:в CMDB в новой несохранённой коллекции AND-условия: '
    r'неархивные Endpoint с (?:ОС )?(?P<os>Ubuntu|Windows))\. Не сохраняй\.?',
    re.IGNORECASE,
)


def expected_from_request(request, stand):
    if stand != 'lab' or not isinstance(request, str) or len(request) > 600:
        return None
    if any(ord(c) < 32 and c not in '\r\n\t' for c in request):
        return None
    match = REQUEST.fullmatch(' '.join(request.split()))
    if not match:
        return None
    os_name = {'ubuntu': 'Ubuntu', 'windows': 'Windows'}[match['os'].lower()]
    return {'logic': 'AND', 'conditions': [
        {'field': 'Archived', 'operator': 'Equal', 'value': False},
        {'field': 'CI class', 'operator': 'Equal', 'value': 'endpoint'},
        {'field': 'OS name', 'operator': 'Contains', 'value': os_name},
    ]}


def request_requirement(request, stand, check_id='planned-001'):
    expected = expected_from_request(request, stand)
    if expected is None:
        return None
    result = requirement_for_plan(expected, check_id, TYPED_FAMILY_PROFILE_ID)
    result['condition_request_binding'] = {
        'adapter_id': ADAPTER_ID,
        'request_sha256': hashlib.sha256(request.encode()).hexdigest(),
    }
    return result


def regression_plan(request, stand):
    requirement = request_requirement(request, stand)
    if requirement is None:
        return None
    expected = 'В новом несохранённом фильтре одновременно прочитаны шесть ячеек трёх AND-условий согласно исходному заданию; без Save.'
    return [{'title': 'Несохранённые условия коллекции: OS family', 'task': request,
             'expected': expected, 'requirement': requirement,
             'checks': [{'check_id': 'planned-001', 'title': expected, 'expected': expected}]}]

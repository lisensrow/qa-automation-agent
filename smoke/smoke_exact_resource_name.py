import ast
import re
from pathlib import Path


uqa_source = Path("uqa.py").read_text(encoding="utf-8")
tree = ast.parse(uqa_source)
names = {
    "_latest_user_text",
    "_navigation_task_text",
    "_exact_resource_name_constraint",
    "_required_name_fill_candidate",
    "_blank_field_constraint_violation",
    "_required_selection_constraints",
    "_selection_key",
    "_is_form_commit_action",
    "record_required_selection_result",
    "_navigation_candidate_matches",
}
module = ast.Module(
    body=[
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef)
        and node.name in names
    ],
    type_ignores=[],
)
scope = {
    "re": re,
    "_PENDING_SELECTION_COMPLETIONS": {},
    "_PENDING_SELECTION_FIELD_TRANSITIONS": {},
    "_PENDING_CONSTRAINED_ACTIONS": {},
    "_COMPLETED_REQUIRED_SELECTIONS": {},
    "_PENDING_SELECTION_CONTINUATIONS": {},
}
exec(compile(module, "uqa.py", "exec"), scope)

messages = [{
    "role": "user",
    "content": (
        "[UQA CORE: REGRESSION CASE]\n"
        "Задача: Создать зону с точным именем "
        "uqa-e2e-cleanup-20260912-152500 на стенде.\n"
        "Ожидаемый результат: null"
    ),
}]
required = scope["_exact_resource_name_constraint"](messages)
assert required == "uqa-e2e-cleanup-20260912-152500"

candidate = scope["_required_name_fill_candidate"](
    "browser_fill_semantic",
    {"field": "Name", "text": "Test Zone", "exact": True},
    messages,
)
assert candidate["arguments"] == {
    "field": "Name",
    "text": "uqa-e2e-cleanup-20260912-152500",
    "exact": True,
}
assert scope["_required_name_fill_candidate"](
    "browser_fill_semantic",
    {
        "field": "Name",
        "text": "uqa-e2e-cleanup-20260912-152500",
        "exact": True,
    },
    messages,
) is None
assert scope["_required_name_fill_candidate"](
    "browser_fill_semantic",
    {"field": "Description", "text": "Test Zone"},
    messages,
) is None

planned_messages = [{
    "role": "user",
    "content": (
        "Задача: Создать временную зону с именем "
        "uqa-e2e-cleanup-20260912-152500, зарегистрировать ресурс.\n"
        "Ожидаемый результат: null"
    ),
}]
assert scope["_exact_resource_name_constraint"](
    planned_messages
) == "uqa-e2e-cleanup-20260912-152500"

blank_messages = [{
    "role": "user",
    "content": (
        "[UQA CORE: REGRESSION CASE]\n"
        "Задача: Создай временный ресурс.\n"
        "Ожидаемый результат: null\n\n"
        "Общий контекст regression job "
        "(соседние test cases удалены Core):\n"
        "Поле Mnemonic code оставь пустым. "
        "Field Description must remain blank.\n\n"
        "Сформируй обычный QA-результат."
    ),
}, {
    "role": "user",
    "content": (
        "[UQA CORE: CONTINUE EXACT ACTION]\n"
        "Call the exact Name fill action now."
    ),
}]
assert "Mnemonic code" in scope["_navigation_task_text"](
    blank_messages
)
assert scope["_blank_field_constraint_violation"](
    "browser_fill_semantic",
    {"field": "Mnemonic code", "text": "TZ001"},
    blank_messages,
) == "Mnemonic code"
assert scope["_blank_field_constraint_violation"](
    "browser_fill_semantic",
    {"field": "Description", "text": "unexpected"},
    blank_messages,
) == "Description"
assert scope["_blank_field_constraint_violation"](
    "browser_fill_semantic",
    {"field": "Mnemonic code", "text": ""},
    blank_messages,
) is None
assert scope["_blank_field_constraint_violation"](
    "browser_fill_semantic",
    {"field": "Name", "text": "allowed"},
    blank_messages,
) is None
assert scope["_blank_field_constraint_violation"](
    "browser_fill_semantic",
    {"field": "Mnemonic code", "text": "TZ001"},
    [{"role": "user", "content": "internal continuation only"}],
    task_text=(
        "В обязательном поле Parent выбери Master, не изменяя его. "
        "Поле Mnemonic code оставь пустым."
    ),
) == "Mnemonic code"
assert "_PENDING_OMISSION_CONTINUATIONS" in uqa_source
assert "[UQA CORE: CONTINUE AFTER OMITTED FIELD]" in uqa_source
assert "Continue with the next required operation" in uqa_source

selection_task = (
    "В обязательном поле Parent выбери существующую зону Master, "
    "не изменяя её."
)
assert scope["_required_selection_constraints"](selection_task) == [{
    "field": "Parent",
    "value": "Master",
}]
assert scope["_is_form_commit_action"](
    "browser_click_semantic",
    {"name": "Save"},
) is True
assert scope["_is_form_commit_action"](
    "browser_click_semantic",
    {"name": "Create acces zone"},
) is False
state_key = ("job-smoke", "case-smoke")
scope["_PENDING_SELECTION_FIELD_TRANSITIONS"][state_key] = {
    "field": "Parent",
    "value": "Master",
}
scope["record_required_selection_result"](
    *state_key,
    {"executed": True, "status": "ok"},
)
assert scope["_PENDING_CONSTRAINED_ACTIONS"][state_key]["arguments"] == {
    "name": "Master",
    "exact": True,
}
assert scope["_PENDING_CONSTRAINED_ACTIONS"][state_key]["allowed_roles"] == [
    "option",
    "treeitem",
]
value_candidate = scope["_PENDING_CONSTRAINED_ACTIONS"][state_key]
assert scope["_navigation_candidate_matches"](
    "browser_click_semantic",
    {"name": "Master", "exact": True, "role": "treeitem"},
    value_candidate,
) is True
assert scope["_navigation_candidate_matches"](
    "browser_click_semantic",
    {"name": "Master", "exact": True, "role": "button"},
    value_candidate,
) is False
scope["_PENDING_SELECTION_COMPLETIONS"][state_key] = {
    "field": "Parent",
    "value": "Master",
}
scope["record_required_selection_result"](
    *state_key,
    {"executed": True, "status": "ok"},
)
assert scope["_selection_key"]("Parent", "Master") in (
    scope["_COMPLETED_REQUIRED_SELECTIONS"][state_key]
)
assert scope["_PENDING_SELECTION_CONTINUATIONS"][state_key] == {
    "field": "Parent",
    "value": "Master",
}
assert "managed_required_selection_missing" in uqa_source
assert "required_selection_field" in uqa_source
assert "required_selection_value" in uqa_source
assert "required_selection_direct" in uqa_source
assert "[UQA CORE: CONTINUE AFTER REQUIRED SELECTION]" in uqa_source
assert '"tool": "browser_select_semantic"' in uqa_source
assert '"option": required["value"]' in uqa_source

print("exact resource-name constraint smoke: PASS")

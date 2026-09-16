import ast
import json
import re
from pathlib import Path


SOURCE = Path("uqa.py").read_text(encoding="utf-8")
TREE = ast.parse(SOURCE)
NAMES = {
    "_latest_user_text",
    "_request_has_explicit_mutation_intent",
    "_request_is_read_only",
    "_normalize_planned_checks",
    "_numbered_items_are_workflow_checks",
    "_workflow_case_title",
    "_request_declares_single_workflow",
    "_coalesce_declared_single_workflow",
    "extract_explicit_regression_cases",
    "_parse_regression_plan",
    "_regression_shared_context",
    "_build_regression_case_prompt",
}
BODY = [
    node
    for node in TREE.body
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    and node.name in NAMES
]
MODULE = ast.Module(body=BODY, type_ignores=[])
SCOPE = {
    "json": json,
    "re": re,
    "MAX_REGRESSION_CASES": 20,
}
exec(compile(MODULE, "uqa.py", "exec"), SCOPE)


def messages(text):
    return [{"role": "user", "content": text}]


is_read_only = SCOPE["_request_is_read_only"]
extract = SCOPE["extract_explicit_regression_cases"]
parse = SCOPE["_parse_regression_plan"]
build_prompt = SCOPE["_build_regression_case_prompt"]
coalesce = SCOPE["_coalesce_declared_single_workflow"]

assert is_read_only(messages("Создай один объект. Не изменяй существующие объекты.")) is False
assert is_read_only(messages("Не изменяй существующие объекты; создай новый.")) is False
assert is_read_only(messages("Create one object; do not modify existing objects.")) is False
assert is_read_only(messages("Только проверь, ничего не меняй и не создавай.")) is True
assert is_read_only(messages("Do not create or change anything; read-only.")) is True
assert is_read_only(messages(
    "Только read-only. Ничего не создавай и не изменяй. Сохрани evidence и результат."
)) is True

workflow = """Проведи контролируемый regression-тест жизненного цикла ресурса.

Создай ровно один временный тестовый объект.
Не создавай другие сущности и не изменяй существующие объекты.

Проверь, что:
1. объект создан и отображается;
2. ресурс зарегистрирован для cleanup;
3. cleanup удаляет именно этот ресурс;
4. после удаления объект не существует.
"""
plan = extract(workflow)
assert len(plan) == 1, plan
assert len(plan[0]["checks"]) == 4, plan
assert plan[0]["task"] == workflow.strip()

independent = """Проверь независимые случаи:
1. Страница входа открывается.
2. Страница справки открывается.
"""
independent_plan = extract(independent)
assert len(independent_plan) == 2, independent_plan

parsed = parse(json.dumps({
    "cases": [{
        "title": "Один workflow",
        "task": "Создать, проверить и очистить ресурс",
        "expected": None,
        "checks": ["создан", "зарегистрирован", "удалён", "не существует"],
    }]
}, ensure_ascii=False))
assert len(parsed) == 1
assert len(parsed[0]["checks"]) == 4

split_plan = [
    {"title": "Создание", "task": "Создать объект", "expected": None, "checks": []},
    {"title": "Регистрация", "task": "Проверить ledger", "expected": None, "checks": []},
    {"title": "Удаление", "task": "Проверить cleanup", "expected": None, "checks": []},
]
coalesced = coalesce(
    "Выполни один последовательный workflow для одного и того же объекта.",
    split_plan,
)
assert len(coalesced) == 1
assert len(coalesced[0]["checks"]) == 3
assert len(coalesce(
    "Внутри одного test case проверь весь жизненный цикл.",
    split_plan,
)) == 1
assert len(coalesce(
    "Выполни regression как один последовательный test case: создай, проверь и очисти ресурс.",
    split_plan,
)) == 1
assert coalesce("Проверь три независимых страницы.", split_plan) == split_plan

prompt = build_prompt(
    original_request=workflow,
    safe_request=workflow,
    job_id="job-smoke",
    case_id="case-smoke",
    index=1,
    total=1,
    case_spec=plan[0],
)
assert "Плановые проверки внутри текущего test case" in prompt
assert prompt.count('"title"') == 4
assert "Каждую плановую проверку" in prompt

print("v069c/v070c isolated smoke: PASS")

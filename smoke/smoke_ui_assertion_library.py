from tools.browser import BrowserSession
from uqa import _evaluate_ui_assertions, compile_locked_ui_requirement


def evaluate(result, assertions):
    return _evaluate_ui_assertions(
        assertions,
        {
            "observation_id": "obs-smoke",
            "data": result,
        },
    )


session = BrowserSession()

try:
    session._ensure_started()
    session.page.set_content("""
      <label><input type="checkbox" checked required>Enabled</label>
      <div role="tablist"><button role="tab" aria-selected="true">Safe</button></div>
      <button aria-expanded="false" aria-controls="details">Details</button>
      <input aria-label="Name" readonly aria-invalid="true" value="demo">
      <div id="details">Body</div>
    """)

    checkbox = session.inspect_semantic("Enabled", role="checkbox")
    assert checkbox["checked"] is True, checkbox
    assert checkbox["required"] is True, checkbox
    assert checkbox["invalid"] is False, checkbox

    option = session.inspect_semantic("Safe", role="tab")
    assert option["selected"] is True, option

    disclosure = session.inspect_semantic("Details", role="button")
    assert disclosure["expanded"] is False, disclosure

    readonly = session.inspect_semantic("Name", role="textbox")
    assert readonly["read_only"] is True, readonly
    assert readonly["invalid"] is True, readonly

    normalized, issues, passed = evaluate(checkbox, [
        {"field": "checked", "operator": "eq", "expected": True},
        {"field": "required", "operator": "eq", "expected": True},
    ])
    assert not issues, issues
    assert passed is True, normalized

    normalized, issues, passed = evaluate(disclosure, [
        {"field": "expanded", "operator": "eq", "expected": True},
    ])
    assert not issues, issues
    assert passed is False, normalized

finally:
    session.close()


compiled = {
    "checked": compile_locked_ui_requirement({"title": "Флажок Enabled отмечен"}),
    "selected": compile_locked_ui_requirement({"title": "Пункт Safe выбран"}),
    "collapsed": compile_locked_ui_requirement({"title": "Раздел Details свёрнут"}),
}
assert compiled["checked"]["assertions"][0] == {
    "field": "checked", "operator": "eq", "expected": True,
}, compiled
assert compiled["selected"]["assertions"][0] == {
    "field": "selected", "operator": "eq", "expected": True,
}, compiled
assert compiled["collapsed"]["assertions"][0] == {
    "field": "expanded", "operator": "eq", "expected": False,
}, compiled
assert compile_locked_ui_requirement({
    "title": "После сохранения флажок Enabled отмечен",
}) is None
assert compile_locked_ui_requirement({
    "task": "Проверить объект home-server в режиме read-only",
}) is None

print("UI assertion library smoke: PASS")

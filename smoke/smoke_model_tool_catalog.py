import json
import uqa

original = json.dumps(uqa.TOOLS, ensure_ascii=False)
click = next(t['function'] for t in uqa.TOOLS if t['function']['name'] == 'browser_click_semantic')
assert {'row', 'treeitem', 'combobox'} <= set(click['parameters']['properties']['role']['enum'])
assert 'tr/[role=row]' in click['parameters']['properties']['container']['description']
assert 'без role/container' in click['description']
assert click['parameters']['required'] == ['name']
assert uqa.classify_tool_action('browser_click_semantic', {'name': 'plus'}) == 'write'
base = uqa.model_tool_catalog()
assert len(json.dumps(base, ensure_ascii=False)) < len(original) / 3
available = {t["function"]["name"] for t in uqa.TOOLS}
enum = base[0]["function"]["parameters"]["properties"]["names"]["items"]["enum"]
assert set(enum) == available
assert uqa.MODEL_CATALOG_TOOL_NAME not in available

selected = uqa.select_model_tools({"names": ["browser_open_exact_table_row_details_semantic"]})
loaded = {t["function"]["name"] for t in uqa.model_tool_catalog(selected)}
assert "browser_open_exact_table_row_details_semantic" in loaded
assert uqa.MODEL_BASE_TOOL_NAMES & available <= loaded
assert "browser_open_exact_table_row_details_semantic" not in {
    t["function"]["name"] for t in base}
assert json.dumps(uqa.TOOLS, ensure_ascii=False) == original
for arguments in (
    None, {}, {"names": []}, {"names": [None]}, {"names": ["unknown"]},
    {"names": ["browser_open_page", "browser_open_page"]},
    {"names": enum[:13]}, {"names": [enum[0]], "unsafe": True},
):
    try:
        uqa.select_model_tools(arguments)
        raise AssertionError("invalid selection accepted")
    except ValueError:
        pass

# Discovery does not reclassify loaded tools or weaken their policy.
assert uqa.classify_tool_action("browser_click_semantic", {"name": "Delete"}) == "destructive"
assert uqa.classify_tool_action("browser_click_semantic", {"name": "Add"}) == "write"

saved_ask = uqa.ask_ollama
saved_execute = uqa.execute_tool_with_policy
seen = []
seen_history = []
responses = iter([
    {"message": {"tool_calls": [{"function": {"name": uqa.MODEL_CATALOG_TOOL_NAME,
        "arguments": {"names": ["unknown"]}}}]}},
    {"message": {"tool_calls": [{"function": {"name": uqa.MODEL_CATALOG_TOOL_NAME,
        "arguments": {"names": ["browser_open_exact_table_row_details_semantic"]}}}]}},
    {"message": {"content": "Diagnostic complete"}},
])

def fake_ask(messages, tools):
    seen.append({t["function"]["name"] for t in tools})
    seen_history[:] = messages
    return next(responses)

def reject_execute(*args, **kwargs):
    raise AssertionError("catalog selection attempted a real action")

try:
    uqa.ask_ollama = fake_ask
    uqa.execute_tool_with_policy = reject_execute
    history = []
    uqa.run_turn(history)
    target = "browser_open_exact_table_row_details_semantic"
    assert target not in seen[0] and target not in seen[1] and target in seen[2]
    results = [json.loads(m["content"]) for m in seen_history
               if m.get("tool_name") == uqa.MODEL_CATALOG_TOOL_NAME]
    assert results[0]["error"] == "model_catalog_selection_invalid"
    assert results[1]["status"] == "loaded"
    assert all(r["execution_performed"] is False and r["usable_for_verdict"] is False
               for r in results)
finally:
    uqa.ask_ollama = saved_ask
    uqa.execute_tool_with_policy = saved_execute
print("progressive model tool catalog smoke: PASS")

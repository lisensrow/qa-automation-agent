import os
import re
from pathlib import Path

from tools.registry import CLEANUP_ONLY_TOOLS, TOOLS
from uqa import classify_tool_action

root = Path(os.getenv("UQA_SMOKE_ROOT", "/opt/uqa"))
registry_source = (root / "tools" / "registry.py").read_text(encoding="utf-8")

declared = [
    item["function"]["name"]
    for item in [*TOOLS, *CLEANUP_ONLY_TOOLS]
    if item.get("type") == "function"
]
browser_declared = [name for name in declared if name.startswith("browser_")]
dispatch = re.findall(r'if name == "(browser_[^"]+)"', registry_source)

assert len(declared) == len(set(declared)), "duplicate public tool declaration"
assert len(dispatch) == len(set(dispatch)), "duplicate browser dispatch branch"
assert set(browser_declared) == set(dispatch), {
    "declared_without_dispatch": sorted(set(browser_declared) - set(dispatch)),
    "dispatch_without_declaration": sorted(set(dispatch) - set(browser_declared)),
}

wrong_observe = {
    name: classify_tool_action(name, {})
    for name in browser_declared
    if (
        name.startswith("browser_observe_")
        and classify_tool_action(name, {}) != "observe"
    ) or (
        name.startswith("browser_inspect_")
        and classify_tool_action(name, {}) not in {"observe", "interact"}
    )
}
assert not wrong_observe, wrong_observe

print(
    "tool registry integrity smoke: PASS "
    f"({len(browser_declared)} browser tools, "
    f"{sum(classify_tool_action(name, {}) == 'observe' for name in browser_declared)} observe tools)"
)

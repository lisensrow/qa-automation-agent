from tools.browser import BrowserSession


session = BrowserSession()

try:
    session._ensure_started()
    session.page.set_content(
        """
        <html><body>
          <div role="listbox" aria-label="Teams" aria-multiselectable="true">
            <div role="option" aria-selected="true">Alpha</div>
            <div role="option" aria-selected="true">Beta</div>
            <div role="option" aria-selected="false">Gamma</div>
          </div>
          <script>
            document.querySelectorAll('[role="option"]').forEach(option => {
              option.addEventListener('click', () => {
                const selected = option.getAttribute('aria-selected') === 'true';
                option.setAttribute('aria-selected', selected ? 'false' : 'true');
              });
            });
          </script>
        </body></html>
        """
    )
    direct = session.select_many_semantic(
        "Teams",
        ["Alpha", "Gamma"],
    )
    assert direct.get("selection_status") == "selected", direct
    assert set(direct.get("selected_options") or []) == {
        "Alpha",
        "Gamma",
    }, direct
    assert direct.get("field_match_strategy") == (
        "aria-multiselectable-listbox"
    ), direct

    repeated = session.select_many_semantic(
        "Teams",
        ["Alpha", "Gamma"],
    )
    assert repeated.get("selection_status") == "already_satisfied", repeated
    assert repeated.get("mutation_executed") is False, repeated

    session.page.set_content(
        """
        <html><body>
          <label for="people">People</label>
          <input id="people" role="combobox" aria-controls="people-list"
                 aria-expanded="false">
          <div id="chips"></div>
          <div id="people-list" role="listbox" aria-multiselectable="true"
               hidden>
            <div role="option" aria-selected="true">Alice</div>
            <div role="option" aria-selected="false">Bob</div>
            <div role="option" aria-selected="true">Carol</div>
          </div>
          <script>
            const input = document.getElementById('people');
            const list = document.getElementById('people-list');
            const chips = document.getElementById('chips');
            function render() {
              chips.innerHTML = '';
              list.querySelectorAll('[aria-selected="true"]').forEach(option => {
                const chip = document.createElement('span');
                chip.setAttribute('role', 'option');
                chip.setAttribute('aria-selected', 'true');
                chip.textContent = option.textContent;
                chips.appendChild(chip);
              });
            }
            input.addEventListener('click', () => {
              list.hidden = false;
              input.setAttribute('aria-expanded', 'true');
            });
            list.querySelectorAll('[role="option"]').forEach(option => {
              option.addEventListener('click', () => {
                const selected = option.getAttribute('aria-selected') === 'true';
                option.setAttribute('aria-selected', selected ? 'false' : 'true');
                render();
              });
            });
            render();
          </script>
        </body></html>
        """
    )
    chips = session.select_many_semantic(
        "People",
        ["Alice", "Bob"],
    )
    assert chips.get("selection_status") == "selected", chips
    assert set(chips.get("selected_options") or []) == {
        "Alice",
        "Bob",
    }, chips
    assert chips.get("field_match_strategy") == (
        "aria-combobox-listbox"
    ), chips
    rendered = session.page.locator("#chips [role=option]").all_inner_texts()
    assert set(rendered) == {"Alice", "Bob"}, rendered
finally:
    session.close()

print("ARIA multiselect/chips smoke: PASS")

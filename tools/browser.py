import atexit
import os
import re
import uuid
from datetime import datetime
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit

os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", "/opt/uqa/browsers")

from playwright.sync_api import sync_playwright


ARTIFACTS_BASE = Path("/opt/uqa/artifacts/browser")

_run_user_raw = (
    os.getenv("UQA_USER")
    or os.getenv("USER")
    or "unknown"
)

RUN_USER = "".join(
    ch if ch.isalnum() or ch in "._-" else "_"
    for ch in _run_user_raw
)

ARTIFACTS_ROOT = ARTIFACTS_BASE / RUN_USER
ARTIFACTS_ROOT.mkdir(parents=True, exist_ok=True)
os.chmod(ARTIFACTS_ROOT, 0o700)

UC_ORIGIN = "https://uc.lab.local"
UC_PFX = Path("/opt/uqa/secrets/Realm-manager.pfx")
UC_PFX_PASSWORD = Path("/opt/uqa/secrets/password.txt")


def _field_metadata_matches(values, field, exact=True):
    normalized_field = str(field or "").strip().casefold()

    if not normalized_field:
        return False

    normalized_values = [
        str(value or "").strip().casefold()
        for value in values
        if str(value or "").strip()
    ]

    if exact:
        if normalized_field in normalized_values:
            return True

        field_tokens = set(
            re.findall(r"[\w-]+", normalized_field)
        )

        return any(
            value in field_tokens
            for value in normalized_values
        )

    return any(
        normalized_field in value
        for value in normalized_values
    )


class BrowserSession:
    def __init__(self):
        self.session_id = (
            datetime.now().strftime("%Y%m%d-%H%M%S")
            + "-"
            + uuid.uuid4().hex[:6]
        )

        self.session_dir = ARTIFACTS_ROOT / self.session_id
        self.session_dir.mkdir(parents=True, exist_ok=True)
        os.chmod(self.session_dir, 0o700)

        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None

        self.action_counter = 0
        self.element_counter = 0

        self.console_errors = []
        self.failed_requests = []
        self.http_errors = []

        # Компактный журнал fetch/XHR текущего действия.
        self.network_events = []
        self.network_counter = 0

        # Ссылки на конкретные fetch/XHR храним всю браузерную сессию.
        # В модель они не попадают, пока она явно не запросит nXX.
        self.network_details = {}

        # Идентичность конкретного UI-действия.
        # Отдельный counter нужен потому, что action_counter
        # увеличивается только при _capture_state().
        self.action_execution_counter = 0
        self.active_action_execution_id = None

        self.last_uc_auth = None

    def _context_kwargs(self):
        context_kwargs = {
            "ignore_https_errors": True,
            "viewport": {
                "width": 1920,
                "height": 1080,
            },
        }

        if (
            UC_PFX.exists()
            and UC_PFX_PASSWORD.exists()
        ):
            pfx_password = (
                UC_PFX_PASSWORD.read_text(
                    encoding="utf-8"
                ).strip()
            )

            context_kwargs[
                "client_certificates"
            ] = [
                {
                    "origin": UC_ORIGIN,
                    "pfxPath": str(UC_PFX),
                    "passphrase": pfx_password,
                }
            ]

        return context_kwargs


    def _create_context(self):
        self.context = (
            self.browser.new_context(
                **self._context_kwargs()
            )
        )

        self.page = (
            self.context.new_page()
        )

        self.page.on(
            "console",
            self._on_console,
        )

        self.page.on(
            "requestfailed",
            self._on_request_failed,
        )

        self.page.on(
            "response",
            self._on_response,
        )

        self.last_uc_auth = None


    def _ensure_started(self):
        if self.browser is not None:
            return

        self.playwright = (
            sync_playwright().start()
        )

        self.browser = (
            self.playwright.chromium.launch(
                headless=True
            )
        )

        self._create_context()


    def reset_case_context(self):
        """
        Create a clean Playwright BrowserContext for a new
        regression test case while keeping Chromium alive.

        Browser state from the previous case must not leak:
        cookies, local/session storage, page state and runtime
        diagnostics are discarded.

        Global artifact/action counters remain monotonic so
        evidence filenames and action ids cannot collide.
        """
        if self.browser is None:
            self._ensure_started()

            return {
                "status": "initialized",
                "session_id": self.session_id,
            }

        try:
            if self.context is not None:
                self.context.close()
        finally:
            self.page = None
            self.context = None

        # Per-context diagnostics/state.
        self.console_errors = []
        self.failed_requests = []
        self.http_errors = []

        self.network_events = []
        self.network_details = {}

        self.active_action_execution_id = None
        self.last_uc_auth = None

        # Intentionally DO NOT reset:
        # action_counter
        # action_execution_counter
        # network_counter
        # They stay unique inside this BrowserSession.

        self._create_context()

        return {
            "status": "reset",
            "session_id": self.session_id,
        }


    def _ensure_uc_authenticated(self, url: str):
        if not (
            url == UC_ORIGIN
            or url.startswith(UC_ORIGIN + "/")
        ):
            return None

        check_before = self.page.evaluate(
            """
            async () => {
                const r = await fetch('/check-auth', {
                    credentials: 'include'
                });

                return {
                    status: r.status,
                    body: await r.text()
                };
            }
            """
        )

        if check_before["status"] == 200:
            return {
                "status": "already_authenticated",
                "check_before": 200,
                "cert_login": None,
                "check_after": 200,
            }

        if (
            check_before["status"] == 428
            and "valid cert" in check_before["body"].lower()
        ):
            cert_login = self.page.evaluate(
                """
                async () => {
                    const r = await fetch(
                        '/api/v1/u-auth/cert-login',
                        {
                            method: 'POST',
                            credentials: 'include'
                        }
                    );

                    return {
                        status: r.status,
                        body: await r.text()
                    };
                }
                """
            )

            check_after = self.page.evaluate(
                """
                async () => {
                    const r = await fetch('/check-auth', {
                        credentials: 'include'
                    });

                    return {
                        status: r.status,
                        body: await r.text()
                    };
                }
                """
            )

            if (
                cert_login["status"] == 200
                and check_after["status"] == 200
            ):
                self.page.reload(
                    wait_until="domcontentloaded",
                    timeout=30000,
                )

                self.page.wait_for_timeout(1500)

                return {
                    "status": "authenticated_by_certificate",
                    "check_before": check_before["status"],
                    "cert_login": cert_login["status"],
                    "check_after": check_after["status"],
                }

            return {
                "status": "authentication_failed",
                "check_before": check_before["status"],
                "cert_login": cert_login["status"],
                "check_after": check_after["status"],
            }

        return {
            "status": "not_authenticated",
            "check_before": check_before["status"],
            "cert_login": None,
            "check_after": None,
        }

    def authenticate_saved_stand(self, stand: str = None):
        """
        Authenticate a visible web login form with credentials decrypted
        inside UQA Core. Secret values never enter model/tool arguments or
        returned evidence. This path is disabled unless the operator enables
        it explicitly for the current process.
        """
        enabled = (
            os.getenv("UQA_USE_SSH_CREDS_FOR_WEB", "0")
            .strip()
            .casefold()
            in {"1", "true", "yes", "on"}
        )

        if not enabled:
            return {
                "error": "saved_web_auth_not_enabled",
                "status": "blocked_by_policy",
                "executed": False,
                "reason": (
                    "Set UQA_USE_SSH_CREDS_FOR_WEB=1 only after "
                    "the operator authorizes reusing saved credentials."
                ),
            }

        self._ensure_started()

        from stands import get_stand

        current_url = urlsplit(self.page.url)
        current_host = current_url.hostname
        requested_stand = str(stand or current_host or "").strip()
        stand_info = get_stand(
            requested_stand,
            include_password=True,
        ) or {}
        stored_host = urlsplit(
            str(stand_info.get("web_url") or "")
        ).hostname

        if (
            current_url.scheme.casefold() != "https"
            or not current_host
            or current_host != stored_host
        ):
            return {
                "error": "saved_web_auth_origin_mismatch",
                "status": "blocked_by_policy",
                "executed": False,
            }

        username = str(stand_info.get("ssh_username") or "").strip()
        password = stand_info.get("ssh_password")

        if not username or not password:
            return {
                "error": "saved_web_credentials_missing",
                "status": "error",
                "executed": False,
            }

        password_inputs = self.page.locator(
            'input[type="password"]'
        )
        visible_passwords = [
            password_inputs.nth(index)
            for index in range(min(password_inputs.count(), 10))
            if password_inputs.nth(index).is_visible()
        ]

        username_inputs = self.page.locator(
            'input[name="login"], input[name="username"], '
            'input[autocomplete="username"], input[type="text"]'
        )
        visible_usernames = []

        for index in range(min(username_inputs.count(), 20)):
            candidate = username_inputs.nth(index)

            if not candidate.is_visible():
                continue

            if candidate in visible_usernames:
                continue

            visible_usernames.append(candidate)

        if len(visible_passwords) != 1 or len(visible_usernames) != 1:
            password = None
            return {
                "error": "saved_web_login_form_ambiguous",
                "status": "error",
                "executed": False,
                "username_fields": len(visible_usernames),
                "password_fields": len(visible_passwords),
            }

        sign_in = self.page.get_by_role(
            "button",
            name=re.compile(r"^sign\s+in$", re.IGNORECASE),
        )
        visible_buttons = [
            sign_in.nth(index)
            for index in range(min(sign_in.count(), 10))
            if sign_in.nth(index).is_visible()
        ]

        if len(visible_buttons) != 1:
            password = None
            return {
                "error": "saved_web_sign_in_button_ambiguous",
                "status": "error",
                "executed": False,
                "matches": len(visible_buttons),
            }

        self._reset_diagnostics()
        self._begin_action_execution()

        try:
            visible_usernames[0].fill(username)
            visible_passwords[0].fill(password)
            password = None
            click_error_type = None

            try:
                visible_buttons[0].click(
                    timeout=10000,
                    no_wait_after=True,
                )
            except Exception as exc:
                # A submitted login can outlive Playwright's click wait when
                # the application keeps requests open. Verify the resulting
                # form state instead of treating the timeout as definitive.
                click_error_type = type(exc).__name__

            try:
                self.page.wait_for_load_state(
                    "domcontentloaded",
                    timeout=5000,
                )
            except Exception:
                pass

            try:
                self.page.wait_for_function(
                    """
                    () => {
                        const visible = (el) => {
                            const style = window.getComputedStyle(el);
                            const box = el.getBoundingClientRect();
                            return style.visibility !== "hidden"
                                && style.display !== "none"
                                && box.width > 0
                                && box.height > 0;
                        };
                        const passwordVisible = Array.from(
                            document.querySelectorAll('input[type="password"]')
                        ).some(visible);
                        const signInVisible = Array.from(
                            document.querySelectorAll('button, [role="button"]')
                        ).some((el) => {
                            if (!visible(el)) return false;
                            const label = (
                                el.getAttribute("aria-label")
                                || el.innerText
                                || el.textContent
                                || ""
                            ).trim();
                            return /^sign\s+in$/i.test(label);
                        });
                        return !passwordVisible && !signInVisible;
                    }
                    """,
                    timeout=15000,
                )
            except Exception:
                # Keep the final decision evidence-based below. A timeout can
                # mean either rejected credentials or a slow application.
                pass

            self.page.wait_for_timeout(500)

            remaining_passwords = self.page.locator(
                'input[type="password"]'
            )
            password_form_visible = any(
                remaining_passwords.nth(index).is_visible()
                for index in range(min(remaining_passwords.count(), 10))
            )
            remaining_sign_in = self.page.get_by_role(
                "button",
                name=re.compile(r"^sign\s+in$", re.IGNORECASE),
            )
            sign_in_visible = any(
                remaining_sign_in.nth(index).is_visible()
                for index in range(min(remaining_sign_in.count(), 10))
            )
            login_form_visible = (
                password_form_visible or sign_in_visible
            )

            result = self._capture_state(
                "authenticate-saved-stand"
            )
            result["executed"] = True
            result["credential_source"] = "encrypted_stand_store"
            result["authentication_status"] = (
                "failed" if login_form_visible else "authenticated"
            )
            result["success"] = not login_form_visible
            result["submission_wait_status"] = (
                "completed"
                if click_error_type is None
                else "click_wait_error"
            )

            if login_form_visible:
                result["error"] = (
                    "saved_web_authentication_click_error"
                    if click_error_type
                    else "saved_web_authentication_failed"
                )

                if click_error_type:
                    result["error_type"] = click_error_type

            return self._finish_action_execution(result)

        except Exception as exc:
            password = None
            result = {
                "error": "saved_web_authentication_error",
                "error_type": type(exc).__name__,
                "status": "error",
                "executed": False,
            }
            return self._finish_action_execution(result)

    def _on_console(self, msg):
        if msg.type != "error":
            return

        # HTTP 4xx/5xx собираем отдельно через response,
        # чтобы видеть URL и статус, а не бесполезное
        # "Failed to load resource".
        if msg.text.startswith(
            "Failed to load resource: "
            "the server responded with a status of"
        ):
            return

        self.console_errors.append(msg.text)

    def _safe_network_url(self, url: str):
        try:
            parts = urlsplit(url)

            safe_query = []

            sensitive_words = (
                "token",
                "password",
                "passwd",
                "secret",
                "cookie",
                "session",
                "authorization",
                "auth_token",
                "api_key",
                "apikey",
            )

            for key, value in parse_qsl(
                parts.query,
                keep_blank_values=True,
            ):
                lowered = key.lower()

                if any(
                    word in lowered
                    for word in sensitive_words
                ):
                    value = "<redacted>"

                safe_query.append((key, value))

            query = urlencode(safe_query)

            if (
                parts.scheme == "https"
                and parts.netloc == "uc.lab.local"
            ):
                result = parts.path or "/"
            else:
                result = (
                    f"{parts.scheme}://"
                    f"{parts.netloc}"
                    f"{parts.path or '/'}"
                )

            if query:
                result += "?" + query

            return result

        except Exception:
            return "<unparseable-url>"

    def _filtered_network_events(self, action: str):
        events = list(self.network_events)

        # Это доказанные служебные запросы стартовой
        # сертификатной авторизации U-Connect.
        if (
            action == "open"
            and self.last_uc_auth
            and self.last_uc_auth.get("status")
            in (
                "authenticated_by_certificate",
                "already_authenticated",
            )
        ):
            ignored_paths = (
                "/check-auth",
                "/check-krb-auth",
                "/api/v1/u-auth/cert-login",
            )

            events = [
                item
                for item in events
                if not any(
                    item.get("url", "").startswith(path)
                    for path in ignored_paths
                )
            ]

        # В модель не отправляем бесконечный Network.
        return events[-30:]

    def _begin_action_execution(self):
        self.action_execution_counter += 1

        execution_id = (
            f"{self.session_id}"
            f"-a{self.action_execution_counter:04d}"
        )

        self.active_action_execution_id = (
            execution_id
        )

        return execution_id

    def _finish_action_execution(
        self,
        result: dict,
    ):
        execution_id = (
            self.active_action_execution_id
        )

        if execution_id:
            result["action_execution_id"] = (
                execution_id
            )

            # Это НЕ означает, что мы доказали
            # отсутствие любого возможного позднего XHR.
            # Означает только, что окно наблюдения
            # данного действия закрыто в момент capture_state.
            result["network_window_closed"] = True

            result["network_capture_scope"] = (
                "fetch_xhr_until_capture_state"
            )

        self.active_action_execution_id = None

        return result

    def _on_response(self, response):
        request = response.request

        if request.resource_type in ("fetch", "xhr"):
            self.network_counter += 1

            request_id = f"n{self.network_counter}"

            self.network_events.append(
                {
                    "request_id": request_id,
                    "session_id": self.session_id,
                    "action_execution_id": (
                        self.active_action_execution_id
                    ),
                    "method": request.method,
                    "status": response.status,
                    "type": request.resource_type,
                    "url": self._safe_network_url(
                        response.url
                    ),
                }
            )

            self.network_details[request_id] = {
                "request": request,
                "response": response,
                "session_id": self.session_id,
                "action_execution_id": (
                    self.active_action_execution_id
                ),
            }

        if response.status >= 400:
            self.http_errors.append(
                {
                    "status": response.status,
                    "method": request.method,
                    "url": self._safe_network_url(
                        response.url
                    ),
                }
            )

    def _reset_diagnostics(self):
        self.console_errors.clear()
        self.failed_requests.clear()
        self.http_errors.clear()
        self.network_events.clear()
        self.active_action_execution_id = None

    def _on_request_failed(self, request):
        self.failed_requests.append(
            {
                "url": request.url,
                "error": request.failure,
            }
        )

    def _inspect_elements(self):
        selector = (
            "input, button, select, textarea, a, "
            "[role='button'], [role='link'], "
            "[role='menuitem'], [role='tab'], [role='option'], "
            "[role='checkbox'], [role='radio'], "
            "[aria-selected], [aria-checked]"
        )

        elements = self.page.locator(selector)
        result = []

        count = min(elements.count(), 100)

        for i in range(count):
            element = elements.nth(i)

            try:
                if not element.is_visible():
                    continue

                uqa_id = element.get_attribute("data-uqa-id")

                if not uqa_id:
                    self.element_counter += 1
                    uqa_id = f"e{self.element_counter}"

                    element.evaluate(
                        "(el, id) => el.setAttribute('data-uqa-id', id)",
                        uqa_id,
                    )

                info = element.evaluate(
                    """
                    el => {
                        let label = "";

                        if (el.labels && el.labels.length) {
                            label = Array.from(el.labels)
                                .map(x => x.innerText || x.textContent || "")
                                .join(" ")
                                .trim();
                        }

                        const tag =
                            (el.tagName || "").toLowerCase();

                        const type =
                            (el.getAttribute("type") || "").toLowerCase();

                        const role =
                            (el.getAttribute("role") || "").toLowerCase();

                        const checkable =
                            tag === "input" &&
                            (type === "checkbox" || type === "radio");

                        return {
                            tag: tag,
                            type: type,
                            role: role,
                            name: el.getAttribute("name") || "",
                            placeholder: el.getAttribute("placeholder") || "",
                            aria_label: el.getAttribute("aria-label") || "",

                            icon_hints: (() => {
                                const hints = new Set();
                                const nodes = [
                                    el,
                                    ...el.querySelectorAll("*")
                                ];

                                for (const node of nodes) {
                                    for (const cls of (node.classList || [])) {
                                        const match = cls.match(
                                            /^(?:pi|fa|fas|far|fab|mdi|icon)-(.+)$/i
                                        );

                                        if (match && match[1]) {
                                            hints.add(match[1].toLowerCase());
                                        }
                                    }

                                    for (const attr of [
                                        "data-icon",
                                        "data-lucide"
                                    ]) {
                                        const value = node.getAttribute?.(attr);

                                        if (value) {
                                            hints.add(value.toLowerCase());
                                        }
                                    }
                                }

                                return Array.from(hints).slice(0, 10);
                            })(),

                            checked:
                                checkable
                                    ? Boolean(el.checked)
                                    : null,

                            indeterminate:
                                checkable
                                    ? Boolean(el.indeterminate)
                                    : null,

                            aria_checked:
                                el.getAttribute("aria-checked"),

                            aria_selected:
                                el.getAttribute("aria-selected"),

                            disabled_attribute:
                                el.hasAttribute("disabled"),

                            aria_disabled:
                                el.getAttribute("aria-disabled"),

                            readonly_attribute:
                                el.hasAttribute("readonly"),

                            table_context: (() => {
                                const row = el.closest("tr");

                                if (!row) {
                                    return null;
                                }

                                let section = "";

                                if (row.closest("thead")) {
                                    section = "thead";
                                } else if (row.closest("tbody")) {
                                    section = "tbody";
                                } else if (row.closest("tfoot")) {
                                    section = "tfoot";
                                }

                                return {
                                    section: section,
                                    row_text:
                                        (row.innerText || row.textContent || "")
                                            .trim()
                                            .slice(0, 500),
                                    data_cell_count:
                                        row.querySelectorAll("td").length,
                                    header_cell_count:
                                        row.querySelectorAll("th").length
                                };
                            })(),

                            text: (el.innerText || el.textContent || "")
                                .trim()
                                .slice(0, 300),

                            label: label.slice(0, 300)
                        };
                    }
                    """
                )

                info["element_id"] = uqa_id

                try:
                    info["enabled"] = element.is_enabled()
                except Exception:
                    info["enabled"] = None

                result.append(info)

            except Exception:
                continue

        return result

    def _visible_icon_matches(self, name: str):
        normalized = str(name or "").strip().casefold()

        if normalized.startswith("icon:"):
            normalized = normalized.split(":", 1)[1].strip()

        normalized = normalized.replace("_", "-")

        if not normalized:
            return []

        locator = self.page.locator(
            "button, a, [role='button'], [role='menuitem']"
        )
        matches = []

        try:
            count = min(locator.count(), 100)
        except Exception:
            return matches

        for index in range(count):
            candidate = locator.nth(index)

            try:
                if not candidate.is_visible():
                    continue

                hints = candidate.evaluate(
                    """
                    el => {
                        const result = new Set();
                        const nodes = [
                            el,
                            ...el.querySelectorAll("*")
                        ];

                        for (const node of nodes) {
                            for (const cls of (node.classList || [])) {
                                const match = cls.match(
                                    /^(?:pi|fa|fas|far|fab|mdi|icon)-(.+)$/i
                                );

                                if (match && match[1]) {
                                    result.add(match[1].toLowerCase());
                                }
                            }

                            for (const attr of [
                                "data-icon",
                                "data-lucide"
                            ]) {
                                const value = node.getAttribute?.(attr);

                                if (value) {
                                    result.add(value.toLowerCase());
                                }
                            }
                        }

                        return Array.from(result);
                    }
                    """
                )

                normalized_hints = {
                    str(value).strip().casefold().replace("_", "-")
                    for value in (hints or [])
                    if str(value).strip()
                }

                if normalized in normalized_hints:
                    matches.append(candidate)

            except Exception:
                continue

        return matches

    def _visible_explicit_role_matches(
        self,
        name: str,
        role: str,
        exact: bool,
    ):
        """
        Match the same explicit DOM roles exposed by _inspect_elements.

        Playwright's accessibility-name lookup can legitimately omit an
        otherwise visible element whose framework-provided role and text are
        still actionable.  This fallback is used only when the caller passed
        an explicit, already-observed role.
        """
        wanted = re.sub(
            r"\s+",
            " ",
            str(name or "").strip(),
        ).casefold()

        if not wanted:
            return []

        locator = self.page.locator(
            f'[role="{role}"]'
        )
        matches = []

        try:
            count = min(locator.count(), 100)
        except Exception:
            return matches

        for index in range(count):
            candidate = locator.nth(index)

            try:
                if not candidate.is_visible():
                    continue

                label = (
                    candidate.get_attribute("aria-label")
                    or candidate.inner_text()
                    or ""
                )
                normalized = re.sub(
                    r"\s+",
                    " ",
                    label.strip(),
                ).casefold()

                matched = (
                    normalized == wanted
                    if exact
                    else wanted in normalized
                )

                if matched:
                    matches.append(candidate)
            except Exception:
                continue

        return matches

    def _visible_labeled_popup_matches(
        self,
        name: str,
        exact: bool,
    ):
        """Find a popup control by nearby visible label text.

        Some component libraries render an unnamed hidden combobox input and
        a separate popup button.  When an explicit combobox lookup fails,
        associate a visible label (optionally ending in a required-field `*`)
        with the nearest ancestor containing one visible popup control.
        """
        wanted = re.sub(
            r"\s+",
            " ",
            str(name or "").strip(),
        ).casefold()

        if not wanted:
            return []

        labels = self.page.locator("label, div, span")
        matches = []
        seen = set()

        try:
            count = min(labels.count(), 1500)
        except Exception:
            return matches

        for index in range(count):
            label = labels.nth(index)

            try:
                if not label.is_visible():
                    continue

                label_text = re.sub(
                    r"\s+",
                    " ",
                    (label.inner_text() or "").strip(),
                )
                label_text = re.sub(
                    r"\s*\*\s*$",
                    "",
                    label_text,
                ).strip().casefold()
                label_matches = (
                    label_text == wanted
                    if exact
                    else wanted in label_text
                )

                if not label_matches:
                    continue

                ancestor = label

                for _ in range(5):
                    ancestor = ancestor.locator("xpath=..")
                    controls = ancestor.locator(
                        '[role="button"][aria-haspopup], [role="combobox"]'
                    )
                    visible_controls = []

                    for control_index in range(min(controls.count(), 20)):
                        control = controls.nth(control_index)

                        if control.is_visible():
                            visible_controls.append(control)

                    if not visible_controls:
                        continue

                    popup_buttons = [
                        control
                        for control in visible_controls
                        if (
                            control.get_attribute("role") == "button"
                            and control.get_attribute("aria-haspopup")
                        )
                    ]
                    selected = (
                        popup_buttons
                        if len(popup_buttons) == 1
                        else visible_controls
                    )

                    if len(selected) == 1:
                        control = selected[0]
                        key = (
                            control.get_attribute("data-uqa-id")
                            or control.get_attribute("id")
                            or control.evaluate(
                                "e => e.tagName + ':' + e.outerHTML"
                            )[:500]
                        )

                        if key not in seen:
                            seen.add(key)
                            matches.append(control)

                    break

            except Exception:
                continue

        return matches

    def _visible_nearby_labeled_field_matches(
        self,
        name: str,
        exact: bool,
    ):
        """Find an editable control grouped with a visible text label.

        Some component libraries render a label-looking ``div`` or ``span``
        beside an input without connecting the two through ``for``/``id`` or
        ARIA.  Playwright therefore cannot resolve ``get_by_label`` even
        though the relationship is unambiguous to a user.  Walk only nearby
        ancestors and accept the first level containing exactly one visible
        editable control.  Multiple matching groups stay ambiguous.
        """
        wanted = re.sub(
            r"\s+",
            " ",
            str(name or "").strip(),
        ).casefold()

        if not wanted:
            return []

        labels = self.page.locator("label, div, span")
        matches = []
        seen = set()
        editable_selector = (
            'input:not([type="hidden"]), textarea, select, '
            '[contenteditable="true"], [role="textbox"], '
            '[role="searchbox"], [role="combobox"], '
            '[role="spinbutton"]'
        )

        try:
            count = min(labels.count(), 1500)
        except Exception:
            return matches

        for index in range(count):
            label = labels.nth(index)

            try:
                if not label.is_visible():
                    continue

                label_text = re.sub(
                    r"\s+",
                    " ",
                    (label.inner_text() or "").strip(),
                )
                label_text = re.sub(
                    r"\s*\*\s*$",
                    "",
                    label_text,
                ).strip().casefold()
                label_matches = (
                    label_text == wanted
                    if exact
                    else wanted in label_text
                )

                if not label_matches:
                    continue

                ancestor = label

                for _ in range(4):
                    ancestor = ancestor.locator("xpath=..")
                    controls = ancestor.locator(editable_selector)
                    visible_controls = []

                    for control_index in range(min(controls.count(), 20)):
                        control = controls.nth(control_index)

                        if control.is_visible():
                            visible_controls.append(control)

                    if not visible_controls:
                        continue

                    if len(visible_controls) == 1:
                        control = visible_controls[0]
                        key = (
                            control.get_attribute("data-uqa-id")
                            or control.get_attribute("id")
                            or control.evaluate(
                                "e => e.tagName + ':' + e.outerHTML"
                            )[:500]
                        )

                        if key not in seen:
                            seen.add(key)
                            matches.append(control)

                    # The nearest ancestor already contains editable fields.
                    # Do not widen scope and guess among a larger form.
                    break

            except Exception:
                continue

        return matches

    def _filtered_http_errors(self, action: str):
        errors = list(self.http_errors)

        # Во время первого открытия U-Connect это штатные
        # запросы определения способа авторизации.
        # После успешной авторизации они не являются
        # дефектами проверяемой страницы.
        if (
            action == "open"
            and self.last_uc_auth
            and self.last_uc_auth.get("status")
            in (
                "authenticated_by_certificate",
                "already_authenticated",
            )
        ):
            filtered = []

            for item in errors:
                url = item.get("url", "")
                status = item.get("status")

                # _safe_network_url() для нашего UC origin
                # возвращает относительный URL.
                # На всякий случай поддерживаем и абсолютный.
                relative_url = url

                if relative_url.startswith(UC_ORIGIN):
                    relative_url = (
                        relative_url[len(UC_ORIGIN):]
                        or "/"
                    )

                is_check_auth = (
                    relative_url == "/check-auth"
                    or relative_url.startswith(
                        "/check-auth?"
                    )
                )

                is_check_krb_auth = (
                    relative_url == "/check-krb-auth"
                    or relative_url.startswith(
                        "/check-krb-auth?"
                    )
                )

                expected_auth_event = (
                    status == 428
                    and is_check_auth
                ) or (
                    status == 400
                    and is_check_krb_auth
                )

                if not expected_auth_event:
                    filtered.append(item)

            errors = filtered

        return errors[-20:]


    @staticmethod
    def _element_is_effectively_disabled(item):
        return (
            item.get("enabled") is False
            or item.get("disabled_attribute") is True
            or str(item.get("aria_disabled") or "")
            .strip()
            .casefold()
            == "true"
        )

    def _capture_state(self, action: str):
        self.action_counter += 1

        screenshot_path = (
            self.session_dir
            / f"{self.action_counter:03d}-{action}.png"
        )

        try:
            body_text = self.page.locator("body").inner_text(
                timeout=5000
            )
        except Exception:
            body_text = ""

        interactive_elements = self._inspect_elements()

        unnamed_icon_counts = {}

        for item in interactive_elements:
            if self._element_is_effectively_disabled(item):
                continue

            if any(
                str(item.get(key) or "").strip()
                for key in (
                    "aria_label",
                    "text",
                    "label",
                    "name",
                    "placeholder",
                )
            ):
                continue

            for hint in item.get("icon_hints") or []:
                hint = str(hint or "").strip().casefold()

                if hint:
                    unnamed_icon_counts[hint] = (
                        unnamed_icon_counts.get(hint, 0)
                        + 1
                    )

        unique_unnamed_icon_hints = sorted(
            hint
            for hint, count in unnamed_icon_counts.items()
            if count == 1
        )

        navigation_labels = []

        for item in interactive_elements:
            if self._element_is_effectively_disabled(item):
                continue

            if (
                item.get("tag") != "a"
                and item.get("role")
                not in {
                    "link",
                    "menuitem",
                    "tab",
                }
            ):
                continue

            label = next(
                (
                    str(item.get(key) or "").strip()
                    for key in (
                        "aria_label",
                        "text",
                        "label",
                    )
                    if str(item.get(key) or "").strip()
                ),
                "",
            )

            if label and label not in navigation_labels:
                navigation_labels.append(label)

        network_requests = self._filtered_network_events(
            action
        )

        self.page.screenshot(
            path=str(screenshot_path),
            full_page=True,
        )

        return {
            "session_id": self.session_id,
            "action": action,
            "current_url": self.page.url,
            "title": self.page.title(),
            "text_preview": body_text[:5000],
            "unique_unnamed_icon_hints": unique_unnamed_icon_hints,
            "navigation_labels": navigation_labels[:50],
            "interactive_elements": interactive_elements,
            "screenshot": str(screenshot_path),
            "console_errors": self.console_errors[-20:],
            "http_errors": self._filtered_http_errors(action),
            "failed_requests": self.failed_requests[-20:],
            "network_request_count": len(network_requests),
            "network_requests": network_requests,
        }

    def open_page(self, url: str):
        self._ensure_started()

        self._reset_diagnostics()

        response = self.page.goto(
            url,
            wait_until="domcontentloaded",
            timeout=30000,
        )

        self.page.wait_for_timeout(1500)

        uc_auth = self._ensure_uc_authenticated(url)
        self.last_uc_auth = uc_auth

        result = self._capture_state("open")

        public_uc_auth = None

        if uc_auth:
            status = uc_auth.get("status")

            public_uc_auth = {
                "status": status,
            }

            if status == "authenticated_by_certificate":
                public_uc_auth["method"] = "client_certificate"

            elif status == "already_authenticated":
                public_uc_auth["method"] = "existing_session"

        result.update(
            {
                "requested_url": url,
                "final_url": self.page.url,
                "http_status": (
                    response.status
                    if response
                    else None
                ),
                "uc_auth": public_uc_auth,
            }
        )

        return result

    def get_network_detail(self, request_id: str):
        self._ensure_started()

        item = self.network_details.get(request_id)

        if item is None:
            return {
                "error": (
                    f"Network request not found: {request_id}"
                ),
                "request_id": request_id,
            }

        request = item["request"]
        response = item["response"]

        safe_url = self._safe_network_url(response.url)

        # Служебную авторизацию специально не раскрываем.
        protected_paths = (
            "/check-auth",
            "/check-krb-auth",
            "/api/v1/u-auth/cert-login",
        )

        if any(
            safe_url.startswith(path)
            for path in protected_paths
        ):
            return {
                "error": (
                    "Auth network details are protected"
                ),
                "request_id": request_id,
            }

        sensitive_words = (
            "password",
            "passwd",
            "token",
            "secret",
            "cookie",
            "authorization",
            "session",
            "api_key",
            "apikey",
        )

        def redact_json(value):
            if isinstance(value, dict):
                result = {}

                for key, child in value.items():
                    lowered = str(key).lower()

                    if any(
                        word in lowered
                        for word in sensitive_words
                    ):
                        result[key] = "<redacted>"
                    else:
                        result[key] = redact_json(child)

                return result

            if isinstance(value, list):
                return [
                    redact_json(child)
                    for child in value
                ]

            return value

        def safe_body(raw, limit=8000):
            if not raw:
                return None

            try:
                import json

                parsed = json.loads(raw)

                result = json.dumps(
                    redact_json(parsed),
                    ensure_ascii=False,
                    indent=2,
                )
            except Exception:
                result = raw

            if len(result) > limit:
                result = (
                    result[:limit]
                    + "\n...<truncated>"
                )

            return result

        # Не отдаём модели Cookie/Authorization headers.
        allowed_request_headers = (
            "accept",
            "content-type",
            "origin",
        )

        allowed_response_headers = (
            "content-type",
            "content-length",
        )

        try:
            request_headers_raw = request.all_headers()
        except Exception:
            request_headers_raw = {}

        try:
            response_headers_raw = response.all_headers()
        except Exception:
            response_headers_raw = {}

        request_headers = {
            key: value
            for key, value in request_headers_raw.items()
            if key.lower() in allowed_request_headers
        }

        response_headers = {
            key: value
            for key, value in response_headers_raw.items()
            if key.lower() in allowed_response_headers
        }

        try:
            request_body = request.post_data
        except Exception:
            request_body = None

        content_type = (
            response_headers_raw.get(
                "content-type",
                ""
            ).lower()
        )

        response_body = None
        response_body_note = None

        text_types = (
            "json",
            "text/",
            "javascript",
            "xml",
            "x-www-form-urlencoded",
        )

        if any(
            marker in content_type
            for marker in text_types
        ):
            try:
                response_body = response.text()
            except Exception as exc:
                response_body_note = str(exc)
        else:
            response_body_note = (
                "Body not read: non-text content type"
            )

        return {
            "request_id": request_id,
            "session_id": item.get(
                "session_id"
            ),
            "action_execution_id": item.get(
                "action_execution_id"
            ),
            "method": request.method,
            "url": safe_url,
            "resource_type": request.resource_type,
            "status": response.status,
            "request_headers": request_headers,
            "request_body": safe_body(request_body),
            "response_headers": response_headers,
            "response_body": safe_body(response_body),
            "response_body_note": response_body_note,
        }

    def get_state(self):
        self._ensure_started()
        self._reset_diagnostics()
        return self._capture_state("state")

    def fill_semantic(
        self,
        field: str,
        text: str,
        exact: bool = True,
    ):
        self._ensure_started()
        self._reset_diagnostics()

        def visible_matches(locator):
            result = []

            for i in range(min(locator.count(), 50)):
                candidate = locator.nth(i)

                try:
                    if candidate.is_visible():
                        result.append(candidate)
                except Exception:
                    continue

            return result

        # Сначала ищем по accessibility role + name.
        for role in [
            "searchbox",
            "textbox",
            "combobox",
            "spinbutton",
        ]:
            locator = self.page.get_by_role(
                role,
                name=field,
                exact=exact,
            )

            matches = visible_matches(locator)

            if len(matches) == 1:
                target = matches[0]
                strategy = f"role:{role}"
                break

            if len(matches) > 1:
                return {
                    "error": (
                        f'Ambiguous field: {field}. '
                        f'role={role}, matches={len(matches)}'
                    ),
                    "field": field,
                    "matches": len(matches),
                }
        else:
            target = None
            strategy = None

        # Потом label.
        if target is None:
            locator = self.page.get_by_label(
                field,
                exact=exact,
            )

            matches = visible_matches(locator)

            if len(matches) == 1:
                target = matches[0]
                strategy = "label"

            elif len(matches) > 1:
                return {
                    "error": (
                        f'Ambiguous field label: {field}. '
                        f'Matches: {len(matches)}'
                    ),
                    "field": field,
                    "matches": len(matches),
                }

        # Затем nearby visible label для UI без for/id или ARIA.
        if target is None:
            matches = self._visible_nearby_labeled_field_matches(
                field,
                exact,
            )

            if len(matches) == 1:
                target = matches[0]
                strategy = "nearby-visible-label"

            elif len(matches) > 1:
                return {
                    "error": (
                        f'Ambiguous nearby field label: {field}. '
                        f'Matches: {len(matches)}'
                    ),
                    "field": field,
                    "matches": len(matches),
                }

        # Потом placeholder.
        if target is None:
            locator = self.page.get_by_placeholder(
                field,
                exact=exact,
            )

            matches = visible_matches(locator)

            if len(matches) == 1:
                target = matches[0]
                strategy = "placeholder"

            elif len(matches) > 1:
                return {
                    "error": (
                        f'Ambiguous placeholder: {field}. '
                        f'Matches: {len(matches)}'
                    ),
                    "field": field,
                    "matches": len(matches),
                }

        # Последний fallback — HTML metadata:
        # name / placeholder / aria-label.
        if target is None:
            controls = self.page.locator(
                "input, textarea, select"
            )

            matches = []

            for i in range(min(controls.count(), 100)):
                candidate = controls.nth(i)

                try:
                    if not candidate.is_visible():
                        continue

                    values = [
                        candidate.get_attribute("name") or "",
                        candidate.get_attribute("placeholder") or "",
                        candidate.get_attribute("aria-label") or "",
                    ]

                    matched = _field_metadata_matches(
                        values,
                        field,
                        exact,
                    )

                    if matched:
                        matches.append(candidate)

                except Exception:
                    continue

            if len(matches) == 1:
                target = matches[0]
                strategy = "html-metadata"

            elif len(matches) > 1:
                return {
                    "error": (
                        f'Ambiguous HTML field: {field}. '
                        f'Matches: {len(matches)}'
                    ),
                    "field": field,
                    "matches": len(matches),
                }

        if target is None:
            available_fields = []

            controls = self.page.locator(
                "input, textarea, select"
            )

            for i in range(min(controls.count(), 50)):
                candidate = controls.nth(i)

                try:
                    if not candidate.is_visible():
                        continue

                    available_fields.append(
                        {
                            "tag": candidate.evaluate(
                                "el => el.tagName.toLowerCase()"
                            ),
                            "type": (
                                candidate.get_attribute("type")
                                or ""
                            ),
                            "name": (
                                candidate.get_attribute("name")
                                or ""
                            ),
                            "placeholder": (
                                candidate.get_attribute(
                                    "placeholder"
                                )
                                or ""
                            ),
                            "aria_label": (
                                candidate.get_attribute(
                                    "aria-label"
                                )
                                or ""
                            ),
                        }
                    )
                except Exception:
                    continue

            return {
                "error": f'Field not found: {field}',
                "field": field,
                "available_fields": available_fields,
            }

        input_type = (
            target.get_attribute("type") or ""
        ).lower()

        if input_type == "password":
            return {
                "error": (
                    "Refusing semantic fill: "
                    "password fields are secret"
                ),
                "field": field,
            }

        # Всё, что происходило во время поиска
        # элемента, к самому UI-действию не относим.
        self._reset_diagnostics()

        self._begin_action_execution()

        target.fill(text)

        # Даём SPA/фильтру время обработать input.
        self.page.wait_for_timeout(1000)

        result = self._capture_state(
            "fill-semantic"
        )

        result["filled_field"] = field
        result["fill_strategy"] = strategy
        result["post_action_wait_ms"] = 1000

        result = self._finish_action_execution(
            result
        )

        return result

    def delete_json_resource(
        self,
        collection_endpoint: str,
        exact_name: str,
        mutation_method: str = "DELETE",
        operation_suffix: str = None,
    ):
        """Delete one exact JSON collection member using its observed endpoint."""
        self._ensure_started()

        endpoint = str(collection_endpoint or "").strip()
        wanted = str(exact_name or "").strip()
        method = str(mutation_method or "").strip().upper()
        suffix = str(operation_suffix or "").strip()

        if not endpoint.startswith("/") or endpoint.startswith("//"):
            return {
                "error": "invalid_collection_endpoint",
                "status": "error",
                "executed": False,
            }

        if not wanted:
            return {
                "error": "exact_name_required",
                "status": "error",
                "executed": False,
            }

        if method not in {"DELETE", "POST"}:
            return {
                "error": "unsupported_json_cleanup_method",
                "status": "error",
                "executed": False,
            }

        if suffix and not re.fullmatch(r"[A-Za-z0-9_-]+", suffix):
            return {
                "error": "invalid_json_cleanup_suffix",
                "status": "error",
                "executed": False,
            }

        current = urlsplit(self.page.url)
        collection_url = (
            f"{current.scheme}://{current.netloc}{endpoint}"
        )
        self._reset_diagnostics()
        self._begin_action_execution()

        script = """
        async ({collectionUrl, exactName, mutationMethod, operationSuffix}) => {
            const findMatches = (payload) => {
                const matches = [];
                const queue = [payload];
                while (queue.length && matches.length < 20) {
                    const value = queue.shift();
                    if (Array.isArray(value)) {
                        queue.push(...value);
                        continue;
                    }
                    if (!value || typeof value !== 'object') continue;
                    const scalarValues = Object.values(value).filter(
                        (item) => ['string', 'number'].includes(typeof item)
                    );
                    if (scalarValues.some((item) => String(item) === exactName)) {
                        matches.push(value);
                    } else {
                        queue.push(...Object.values(value));
                    }
                }
                return matches;
            };
            const identifierFor = (item) => {
                for (const key of ['id', 'uid', 'uuid', 'external_id']) {
                    if (item[key] !== undefined && item[key] !== null && String(item[key]).trim()) {
                        return {key, value: String(item[key]).trim()};
                    }
                }
                return null;
            };
            const readCollection = async () => {
                const response = await fetch(collectionUrl, {
                    method: 'GET',
                    credentials: 'include',
                    headers: {Accept: 'application/json'},
                });
                let payload = null;
                try { payload = await response.json(); } catch (_) {}
                const matches = payload === null ? [] : findMatches(payload);
                return {
                    status: response.status,
                    matches,
                    identifiers: matches.map(identifierFor),
                };
            };
            const before = await readCollection();
            if (before.status < 200 || before.status >= 300) {
                return {phase: 'preflight', preflight_status: before.status};
            }
            if (before.matches.length !== 1 || !before.identifiers[0]) {
                return {
                    phase: 'preflight',
                    preflight_status: before.status,
                    exact_match_count: before.matches.length,
                    identifier_count: before.identifiers.filter(Boolean).length,
                };
            }
            const identifier = before.identifiers[0];
            const parsedMemberUrl = new URL(collectionUrl);
            parsedMemberUrl.pathname =
                parsedMemberUrl.pathname.replace(/\/+$/, '') +
                '/' + encodeURIComponent(identifier.value);
            if (operationSuffix) {
                parsedMemberUrl.pathname += '/' + operationSuffix;
            }
            parsedMemberUrl.search = '';
            const memberUrl = parsedMemberUrl.toString();
            const deletion = await fetch(memberUrl, {
                method: mutationMethod,
                credentials: 'include',
                headers: {Accept: 'application/json'},
            });
            const after = await readCollection();
            return {
                phase: 'complete',
                preflight_status: before.status,
                exact_match_count: before.matches.length,
                identifier_key: identifier.key,
                identifier_value: identifier.value,
                member_url: memberUrl,
                mutation_method: mutationMethod,
                operation_suffix: operationSuffix || null,
                mutation_status: deletion.status,
                post_delete_status: after.status,
                post_delete_match_count: after.matches.length,
            };
        }
        """

        try:
            raw = self.page.evaluate(
                script,
                {
                    "collectionUrl": collection_url,
                    "exactName": wanted,
                    "mutationMethod": method,
                    "operationSuffix": suffix,
                },
            )
        except Exception as exc:
            self.active_action_execution_id = None
            return {
                "error": "json_resource_delete_failed",
                "status": "error",
                "executed": False,
                "reason": type(exc).__name__,
            }

        if raw.get("phase") == "preflight" and raw.get("exact_match_count") == 1:
            self.active_action_execution_id = None
            return {
                "error": "json_resource_identifier_missing",
                "status": "error",
                "executed": False,
                **raw,
            }

        self.page.wait_for_timeout(500)
        result = self._capture_state("delete-json-resource")
        result.update(raw)
        result["collection_endpoint"] = self._safe_network_url(collection_url)
        if raw.get("member_url"):
            result["member_endpoint"] = self._safe_network_url(raw["member_url"])

        successful = (
            raw.get("phase") == "complete"
            and 200 <= int(raw.get("mutation_status") or 0) < 300
            and 200 <= int(raw.get("post_delete_status") or 0) < 300
            and raw.get("post_delete_match_count") == 0
        )
        result["executed"] = raw.get("phase") == "complete"
        result["status"] = "ok" if successful else "failed"
        if method == "DELETE":
            result["delete_status"] = raw.get("mutation_status")
        if not successful:
            result["error"] = "json_resource_delete_not_verified"

        return self._finish_action_execution(result)

    def archive_json_resource(
        self,
        collection_endpoint: str,
        exact_name: str,
    ):
        return self.delete_json_resource(
            collection_endpoint,
            exact_name,
            mutation_method="POST",
            operation_suffix="archive",
        )

    def fill(self, element_id: str, text: str):
        self._ensure_started()
        self._reset_diagnostics()

        locator = self.page.locator(
            f'[data-uqa-id="{element_id}"]'
        )

        if locator.count() != 1:
            return {
                "error": (
                    f"Element {element_id} not found "
                    f"or is not unique"
                )
            }

        locator.fill(text)

        result = self._capture_state(
            f"fill-{element_id}"
        )

        result["filled_element"] = element_id
        return result

    def click(self, element_id: str):
        self._ensure_started()
        self._reset_diagnostics()

        locator = self.page.locator(
            f'[data-uqa-id="{element_id}"]'
        )

        if locator.count() != 1:
            return {
                "error": (
                    f"Element {element_id} not found "
                    f"or is not unique"
                )
            }

        locator.click(timeout=10000)

        try:
            self.page.wait_for_load_state(
                "domcontentloaded",
                timeout=5000,
            )
        except Exception:
            pass

        self.page.wait_for_timeout(1000)

        result = self._capture_state(
            f"click-{element_id}"
        )

        result["clicked_element"] = element_id
        return result

    def inspect_semantic(
        self,
        name: str,
        exact: bool = True,
        role: str = None,
    ):
        self._ensure_started()
        self._reset_diagnostics()

        def visible_matches(locator):
            matches = []

            try:
                count = min(locator.count(), 50)
            except Exception:
                return matches

            for i in range(count):
                candidate = locator.nth(i)

                try:
                    if candidate.is_visible():
                        matches.append(candidate)
                except Exception:
                    continue

            return matches

        # ----------------------------------------------------
        # 1. Semantic roles.
        #
        # Form controls are important here:
        # textbox/searchbox/combobox were previously missing,
        # therefore inputs such as "Search by name" could not
        # be inspected.
        # ----------------------------------------------------
        supported_roles = [
            "tab",
            "button",
            "link",
            "menuitem",
            "option",
            "treeitem",
            "checkbox",
            "radio",
            "textbox",
            "searchbox",
            "combobox",
        ]

        requested_role = str(role or "").strip().casefold()

        if requested_role and requested_role not in supported_roles:
            return {
                "error": "unsupported_semantic_role",
                "name": name,
                "role": requested_role,
                "supported_roles": supported_roles,
            }

        roles = (
            [requested_role]
            if requested_role
            else supported_roles
        )

        for role in roles:
            locator = self.page.get_by_role(
                role,
                name=name,
                exact=exact,
            )

            matches = visible_matches(locator)

            if len(matches) == 1:
                target = matches[0]
                strategy = f"role:{role}"
                break

            if len(matches) > 1:
                return {
                    "error": "ambiguous_semantic_element",
                    "name": name,
                    "strategy": f"role:{role}",
                    "matches": len(matches),
                }

        else:
            target = None
            strategy = None

        if requested_role and target is None:
            matches = self._visible_explicit_role_matches(
                name,
                requested_role,
                exact,
            )

            if len(matches) == 1:
                target = matches[0]
                strategy = (
                    f"explicit_role_text:{requested_role}"
                )

            elif len(matches) > 1:
                return {
                    "error": "ambiguous_semantic_element",
                    "name": name,
                    "strategy": (
                        f"explicit_role_text:{requested_role}"
                    ),
                    "matches": len(matches),
                }

        if requested_role and target is None:
            return {
                "error": "semantic_element_not_found",
                "name": name,
                "role": requested_role,
            }

        # ----------------------------------------------------
        # 2. Explicit <label>.
        # ----------------------------------------------------
        if target is None:
            locator = self.page.get_by_label(
                name,
                exact=exact,
            )

            matches = visible_matches(locator)

            if len(matches) == 1:
                target = matches[0]
                strategy = "label"

            elif len(matches) > 1:
                return {
                    "error": "ambiguous_semantic_element",
                    "name": name,
                    "strategy": "label",
                    "matches": len(matches),
                }

        # ----------------------------------------------------
        # 3. Placeholder.
        #
        # This is the important fallback for inputs such as:
        # <input placeholder="Search by name">
        # ----------------------------------------------------
        if target is None:
            locator = self.page.get_by_placeholder(
                name,
                exact=exact,
            )

            matches = visible_matches(locator)

            if len(matches) == 1:
                target = matches[0]
                strategy = "placeholder"

            elif len(matches) > 1:
                return {
                    "error": "ambiguous_semantic_element",
                    "name": name,
                    "strategy": "placeholder",
                    "matches": len(matches),
                }

        # ----------------------------------------------------
        # 4. Exact icon hint for otherwise unnamed controls.
        # ----------------------------------------------------
        if target is None:
            matches = self._visible_icon_matches(name)

            if len(matches) == 1:
                target = matches[0]
                strategy = "icon_hint"

            elif len(matches) > 1:
                return {
                    "error": "ambiguous_semantic_icon",
                    "name": name,
                    "strategy": "icon_hint",
                    "matches": len(matches),
                }

        # ----------------------------------------------------
        # 5. Visible text fallback.
        # ----------------------------------------------------
        if target is None:
            locator = self.page.get_by_text(
                name,
                exact=exact,
            )

            matches = visible_matches(locator)

            if not matches:
                return {
                    "error": "semantic_element_not_found",
                    "name": name,
                }

            if len(matches) > 1:
                return {
                    "error": "ambiguous_visible_text",
                    "name": name,
                    "matches": len(matches),
                }

            target = matches[0]
            strategy = "text"

        try:
            visible = target.is_visible()
        except Exception:
            visible = None

        try:
            enabled = target.is_enabled()
        except Exception:
            enabled = None

        try:
            editable = target.is_editable()
        except Exception:
            editable = None

        try:
            metadata = target.evaluate(
                """
                el => {
                    const tag = (
                        el.tagName || ""
                    ).toLowerCase();

                    const role = (
                        el.getAttribute("role")
                        || ""
                    ).toLowerCase();

                    const value = (
                        "value" in el
                        ? String(el.value ?? "")
                        : ""
                    );

                    const placeholder = (
                        el.getAttribute("placeholder")
                        || ""
                    );

                    const ariaValueText = (
                        el.getAttribute(
                            "aria-valuetext"
                        )
                        || ""
                    );

                    let selectedValue = "";
                    let selectedText = "";
                    let selectionState = "unknown";
                    let selectionReason = (
                        "selection_not_provable"
                    );

                    /*
                     * Native <select> is deterministic.
                     */
                    if (tag === "select") {
                        const selected = Array.from(
                            el.selectedOptions || []
                        );

                        selectedValue = selected
                            .map(
                                option =>
                                    String(
                                        option.value ?? ""
                                    )
                            )
                            .join(",");

                        selectedText = selected
                            .map(
                                option =>
                                    (
                                        option.textContent
                                        || ""
                                    ).trim()
                            )
                            .join(", ");

                        const meaningful = (
                            selected.filter(
                                option => (
                                    !option.disabled
                                    &&
                                    String(
                                        option.value ?? ""
                                    ).trim() !== ""
                                )
                            )
                        );

                        selectionState = (
                            meaningful.length > 0
                            ? "present"
                            : "absent"
                        );

                        selectionReason = (
                            "native_select"
                        );
                    }

                    /*
                     * For a combobox/input a non-empty
                     * value proves that some value exists.
                     *
                     * Empty value does NOT universally prove
                     * absence because React/Vue controls may
                     * render selected chips elsewhere.
                     */
                    else if (
                        (
                            role === "combobox"
                            || tag === "input"
                            || tag === "textarea"
                        )
                        && value.trim() !== ""
                    ) {
                        selectedValue = value;
                        selectionState = "present";
                        selectionReason = (
                            "control_value_nonempty"
                        );
                    }

                    /*
                     * aria-valuetext is also explicit positive
                     * evidence of a represented value.
                     */
                    else if (
                        ariaValueText.trim() !== ""
                    ) {
                        selectedValue = ariaValueText;
                        selectionState = "present";
                        selectionReason = (
                            "aria_valuetext_nonempty"
                        );
                    }

                    return {
                        tag,
                        role,
                        type:
                            el.getAttribute("type")
                            || "",
                        id:
                            el.getAttribute("id")
                            || "",
                        name:
                            el.getAttribute("name")
                            || "",
                        placeholder,
                        value,
                        disabled_attribute:
                            el.hasAttribute("disabled"),
                        readonly_attribute:
                            el.hasAttribute("readonly"),
                        aria_disabled:
                            el.getAttribute(
                                "aria-disabled"
                            ),
                        aria_label:
                            el.getAttribute(
                                "aria-label"
                            ) || "",
                        aria_expanded:
                            el.getAttribute(
                                "aria-expanded"
                            ),
                        aria_controls:
                            el.getAttribute(
                                "aria-controls"
                            ) || "",
                        aria_activedescendant:
                            el.getAttribute(
                                "aria-activedescendant"
                            ) || "",
                        aria_valuetext:
                            ariaValueText,
                        selected_value:
                            selectedValue,
                        selected_text:
                            selectedText,
                        selection_state:
                            selectionState,
                        selection_reason:
                            selectionReason,
                        text:
                            (
                                el.innerText
                                || el.textContent
                                || ""
                            )
                            .trim()
                            .slice(0, 500)
                    };
                }
                """
            )
        except Exception:
            metadata = {}

        result = self._capture_state(
            "inspect-semantic"
        )

        result.update(
            {
                "semantic_name": name,
                "semantic_strategy": strategy,
                "visible": visible,
                "enabled": enabled,
                "editable": editable,
                "disabled": (
                    not enabled
                    if enabled is not None
                    else None
                ),
                "element": metadata,
                "inspection_status": "observed",
            }
        )

        return result

    def click_semantic(
        self,
        name: str,
        exact: bool = True,
        role: str = None,
        container: str = None,
    ):
        self._ensure_started()
        self._reset_diagnostics()

        supported_roles = [
            "tab",
            "button",
            "link",
            "menuitem",
            "option",
            "treeitem",
            "checkbox",
            "radio",
            "combobox",
        ]

        requested_role = str(role or "").strip().casefold()

        if requested_role and requested_role not in supported_roles:
            return {
                "error": "unsupported_semantic_role",
                "name": name,
                "role": requested_role,
                "supported_roles": supported_roles,
            }

        roles = (
            [requested_role]
            if requested_role
            else supported_roles
        )

        role_matches = []
        explicit_role_fallback = False

        def matches_container(candidate):
            wanted = re.sub(
                r"\s+",
                " ",
                str(container or "").strip(),
            ).casefold()

            if not wanted:
                return True

            try:
                return bool(candidate.evaluate(
                    """
                    (el, wanted) => {
                        const owner = el.closest(
                            'tr, [role="row"], li, [role="treeitem"]'
                        );
                        if (!owner) return false;
                        const lines = (owner.innerText || owner.textContent || '')
                            .split(/\\r?\\n/)
                            .map((value) => value.trim().replace(/\\s+/g, ' ').toLowerCase())
                            .filter(Boolean);
                        return lines.includes(wanted);
                    }
                    """,
                    wanted,
                ))
            except Exception:
                return False

        for role in roles:
            if requested_role and container and not str(name or "").strip():
                locator = self.page.get_by_role(role)
            else:
                locator = self.page.get_by_role(
                    role,
                    name=name,
                    exact=exact,
                )

            for i in range(min(locator.count(), 50)):
                candidate = locator.nth(i)

                try:
                    if candidate.is_visible():
                        role_matches.append(
                            (role, candidate)
                        )
                except Exception:
                    continue

        if requested_role and not role_matches:
            role_matches = [
                (requested_role, candidate)
                for candidate
                in self._visible_explicit_role_matches(
                    name,
                    requested_role,
                    exact,
                )
            ]
            explicit_role_fallback = bool(
                role_matches
            )

        if container:
            role_matches = [
                (matched_role, candidate)
                for matched_role, candidate in role_matches
                if matches_container(candidate)
            ]

        labeled_popup_fallback = False

        if (
            requested_role == "combobox"
            and not role_matches
        ):
            role_matches = [
                (
                    requested_role,
                    candidate,
                )
                for candidate in self._visible_labeled_popup_matches(
                    name,
                    exact,
                )
            ]
            labeled_popup_fallback = bool(role_matches)

        if len(role_matches) == 1:
            matched_role, target = role_matches[0]
            strategy = (
                "labeled_popup_control"
                if labeled_popup_fallback
                else (
                    f"explicit_role_text:{matched_role}"
                    if explicit_role_fallback
                    else f"role:{matched_role}"
                )
            )

        elif len(role_matches) > 1:
            return {
                "error": (
                    f'Ambiguous semantic element: {name}. '
                    f'Role matches: {len(role_matches)}'
                ),
                "name": name,
                "matches": [
                    role
                    for role, _ in role_matches
                ],
            }

        else:
            if requested_role:
                return {
                    "error": "semantic_element_not_found",
                    "name": name,
                    "role": requested_role,
                    "container": container,
                }

            icon_matches = self._visible_icon_matches(
                name
            )

            if len(icon_matches) == 1:
                target = icon_matches[0]
                strategy = "icon_hint"

            elif len(icon_matches) > 1:
                return {
                    "error": (
                        f'Ambiguous semantic icon: {name}. '
                        f'Matches: {len(icon_matches)}'
                    ),
                    "name": name,
                    "matches": len(icon_matches),
                    "strategy": "icon_hint",
                }

            else:
                locator = self.page.get_by_text(
                    name,
                    exact=exact,
                )

                visible = []

                for i in range(min(locator.count(), 50)):
                    candidate = locator.nth(i)

                    try:
                        if candidate.is_visible():
                            visible.append(candidate)
                    except Exception:
                        continue

                if not visible:
                    return {
                        "error": (
                            f'Visible semantic element '
                            f'not found: {name}'
                        ),
                        "name": name,
                    }

                if len(visible) > 1:
                    return {
                        "error": (
                            f'Ambiguous visible text: {name}. '
                            f'Matches: {len(visible)}'
                        ),
                        "name": name,
                        "matches": len(visible),
                    }

                target = visible[0]
                strategy = "text"

        # Всё, что происходило во время поиска
        # элемента, к самому UI-действию не относим.
        self._reset_diagnostics()

        # Disabled-элемент найден корректно, но клик по нему
        # фактически не может быть выполнен.
        if not target.is_enabled():
            result = self._capture_state(
                "click-semantic-disabled"
            )

            result["error"] = "element_disabled"
            result["semantic_name"] = name
            result["semantic_strategy"] = strategy
            result["click_status"] = "not_executed"

            return result

        self._begin_action_execution()

        try:
            target.click(timeout=10000)
        except Exception as exc:
            result = self._capture_state(
                "click-semantic-failed"
            )

            result["error"] = "click_failed"
            result["error_type"] = type(exc).__name__
            result["error_message"] = (
                str(exc).splitlines()[0][:500]
            )
            result["semantic_name"] = name
            result["semantic_strategy"] = strategy
            result["click_status"] = "failed"

            return self._finish_action_execution(
                result
            )

        try:
            self.page.wait_for_load_state(
                "domcontentloaded",
                timeout=5000,
            )
        except Exception:
            pass

        self.page.wait_for_timeout(1000)

        result = self._capture_state(
            "click-semantic"
        )

        result["semantic_name"] = name
        result["semantic_strategy"] = strategy
        result["semantic_container"] = container
        result["click_status"] = "executed"
        result["post_action_wait_ms"] = 1000

        result = self._finish_action_execution(
            result
        )

        return result

    def context_menu_semantic(
        self,
        name: str,
        exact: bool = True,
    ):
        """Open the context menu for one exact visible semantic row/item."""
        self._ensure_started()
        self._reset_diagnostics()

        if not exact or not str(name or "").strip():
            return {
                "error": "exact_semantic_name_required",
                "status": "error",
                "executed": False,
            }

        locator = self.page.get_by_text(name, exact=True)
        visible = []

        for index in range(min(locator.count(), 50)):
            candidate = locator.nth(index)
            try:
                if candidate.is_visible():
                    visible.append(candidate)
            except Exception:
                continue

        if len(visible) != 1:
            return {
                "error": (
                    "semantic_element_not_found"
                    if not visible
                    else "ambiguous_semantic_element"
                ),
                "status": "error",
                "executed": False,
                "name": name,
                "matches": len(visible),
            }

        target = visible[0]
        row = target.locator("xpath=ancestor::tr[1]")
        if row.count() == 1 and row.is_visible():
            target = row
            strategy = "exact_text_table_row"
        else:
            strategy = "exact_text"

        self._reset_diagnostics()
        self._begin_action_execution()

        try:
            target.click(button="right", timeout=10000)
        except Exception as exc:
            result = self._capture_state("context-menu-semantic-failed")
            result.update({
                "error": "context_menu_failed",
                "error_type": type(exc).__name__,
                "executed": False,
                "semantic_name": name,
                "semantic_strategy": strategy,
            })
            return self._finish_action_execution(result)

        self.page.wait_for_timeout(500)
        result = self._capture_state("context-menu-semantic")
        result.update({
            "executed": True,
            "status": "ok",
            "semantic_name": name,
            "semantic_strategy": strategy,
            "context_menu_status": "opened",
            "post_action_wait_ms": 500,
        })
        return self._finish_action_execution(result)

    def click_role(
        self,
        role: str,
        name: str,
        exact: bool = True,
    ):
        self._ensure_started()
        self._reset_diagnostics()

        locator = self.page.get_by_role(
            role,
            name=name,
            exact=exact,
        )

        visible = []

        for i in range(min(locator.count(), 50)):
            candidate = locator.nth(i)

            try:
                if candidate.is_visible():
                    visible.append(candidate)
            except Exception:
                continue

        if not visible:
            return {
                "error": (
                    f'Visible element not found: '
                    f'role={role}, name={name}'
                ),
                "role": role,
                "name": name,
            }

        if len(visible) > 1:
            return {
                "error": (
                    f'Ambiguous element: role={role}, '
                    f'name={name}. Matches: {len(visible)}'
                ),
                "role": role,
                "name": name,
                "matches": len(visible),
            }

        visible[0].click(timeout=10000)

        try:
            self.page.wait_for_load_state(
                "domcontentloaded",
                timeout=5000,
            )
        except Exception:
            pass

        self.page.wait_for_timeout(1000)

        result = self._capture_state("click-role")
        result["clicked_role"] = role
        result["clicked_name"] = name

        return result

    def click_text(self, text: str, exact: bool = True):
        self._ensure_started()
        self._reset_diagnostics()

        locator = self.page.get_by_text(
            text,
            exact=exact,
        )

        visible = []

        for i in range(min(locator.count(), 50)):
            candidate = locator.nth(i)

            try:
                if candidate.is_visible():
                    visible.append(candidate)
            except Exception:
                continue

        # Если exact ничего не нашёл — один раз пробуем
        # частичное совпадение.
        if not visible and exact:
            locator = self.page.get_by_text(
                text,
                exact=False,
            )

            for i in range(min(locator.count(), 50)):
                candidate = locator.nth(i)

                try:
                    if candidate.is_visible():
                        visible.append(candidate)
                except Exception:
                    continue

        if not visible:
            return {
                "error": f'Visible text not found: {text}',
                "searched_text": text,
            }

        if len(visible) > 1:
            return {
                "error": (
                    f'Ambiguous visible text: {text}. '
                    f'Matches: {len(visible)}'
                ),
                "searched_text": text,
                "matches": len(visible),
            }

        visible[0].click(timeout=10000)

        try:
            self.page.wait_for_load_state(
                "domcontentloaded",
                timeout=5000,
            )
        except Exception:
            pass

        self.page.wait_for_timeout(1000)

        result = self._capture_state("click-text")
        result["clicked_text"] = text

        return result

    def close(self):
        try:
            if self.context is not None:
                self.context.close()
        except Exception:
            pass

        try:
            if self.browser is not None:
                self.browser.close()
        except Exception:
            pass

        try:
            if self.playwright is not None:
                self.playwright.stop()
        except Exception:
            pass

        self.page = None
        self.context = None
        self.browser = None
        self.playwright = None


_session = BrowserSession()


def open_page(url: str) -> dict:
    return _session.open_page(url)


def get_state() -> dict:
    return _session.get_state()


def get_network_detail(request_id: str) -> dict:
    return _session.get_network_detail(request_id)


def delete_json_resource(
    collection_endpoint: str,
    exact_name: str,
) -> dict:
    return _session.delete_json_resource(
        collection_endpoint,
        exact_name,
    )


def archive_json_resource(
    collection_endpoint: str,
    exact_name: str,
) -> dict:
    return _session.archive_json_resource(
        collection_endpoint,
        exact_name,
    )


def authenticate_saved_stand(stand: str = None) -> dict:
    return _session.authenticate_saved_stand(stand)


def fill_semantic(
    field: str,
    text: str,
    exact: bool = True,
) -> dict:
    return _session.fill_semantic(
        field,
        text,
        exact,
    )


def fill(element_id: str, text: str) -> dict:
    return _session.fill(element_id, text)


def click(element_id: str) -> dict:
    return _session.click(element_id)


def click_semantic(
    name: str,
    exact: bool = True,
    role: str = None,
    container: str = None,
) -> dict:
    return _session.click_semantic(
        name,
        exact,
        role,
        container,
    )


def context_menu_semantic(
    name: str,
    exact: bool = True,
) -> dict:
    return _session.context_menu_semantic(
        name,
        exact,
    )



def click_role(
    role: str,
    name: str,
    exact: bool = True,
) -> dict:
    return _session.click_role(role, name, exact)


def click_text(text: str, exact: bool = True) -> dict:
    return _session.click_text(text, exact)


def inspect_semantic(
    name: str,
    exact: bool = True,
    role: str = None,
) -> dict:
    return _session.inspect_semantic(
        name,
        exact,
        role,
    )


def reset_case_context() -> dict:
    return _session.reset_case_context()


def close_browser_session():
    _session.close()


atexit.register(close_browser_session)

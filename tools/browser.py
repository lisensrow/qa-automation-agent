import atexit
import hashlib
import json
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
        matching_labels = []
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

                matching_labels.append(label)

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

        if matches or not matching_labels:
            return matches

        # A form can render labels and controls in separate sibling branches,
        # leaving their first shared ancestor as the whole form.  In that case
        # use layout only as a final, bounded fallback: the control must be
        # below (or level with) the label, horizontally overlap it, and be
        # clearly closer than any alternative.
        controls = self.page.locator(editable_selector)
        visible_controls = []

        try:
            for control_index in range(min(controls.count(), 100)):
                control = controls.nth(control_index)

                if not control.is_visible():
                    continue

                box = control.bounding_box()

                if box:
                    visible_controls.append((control, box))
        except Exception:
            return matches

        for label in matching_labels:
            try:
                label_box = label.bounding_box()

                if not label_box:
                    continue

                label_bottom = label_box["y"] + label_box["height"]
                label_left = label_box["x"]
                label_right = label_left + label_box["width"]
                candidates = []

                for control, control_box in visible_controls:
                    control_top = control_box["y"]
                    control_left = control_box["x"]
                    control_right = control_left + control_box["width"]
                    vertical_gap = control_top - label_bottom
                    horizontal_overlap = (
                        min(label_right, control_right)
                        - max(label_left, control_left)
                    )

                    if vertical_gap < -4 or vertical_gap > 140:
                        continue

                    if horizontal_overlap <= 0:
                        continue

                    score = (
                        max(vertical_gap, 0)
                        + abs(control_left - label_left) * 0.02
                    )
                    candidates.append((score, control))

                candidates.sort(key=lambda item: item[0])

                if not candidates:
                    continue

                if (
                    len(candidates) > 1
                    and abs(candidates[1][0] - candidates[0][0]) <= 4
                ):
                    continue

                control = candidates[0][1]
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

    def probe_capabilities(self):
        """Inspect generic UI contracts without interacting with the page."""
        self._ensure_started()
        self._reset_diagnostics()
        raw = self.page.evaluate(
            """
            () => {
                const visible = el => {
                    const style = window.getComputedStyle(el);
                    const box = el.getBoundingClientRect();
                    return !el.hidden
                        && style.display !== 'none'
                        && style.visibility !== 'hidden'
                        && box.width > 0
                        && box.height > 0;
                };
                const accessibleName = el => {
                    const labels = el.labels
                        ? Array.from(el.labels)
                            .map(label => label.innerText || label.textContent || '')
                        : [];
                    return (
                        el.getAttribute('aria-label')
                        || el.getAttribute('title')
                        || labels.join(' ')
                        || el.innerText
                        || el.textContent
                        || el.getAttribute('placeholder')
                        || ''
                    ).trim();
                };
                const countVisible = selector => Array.from(
                    document.querySelectorAll(selector)
                ).filter(visible).length;
                const interactive = Array.from(document.querySelectorAll(
                    'button, a[href], input:not([type="hidden"]), select, textarea, '
                    + '[contenteditable="true"], [role="button"], [role="link"], '
                    + '[role="textbox"], [role="searchbox"], [role="combobox"], '
                    + '[role="checkbox"], [role="radio"], [role="switch"], '
                    + '[role="tab"], [role="menuitem"], [role="treeitem"], '
                    + '[role="slider"], [role="option"]'
                )).filter(visible);
                const named = interactive.filter(el => accessibleName(el));
                const shadowRoots = Array.from(
                    document.querySelectorAll('*')
                ).filter(el => Boolean(el.shadowRoot)).length;
                return {
                    counts: {
                        visible_interactive: interactive.length,
                        named_interactive: named.length,
                        native_tables: countVisible('table'),
                        aria_grids: countVisible('[role="grid"], [role="treegrid"]'),
                        native_selects: countVisible('select:not([multiple])'),
                        native_multiselects: countVisible('select[multiple]'),
                        aria_comboboxes: countVisible('[role="combobox"]'),
                        aria_listboxes: countVisible('[role="listbox"]'),
                        aria_multiselects: countVisible(
                            '[role="listbox"][aria-multiselectable="true"]'
                        ),
                        aria_multiselects: countVisible(
                            '[role="listbox"][aria-multiselectable="true"]'
                        ),
                        checkboxes: countVisible('input[type="checkbox"], [role="checkbox"]'),
                        radios: countVisible('input[type="radio"], [role="radio"]'),
                        switches: countVisible('[role="switch"]'),
                        sliders: countVisible('input[type="range"], [role="slider"]'),
                        trees: countVisible('[role="tree"], [role="treegrid"]'),
                        dialogs: countVisible('dialog, [role="dialog"], [role="alertdialog"]'),
                        date_inputs: countVisible('input[type="date"], input[type="datetime-local"], input[type="time"]'),
                        file_inputs: countVisible('input[type="file"]'),
                        contenteditables: countVisible('[contenteditable="true"]'),
                        canvases: countVisible('canvas'),
                        open_shadow_roots: shadowRoots
                    },
                    document: {
                        lang: document.documentElement.lang || '',
                        title: document.title || ''
                    }
                };
            }
            """
        )
        counts = raw.get("counts") or {}
        visible_count = int(counts.get("visible_interactive") or 0)
        named_count = int(counts.get("named_interactive") or 0)
        coverage = (
            round(named_count / visible_count, 3)
            if visible_count
            else 1.0
        )
        coverage_bucket = (
            "high"
            if coverage >= 0.85
            else "medium"
            if coverage >= 0.5
            else "low"
        )
        adapters = {
            "table": [
                name
                for name, available in (
                    ("html_table", counts.get("native_tables")),
                    ("aria_grid", counts.get("aria_grids")),
                )
                if available
            ],
            "selection": [
                name
                for name, available in (
                    ("native_select", counts.get("native_selects")),
                    ("native_multiselect", counts.get("native_multiselects")),
                    ("aria_combobox", counts.get("aria_comboboxes")),
                    ("aria_listbox", counts.get("aria_listboxes")),
                    ("aria_multiselect", counts.get("aria_multiselects")),
                    ("aria_multiselect", counts.get("aria_multiselects")),
                )
                if available
            ],
            "form": [
                name
                for name, available in (
                    ("checkbox", counts.get("checkboxes")),
                    ("radio", counts.get("radios")),
                    ("switch", counts.get("switches")),
                    ("slider", counts.get("sliders")),
                    ("native_date_time", counts.get("date_inputs")),
                    ("file_input", counts.get("file_inputs")),
                    ("contenteditable", counts.get("contenteditables")),
                )
                if available
            ],
            "structure": [
                name
                for name, available in (
                    ("tree", counts.get("trees")),
                    ("dialog", counts.get("dialogs")),
                    ("open_shadow_dom", counts.get("open_shadow_roots")),
                    ("canvas", counts.get("canvases")),
                )
                if available
            ],
        }
        capability_gaps = []
        if (
            counts.get("canvases")
            and visible_count == 0
        ):
            capability_gaps.append("canvas_only_ui")
        if visible_count >= 4 and coverage_bucket == "low":
            capability_gaps.append("low_semantic_name_coverage")

        feature_flags = {
            key: bool(value)
            for key, value in counts.items()
            if key not in {
                "visible_interactive",
                "named_interactive",
            }
        }
        contract = {
            "schema_version": 1,
            "adapters": adapters,
            "feature_flags": feature_flags,
            "semantic_name_coverage_bucket": coverage_bucket,
        }
        fingerprint = hashlib.sha256(
            json.dumps(
                contract,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()
        safe_url = self._safe_network_url(self.page.url)
        parsed = urlsplit(safe_url)
        normalized_segments = []
        for segment in parsed.path.split("/"):
            if (
                re.fullmatch(r"\d+", segment)
                or re.fullmatch(
                    r"[0-9a-f]{8}-[0-9a-f-]{20,}",
                    segment,
                    flags=re.IGNORECASE,
                )
            ):
                normalized_segments.append("{id}")
            else:
                normalized_segments.append(segment)
        normalized_path = "/".join(normalized_segments) or "/"
        page_key = (
            f"{parsed.scheme}://{parsed.netloc}{normalized_path}"
            if parsed.scheme and parsed.netloc
            else normalized_path
        )

        result = self._capture_state("probe-capabilities")
        result.update(
            {
                "compatibility_probe_status": "observed",
                "compatibility_status": (
                    "incompatible"
                    if capability_gaps
                    else "compatible"
                ),
                "contract_schema_version": 1,
                "contract_fingerprint": fingerprint,
                "page_contract_key": page_key,
                "capability_contract": contract,
                "capability_counts": counts,
                "semantic_name_coverage": coverage,
                "recommended_adapters": adapters,
                "capability_gaps": capability_gaps,
                "document_language": (
                    raw.get("document") or {}
                ).get("lang") or None,
                "mutation_executed": False,
            }
        )
        return result

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

    def select_semantic(
        self,
        field: str,
        option: str,
        exact: bool = True,
    ):
        """Select one exact option from a native or ARIA combobox."""
        self._ensure_started()
        self._reset_diagnostics()

        def visible_matches(locator, limit=50):
            matches = []
            for index in range(min(locator.count(), limit)):
                candidate = locator.nth(index)
                try:
                    if candidate.is_visible():
                        matches.append(candidate)
                except Exception:
                    continue
            return matches

        target = None
        strategy = None

        for locator, candidate_strategy in (
            (
                self.page.get_by_role(
                    "combobox",
                    name=field,
                    exact=exact,
                ),
                "role:combobox",
            ),
            (
                self.page.get_by_label(field, exact=exact),
                "label",
            ),
        ):
            matches = visible_matches(locator)
            if len(matches) == 1:
                target = matches[0]
                strategy = candidate_strategy
                break
            if len(matches) > 1:
                return {
                    "error": "ambiguous_select_field",
                    "field": field,
                    "matches": len(matches),
                    "executed": False,
                }

        if target is None:
            matches = self._visible_nearby_labeled_field_matches(
                field,
                exact,
            )
            matches = [
                item
                for item in matches
                if (
                    item.evaluate("el => el.tagName.toLowerCase()")
                    == "select"
                    or (item.get_attribute("role") or "").casefold()
                    == "combobox"
                )
            ]
            if len(matches) == 1:
                target = matches[0]
                strategy = "nearby-visible-label"
            elif len(matches) > 1:
                return {
                    "error": "ambiguous_select_field",
                    "field": field,
                    "matches": len(matches),
                    "executed": False,
                }

        if target is None:
            controls = self.page.locator("select, [role='combobox']")
            matches = []
            for index in range(min(controls.count(), 100)):
                candidate = controls.nth(index)
                try:
                    if not candidate.is_visible():
                        continue
                    values = [
                        candidate.get_attribute("name") or "",
                        candidate.get_attribute("aria-label") or "",
                        candidate.get_attribute("placeholder") or "",
                    ]
                    if _field_metadata_matches(values, field, exact):
                        matches.append(candidate)
                except Exception:
                    continue
            if len(matches) == 1:
                target = matches[0]
                strategy = "html-metadata"
            elif len(matches) > 1:
                return {
                    "error": "ambiguous_select_field",
                    "field": field,
                    "matches": len(matches),
                    "executed": False,
                }

        if target is None:
            return {
                "error": "select_field_not_found",
                "field": field,
                "executed": False,
            }

        tag = target.evaluate("el => el.tagName.toLowerCase()")
        wanted = str(option or "").strip()
        if not wanted:
            return {
                "error": "select_option_required",
                "field": field,
                "executed": False,
            }

        self._reset_diagnostics()

        if tag == "select":
            options = target.locator("option")
            option_matches = []
            for index in range(min(options.count(), 500)):
                candidate = options.nth(index)
                label = (candidate.inner_text() or "").strip()
                matched = (
                    label.casefold() == wanted.casefold()
                    if exact
                    else wanted.casefold() in label.casefold()
                )
                if matched:
                    option_matches.append(
                        {
                            "label": label,
                            "value": candidate.get_attribute("value"),
                        }
                    )
            if len(option_matches) != 1:
                return {
                    "error": (
                        "select_option_not_found"
                        if not option_matches
                        else "ambiguous_select_option"
                    ),
                    "field": field,
                    "option": option,
                    "matches": len(option_matches),
                    "executed": False,
                }
            selected = option_matches[0]
            current_label = target.evaluate(
                """
                el => (el.selectedOptions[0]?.textContent || '').trim()
                """
            )
            if current_label.casefold() == selected["label"].casefold():
                result = self._capture_state("select-semantic")
                result.update(
                    {
                        "selected_field": field,
                        "selected_option": option,
                        "selected_value": target.input_value(),
                        "selected_text": current_label,
                        "selection_strategy": "native-select",
                        "field_match_strategy": strategy,
                        "selection_status": "already_satisfied",
                        "mutation_executed": False,
                    }
                )
                return result
            self._begin_action_execution()
            target.select_option(label=selected["label"])
            selection_strategy = "native-select"
        else:
            target.click()
            self.page.wait_for_timeout(300)
            autocomplete_typed = False

            def visible_option_matches():
                return visible_matches(
                    self.page.get_by_role(
                        "option",
                        name=option,
                        exact=exact,
                    ),
                    100,
                )

            option_matches = visible_option_matches()
            if not option_matches and tag == "input":
                self._begin_action_execution()
                target.fill(wanted)
                autocomplete_typed = True
                self.page.wait_for_timeout(500)
                option_matches = visible_option_matches()

            if len(option_matches) != 1:
                error_result = {
                    "error": (
                        "select_option_not_found"
                        if not option_matches
                        else "ambiguous_select_option"
                    ),
                    "field": field,
                    "option": option,
                    "matches": len(option_matches),
                    "executed": autocomplete_typed,
                    "mutation_executed": autocomplete_typed,
                }
                if autocomplete_typed:
                    error_result.update(
                        self._capture_state("select-semantic-error")
                    )
                    return self._finish_action_execution(error_result)
                return error_result
            if not autocomplete_typed:
                self._begin_action_execution()
            option_matches[0].click()
            selection_strategy = (
                "aria-autocomplete-option"
                if autocomplete_typed
                else "aria-option"
            )

        self.page.wait_for_timeout(500)
        selected_value = target.input_value() if tag == "select" else None
        selected_text = target.evaluate(
            """
            el => el.tagName.toLowerCase() === 'select'
                ? (el.selectedOptions[0]?.textContent || '').trim()
                : (
                    el.getAttribute('aria-valuetext')
                    || el.getAttribute('aria-label')
                    || el.textContent
                    || ''
                ).trim()
            """
        )
        result = self._capture_state("select-semantic")
        result.update(
            {
                "selected_field": field,
                "selected_option": option,
                "selected_value": selected_value,
                "selected_text": selected_text,
                "selection_strategy": selection_strategy,
                "field_match_strategy": strategy,
                "selection_status": "selected",
                "mutation_executed": True,
                "post_action_wait_ms": 500,
            }
        )
        return self._finish_action_execution(result)

    def set_checked_semantic(
        self,
        field: str,
        checked: bool,
        exact: bool = True,
    ):
        """Set a checkbox or switch to the requested state idempotently."""
        self._ensure_started()
        self._reset_diagnostics()

        def visible_matches(locator):
            matches = []
            for index in range(min(locator.count(), 50)):
                candidate = locator.nth(index)
                try:
                    if candidate.is_visible():
                        matches.append(candidate)
                except Exception:
                    continue
            return matches

        target = None
        strategy = None
        for role in ("checkbox", "switch"):
            matches = visible_matches(
                self.page.get_by_role(
                    role,
                    name=field,
                    exact=exact,
                )
            )
            if len(matches) == 1:
                target = matches[0]
                strategy = f"role:{role}"
                break
            if len(matches) > 1:
                return {
                    "error": "ambiguous_checkable_field",
                    "field": field,
                    "matches": len(matches),
                    "executed": False,
                }

        if target is None:
            matches = visible_matches(
                self.page.get_by_label(field, exact=exact)
            )
            matches = [
                item
                for item in matches
                if (
                    (item.get_attribute("type") or "").casefold()
                    == "checkbox"
                    or (item.get_attribute("role") or "").casefold()
                    in {"checkbox", "switch"}
                )
            ]
            if len(matches) == 1:
                target = matches[0]
                strategy = "label"
            elif len(matches) > 1:
                return {
                    "error": "ambiguous_checkable_field",
                    "field": field,
                    "matches": len(matches),
                    "executed": False,
                }

        if target is None:
            return {
                "error": "checkable_field_not_found",
                "field": field,
                "executed": False,
            }

        def current_state():
            try:
                return bool(target.is_checked())
            except Exception:
                value = str(target.get_attribute("aria-checked") or "")
                if value.casefold() in {"true", "false"}:
                    return value.casefold() == "true"
                return None

        desired = bool(checked)
        previous = current_state()
        if previous is None:
            return {
                "error": "checkable_state_unavailable",
                "field": field,
                "executed": False,
            }

        if previous == desired:
            result = self._capture_state("set-checked-semantic")
            result.update(
                {
                    "checked_field": field,
                    "previous_checked": previous,
                    "checked": previous,
                    "check_status": "already_satisfied",
                    "field_match_strategy": strategy,
                    "mutation_executed": False,
                }
            )
            return result

        self._reset_diagnostics()
        self._begin_action_execution()
        target.click()
        self.page.wait_for_timeout(300)
        actual = current_state()
        result = self._capture_state("set-checked-semantic")
        result.update(
            {
                "checked_field": field,
                "previous_checked": previous,
                "checked": actual,
                "check_status": (
                    "set" if actual == desired else "not_applied"
                ),
                "field_match_strategy": strategy,
                "mutation_executed": True,
                "post_action_wait_ms": 300,
            }
        )
        result = self._finish_action_execution(result)
        if actual != desired:
            result["error"] = "checked_state_not_applied"
        return result

    def choose_radio_semantic(
        self,
        option: str,
        group: str = None,
        exact: bool = True,
    ):
        """Choose one radio option, optionally within one named group."""
        self._ensure_started()
        self._reset_diagnostics()

        def visible_matches(locator, limit=100):
            matches = []
            for index in range(min(locator.count(), limit)):
                candidate = locator.nth(index)
                try:
                    if candidate.is_visible():
                        matches.append(candidate)
                except Exception:
                    continue
            return matches

        scope = self.page
        group_strategy = None
        wanted_group = str(group or "").strip()

        if wanted_group:
            group_matches = []
            for role in ("radiogroup", "group"):
                matches = visible_matches(
                    self.page.get_by_role(
                        role,
                        name=wanted_group,
                        exact=exact,
                    )
                )
                if matches:
                    group_matches.extend(matches)
                    group_strategy = f"role:{role}"
                    break

            if not group_matches:
                fieldsets = self.page.locator("fieldset")
                for index in range(min(fieldsets.count(), 100)):
                    fieldset = fieldsets.nth(index)
                    try:
                        if not fieldset.is_visible():
                            continue
                        legend = fieldset.locator("legend").first
                        if not legend.is_visible():
                            continue
                        label = (legend.inner_text() or "").strip()
                        matched = (
                            label.casefold() == wanted_group.casefold()
                            if exact
                            else wanted_group.casefold() in label.casefold()
                        )
                        if matched:
                            group_matches.append(fieldset)
                            group_strategy = "fieldset-legend"
                    except Exception:
                        continue

            if len(group_matches) != 1:
                return {
                    "error": (
                        "radio_group_not_found"
                        if not group_matches
                        else "ambiguous_radio_group"
                    ),
                    "group": group,
                    "matches": len(group_matches),
                    "executed": False,
                }
            scope = group_matches[0]

        radio_matches = visible_matches(
            scope.get_by_role(
                "radio",
                name=option,
                exact=exact,
            )
        )
        if not radio_matches and not wanted_group:
            radio_matches = [
                item
                for item in visible_matches(
                    self.page.get_by_label(option, exact=exact)
                )
                if (
                    (item.get_attribute("type") or "").casefold()
                    == "radio"
                    or (item.get_attribute("role") or "").casefold()
                    == "radio"
                )
            ]

        if len(radio_matches) != 1:
            return {
                "error": (
                    "radio_option_not_found"
                    if not radio_matches
                    else "ambiguous_radio_option"
                ),
                "group": group,
                "option": option,
                "matches": len(radio_matches),
                "executed": False,
            }

        target = radio_matches[0]
        try:
            previous = bool(target.is_checked())
        except Exception:
            previous = (
                str(target.get_attribute("aria-checked") or "").casefold()
                == "true"
            )

        if previous:
            result = self._capture_state("choose-radio-semantic")
            result.update(
                {
                    "radio_group": group,
                    "selected_option": option,
                    "radio_status": "already_satisfied",
                    "group_match_strategy": group_strategy,
                    "mutation_executed": False,
                }
            )
            return result

        self._reset_diagnostics()
        self._begin_action_execution()
        target.click()
        self.page.wait_for_timeout(300)
        try:
            selected = bool(target.is_checked())
        except Exception:
            selected = (
                str(target.get_attribute("aria-checked") or "").casefold()
                == "true"
            )
        result = self._capture_state("choose-radio-semantic")
        result.update(
            {
                "radio_group": group,
                "selected_option": option,
                "radio_status": "selected" if selected else "not_applied",
                "group_match_strategy": group_strategy,
                "mutation_executed": True,
                "post_action_wait_ms": 300,
            }
        )
        result = self._finish_action_execution(result)
        if not selected:
            result["error"] = "radio_selection_not_applied"
        return result

    def select_many_semantic(
        self,
        field: str,
        options: list,
        exact: bool = True,
    ):
        """Set the exact selection of one native HTML multiple select."""
        self._ensure_started()
        self._reset_diagnostics()
        requested = [
            str(value or "").strip()
            for value in (options or [])
            if str(value or "").strip()
        ]
        if not requested:
            return {
                "error": "multiselect_options_required",
                "field": field,
                "executed": False,
            }
        if len({value.casefold() for value in requested}) != len(requested):
            return {
                "error": "duplicate_multiselect_options",
                "field": field,
                "executed": False,
            }

        def visible_matches(locator):
            matches = []
            for index in range(min(locator.count(), 50)):
                candidate = locator.nth(index)
                try:
                    if candidate.is_visible():
                        matches.append(candidate)
                except Exception:
                    continue
            return matches

        target = None
        strategy = None
        for locator, candidate_strategy in (
            (
                self.page.get_by_role(
                    "listbox",
                    name=field,
                    exact=exact,
                ),
                "role:listbox",
            ),
            (
                self.page.get_by_label(field, exact=exact),
                "label",
            ),
        ):
            matches = [
                item
                for item in visible_matches(locator)
                if (
                    item.evaluate("el => el.tagName.toLowerCase()")
                    == "select"
                    and item.get_attribute("multiple") is not None
                )
            ]
            if len(matches) == 1:
                target = matches[0]
                strategy = candidate_strategy
                break
            if len(matches) > 1:
                return {
                    "error": "ambiguous_multiselect_field",
                    "field": field,
                    "matches": len(matches),
                    "executed": False,
                }

        if target is None:
            controls = self.page.locator("select[multiple]")
            matches = []
            for index in range(min(controls.count(), 100)):
                candidate = controls.nth(index)
                try:
                    if not candidate.is_visible():
                        continue
                    values = [
                        candidate.get_attribute("name") or "",
                        candidate.get_attribute("aria-label") or "",
                    ]
                    if _field_metadata_matches(values, field, exact):
                        matches.append(candidate)
                except Exception:
                    continue
            if len(matches) == 1:
                target = matches[0]
                strategy = "html-metadata"
            elif len(matches) > 1:
                return {
                    "error": "ambiguous_multiselect_field",
                    "field": field,
                    "matches": len(matches),
                    "executed": False,
                }

        if target is None:
            return self._select_many_aria_semantic(
                field,
                requested,
                exact,
            )

        available = []
        option_nodes = target.locator("option")
        for index in range(min(option_nodes.count(), 500)):
            candidate = option_nodes.nth(index)
            available.append((candidate.inner_text() or "").strip())

        selected_labels = []
        for requested_label in requested:
            matches = [
                label
                for label in available
                if (
                    label.casefold() == requested_label.casefold()
                    if exact
                    else requested_label.casefold() in label.casefold()
                )
            ]
            if len(matches) != 1:
                return {
                    "error": (
                        "multiselect_option_not_found"
                        if not matches
                        else "ambiguous_multiselect_option"
                    ),
                    "field": field,
                    "option": requested_label,
                    "matches": len(matches),
                    "executed": False,
                }
            selected_labels.append(matches[0])

        current = target.evaluate(
            """
            el => Array.from(el.selectedOptions)
                .map(option => (option.textContent || '').trim())
            """
        )
        if {value.casefold() for value in current} == {
            value.casefold() for value in selected_labels
        }:
            result = self._capture_state("select-many-semantic")
            result.update(
                {
                    "selected_field": field,
                    "selected_options": current,
                    "selection_status": "already_satisfied",
                    "field_match_strategy": strategy,
                    "mutation_executed": False,
                }
            )
            return result

        self._reset_diagnostics()
        self._begin_action_execution()
        target.select_option(label=selected_labels)
        self.page.wait_for_timeout(500)
        actual = target.evaluate(
            """
            el => Array.from(el.selectedOptions)
                .map(option => (option.textContent || '').trim())
            """
        )
        expected_set = {value.casefold() for value in selected_labels}
        actual_set = {value.casefold() for value in actual}
        result = self._capture_state("select-many-semantic")
        result.update(
            {
                "selected_field": field,
                "selected_options": actual,
                "selection_status": (
                    "selected" if actual_set == expected_set else "not_applied"
                ),
                "field_match_strategy": strategy,
                "mutation_executed": True,
                "post_action_wait_ms": 500,
            }
        )
        result = self._finish_action_execution(result)
        if actual_set != expected_set:
            result["error"] = "multiselect_state_not_applied"
        return result

    def _select_many_aria_semantic(
        self,
        field: str,
        requested: list,
        exact: bool = True,
    ):
        """Set the exact value set of one ARIA multi-select contract."""

        def visible_matches(locator, limit=100):
            matches = []
            for index in range(min(locator.count(), limit)):
                candidate = locator.nth(index)
                try:
                    if candidate.is_visible():
                        matches.append(candidate)
                except Exception:
                    continue
            return matches

        direct = [
            item
            for item in visible_matches(
                self.page.get_by_role(
                    "listbox",
                    name=field,
                    exact=exact,
                )
            )
            if str(
                item.get_attribute("aria-multiselectable") or ""
            ).casefold() == "true"
        ]
        if len(direct) > 1:
            return {
                "error": "ambiguous_aria_multiselect_field",
                "field": field,
                "matches": len(direct),
                "executed": False,
            }

        comboboxes = visible_matches(
            self.page.get_by_role(
                "combobox",
                name=field,
                exact=exact,
            )
        )
        if not comboboxes:
            comboboxes = [
                item
                for item in visible_matches(
                    self.page.get_by_label(field, exact=exact)
                )
                if str(
                    item.get_attribute("role") or ""
                ).casefold() == "combobox"
            ]

        if not direct and len(comboboxes) > 1:
            return {
                "error": "ambiguous_aria_multiselect_field",
                "field": field,
                "matches": len(comboboxes),
                "executed": False,
            }
        if not direct and not comboboxes:
            return {
                "error": "multiselect_field_not_found",
                "field": field,
                "executed": False,
            }

        control = comboboxes[0] if comboboxes else None
        controlled_id = (
            str(control.get_attribute("aria-controls") or "").strip()
            if control is not None
            else ""
        )

        def resolve_listbox(open_if_needed=True):
            if direct:
                return direct[0]

            candidates = []
            if controlled_id:
                controlled = self.page.locator(
                    "[id=" + json.dumps(controlled_id) + "]"
                )
                candidates = [
                    item
                    for item in visible_matches(controlled)
                    if str(item.get_attribute("role") or "").casefold()
                    == "listbox"
                ]

            if not candidates:
                candidates = visible_matches(
                    self.page.get_by_role("listbox")
                )

            if len(candidates) == 1:
                return candidates[0]
            if len(candidates) > 1:
                return None
            if not open_if_needed:
                return None

            control.click()
            self.page.wait_for_timeout(200)
            return resolve_listbox(False)

        def option_snapshot(listbox):
            values = []
            options = listbox.get_by_role("option")
            for index in range(min(options.count(), 500)):
                option = options.nth(index)
                try:
                    if not option.is_visible():
                        continue
                    label = (option.inner_text() or "").strip()
                    selected = any(
                        str(option.get_attribute(attribute) or "").casefold()
                        == "true"
                        for attribute in ("aria-selected", "aria-checked")
                    )
                    values.append((label, selected))
                except Exception:
                    continue
            return values

        listbox = resolve_listbox()
        if listbox is None:
            return {
                "error": "aria_multiselect_listbox_not_unique",
                "field": field,
                "executed": False,
            }

        initial = option_snapshot(listbox)
        available = [label for label, _selected in initial]
        resolved = []
        for requested_label in requested:
            matches = [
                label
                for label in available
                if (
                    label.casefold() == requested_label.casefold()
                    if exact
                    else requested_label.casefold() in label.casefold()
                )
            ]
            if len(matches) != 1:
                return {
                    "error": (
                        "multiselect_option_not_found"
                        if not matches
                        else "ambiguous_multiselect_option"
                    ),
                    "field": field,
                    "option": requested_label,
                    "matches": len(matches),
                    "executed": False,
                }
            resolved.append(matches[0])

        expected_set = {value.casefold() for value in resolved}
        current = [label for label, selected in initial if selected]
        current_set = {value.casefold() for value in current}
        strategy = (
            "aria-multiselectable-listbox"
            if direct
            else "aria-combobox-listbox"
        )
        if current_set == expected_set:
            result = self._capture_state("select-many-semantic")
            result.update(
                {
                    "selected_field": field,
                    "selected_options": current,
                    "selection_status": "already_satisfied",
                    "field_match_strategy": strategy,
                    "mutation_executed": False,
                }
            )
            return result

        toggles = [
            label
            for label, selected in initial
            if selected != (label.casefold() in expected_set)
        ]
        self._reset_diagnostics()
        self._begin_action_execution()
        executed_toggles = []
        mutation_error = None
        for label in toggles:
            listbox = resolve_listbox()
            if listbox is None:
                mutation_error = {
                    "error": "aria_multiselect_listbox_not_unique",
                    "option": label,
                }
                break
            candidates = visible_matches(
                listbox.get_by_role("option", name=label, exact=True)
            )
            if len(candidates) != 1:
                mutation_error = {
                    "error": "aria_multiselect_option_changed",
                    "option": label,
                    "matches": len(candidates),
                }
                break
            candidates[0].click()
            executed_toggles.append(label)
            self.page.wait_for_timeout(200)

        listbox = resolve_listbox()
        actual = (
            [
                label
                for label, selected in option_snapshot(listbox)
                if selected
            ]
            if listbox is not None
            else []
        )
        actual_set = {value.casefold() for value in actual}
        result = self._capture_state("select-many-semantic")
        result.update(
            {
                "selected_field": field,
                "selected_options": actual,
                "selection_status": (
                    "selected" if actual_set == expected_set else "not_applied"
                ),
                "field_match_strategy": strategy,
                "mutation_executed": bool(executed_toggles),
                "changed_options": executed_toggles,
                "post_action_wait_ms": 200 * len(executed_toggles),
            }
        )
        result = self._finish_action_execution(result)
        if mutation_error:
            result.update(mutation_error)
        elif actual_set != expected_set:
            result["error"] = "multiselect_state_not_applied"
        return result

    def _focused_element_summary(self):
        return self.page.evaluate(
            """
            () => {
                const el = document.activeElement;
                if (!el || el === document.body) return null;
                const labels = el.labels
                    ? Array.from(el.labels)
                        .map(label => (label.innerText || label.textContent || '').trim())
                        .filter(Boolean)
                    : [];
                const text = (el.innerText || el.textContent || '').trim();
                const name = (
                    el.getAttribute('aria-label')
                    || labels.join(' ')
                    || text
                    || el.getAttribute('placeholder')
                    || el.getAttribute('name')
                    || el.id
                    || ''
                ).trim();
                return {
                    tag: el.tagName.toLowerCase(),
                    type: el.getAttribute('type') || '',
                    role: el.getAttribute('role') || '',
                    name: name.slice(0, 300),
                    id: el.id || '',
                    aria_label: el.getAttribute('aria-label') || '',
                    disabled: el.disabled === true
                        || el.getAttribute('aria-disabled') === 'true'
                };
            }
            """
        )

    def _keyboard_target(self, name, exact=True, role=None):
        def visible_matches(locator):
            matches = []
            for index in range(min(locator.count(), 100)):
                candidate = locator.nth(index)
                try:
                    if candidate.is_visible():
                        matches.append(candidate)
                except Exception:
                    continue
            return matches

        roles = (
            [role]
            if role
            else [
                "button",
                "link",
                "textbox",
                "searchbox",
                "combobox",
                "checkbox",
                "switch",
                "radio",
                "tab",
                "menuitem",
                "treeitem",
                "listbox",
                "spinbutton",
            ]
        )
        for candidate_role in roles:
            matches = visible_matches(
                self.page.get_by_role(
                    candidate_role,
                    name=name,
                    exact=exact,
                )
            )
            if len(matches) == 1:
                return matches[0], f"role:{candidate_role}", None
            if len(matches) > 1:
                return None, None, {
                    "error": "ambiguous_keyboard_target",
                    "target": name,
                    "role": candidate_role,
                    "matches": len(matches),
                    "executed": False,
                }

        matches = visible_matches(
            self.page.get_by_label(name, exact=exact)
        )
        if len(matches) == 1:
            return matches[0], "label", None
        if len(matches) > 1:
            return None, None, {
                "error": "ambiguous_keyboard_target",
                "target": name,
                "matches": len(matches),
                "executed": False,
            }
        return None, None, {
            "error": "keyboard_target_not_found",
            "target": name,
            "role": role,
            "executed": False,
        }

    def press_key_semantic(
        self,
        key: str,
        target: str = None,
        exact: bool = True,
        role: str = None,
    ):
        """Press one policy-classified key, optionally on an exact target."""
        self._ensure_started()
        self._reset_diagnostics()
        allowed = {
            "Tab",
            "Shift+Tab",
            "Escape",
            "Enter",
            "Space",
            "ArrowUp",
            "ArrowDown",
            "ArrowLeft",
            "ArrowRight",
            "Home",
            "End",
            "PageUp",
            "PageDown",
            "Backspace",
            "Delete",
        }
        normalized = str(key or "").strip()
        canonical = next(
            (
                value
                for value in allowed
                if value.casefold() == normalized.casefold()
            ),
            None,
        )
        if canonical is None:
            return {
                "error": "unsupported_keyboard_key",
                "key": key,
                "allowed_keys": sorted(allowed),
                "executed": False,
            }

        target_strategy = None
        if target:
            locator, target_strategy, error = self._keyboard_target(
                target,
                exact,
                role,
            )
            if error:
                return error
            try:
                if not locator.is_enabled():
                    return {
                        "error": "keyboard_target_disabled",
                        "target": target,
                        "executed": False,
                    }
            except Exception:
                pass
            locator.focus()

        focus_before = self._focused_element_summary()
        if target and not focus_before:
            return {
                "error": "keyboard_target_focus_failed",
                "target": target,
                "executed": False,
            }

        self._reset_diagnostics()
        self._begin_action_execution()
        self.page.keyboard.press(canonical)
        self.page.wait_for_timeout(300)
        focus_after = self._focused_element_summary()
        result = self._capture_state("press-key-semantic")
        result.update(
            {
                "pressed_key": canonical,
                "keyboard_target": target,
                "keyboard_target_strategy": target_strategy,
                "focus_before": focus_before,
                "focus_after": focus_after,
                "keyboard_event_executed": True,
                "post_action_wait_ms": 300,
            }
        )
        return self._finish_action_execution(result)

    def check_focus_order_semantic(
        self,
        targets: list,
        exact: bool = True,
    ):
        """Verify forward Tab order for an exact list of semantic names."""
        self._ensure_started()
        self._reset_diagnostics()
        expected = [
            str(value or "").strip()
            for value in (targets or [])
            if str(value or "").strip()
        ]
        if len(expected) < 2:
            return {
                "error": "focus_order_requires_two_targets",
                "executed": False,
            }
        if len(expected) > 50:
            return {
                "error": "focus_order_too_large",
                "target_count": len(expected),
                "executed": False,
            }

        first, strategy, error = self._keyboard_target(
            expected[0],
            exact,
        )
        if error:
            return error
        first.focus()
        sequence = [self._focused_element_summary()]
        self._reset_diagnostics()
        self._begin_action_execution()

        mismatch = None
        for index, wanted in enumerate(expected[1:], start=1):
            self.page.keyboard.press("Tab")
            self.page.wait_for_timeout(100)
            actual = self._focused_element_summary()
            sequence.append(actual)
            actual_name = str((actual or {}).get("name") or "").strip()
            matched = (
                actual_name.casefold() == wanted.casefold()
                if exact
                else wanted.casefold() in actual_name.casefold()
            )
            if not matched:
                mismatch = {
                    "index": index,
                    "expected": wanted,
                    "actual": actual_name,
                }
                break

        result = self._capture_state("check-focus-order-semantic")
        result.update(
            {
                "expected_focus_order": expected,
                "observed_focus_order": sequence,
                "focus_order_status": (
                    "matched" if mismatch is None else "mismatch"
                ),
                "focus_order_mismatch": mismatch,
                "initial_target_strategy": strategy,
                "keyboard_event_executed": True,
                "mutation_executed": False,
            }
        )
        return self._finish_action_execution(result)

    def _pointer_target(self, name, exact=True, role=None):
        def visible_matches(locator):
            matches = []
            for index in range(min(locator.count(), 150)):
                candidate = locator.nth(index)
                try:
                    if candidate.is_visible():
                        matches.append(candidate)
                except Exception:
                    continue
            return matches

        roles = (
            [role]
            if role
            else [
                "button",
                "link",
                "tab",
                "menuitem",
                "treeitem",
                "listitem",
                "row",
                "columnheader",
                "rowheader",
                "gridcell",
                "option",
                "checkbox",
                "radio",
                "switch",
                "slider",
                "separator",
                "region",
                "img",
            ]
        )
        for candidate_role in roles:
            matches = visible_matches(
                self.page.get_by_role(
                    candidate_role,
                    name=name,
                    exact=exact,
                )
            )
            if len(matches) == 1:
                return matches[0], f"role:{candidate_role}", None
            if len(matches) > 1:
                return None, None, {
                    "error": "ambiguous_pointer_target",
                    "target": name,
                    "role": candidate_role,
                    "matches": len(matches),
                    "executed": False,
                }

        matches = visible_matches(
            self.page.get_by_text(name, exact=exact)
        )
        if len(matches) == 1:
            return matches[0], "visible-text", None
        if len(matches) > 1:
            return None, None, {
                "error": "ambiguous_pointer_target",
                "target": name,
                "matches": len(matches),
                "executed": False,
            }
        return None, None, {
            "error": "pointer_target_not_found",
            "target": name,
            "role": role,
            "executed": False,
        }

    def drag_semantic(
        self,
        source: str,
        target: str,
        exact: bool = True,
        source_role: str = None,
        target_role: str = None,
    ):
        """Drag one exact visible semantic source onto one exact target."""
        self._ensure_started()
        self._reset_diagnostics()
        if str(source or "").strip().casefold() == (
            str(target or "").strip().casefold()
        ):
            return {
                "error": "drag_source_equals_target",
                "source": source,
                "target": target,
                "executed": False,
            }

        source_locator, source_strategy, error = self._pointer_target(
            source,
            exact,
            source_role,
        )
        if error:
            error["drag_endpoint"] = "source"
            return error
        target_locator, target_strategy, error = self._pointer_target(
            target,
            exact,
            target_role,
        )
        if error:
            error["drag_endpoint"] = "target"
            return error

        source_before = source_locator.bounding_box()
        target_before = target_locator.bounding_box()
        if not source_before or not target_before:
            return {
                "error": "drag_bounding_box_unavailable",
                "source": source,
                "target": target,
                "executed": False,
            }

        self._reset_diagnostics()
        self._begin_action_execution()
        source_locator.drag_to(target_locator)
        self.page.wait_for_timeout(500)
        source_after = source_locator.bounding_box()
        target_after = target_locator.bounding_box()
        result = self._capture_state("drag-semantic")
        result.update(
            {
                "drag_source": source,
                "drag_target": target,
                "source_match_strategy": source_strategy,
                "target_match_strategy": target_strategy,
                "source_box_before": source_before,
                "target_box_before": target_before,
                "source_box_after": source_after,
                "target_box_after": target_after,
                "drag_status": "performed",
                "mutation_executed": True,
                "post_action_wait_ms": 500,
            }
        )
        return self._finish_action_execution(result)

    def resize_semantic(
        self,
        target: str,
        delta_x: int = 0,
        delta_y: int = 0,
        edge: str = "right",
        exact: bool = True,
        role: str = None,
    ):
        """Resize one exact target by dragging one of its visible edges."""
        self._ensure_started()
        self._reset_diagnostics()
        try:
            dx = int(delta_x)
            dy = int(delta_y)
        except (TypeError, ValueError):
            return {
                "error": "resize_delta_must_be_integer",
                "target": target,
                "executed": False,
            }
        if dx == 0 and dy == 0:
            return {
                "error": "resize_delta_required",
                "target": target,
                "executed": False,
            }
        if abs(dx) > 1000 or abs(dy) > 1000:
            return {
                "error": "resize_delta_out_of_range",
                "target": target,
                "executed": False,
            }
        canonical_edge = str(edge or "").strip().casefold()
        if canonical_edge not in {"right", "bottom", "bottom-right"}:
            return {
                "error": "unsupported_resize_edge",
                "target": target,
                "edge": edge,
                "executed": False,
            }

        locator, strategy, error = self._pointer_target(
            target,
            exact,
            role,
        )
        if error:
            return error
        before = locator.bounding_box()
        if not before:
            return {
                "error": "resize_bounding_box_unavailable",
                "target": target,
                "executed": False,
            }

        start_x = (
            before["x"] + before["width"] - 2
            if canonical_edge in {"right", "bottom-right"}
            else before["x"] + before["width"] / 2
        )
        start_y = (
            before["y"] + before["height"] - 2
            if canonical_edge in {"bottom", "bottom-right"}
            else before["y"] + before["height"] / 2
        )
        end_x = start_x + dx
        end_y = start_y + dy

        self._reset_diagnostics()
        self._begin_action_execution()
        self.page.mouse.move(start_x, start_y)
        self.page.mouse.down()
        self.page.mouse.move(end_x, end_y, steps=10)
        self.page.mouse.up()
        self.page.wait_for_timeout(500)
        after = locator.bounding_box()
        changed = bool(
            after
            and (
                abs(after["width"] - before["width"]) >= 1
                or abs(after["height"] - before["height"]) >= 1
            )
        )
        result = self._capture_state("resize-semantic")
        result.update(
            {
                "resized_target": target,
                "resize_edge": canonical_edge,
                "resize_delta_x": dx,
                "resize_delta_y": dy,
                "target_match_strategy": strategy,
                "target_box_before": before,
                "target_box_after": after,
                "resize_status": "resized" if changed else "not_observed",
                "mutation_executed": True,
                "post_action_wait_ms": 500,
            }
        )
        result = self._finish_action_execution(result)
        if not changed:
            result["error"] = "resize_not_observed"
        return result

    def _resolve_table(self, table=None, exact=True):
        candidates = (
            self.page.get_by_role("table", name=table, exact=exact)
            if table
            else self.page.locator("table")
        )
        visible = []
        for index in range(min(candidates.count(), 100)):
            candidate = candidates.nth(index)
            try:
                if candidate.is_visible():
                    visible.append(candidate)
            except Exception:
                continue
        if len(visible) == 1:
            return visible[0], None
        return None, {
            "error": (
                "table_not_found"
                if not visible
                else "ambiguous_table"
            ),
            "table": table,
            "matches": len(visible),
            "executed": False,
        }

    @staticmethod
    def _table_snapshot(table_locator):
        return table_locator.evaluate(
            """
            table => {
                const clean = value => String(value || '')
                    .replace(/\\s+/g, ' ')
                    .trim();
                const headerCells = Array.from(
                    table.querySelectorAll('thead th, thead [role="columnheader"]')
                );
                const headers = headerCells.slice(0, 50).map(cell => ({
                    name: clean(
                        cell.getAttribute('aria-label')
                        || cell.innerText
                        || cell.textContent
                    ),
                    aria_sort: cell.getAttribute('aria-sort')
                }));
                const bodyRows = Array.from(
                    table.querySelectorAll('tbody tr, [role="rowgroup"] [role="row"]')
                ).filter(row => {
                    if (row.closest('thead')) return false;
                    const style = window.getComputedStyle(row);
                    return !row.hidden
                        && style.display !== 'none'
                        && style.visibility !== 'hidden'
                        && row.getClientRects().length > 0;
                }).slice(0, 200);
                const rows = bodyRows.map(row => {
                    const cells = Array.from(
                        row.querySelectorAll(':scope > td, :scope > th, :scope > [role="cell"], :scope > [role="gridcell"]')
                    ).slice(0, 50).map(cell => clean(
                        cell.innerText || cell.textContent
                    ).slice(0, 300));
                    const valuesByHeader = {};
                    if (headers.length === cells.length) {
                        headers.forEach((header, index) => {
                            if (header.name) valuesByHeader[header.name] = cells[index];
                        });
                    }
                    return {
                        text: clean(row.innerText || row.textContent).slice(0, 1000),
                        cells,
                        values_by_header: valuesByHeader,
                        aria_selected: row.getAttribute('aria-selected')
                    };
                });
                return {
                    headers,
                    rows,
                    visible_row_count: rows.length,
                    row_signature: rows.map(row => row.cells.join('\u241f'))
                };
            }
            """
        )

    def inspect_table_semantic(
        self,
        table: str = None,
        exact: bool = True,
    ):
        """Return a bounded structured snapshot of one visible table."""
        self._ensure_started()
        self._reset_diagnostics()
        locator, error = self._resolve_table(table, exact)
        if error:
            return error
        summary = self._table_snapshot(locator)
        result = self._capture_state("inspect-table-semantic")
        result.update(
            {
                "table_name": table,
                "table_inspection_status": "observed",
                "table_summary": summary,
                "mutation_executed": False,
            }
        )
        return result

    def sort_table_semantic(
        self,
        column: str,
        direction: str,
        table: str = None,
        exact: bool = True,
    ):
        """Trigger and verify ascending or descending sort on one column."""
        self._ensure_started()
        self._reset_diagnostics()
        wanted_direction = str(direction or "").strip().casefold()
        direction_map = {
            "asc": "ascending",
            "ascending": "ascending",
            "desc": "descending",
            "descending": "descending",
        }
        wanted_sort = direction_map.get(wanted_direction)
        if not wanted_sort:
            return {
                "error": "unsupported_sort_direction",
                "direction": direction,
                "executed": False,
            }
        table_locator, error = self._resolve_table(table, exact)
        if error:
            return error

        header_locator = table_locator.get_by_role(
            "columnheader",
            name=column,
            exact=exact,
        )
        headers = []
        for index in range(min(header_locator.count(), 50)):
            candidate = header_locator.nth(index)
            if candidate.is_visible():
                headers.append(candidate)
        if len(headers) != 1:
            return {
                "error": (
                    "table_column_not_found"
                    if not headers
                    else "ambiguous_table_column"
                ),
                "table": table,
                "column": column,
                "matches": len(headers),
                "executed": False,
            }

        header = headers[0]
        before = self._table_snapshot(table_locator)
        current_sort = str(
            header.get_attribute("aria-sort") or ""
        ).strip().casefold()
        if current_sort == wanted_sort:
            result = self._capture_state("sort-table-semantic")
            result.update(
                {
                    "table_name": table,
                    "sorted_column": column,
                    "sort_direction": wanted_sort,
                    "sort_status": "already_satisfied",
                    "table_before": before,
                    "table_after": before,
                    "mutation_executed": False,
                }
            )
            return result

        self._reset_diagnostics()
        self._begin_action_execution()
        attempts = 0
        final_sort = current_sort
        while attempts < 2 and final_sort != wanted_sort:
            header.click()
            attempts += 1
            self.page.wait_for_timeout(400)
            final_sort = str(
                header.get_attribute("aria-sort") or ""
            ).strip().casefold()
            if not final_sort:
                break

        after = self._table_snapshot(table_locator)
        verified = final_sort == wanted_sort
        changed = before.get("row_signature") != after.get("row_signature")
        result = self._capture_state("sort-table-semantic")
        result.update(
            {
                "table_name": table,
                "sorted_column": column,
                "sort_direction": wanted_sort,
                "observed_aria_sort": final_sort or None,
                "sort_click_attempts": attempts,
                "sort_status": (
                    "sorted"
                    if verified
                    else "triggered_unverified"
                    if changed
                    else "not_observed"
                ),
                "table_before": before,
                "table_after": after,
                "mutation_executed": True,
            }
        )
        result = self._finish_action_execution(result)
        if not verified and not changed:
            result["error"] = "table_sort_not_observed"
        return result

    def set_table_row_selected(
        self,
        name: str,
        selected: bool,
        exact: bool = True,
    ):
        """Set the selection checkbox in one row matched by an exact cell."""
        self._ensure_started()
        self._reset_diagnostics()
        wanted = " ".join(str(name or "").split())
        if not wanted:
            return {
                "error": "table_row_name_required",
                "executed": False,
            }
        row_matches = []
        rows = self.page.locator("tr")
        for index in range(min(rows.count(), 500)):
            row = rows.nth(index)
            try:
                if not row.is_visible() or row.locator("td").count() == 0:
                    continue
                cells = row.locator(":scope > td, :scope > th").all_inner_texts()
                row_text = " ".join((row.inner_text() or "").split())
                matched = (
                    any(" ".join(cell.split()) == wanted for cell in cells)
                    if exact
                    else wanted.casefold() in row_text.casefold()
                )
                if matched:
                    row_matches.append(row)
            except Exception:
                continue
        if len(row_matches) != 1:
            return {
                "error": (
                    "table_row_not_found"
                    if not row_matches
                    else "ambiguous_table_row"
                ),
                "name": name,
                "matches": len(row_matches),
                "executed": False,
            }

        row = row_matches[0]
        controls = row.locator(
            'input[type="checkbox"], [role="checkbox"]'
        )
        checkboxes = []
        for index in range(min(controls.count(), 20)):
            candidate = controls.nth(index)
            if candidate.is_visible():
                checkboxes.append(candidate)
        if len(checkboxes) != 1:
            return {
                "error": (
                    "table_row_checkbox_not_found"
                    if not checkboxes
                    else "ambiguous_table_row_checkbox"
                ),
                "name": name,
                "matches": len(checkboxes),
                "executed": False,
            }

        checkbox = checkboxes[0]
        try:
            previous = bool(checkbox.is_checked())
        except Exception:
            previous = (
                str(checkbox.get_attribute("aria-checked") or "").casefold()
                == "true"
            )
        desired = bool(selected)
        if previous == desired:
            result = self._capture_state("set-table-row-selected")
            result.update(
                {
                    "table_row_name": name,
                    "previous_selected": previous,
                    "selected": previous,
                    "row_selection_status": "already_satisfied",
                    "mutation_executed": False,
                }
            )
            return result

        self._reset_diagnostics()
        self._begin_action_execution()
        checkbox.click()
        self.page.wait_for_timeout(300)
        try:
            actual = bool(checkbox.is_checked())
        except Exception:
            actual = (
                str(checkbox.get_attribute("aria-checked") or "").casefold()
                == "true"
            )
        result = self._capture_state("set-table-row-selected")
        result.update(
            {
                "table_row_name": name,
                "previous_selected": previous,
                "selected": actual,
                "row_selection_status": (
                    "selected" if actual == desired else "not_applied"
                ),
                "mutation_executed": False,
            }
        )
        result = self._finish_action_execution(result)
        if actual != desired:
            result["error"] = "table_row_selection_not_applied"
        return result

    def table_page_semantic(
        self,
        control: str,
        table: str = None,
        exact: bool = True,
    ):
        """Activate one exact pagination control and verify row-set change."""
        self._ensure_started()
        self._reset_diagnostics()
        table_locator, error = self._resolve_table(table, exact)
        if error:
            return error
        before = self._table_snapshot(table_locator)
        candidates = []
        for role in ("button", "link"):
            locator = self.page.get_by_role(
                role,
                name=control,
                exact=exact,
            )
            matches = []
            for index in range(min(locator.count(), 50)):
                candidate = locator.nth(index)
                if candidate.is_visible():
                    matches.append(candidate)
            if matches:
                candidates = matches
                break
        if len(candidates) != 1:
            return {
                "error": (
                    "table_page_control_not_found"
                    if not candidates
                    else "ambiguous_table_page_control"
                ),
                "control": control,
                "matches": len(candidates),
                "executed": False,
            }
        control_locator = candidates[0]
        if not control_locator.is_enabled():
            return {
                "error": "table_page_control_disabled",
                "control": control,
                "executed": False,
            }

        self._reset_diagnostics()
        self._begin_action_execution()
        control_locator.click()
        self.page.wait_for_timeout(700)
        after = self._table_snapshot(table_locator)
        changed = before.get("row_signature") != after.get("row_signature")
        result = self._capture_state("table-page-semantic")
        result.update(
            {
                "table_name": table,
                "table_page_control": control,
                "table_page_status": "changed" if changed else "not_changed",
                "table_before": before,
                "table_after": after,
                "mutation_executed": False,
            }
        )
        result = self._finish_action_execution(result)
        if not changed:
            result["error"] = "table_page_not_changed"
        return result

    def fill_table_filter_semantic(
        self,
        column: str,
        text: str,
        table: str = None,
        exact: bool = True,
    ):
        """Fill one filter control associated with an exact table column."""
        self._ensure_started()
        self._reset_diagnostics()
        table_locator, error = self._resolve_table(table, exact)
        if error:
            return error

        header_locator = table_locator.get_by_role(
            "columnheader",
            name=column,
            exact=exact,
        )
        headers = []
        for index in range(min(header_locator.count(), 50)):
            candidate = header_locator.nth(index)
            if candidate.is_visible():
                headers.append(candidate)
        if len(headers) != 1:
            return {
                "error": (
                    "table_column_not_found"
                    if not headers
                    else "ambiguous_table_column"
                ),
                "column": column,
                "matches": len(headers),
                "executed": False,
            }

        header = headers[0]
        column_index = header.evaluate(
            "el => Number.isInteger(el.cellIndex) ? el.cellIndex : -1"
        )
        if column_index < 0:
            return {
                "error": "table_column_index_unavailable",
                "column": column,
                "executed": False,
            }

        candidates = []
        seen = set()
        header_rows = table_locator.locator("thead tr")
        for row_index in range(min(header_rows.count(), 20)):
            row = header_rows.nth(row_index)
            cells = row.locator(":scope > th, :scope > td")
            if column_index >= cells.count():
                continue
            controls = cells.nth(column_index).locator(
                'input:not([type="hidden"]), textarea, '
                '[role="textbox"], [role="searchbox"]'
            )
            for control_index in range(min(controls.count(), 20)):
                candidate = controls.nth(control_index)
                try:
                    if not candidate.is_visible():
                        continue
                    key = candidate.evaluate(
                        "el => el.id || el.name || el.outerHTML"
                    )
                    if key not in seen:
                        seen.add(key)
                        candidates.append(candidate)
                except Exception:
                    continue

        if len(candidates) != 1:
            return {
                "error": (
                    "table_column_filter_not_found"
                    if not candidates
                    else "ambiguous_table_column_filter"
                ),
                "column": column,
                "matches": len(candidates),
                "executed": False,
            }

        target = candidates[0]
        if (target.get_attribute("type") or "").casefold() == "password":
            return {
                "error": "table_filter_password_forbidden",
                "column": column,
                "executed": False,
            }
        wanted = str(text or "")
        current = target.input_value()
        before = self._table_snapshot(table_locator)
        if current == wanted:
            result = self._capture_state("fill-table-filter-semantic")
            result.update(
                {
                    "table_name": table,
                    "filtered_column": column,
                    "filter_text": wanted,
                    "filter_status": "already_satisfied",
                    "table_before": before,
                    "table_after": before,
                    "mutation_executed": False,
                }
            )
            return result

        self._reset_diagnostics()
        self._begin_action_execution()
        target.fill(wanted)
        self.page.wait_for_timeout(500)
        actual = target.input_value()
        after = self._table_snapshot(table_locator)
        applied = actual == wanted
        result = self._capture_state("fill-table-filter-semantic")
        result.update(
            {
                "table_name": table,
                "filtered_column": column,
                "filter_text": wanted,
                "observed_filter_text": actual,
                "filter_status": "applied" if applied else "not_applied",
                "rows_changed": (
                    before.get("row_signature")
                    != after.get("row_signature")
                ),
                "table_before": before,
                "table_after": after,
                "mutation_executed": False,
            }
        )
        result = self._finish_action_execution(result)
        if not applied:
            result["error"] = "table_filter_not_applied"
        return result

    def set_table_all_selected(
        self,
        selected: bool,
        table: str = None,
        exact: bool = True,
    ):
        """Set one table header checkbox and verify all visible row checkboxes."""
        self._ensure_started()
        self._reset_diagnostics()
        table_locator, error = self._resolve_table(table, exact)
        if error:
            return error

        header_controls = table_locator.locator(
            'thead input[type="checkbox"], thead [role="checkbox"]'
        )
        headers = []
        for index in range(min(header_controls.count(), 20)):
            candidate = header_controls.nth(index)
            if candidate.is_visible():
                headers.append(candidate)
        if len(headers) != 1:
            return {
                "error": (
                    "table_select_all_not_found"
                    if not headers
                    else "ambiguous_table_select_all"
                ),
                "table": table,
                "matches": len(headers),
                "executed": False,
            }

        row_controls = table_locator.locator(
            'tbody input[type="checkbox"], tbody [role="checkbox"]'
        )
        rows = []
        for index in range(min(row_controls.count(), 500)):
            candidate = row_controls.nth(index)
            if candidate.is_visible():
                rows.append(candidate)
        if not rows:
            return {
                "error": "table_row_checkboxes_not_found",
                "table": table,
                "executed": False,
            }

        def checked_state(locator):
            try:
                return bool(locator.is_checked())
            except Exception:
                return (
                    str(locator.get_attribute("aria-checked") or "").casefold()
                    == "true"
                )

        desired = bool(selected)
        before_states = [checked_state(item) for item in rows]
        if all(value == desired for value in before_states):
            result = self._capture_state("set-table-all-selected")
            result.update(
                {
                    "table_name": table,
                    "selected": desired,
                    "selected_row_count": sum(before_states),
                    "visible_selectable_row_count": len(rows),
                    "select_all_status": "already_satisfied",
                    "mutation_executed": False,
                }
            )
            return result

        header = headers[0]
        self._reset_diagnostics()
        self._begin_action_execution()
        header.click()
        self.page.wait_for_timeout(300)
        after_states = [checked_state(item) for item in rows]
        applied = all(value == desired for value in after_states)
        result = self._capture_state("set-table-all-selected")
        result.update(
            {
                "table_name": table,
                "selected": desired,
                "selected_row_count": sum(after_states),
                "visible_selectable_row_count": len(rows),
                "select_all_status": (
                    "selected" if applied else "not_applied"
                ),
                "mutation_executed": False,
            }
        )
        result = self._finish_action_execution(result)
        if not applied:
            result["error"] = "table_select_all_not_applied"
        return result

    def inspect_bulk_action_semantic(
        self,
        name: str,
        table: str = None,
        exact: bool = True,
        role: str = None,
    ):
        """Inspect one bulk-action control without activating it."""
        self._ensure_started()
        self._reset_diagnostics()
        table_locator, error = self._resolve_table(table, exact)
        if error:
            return error
        action, strategy, error = self._pointer_target(
            name,
            exact,
            role,
        )
        if error:
            return error

        enabled = None
        try:
            enabled = bool(action.is_enabled())
        except Exception:
            pass
        action_state = action.evaluate(
            """
            el => ({
                tag: el.tagName.toLowerCase(),
                role: el.getAttribute('role') || '',
                text: (el.innerText || el.textContent || '').trim().slice(0, 300),
                aria_disabled: el.getAttribute('aria-disabled'),
                disabled_attribute: el.hasAttribute('disabled')
            })
            """
        )
        row_controls = table_locator.locator(
            'tbody input[type="checkbox"], tbody [role="checkbox"]'
        )
        selected_count = 0
        selectable_count = 0
        for index in range(min(row_controls.count(), 500)):
            candidate = row_controls.nth(index)
            if not candidate.is_visible():
                continue
            selectable_count += 1
            try:
                checked = bool(candidate.is_checked())
            except Exception:
                checked = (
                    str(candidate.get_attribute("aria-checked") or "").casefold()
                    == "true"
                )
            if checked:
                selected_count += 1

        result = self._capture_state("inspect-bulk-action-semantic")
        result.update(
            {
                "table_name": table,
                "bulk_action_name": name,
                "bulk_action_strategy": strategy,
                "bulk_action_status": "observed",
                "bulk_action_enabled": enabled,
                "bulk_action": action_state,
                "selected_row_count": selected_count,
                "visible_selectable_row_count": selectable_count,
                "mutation_executed": False,
            }
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
            const isArchived = (item) => {
                if (!item || typeof item !== 'object') return false;
                for (const key of ['is_archived', 'archived', 'isArchived']) {
                    if (item[key] === true) return true;
                    if (String(item[key] ?? '').toLowerCase() === 'true') {
                        return true;
                    }
                }
                return ['archived'].includes(
                    String(item.status ?? item.state ?? '').toLowerCase()
                );
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
            const archiveOperation =
                mutationMethod === 'POST' && operationSuffix === 'archive';
            if (archiveOperation && isArchived(before.matches[0])) {
                return {
                    phase: 'complete',
                    preflight_status: before.status,
                    exact_match_count: before.matches.length,
                    identifier_key: identifier.key,
                    identifier_value: identifier.value,
                    mutation_method: mutationMethod,
                    operation_suffix: operationSuffix,
                    mutation_status: null,
                    mutation_executed: false,
                    already_satisfied: true,
                    post_delete_status: before.status,
                    post_delete_match_count: before.matches.length,
                    post_delete_archived_match_count: 1,
                    post_delete_verified: true,
                };
            }
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
            const archivedMatches = after.matches.filter(isArchived).length;
            const verified = archiveOperation
                ? after.matches.length === 1 && archivedMatches === 1
                : after.matches.length === 0;
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
                mutation_executed: true,
                post_delete_status: after.status,
                post_delete_match_count: after.matches.length,
                post_delete_archived_match_count: archivedMatches,
                post_delete_verified: verified,
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
            and (
                raw.get("already_satisfied") is True
                or 200 <= int(raw.get("mutation_status") or 0) < 300
            )
            and 200 <= int(raw.get("post_delete_status") or 0) < 300
            and raw.get("post_delete_verified") is True
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

    def inspect_table_row(
        self,
        name: str,
        exact: bool = True,
    ):
        """Inspect one visible table row by an exact cell value."""
        self._ensure_started()
        self._reset_diagnostics()

        wanted = " ".join(str(name or "").split())

        if not wanted:
            return {
                "error": "table_row_name_required",
                "status": "error",
            }

        matches = []
        rows = self.page.locator("tr")

        try:
            count = min(rows.count(), 500)
        except Exception:
            count = 0

        for index in range(count):
            row = rows.nth(index)

            try:
                if not row.is_visible():
                    continue

                row_data = row.evaluate(
                    """
                    row => {
                        const clean = value => String(value || '')
                            .replace(/\\s+/g, ' ')
                            .trim();
                        const cells = Array.from(
                            row.querySelectorAll(':scope > th, :scope > td')
                        ).map(cell => clean(cell.innerText || cell.textContent));
                        const table = row.closest('table');
                        const headers = table
                            ? Array.from(table.querySelectorAll('thead th'))
                                .map(cell => clean(cell.innerText || cell.textContent))
                            : [];
                        const valuesByHeader = {};
                        if (headers.length === cells.length) {
                            headers.forEach((header, position) => {
                                if (header) valuesByHeader[header] = cells[position];
                            });
                        }
                        return {
                            tag: 'tr',
                            role: (row.getAttribute('role') || 'row').toLowerCase(),
                            text: clean(row.innerText || row.textContent),
                            cells,
                            headers,
                            values_by_header: valuesByHeader,
                            aria_selected: row.getAttribute('aria-selected'),
                        };
                    }
                    """
                )
            except Exception:
                continue

            cells = row_data.get("cells") or []
            row_text = str(row_data.get("text") or "")
            matched = (
                any(cell == wanted for cell in cells)
                if exact
                else wanted.casefold() in row_text.casefold()
            )

            if matched:
                matches.append((row, row_data))

        if not matches:
            return {
                "error": "table_row_not_found",
                "status": "error",
                "name": name,
                "exact": exact,
                "match_mode": "exact_cell" if exact else "row_contains",
            }

        if len(matches) > 1:
            return {
                "error": "ambiguous_table_row",
                "status": "error",
                "name": name,
                "exact": exact,
                "matches": len(matches),
                "match_mode": "exact_cell" if exact else "row_contains",
            }

        _, row_data = matches[0]
        result = self._capture_state("inspect-table-row")
        result.update(
            {
                "semantic_name": name,
                "semantic_strategy": (
                    "table_row_exact_cell"
                    if exact
                    else "table_row_contains"
                ),
                "inspection_status": "observed",
                "visible": True,
                "enabled": None,
                "disabled": None,
                "editable": False,
                "element": row_data,
                "row": row_data,
                "row_match_count": 1,
            }
        )
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
        role_constraint_matched = None

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
                if requested_role:
                    role_constraint_matched = True
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
                role_constraint_matched = True

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
            # A role supplied by the model is only a narrowing hint. If the
            # live DOM does not confirm it, continue through the same strict
            # label/placeholder/icon/text lookup instead of forcing the model
            # into a repeated not-found loop.
            role_constraint_matched = False

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
                    "requested_role": requested_role or None,
                    "role_constraint_matched": role_constraint_matched,
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
                "requested_role": requested_role or None,
                "role_constraint_matched": role_constraint_matched,
                "semantic_role_fallback": (
                    bool(requested_role)
                    and role_constraint_matched is False
                ),
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

        post_click_same_name_button_count = 0

        try:
            confirmation_buttons = self.page.get_by_role(
                "button",
                name=name,
                exact=exact,
            )

            for index in range(
                min(
                    confirmation_buttons.count(),
                    20,
                )
            ):
                try:
                    if confirmation_buttons.nth(
                        index
                    ).is_visible():
                        post_click_same_name_button_count += 1
                except Exception:
                    continue
        except Exception:
            post_click_same_name_button_count = 0

        result = self._capture_state(
            "click-semantic"
        )

        result["semantic_name"] = name
        result["semantic_strategy"] = strategy
        result["semantic_container"] = container
        result["click_status"] = "executed"
        result["post_action_wait_ms"] = 1000
        result[
            "post_click_same_name_button_count"
        ] = post_click_same_name_button_count

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


def probe_capabilities() -> dict:
    return _session.probe_capabilities()


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


def select_semantic(
    field: str,
    option: str,
    exact: bool = True,
) -> dict:
    return _session.select_semantic(field, option, exact)


def set_checked_semantic(
    field: str,
    checked: bool,
    exact: bool = True,
) -> dict:
    return _session.set_checked_semantic(field, checked, exact)


def choose_radio_semantic(
    option: str,
    group: str = None,
    exact: bool = True,
) -> dict:
    return _session.choose_radio_semantic(option, group, exact)


def select_many_semantic(
    field: str,
    options: list,
    exact: bool = True,
) -> dict:
    return _session.select_many_semantic(field, options, exact)


def press_key_semantic(
    key: str,
    target: str = None,
    exact: bool = True,
    role: str = None,
) -> dict:
    return _session.press_key_semantic(key, target, exact, role)


def check_focus_order_semantic(
    targets: list,
    exact: bool = True,
) -> dict:
    return _session.check_focus_order_semantic(targets, exact)


def drag_semantic(
    source: str,
    target: str,
    exact: bool = True,
    source_role: str = None,
    target_role: str = None,
) -> dict:
    return _session.drag_semantic(
        source,
        target,
        exact,
        source_role,
        target_role,
    )


def resize_semantic(
    target: str,
    delta_x: int = 0,
    delta_y: int = 0,
    edge: str = "right",
    exact: bool = True,
    role: str = None,
) -> dict:
    return _session.resize_semantic(
        target,
        delta_x,
        delta_y,
        edge,
        exact,
        role,
    )


def inspect_table_semantic(
    table: str = None,
    exact: bool = True,
) -> dict:
    return _session.inspect_table_semantic(table, exact)


def sort_table_semantic(
    column: str,
    direction: str,
    table: str = None,
    exact: bool = True,
) -> dict:
    return _session.sort_table_semantic(
        column,
        direction,
        table,
        exact,
    )


def set_table_row_selected(
    name: str,
    selected: bool,
    exact: bool = True,
) -> dict:
    return _session.set_table_row_selected(name, selected, exact)


def table_page_semantic(
    control: str,
    table: str = None,
    exact: bool = True,
) -> dict:
    return _session.table_page_semantic(control, table, exact)


def fill_table_filter_semantic(
    column: str,
    text: str,
    table: str = None,
    exact: bool = True,
) -> dict:
    return _session.fill_table_filter_semantic(
        column,
        text,
        table,
        exact,
    )


def set_table_all_selected(
    selected: bool,
    table: str = None,
    exact: bool = True,
) -> dict:
    return _session.set_table_all_selected(selected, table, exact)


def inspect_bulk_action_semantic(
    name: str,
    table: str = None,
    exact: bool = True,
    role: str = None,
) -> dict:
    return _session.inspect_bulk_action_semantic(
        name,
        table,
        exact,
        role,
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


def inspect_table_row(
    name: str,
    exact: bool = True,
) -> dict:
    return _session.inspect_table_row(
        name,
        exact,
    )


def reset_case_context() -> dict:
    return _session.reset_case_context()


def close_browser_session():
    _session.close()


atexit.register(close_browser_session)

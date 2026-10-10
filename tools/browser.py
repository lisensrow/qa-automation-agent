import atexit
import csv
import hashlib
import json
import mimetypes
import os
import re
import uuid
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", "/opt/uqa/browsers")

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError, sync_playwright

from tools.agent_observability import summarize_agent_observation


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

UPLOAD_FIXTURES = {
    "sample-text": {
        "name": "uqa-sample.txt",
        "mimeType": "text/plain",
        "buffer": b"UQA harmless upload fixture\n",
    },
}

MANAGED_AGENT_TASK_FIXTURES = {
    "posix_printf_marker_v1": {
        "task_name": "executeCommand",
        "program": "/usr/bin/printf",
        "arguments_before_marker": [],
        "os_name_tokens": (
            "linux", "ubuntu", "debian", "centos", "red hat",
            "fedora", "suse", "unix",
        ),
    },
    "windows_cmd_echo_marker_v1": {
        "task_name": "executeCommand",
        "program": r"C:\Windows\System32\cmd.exe",
        "arguments_before_marker": ["/d", "/s", "/c", "echo"],
        "os_name_tokens": ("windows",),
    },
}


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
        self.page_errors = []
        self.failed_requests = []
        self.http_errors = []

        # Компактный журнал fetch/XHR текущего действия.
        self.network_events = []
        self.network_counter = 0

        # Ссылки на конкретные fetch/XHR храним всю браузерную сессию.
        # В модель они не попадают, пока она явно не запросит nXX.
        self.network_details = {}
        self.download_artifacts = {}

        # Идентичность конкретного UI-действия.
        # Отдельный counter нужен потому, что action_counter
        # увеличивается только при _capture_state().
        self.action_execution_counter = 0
        self.active_action_execution_id = None

        self.last_uc_auth = None
        self._last_inspected_exact_target = None
        self._last_inspected_exact_row = None
        self._last_agent_task_inspection = None
        self._agent_task_result_snapshots = {}
        # Expected output is deliberately session-private. The model receives
        # only hashes and booleans, never the command marker or raw result.
        self._managed_agent_tasks = {}
        # Session-private clipboard. It never reads from or writes to the
        # operating-system clipboard and is never persisted to artifacts.
        self._private_clipboard_text = None
        self._private_clipboard_source = None
        # Form values stay private; only their SHA-256 fingerprint is retained.
        self._form_state_baselines = {}

    def _context_kwargs(self):
        context_kwargs = {
            "ignore_https_errors": True,
            "accept_downloads": True,
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
            "pageerror",
            self._on_page_error,
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
        self.download_artifacts = {}

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

    def _on_page_error(self, error):
        self.page_errors.append(
            {
                "error_type": type(error).__name__,
                "message": str(error)[:500],
            }
        )

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
        self.page_errors.clear()
        self.failed_requests.clear()
        self.http_errors.clear()
        self.network_events.clear()
        self.active_action_execution_id = None

    def _on_request_failed(self, request):
        self.failed_requests.append(
            {
                "url": self._safe_network_url(request.url),
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

        frontend_health_passed = not (
            self.console_errors
            or self.page_errors
            or self.failed_requests
            or self._filtered_http_errors(action)
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
            "page_errors": self.page_errors[-20:],
            "http_errors": self._filtered_http_errors(action),
            "failed_requests": self.failed_requests[-20:],
            "frontend_health_passed": frontend_health_passed,
            "network_request_count": len(network_requests),
            "network_requests": network_requests,
        }

    def open_page(self, url: str):
        self._ensure_started()
        self._last_inspected_exact_target = None
        self._last_inspected_exact_row = None
        self._last_agent_task_inspection = None

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

    def inspect_agent_telemetry_semantic(
        self, ci_name: str, max_age_seconds: int = 300,
    ):
        """Correlate the selected CI with responses already seen by this page."""
        self._ensure_started()
        if not isinstance(ci_name, str) or not ci_name.strip():
            return {"error": "ci_name_required", "executed": False}
        try:
            ui_statuses = self.page.evaluate(
                """
                name => {
                    const clean = x => String(x || '').replace(/\\s+/g, ' ').trim();
                    const visible = el => {
                        const style = getComputedStyle(el);
                        return !el.hidden && style.display !== 'none'
                            && style.visibility !== 'hidden'
                            && el.getClientRects().length > 0;
                    };
                    const found = new Set();
                    for (const el of document.querySelectorAll('span,div,h1,h2,h3,td')) {
                        if (el.children.length || clean(el.textContent) !== name || !visible(el))
                            continue;
                        let parent = el.parentElement;
                        for (let depth = 0; depth < 2 && parent; depth++, parent = parent.parentElement) {
                            const lines = String(parent.innerText || '')
                                .split(/\\n+/).map(clean).filter(Boolean);
                            if (lines.length === 2 && lines.includes(name)) {
                                for (const status of ['online', 'offline']) {
                                    if (lines.includes(status)) found.add(status);
                                }
                            }
                        }
                    }
                    return Array.from(found);
                }
                """,
                ci_name,
            )
        except Exception:
            ui_statuses = []
        ui_status = ui_statuses[0] if len(ui_statuses) == 1 else None
        observed = []
        for request_id, detail in list(self.network_details.items())[-150:]:
            try:
                if detail["request"].method != "GET" or detail["response"].status != 200:
                    continue
                payload = detail["response"].json()
                if isinstance(payload, dict):
                    observed.append((request_id, payload))
            except Exception:
                continue
        ci_id = agent_id = None
        ci = agent = monitoring = None
        source_ids = {}
        for request_id, payload in reversed(observed):
            if payload.get("name") == ci_name and payload.get("agent_id") and payload.get("id"):
                ci = payload
                ci_id, agent_id = payload["id"], payload["agent_id"]
                source_ids["ci"] = request_id
                break
        if agent_id:
            for request_id, payload in reversed(observed):
                if payload.get("id") == agent_id and "status" in payload and "version" in payload:
                    agent = payload
                    source_ids["agent"] = request_id
                    break
        if ci_id:
            for request_id, payload in reversed(observed):
                if payload.get("uid") == ci_id and "cpu_usage" in payload and "created_at" in payload:
                    monitoring = payload
                    source_ids["monitoring"] = request_id
                    break
        try:
            summary = summarize_agent_observation(
                ci_name, ci, agent, monitoring, ui_status,
                max_age_seconds=max_age_seconds,
            )
        except ValueError:
            return {"error": "monitoring_age_limit_invalid", "executed": False}
        result = self._capture_state("inspect-agent-telemetry-semantic")
        result.update(summary)
        result["source_request_ids"] = source_ids
        result["mutation_executed"] = False
        return result

    def inspect_agent_plugins_semantic(
        self, ci_name: str, plugin_name: str = None,
        expected_version: str = None, max_age_seconds: int = 3600,
    ):
        """Inspect the selected CI's already-observed plugin audit GET response."""
        from tools.agent_plugins import summarize_plugin_audit

        self._ensure_started()
        if not isinstance(ci_name, str) or not ci_name.strip():
            return {"error": "ci_name_required", "executed": False}
        if plugin_name is not None and (not isinstance(plugin_name, str) or not plugin_name.strip()):
            return {"error": "plugin_name_invalid", "executed": False}
        if ci_name not in self.page.locator("body").inner_text():
            return {"error": "ci_not_visible", "executed": False}
        ci = audit = None
        source_ids = {}
        observed = []
        for request_id, detail in list(self.network_details.items())[-200:]:
            try:
                request, response = detail["request"], detail["response"]
                if request.method != "GET" or response.status != 200:
                    continue
                payload = response.json()
                if isinstance(payload, dict):
                    observed.append((request_id, request.url, payload))
            except Exception:
                continue
        for request_id, url, payload in reversed(observed):
            if payload.get("name") == ci_name and payload.get("agent_id") and payload.get("id"):
                ci = payload
                source_ids["ci"] = request_id
                break
        if ci:
            agent_id = ci["agent_id"]
            for request_id, url, payload in reversed(observed):
                if (payload.get("agent_id") == agent_id
                    and isinstance(payload.get("detail"), list)
                    and "/agents/" in url and url.split("?")[0].endswith("/plugin")):
                    audit = payload
                    source_ids["plugin_audit"] = request_id
                    break
        try:
            summary = summarize_plugin_audit(
                ci, audit, plugin_name, expected_version,
                max_age_seconds=max_age_seconds,
            )
        except ValueError:
            return {"error": "plugin_audit_age_limit_invalid", "executed": False}
        result = self._capture_state("inspect-agent-plugins-semantic")
        result.update(summary)
        result["source_request_ids"] = source_ids
        result["mutation_executed"] = False
        return result

    def inspect_agent_tasks_semantic(
        self, ci_name: str, task_name: str = None, task_id: str = None,
    ):
        """Summarize an already-observed task-list GET for the selected agent."""
        from tools.agent_tasks import summarize_agent_tasks

        self._ensure_started()
        if not isinstance(ci_name, str) or not ci_name.strip():
            return {"error": "ci_name_required", "executed": False}
        if task_name is not None and (
            not isinstance(task_name, str) or not task_name.strip()
        ):
            return {"error": "task_name_invalid", "executed": False}
        if task_id is not None and (
            not isinstance(task_id, str) or not task_id.strip()
        ):
            return {"error": "task_id_invalid", "executed": False}
        if ci_name not in self.page.locator("body").inner_text():
            return {"error": "ci_not_visible", "executed": False}

        observed = []
        for request_id, detail in list(self.network_details.items())[-200:]:
            try:
                request, response = detail["request"], detail["response"]
                if request.method != "GET" or response.status != 200:
                    continue
                payload = response.json()
                if isinstance(payload, dict):
                    observed.append((request_id, urlsplit(request.url).path, payload))
            except Exception:
                continue

        ci = task_page = None
        source_ids = {}
        for request_id, path, payload in reversed(observed):
            if (
                payload.get("name") == ci_name
                and payload.get("id") and payload.get("agent_id")
            ):
                ci = payload
                source_ids["ci"] = request_id
                break
        if ci:
            expected_path = f"/agents/{ci['agent_id']}/tasks"
            for request_id, path, payload in reversed(observed):
                if path.endswith(expected_path) and isinstance(payload.get("items"), list):
                    task_page = payload
                    source_ids["tasks"] = request_id
                    break

        summary = summarize_agent_tasks(ci, task_page, task_name, task_id)
        if summary.get("reason") == "task_list_get_not_observed":
            summary["next_step_hint"] = (
                "Open the selected CI's Agent → Tasks tab, then inspect again."
            )
        inspection_key = (
            ci_name, task_name, task_id, source_ids.get("tasks"), self.page.url,
        )
        if self._last_agent_task_inspection == inspection_key:
            return {
                "error": "identical_task_inspection_no_new_data",
                "executed": False,
                "ci_name": ci_name,
                "task_name": task_name,
                "task_id": task_id,
                "reason": summary.get("reason"),
                "available_task_names": summary.get("available_task_names"),
            }
        self._last_agent_task_inspection = inspection_key
        result = self._capture_state("inspect-agent-tasks-semantic")
        result.update(summary)
        result["source_request_ids"] = source_ids
        return result

    def inspect_agent_task_result_semantic(
        self, ci_name: str, task_id: str,
        expected_text: str = None, expected_error_code: int = None,
        verify_periodic: bool = False,
    ):
        """Read one observed task's full GET; return metadata, never its result."""
        from tools.agent_tasks import (
            summarize_agent_task_full, summarize_agent_tasks,
            summarize_periodic_progress,
        )

        self._ensure_started()
        if not isinstance(ci_name, str) or not ci_name.strip():
            return {"error": "ci_name_required", "executed": False}
        try:
            canonical_task_id = str(uuid.UUID(task_id))
        except (ValueError, TypeError, AttributeError):
            return {"error": "task_id_invalid", "executed": False}
        if canonical_task_id != task_id:
            return {"error": "task_id_invalid", "executed": False}
        if ci_name not in self.page.locator("body").inner_text():
            return {"error": "ci_not_visible", "executed": False}

        observed = []
        for request_id, detail in list(self.network_details.items())[-200:]:
            try:
                request, response = detail["request"], detail["response"]
                if request.method != "GET" or response.status != 200:
                    continue
                payload = response.json()
                if isinstance(payload, dict):
                    observed.append((request_id, request.url, payload))
            except Exception:
                continue

        ci = task_page = task_request_url = None
        source_ids = {}
        for request_id, request_url, payload in reversed(observed):
            if (
                payload.get("name") == ci_name
                and payload.get("id") and payload.get("agent_id")
            ):
                ci = payload
                source_ids["ci"] = request_id
                break
        if ci is not None:
            for request_id, request_url, payload in reversed(observed):
                if (
                    urlsplit(request_url).path.endswith(
                        f"/agents/{ci['agent_id']}/tasks"
                    )
                    and isinstance(payload.get("items"), list)
                ):
                    task_page = payload
                    task_request_url = request_url
                    source_ids["tasks"] = request_id
                    break

        listed = summarize_agent_tasks(ci, task_page, task_id=task_id)
        if listed["reason"]:
            result = summarize_agent_task_full(
                ci, task_page, task_id, None,
                expected_text, expected_error_code,
            )
            result["source_request_ids"] = source_ids
            return result
        if (
            not isinstance(task_page.get("total"), int)
            or isinstance(task_page.get("total"), bool)
            or task_page["total"] != len(task_page["items"])
        ):
            result = summarize_agent_task_full(
                ci, task_page, task_id, None,
                expected_text, expected_error_code,
            )
            result["source_request_ids"] = source_ids
            return result

        source = urlsplit(task_request_url)
        current = urlsplit(self.page.url)
        if (
            source.scheme != "https" or current.scheme != "https"
            or source.netloc != current.netloc
        ):
            return {"error": "task_result_origin_mismatch", "executed": False}
        full_path = source.path + f"/{task_id}/full"
        full_url = urlunsplit((source.scheme, source.netloc, full_path, "", ""))
        try:
            response = self.context.request.get(full_url, timeout=15000)
            status = response.status
            full = response.json() if status == 200 else None
        except Exception:
            status, full = None, None
        result = summarize_agent_task_full(
            ci, task_page, task_id, full,
            expected_text, expected_error_code,
        )
        if verify_periodic:
            snapshot_key = (result.get("agent_id"), task_id)
            periodic, snapshot = summarize_periodic_progress(
                listed["matched_tasks"][0],
                result,
                self._agent_task_result_snapshots.get(snapshot_key),
            )
            result.update(periodic)
            if snapshot is not None:
                self._agent_task_result_snapshots[snapshot_key] = snapshot
        if status != 200:
            result["inspection_status"] = "blocked"
            result["reason"] = "task_full_get_unavailable"
        result["full_http_status"] = status
        result["source_request_ids"] = source_ids
        return result

    def _observed_agent_task_context(self, ci_name):
        """Return one exact CI and complete observed task collection."""
        if not isinstance(ci_name, str) or not ci_name.strip():
            return None, None, None, {"error": "ci_name_required", "executed": False}
        if ci_name not in self.page.locator("body").inner_text():
            return None, None, None, {"error": "ci_not_visible", "executed": False}

        observed = []
        for request_id, detail in list(self.network_details.items())[-200:]:
            try:
                request, response = detail["request"], detail["response"]
                if request.method != "GET" or response.status != 200:
                    continue
                payload = response.json()
                if isinstance(payload, dict):
                    observed.append((request_id, request.url, payload))
            except Exception:
                continue

        ci = None
        for _, _, payload in reversed(observed):
            if (
                payload.get("name") == ci_name
                and payload.get("id") and payload.get("agent_id")
            ):
                ci = payload
                break
        if ci is None:
            return None, None, None, {
                "error": "ci_observation_missing_or_mismatched",
                "executed": False,
            }

        expected_path = f"/agents/{ci['agent_id']}/tasks"
        for _, request_url, payload in reversed(observed):
            if (
                urlsplit(request_url).path.endswith(expected_path)
                and isinstance(payload.get("items"), list)
            ):
                return ci, payload, request_url, None

        return ci, None, None, {
            "error": "task_list_get_not_observed",
            "executed": False,
            "next_step_hint": (
                "Open the selected CI's Agent → Tasks tab, then retry."
            ),
        }

    def _wait_for_observed_agent_task_context(
        self, ci_name, timeout_ms=3000, poll_ms=100,
    ):
        """Wait briefly for the task-list GET triggered by the exact tab click."""
        timeout_ms = max(0, min(int(timeout_ms), 5000))
        poll_ms = max(50, min(int(poll_ms), 500))
        wait_count = (timeout_ms + poll_ms - 1) // poll_ms
        retryable_errors = {
            "ci_observation_missing_or_mismatched",
            "task_list_get_not_observed",
        }
        last = (None, None, None, {
            "error": "task_list_get_not_observed",
            "executed": False,
        })

        for attempt in range(wait_count + 1):
            last = self._observed_agent_task_context(ci_name)
            error = last[3]
            if error is None:
                return last
            if error.get("error") not in retryable_errors:
                return last
            if attempt < wait_count:
                self.page.wait_for_timeout(poll_ms)

        error = dict(last[3] or {})
        error["wait_timeout_ms"] = timeout_ms
        error["wait_attempts"] = wait_count + 1
        return last[0], last[1], last[2], error

    def open_agent_tasks_semantic(self, ci_name: str):
        """Open one exact CMDB row's Agent → Tasks tab deterministically."""
        self._ensure_started()
        stages = []

        inspected = self.inspect_table_row(ci_name, exact=True)
        stages.append("ci_row_inspected")
        if inspected.get("error") or inspected.get("row_match_count") != 1:
            return {
                "error": inspected.get("error") or "ci_row_not_unique",
                "executed": False,
                "mutation_executed": False,
                "navigation_status": "blocked",
                "failed_stage": "ci_row_inspection",
                "ci_name": ci_name,
                "row_match_count": inspected.get("row_match_count"),
                "current_url": inspected.get("current_url"),
                "screenshot": inspected.get("screenshot"),
            }

        row_click = self.click_semantic(ci_name, exact=True, role="row")
        stages.append("ci_row_opened")
        if row_click.get("error") or row_click.get("click_status") != "executed":
            return {
                "error": row_click.get("error") or "ci_row_open_failed",
                "executed": False,
                "mutation_executed": False,
                "navigation_status": "blocked",
                "failed_stage": "ci_row_open",
                "ci_name": ci_name,
                "current_url": row_click.get("current_url"),
                "screenshot": row_click.get("screenshot"),
            }

        agent_click = self.click_semantic("Agent", exact=True, role="tab")
        stages.append("agent_tab_opened")
        if agent_click.get("error") or agent_click.get("click_status") != "executed":
            return {
                "error": agent_click.get("error") or "agent_tab_open_failed",
                "executed": False,
                "mutation_executed": False,
                "navigation_status": "blocked",
                "failed_stage": "agent_tab",
                "ci_name": ci_name,
                "current_url": agent_click.get("current_url"),
                "screenshot": agent_click.get("screenshot"),
            }

        tasks_click = self.click_semantic("Tasks", exact=True, role="tab")
        stages.append("tasks_tab_opened")
        if tasks_click.get("error") or tasks_click.get("click_status") != "executed":
            return {
                "error": tasks_click.get("error") or "tasks_tab_open_failed",
                "executed": False,
                "mutation_executed": False,
                "navigation_status": "blocked",
                "failed_stage": "tasks_tab",
                "ci_name": ci_name,
                "current_url": tasks_click.get("current_url"),
                "screenshot": tasks_click.get("screenshot"),
            }

        ci, task_page, _, context_error = (
            self._wait_for_observed_agent_task_context(ci_name)
        )
        if context_error:
            if (
                context_error.get("error") == "task_list_get_not_observed"
                and isinstance(ci, dict)
                and ci.get("id")
                and ci.get("agent_id")
            ):
                return {
                    "status": "ready_for_readiness",
                    "executed": True,
                    "mutation_executed": False,
                    "navigation_status": "ready",
                    "ci_name": ci_name,
                    "ci_id": ci.get("id"),
                    "agent_id": ci.get("agent_id"),
                    "task_list_observed": False,
                    "reason": "task_list_get_not_observed",
                    "navigation_stages": stages,
                    "current_url": tasks_click.get("current_url"),
                    "screenshot": tasks_click.get("screenshot"),
                }
            return {
                **context_error,
                "mutation_executed": False,
                "navigation_status": "blocked",
                "failed_stage": "task_list_observation",
                "ci_name": ci_name,
                "navigation_stages": stages,
                "current_url": tasks_click.get("current_url"),
                "screenshot": tasks_click.get("screenshot"),
            }

        return {
            "status": "ready",
            "executed": True,
            "mutation_executed": False,
            "navigation_status": "ready",
            "ci_name": ci_name,
            "ci_id": ci.get("id"),
            "agent_id": ci.get("agent_id"),
            "task_count": task_page.get("total"),
            "page_count": len(task_page.get("items") or []),
            "task_list_observed": True,
            "navigation_stages": stages,
            "current_url": tasks_click.get("current_url"),
            "screenshot": tasks_click.get("screenshot"),
        }

    def _same_https_origin_url(self, observed_url, path):
        source = urlsplit(observed_url)
        current = urlsplit(self.page.url)
        if (
            source.scheme != "https" or current.scheme != "https"
            or source.netloc != current.netloc
        ):
            return None
        return urlunsplit((source.scheme, source.netloc, path, "", ""))

    def create_managed_agent_task_semantic(
        self, ci_name: str, fixture_id: str,
    ):
        """Create one fixed harmless task; arbitrary commands are impossible."""
        self._ensure_started()
        fixture = MANAGED_AGENT_TASK_FIXTURES.get(str(fixture_id or ""))
        if fixture is None:
            return {"error": "managed_task_fixture_not_allowed", "executed": False}
        ci, _, observed_url, error = self._observed_agent_task_context(ci_name)
        if error:
            return error
        os_name = str(ci.get("os_name") or "").strip()
        os_name_normalized = os_name.casefold()
        if not os_name_normalized or not any(
            token in os_name_normalized
            for token in fixture["os_name_tokens"]
        ):
            return {
                "error": "managed_task_fixture_os_mismatch",
                "executed": False,
                "mutation_executed": False,
                "ci_name": ci_name,
                "fixture_id": fixture_id,
                "os_name": os_name or None,
            }
        source = urlsplit(observed_url)
        collection_url = self._same_https_origin_url(
            observed_url, source.path.rstrip("/"),
        )
        if collection_url is None:
            return {"error": "managed_task_origin_mismatch", "executed": False}

        marker = "UQA_EXEC_OK_" + uuid.uuid4().hex[:16]
        payload = {
            "name": fixture["task_name"],
            "additional_params": {
                "programm": fixture["program"],
                "arguments": [
                    *fixture["arguments_before_marker"],
                    marker,
                ],
            },
        }
        try:
            response = self.context.request.post(
                collection_url, data=payload, timeout=15000,
            )
            status = response.status
            created = response.json() if status == 201 else None
        except Exception:
            status, created = None, None
        if not isinstance(created, dict) or not created.get("id"):
            return {
                "error": "managed_task_create_failed",
                "executed": False,
                "create_status": status,
            }
        task_id = str(created["id"])
        if (
            created.get("agent_id") != ci.get("agent_id")
            or created.get("name") != fixture["task_name"]
        ):
            return {
                "error": "managed_task_create_identity_mismatch",
                "executed": False,
                "create_status": status,
            }
        self._managed_agent_tasks[task_id] = {
            "agent_id": ci["agent_id"],
            "ci_name": ci_name,
            "fixture_id": fixture_id,
            "expected_text": marker,
        }
        return {
            "status": "created",
            "executed": True,
            "mutation_executed": True,
            "create_status": status,
            "ci_name": ci_name,
            "agent_id": ci["agent_id"],
            "task_id": task_id,
            "task_name": fixture["task_name"],
            "fixture_id": fixture_id,
            "expected_marker_sha256": hashlib.sha256(marker.encode()).hexdigest(),
        }

    def inspect_managed_agent_task_result_semantic(
        self, ci_name: str, task_id: str,
    ):
        """Verify a managed task against its private marker."""
        from tools.agent_tasks import summarize_agent_task_full

        self._ensure_started()
        managed = self._managed_agent_tasks.get(str(task_id or ""))
        if not isinstance(managed, dict) or managed.get("ci_name") != ci_name:
            return {
                "error": "managed_task_private_fixture_unavailable",
                "executed": False,
            }
        ci, _, observed_url, context_error = self._observed_agent_task_context(
            ci_name
        )
        if context_error:
            return context_error
        source = urlsplit(observed_url)
        full_url = self._same_https_origin_url(
            observed_url,
            source.path.rstrip("/") + f"/{task_id}/full",
        )
        if full_url is None:
            return {"error": "task_result_origin_mismatch", "executed": False}
        managed_page = {
            "total": 1,
            "items": [{
                "id": task_id,
                "agent_id": managed["agent_id"],
                "name": "executeCommand",
            }],
        }
        result = None
        status = None
        poll_attempts = 0
        for poll_attempts in range(1, 7):
            try:
                response = self.context.request.get(full_url, timeout=15000)
                status = response.status
                full = response.json() if status == 200 else None
            except Exception:
                status, full = None, None
            result = summarize_agent_task_full(
                ci,
                managed_page,
                task_id,
                full,
                managed["expected_text"],
                0,
            )
            if (
                result.get("full_result_observed") is True
                and result.get("assertion_passed") in {True, False}
            ):
                break
            if poll_attempts < 6:
                self.page.wait_for_timeout(5000)
        if status != 200:
            result["inspection_status"] = "blocked"
            result["reason"] = "task_full_get_unavailable"
        result["full_http_status"] = status
        result["managed_poll_attempts"] = poll_attempts
        if isinstance(result, dict):
            result["managed_fixture_id"] = managed["fixture_id"]
            result["managed_fixture_verified"] = (
                result.get("assertion_passed") is True
            )
        return result

    def disable_agent_task_semantic(self, ci_name: str, task_id: str):
        """Disable one exact observed executeCommand task and verify by GET."""
        self._ensure_started()
        try:
            canonical_task_id = str(uuid.UUID(task_id))
        except (ValueError, TypeError, AttributeError):
            return {"error": "task_id_invalid", "executed": False}
        if canonical_task_id != task_id:
            return {"error": "task_id_invalid", "executed": False}
        ci, _, observed_url, error = self._observed_agent_task_context(ci_name)
        if error:
            return error
        source = urlsplit(observed_url)
        task_url = self._same_https_origin_url(
            observed_url, source.path.rstrip("/") + f"/{task_id}",
        )
        if task_url is None:
            return {"error": "managed_task_origin_mismatch", "executed": False}
        try:
            before_response = self.context.request.get(task_url, timeout=15000)
            before = before_response.json() if before_response.status == 200 else None
        except Exception:
            before = None
        if (
            not isinstance(before, dict)
            or before.get("id") != task_id
            or before.get("agent_id") != ci.get("agent_id")
            or before.get("name") != "executeCommand"
        ):
            return {"error": "managed_task_cleanup_identity_mismatch", "executed": False}
        already_disabled = before.get("enabled") in (0, False)
        mutation_status = None
        if not already_disabled:
            try:
                response = self.context.request.put(
                    task_url, data={"enabled": 0}, timeout=15000,
                )
                mutation_status = response.status
            except Exception:
                mutation_status = None
        try:
            verify_response = self.context.request.get(task_url, timeout=15000)
            verified = (
                verify_response.json() if verify_response.status == 200 else None
            )
        except Exception:
            verify_response, verified = None, None
        post_verified = bool(
            isinstance(verified, dict)
            and verified.get("id") == task_id
            and verified.get("agent_id") == ci.get("agent_id")
            and verified.get("name") == "executeCommand"
            and verified.get("enabled") in (0, False)
        )
        if not post_verified:
            return {
                "error": "managed_task_disable_not_verified",
                "executed": not already_disabled and mutation_status is not None,
                "mutation_status": mutation_status,
                "post_disable_verified": False,
            }
        return {
            "status": "ok",
            "executed": True,
            "mutation_executed": not already_disabled,
            "already_satisfied": already_disabled,
            "mutation_status": mutation_status,
            "post_disable_status": verify_response.status,
            "post_disable_verified": True,
            "ci_name": ci_name,
            "agent_id": ci["agent_id"],
            "task_id": task_id,
            "task_name": "executeCommand",
        }

    def get_state(self):
        self._ensure_started()
        self._reset_diagnostics()
        return self._capture_state("state")

    def set_viewport_semantic(self, profile):
        """Apply a fixed responsive viewport and report overflow metrics."""
        self._ensure_started()
        self._reset_diagnostics()
        profiles = {
            "mobile": {"width": 390, "height": 844},
            "tablet": {"width": 768, "height": 1024},
            "desktop": {"width": 1440, "height": 900},
        }
        normalized = str(profile or "").strip().casefold()
        viewport = profiles.get(normalized)
        if viewport is None:
            return {
                "error": "unsupported_viewport_profile",
                "requested_profile": normalized,
                "supported_profiles": list(profiles),
            }

        self.page.set_viewport_size(viewport)
        self.page.wait_for_timeout(50)
        metrics = self.page.evaluate(
            """
            () => {
                const root = document.documentElement;
                const body = document.body;
                const values = [
                    root ? root.scrollWidth : 0,
                    root ? root.offsetWidth : 0,
                    root ? root.clientWidth : 0,
                    body ? body.scrollWidth : 0,
                    body ? body.offsetWidth : 0,
                    body ? body.clientWidth : 0,
                ];
                const documentWidth = Math.max(...values);
                const viewportWidth = window.innerWidth;
                return {
                    viewport_width: viewportWidth,
                    viewport_height: window.innerHeight,
                    document_width: documentWidth,
                    document_height: Math.max(
                        root ? root.scrollHeight : 0,
                        body ? body.scrollHeight : 0
                    ),
                    horizontal_overflow: documentWidth > viewportWidth + 1,
                };
            }
            """
        )
        result = self._capture_state("set-viewport")
        result.update({
            "viewport_status": "applied",
            "viewport_profile": normalized,
            "viewport": dict(viewport),
            "responsive_metrics": metrics,
        })
        return result

    def inspect_accessibility_semantic(self):
        """Run a compact generic DOM accessibility audit."""
        self._ensure_started()
        self._reset_diagnostics()
        audit = self.page.evaluate(
            """
            () => {
                const visible = el => {
                    const style = getComputedStyle(el);
                    const box = el.getBoundingClientRect();
                    return !el.hidden
                        && style.display !== 'none'
                        && style.visibility !== 'hidden'
                        && box.width > 0
                        && box.height > 0;
                };
                const text = value => String(value || '')
                    .replace(/\s+/g, ' ').trim();
                const ariaRefText = (el, attribute) => text(
                    (el.getAttribute(attribute) || '')
                        .split(/\s+/).filter(Boolean)
                        .map(id => document.getElementById(id))
                        .filter(Boolean)
                        .map(node => node.innerText || node.textContent || '')
                        .join(' ')
                );
                const accessibleName = el => {
                    const labels = el.labels
                        ? Array.from(el.labels)
                            .map(label => label.innerText || label.textContent || '')
                        : [];
                    return text(
                        el.getAttribute('aria-label')
                        || ariaRefText(el, 'aria-labelledby')
                        || labels.join(' ')
                        || el.getAttribute('alt')
                        || el.getAttribute('title')
                        || el.innerText
                        || el.textContent
                        || el.value
                    );
                };
                const descriptor = el => ({
                    tag: el.tagName.toLowerCase(),
                    role: el.getAttribute('role') || '',
                    id: el.id || '',
                    type: el.getAttribute('type') || '',
                });

                const interactive = Array.from(document.querySelectorAll(
                    'button, a[href], input:not([type="hidden"]), select, '
                    + 'textarea, [role="button"], [role="link"], '
                    + '[role="checkbox"], [role="radio"], [role="tab"], '
                    + '[role="menuitem"], [role="option"], [role="treeitem"]'
                )).filter(visible);
                const unnamedInteractiveAll = interactive
                    .filter(el => !accessibleName(el));
                const unnamedInteractive = unnamedInteractiveAll
                    .slice(0, 50).map(descriptor);

                const images = Array.from(document.querySelectorAll('img'))
                    .filter(visible);
                const imagesMissingAltAll = images
                    .filter(el => !el.hasAttribute('alt'));
                const imagesMissingAlt = imagesMissingAltAll
                    .slice(0, 50).map(descriptor);

                const idCounts = new Map();
                for (const el of document.querySelectorAll('[id]')) {
                    idCounts.set(el.id, (idCounts.get(el.id) || 0) + 1);
                }
                const duplicateIdsAll = Array.from(idCounts.entries())
                    .filter(([, count]) => count > 1);
                const duplicateIds = duplicateIdsAll
                    .slice(0, 50).map(([id, count]) => ({id, count}));

                const brokenAriaReferences = [];
                const referenceAttributes = [
                    'aria-labelledby', 'aria-describedby', 'aria-controls'
                ];
                for (const el of document.querySelectorAll(
                    '[aria-labelledby], [aria-describedby], [aria-controls]'
                )) {
                    for (const attribute of referenceAttributes) {
                        const ids = (el.getAttribute(attribute) || '')
                            .split(/\s+/).filter(Boolean);
                        const missing = ids.filter(
                            id => !document.getElementById(id)
                        );
                        if (missing.length) {
                            brokenAriaReferences.push({
                                ...descriptor(el), attribute, missing
                            });
                        }
                    }
                }

                const issueCount = unnamedInteractiveAll.length
                    + imagesMissingAltAll.length
                    + duplicateIdsAll.length
                    + brokenAriaReferences.length;
                return {
                    accessibility_passed: issueCount === 0,
                    issue_count: issueCount,
                    visible_interactive_count: interactive.length,
                    unnamed_interactive_count: unnamedInteractiveAll.length,
                    unnamed_interactive: unnamedInteractive,
                    visible_image_count: images.length,
                    images_missing_alt_count: imagesMissingAltAll.length,
                    images_missing_alt: imagesMissingAlt,
                    duplicate_id_count: duplicateIdsAll.length,
                    duplicate_ids: duplicateIds,
                    broken_aria_reference_count: brokenAriaReferences.length,
                    broken_aria_references: brokenAriaReferences.slice(0, 50),
                };
            }
            """
        )
        result = self._capture_state("inspect-accessibility")
        result.update({
            "inspection_status": "observed",
            "accessibility_audit": audit,
        })
        return result

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

    def _file_input_target(self, field, exact=True):
        matches = self.page.get_by_label(field, exact=exact)
        candidates = []
        for index in range(min(matches.count(), 50)):
            candidate = matches.nth(index)
            usable = candidate.evaluate(
                """el => {
                    if (el.tagName !== 'INPUT' || el.type !== 'file') return false;
                    const visible = node => {
                        const style = getComputedStyle(node);
                        return !node.hidden && style.display !== 'none'
                            && style.visibility !== 'hidden'
                            && node.getClientRects().length > 0;
                    };
                    return visible(el) || Array.from(el.labels || []).some(visible);
                }"""
            )
            if usable:
                candidates.append(candidate)
        if len(candidates) != 1:
            return None, {
                "error": "file_input_not_unique",
                "field": field,
                "matches": len(candidates),
                "executed": False,
            }
        target = candidates[0]
        if target.get_attribute("disabled") is not None or target.get_attribute("aria-disabled") == "true":
            return None, {
                "error": "file_input_disabled",
                "field": field,
                "executed": False,
            }
        return target, None

    @staticmethod
    def _file_input_metadata(target):
        return target.evaluate(
            """el => ({
                accept: el.accept || '',
                multiple: el.multiple,
                file_count: el.files ? el.files.length : 0
            })"""
        )

    def inspect_file_input_semantic(self, field, exact=True):
        self._ensure_started()
        self._reset_diagnostics()
        target, error = self._file_input_target(field, exact)
        if error:
            return error
        result = self._capture_state("inspect-file-input-semantic")
        result.update({
            "file_field": field,
            "file_input": self._file_input_metadata(target),
            "mutation_executed": False,
        })
        return result

    def set_upload_fixture_semantic(self, field, fixture, exact=True):
        """Select a built-in harmless fixture; never read an arbitrary path."""
        self._ensure_started()
        self._reset_diagnostics()
        payload = UPLOAD_FIXTURES.get(str(fixture or ""))
        if payload is None:
            return {
                "error": "upload_fixture_not_allowed",
                "fixture": fixture,
                "executed": False,
            }
        target, error = self._file_input_target(field, exact)
        if error:
            return error
        before = self._file_input_metadata(target)
        accepted = [
            token.strip().casefold()
            for token in before["accept"].split(",")
            if token.strip()
        ]
        mime = payload["mimeType"].casefold()
        extension = Path(payload["name"]).suffix.casefold()
        if accepted and not any(
            token == mime
            or token == extension
            or (token.endswith("/*") and mime.startswith(token[:-1]))
            for token in accepted
        ):
            return {
                "error": "upload_fixture_type_not_accepted",
                "field": field,
                "fixture": fixture,
                "accept": before["accept"],
                "executed": False,
            }
        self._begin_action_execution()
        target.set_input_files(payload)
        self.page.wait_for_timeout(500)
        matching_statuses = []
        for event in self.network_events:
            if (
                event.get("action_execution_id") != self.active_action_execution_id
                or event.get("method") not in {"POST", "PUT", "PATCH"}
            ):
                continue
            detail = self.network_details.get(event.get("request_id"))
            if not detail:
                continue
            try:
                body = detail["request"].post_data_buffer or b""
            except Exception:
                continue
            if payload["buffer"] in body:
                matching_statuses.append(event["status"])
        transport_status = (
            "accepted_response_observed"
            if any(200 <= status < 300 for status in matching_statuses)
            else "rejected_response_observed"
            if any(status >= 400 for status in matching_statuses)
            else "not_observed"
        )
        after = target.evaluate(
            """el => {
                const file = el.files && el.files[0];
                return {
                    count: el.files ? el.files.length : 0,
                    name: file ? file.name : null,
                    type: file ? file.type : null,
                    size: file ? file.size : null
                };
            }"""
        )
        selected = (
            after["count"] == 1
            and after["name"] == payload["name"]
            and after["type"] == payload["mimeType"]
            and after["size"] == len(payload["buffer"])
        )
        result = self._capture_state("set-upload-fixture-semantic")
        result.update({
            "file_field": field,
            "upload_fixture": fixture,
            "file_before": before,
            "file_after": after,
            "file_status": "selected" if selected else "not_selected",
            "upload_transport_status": transport_status,
            "upload_transport_http_statuses": matching_statuses,
            "upload_persistence_verified": False,
            "mutation_executed": True,
        })
        result = self._finish_action_execution(result)
        if not selected:
            result["error"] = "upload_fixture_selection_not_observed"
        return result

    def set_staged_file_semantic(
        self, artifact_id, filename, content, field=None, trigger=None,
        exact=True,
    ):
        """Select only bytes supplied by trusted Job staging, never an LLM path."""
        self._ensure_started()
        self._reset_diagnostics()
        if (bool(field) + bool(trigger)) != 1:
            return {"error": "file_field_or_trigger_required", "executed": False}
        if (
            not isinstance(filename, str)
            or not filename
            or Path(filename).name != filename
            or "\\" in filename
            or not isinstance(content, bytes)
            or not content
        ):
            return {"error": "staged_file_payload_invalid", "executed": False}
        guessed_mime, encoding = mimetypes.guess_type(filename)
        mime = (
            "application/gzip" if encoding == "gzip"
            else guessed_mime or "application/octet-stream"
        )
        payload = {"name": filename, "mimeType": mime, "buffer": content}
        target = None
        if field:
            target, error = self._file_input_target(field, exact)
            if error:
                return error
            accept = target.get_attribute("accept") or ""
            allowed = [value.strip().casefold() for value in accept.split(",") if value.strip()]
            if allowed and not any(
                filename.casefold().endswith(value) if value.startswith(".")
                else mime.casefold().startswith(value[:-1]) if value.endswith("/*")
                else value == mime.casefold()
                for value in allowed
            ):
                return {"error": "staged_file_type_not_accepted", "executed": False}
        else:
            buttons = self.page.get_by_role("button", name=trigger, exact=exact)
            visible = [
                buttons.nth(i) for i in range(min(buttons.count(), 50))
                if buttons.nth(i).is_visible()
            ]
            if len(visible) != 1:
                return {
                    "error": "file_chooser_trigger_not_unique",
                    "matches": len(visible), "executed": False,
                }
            button = visible[0]
            if not button.is_enabled() or button.get_attribute("aria-disabled") == "true":
                return {"error": "file_chooser_trigger_disabled", "executed": False}
        self._begin_action_execution()
        if trigger:
            try:
                with self.page.expect_file_chooser(timeout=5000) as event:
                    button.click()
                chooser = event.value
                target = chooser.element
                chooser.set_files(payload)
            except PlaywrightTimeoutError:
                result = self._capture_state("file-chooser-not-observed")
                result.update({
                    "error": "file_chooser_not_observed_after_click",
                    "artifact_id": artifact_id,
                    "mutation_executed": True,
                })
                return self._finish_action_execution(result)
        else:
            target.set_input_files(payload)
        self.page.wait_for_timeout(500)
        actual = target.evaluate(
            """el => {
                const file = el.files && el.files[0];
                return {
                    count: el.files ? el.files.length : 0,
                    name: file ? file.name : null,
                    type: file ? file.type : null,
                    size: file ? file.size : null
                };
            }"""
        )
        selected = (
            actual["count"] == 1
            and actual["name"] == filename
            and actual["type"] == mime
            and actual["size"] == len(content)
        )
        result = self._capture_state("set-staged-file-semantic")
        result.update({
            "artifact_id": artifact_id,
            "file_field": field,
            "file_trigger": trigger,
            "file_after": actual,
            "file_status": "selected" if selected else "not_selected",
            "server_persistence_verified": False,
            "mutation_executed": True,
        })
        result = self._finish_action_execution(result)
        if not selected:
            result["error"] = "staged_file_selection_not_observed"
        return result

    def set_temporal_semantic(
        self,
        field: str,
        value: str,
        exact: bool = True,
    ):
        """Set one native date/time control using its canonical HTML value."""
        self._ensure_started()
        self._reset_diagnostics()
        supported_types = {
            "date",
            "time",
            "datetime-local",
            "month",
            "week",
        }

        def visible_temporal_matches(locator):
            matches = []
            for index in range(min(locator.count(), 50)):
                candidate = locator.nth(index)
                try:
                    if (
                        candidate.is_visible()
                        and candidate.evaluate(
                            "el => el.tagName.toLowerCase() === 'input'"
                        )
                        and str(
                            candidate.get_attribute("type") or ""
                        ).casefold() in supported_types
                    ):
                        matches.append(candidate)
                except Exception:
                    continue
            return matches

        target = None
        strategy = None
        for locator, candidate_strategy in (
            (self.page.get_by_label(field, exact=exact), "label"),
            (self.page.get_by_placeholder(field, exact=exact), "placeholder"),
        ):
            matches = visible_temporal_matches(locator)
            if len(matches) == 1:
                target = matches[0]
                strategy = candidate_strategy
                break
            if len(matches) > 1:
                return {
                    "error": "ambiguous_temporal_field",
                    "field": field,
                    "matches": len(matches),
                    "executed": False,
                }

        if target is None:
            nearby = self._visible_nearby_labeled_field_matches(
                field,
                exact,
            )
            matches = []
            for candidate in nearby:
                try:
                    if str(
                        candidate.get_attribute("type") or ""
                    ).casefold() in supported_types:
                        matches.append(candidate)
                except Exception:
                    continue
            if len(matches) == 1:
                target = matches[0]
                strategy = "nearby-visible-label"
            elif len(matches) > 1:
                return {
                    "error": "ambiguous_temporal_field",
                    "field": field,
                    "matches": len(matches),
                    "executed": False,
                }

        if target is None:
            controls = self.page.locator(
                "input[type=date], input[type=time], "
                "input[type=datetime-local], input[type=month], "
                "input[type=week]"
            )
            matches = []
            for index in range(min(controls.count(), 100)):
                candidate = controls.nth(index)
                try:
                    if not candidate.is_visible():
                        continue
                    metadata = [
                        candidate.get_attribute("name") or "",
                        candidate.get_attribute("aria-label") or "",
                        candidate.get_attribute("placeholder") or "",
                    ]
                    if _field_metadata_matches(metadata, field, exact):
                        matches.append(candidate)
                except Exception:
                    continue
            if len(matches) == 1:
                target = matches[0]
                strategy = "html-metadata"
            elif len(matches) > 1:
                return {
                    "error": "ambiguous_temporal_field",
                    "field": field,
                    "matches": len(matches),
                    "executed": False,
                }

        if target is None:
            return {
                "error": "temporal_field_not_found",
                "field": field,
                "supported_types": sorted(supported_types),
                "executed": False,
            }

        requested_value = str(value or "").strip()
        input_type = str(
            target.get_attribute("type") or ""
        ).casefold()
        if not target.is_enabled() or not target.is_editable():
            return {
                "error": "temporal_field_not_editable",
                "field": field,
                "temporal_input_type": input_type,
                "executed": False,
                "mutation_executed": False,
            }
        validation = target.evaluate(
            """
            (el, requested) => {
                const probe = el.cloneNode(true);
                probe.value = requested;
                return {
                    accepted_value: probe.value,
                    valid: probe.checkValidity(),
                    value_missing: probe.validity.valueMissing,
                    range_underflow: probe.validity.rangeUnderflow,
                    range_overflow: probe.validity.rangeOverflow,
                    step_mismatch: probe.validity.stepMismatch,
                    bad_input: probe.validity.badInput,
                    min: el.getAttribute('min'),
                    max: el.getAttribute('max'),
                    step: el.getAttribute('step')
                };
            }
            """,
            requested_value,
        )
        if (
            not requested_value
            or validation.get("accepted_value") != requested_value
            or not validation.get("valid")
        ):
            return {
                "error": "temporal_value_invalid_or_out_of_range",
                "field": field,
                "temporal_input_type": input_type,
                "requested_value": requested_value,
                "constraint_validation": validation,
                "executed": False,
                "mutation_executed": False,
            }

        previous = target.input_value()
        if previous == requested_value:
            result = self._capture_state("set-temporal-semantic")
            result.update(
                {
                    "temporal_field": field,
                    "temporal_input_type": input_type,
                    "requested_value": requested_value,
                    "previous_value": previous,
                    "actual_value": previous,
                    "temporal_status": "already_satisfied",
                    "constraint_validation": validation,
                    "temporal_match_strategy": strategy,
                    "mutation_executed": False,
                }
            )
            return result

        self._reset_diagnostics()
        self._begin_action_execution()
        target.fill(requested_value)
        self.page.wait_for_timeout(300)
        actual = target.input_value()
        actual_validation = target.evaluate(
            """
            el => ({
                valid: el.checkValidity(),
                value_missing: el.validity.valueMissing,
                range_underflow: el.validity.rangeUnderflow,
                range_overflow: el.validity.rangeOverflow,
                step_mismatch: el.validity.stepMismatch,
                bad_input: el.validity.badInput,
                min: el.getAttribute('min'),
                max: el.getAttribute('max'),
                step: el.getAttribute('step')
            })
            """
        )
        applied = actual == requested_value and actual_validation.get("valid")
        result = self._capture_state("set-temporal-semantic")
        result.update(
            {
                "temporal_field": field,
                "temporal_input_type": input_type,
                "requested_value": requested_value,
                "previous_value": previous,
                "actual_value": actual,
                "temporal_status": "applied" if applied else "not_applied",
                "constraint_validation": actual_validation,
                "temporal_match_strategy": strategy,
                "mutation_executed": True,
            }
        )
        result = self._finish_action_execution(result)
        if not applied:
            result["error"] = "temporal_value_not_applied"
        return result

    def set_slider_semantic(
        self,
        field: str,
        value,
        exact: bool = True,
    ):
        """Set one exact native or ARIA slider value and verify it."""
        self._ensure_started()
        self._reset_diagnostics()
        locator = self.page.get_by_role("slider", name=field, exact=exact)
        matches = []
        for index in range(min(locator.count(), 50)):
            candidate = locator.nth(index)
            try:
                if candidate.is_visible():
                    matches.append(candidate)
            except Exception:
                continue
        if len(matches) != 1:
            return {
                "error": (
                    "slider_not_found" if not matches else "ambiguous_slider"
                ),
                "field": field,
                "matches": len(matches),
                "executed": False,
            }
        target = matches[0]
        if not target.is_enabled():
            return {
                "error": "slider_not_enabled",
                "field": field,
                "executed": False,
                "mutation_executed": False,
            }

        metadata = target.evaluate(
            """
            el => {
                const native = el.matches('input[type="range"]');
                return {
                    adapter: native ? 'native-range' : 'aria-slider',
                    min: native ? (el.min || '0') : (el.getAttribute('aria-valuemin') || '0'),
                    max: native ? (el.max || '100') : (el.getAttribute('aria-valuemax') || '100'),
                    step: native ? (el.step || '1') : (
                        el.getAttribute('aria-valuestep')
                        || el.getAttribute('data-step')
                        || '1'
                    ),
                    current: native ? el.value : el.getAttribute('aria-valuenow'),
                    orientation: el.getAttribute('aria-orientation') || 'horizontal'
                };
            }
            """
        )
        try:
            requested = Decimal(str(value).strip())
            minimum = Decimal(str(metadata.get("min")))
            maximum = Decimal(str(metadata.get("max")))
            current = Decimal(str(metadata.get("current")))
            step_text = str(metadata.get("step") or "1").strip().casefold()
            if step_text == "any":
                raise ValueError("slider_step_any_unsupported")
            step = Decimal(step_text)
        except (InvalidOperation, TypeError, ValueError):
            return {
                "error": "invalid_slider_numeric_contract",
                "field": field,
                "slider_contract": metadata,
                "executed": False,
            }
        if step <= 0 or minimum > maximum:
            return {
                "error": "invalid_slider_numeric_contract",
                "field": field,
                "slider_contract": metadata,
                "executed": False,
            }
        if requested < minimum or requested > maximum:
            return {
                "error": "slider_value_out_of_range",
                "field": field,
                "requested_value": str(requested),
                "slider_contract": metadata,
                "executed": False,
                "mutation_executed": False,
            }
        if (requested - minimum) % step != 0:
            return {
                "error": "slider_value_step_mismatch",
                "field": field,
                "requested_value": str(requested),
                "slider_contract": metadata,
                "executed": False,
                "mutation_executed": False,
            }
        if current == requested:
            result = self._capture_state("set-slider-semantic")
            result.update(
                {
                    "slider_field": field,
                    "slider_adapter": metadata.get("adapter"),
                    "requested_value": str(requested),
                    "actual_value": str(current),
                    "slider_status": "already_satisfied",
                    "slider_contract": metadata,
                    "mutation_executed": False,
                }
            )
            return result

        delta_steps = (requested - current) / step
        if delta_steps != delta_steps.to_integral_value():
            return {
                "error": "slider_current_value_off_step",
                "field": field,
                "slider_contract": metadata,
                "executed": False,
            }
        step_count = abs(int(delta_steps))
        if step_count > 500:
            return {
                "error": "slider_step_limit_exceeded",
                "field": field,
                "required_steps": step_count,
                "executed": False,
            }

        orientation = str(metadata.get("orientation") or "horizontal")
        if delta_steps > 0:
            key = "ArrowUp" if orientation == "vertical" else "ArrowRight"
        else:
            key = "ArrowDown" if orientation == "vertical" else "ArrowLeft"
        self._reset_diagnostics()
        self._begin_action_execution()
        target.focus()
        for _ in range(step_count):
            target.press(key)
        self.page.wait_for_timeout(300)
        actual_text = target.evaluate(
            """
            el => el.matches('input[type="range"]')
                ? el.value
                : el.getAttribute('aria-valuenow')
            """
        )
        try:
            actual = Decimal(str(actual_text))
        except InvalidOperation:
            actual = None
        applied = actual == requested
        result = self._capture_state("set-slider-semantic")
        result.update(
            {
                "slider_field": field,
                "slider_adapter": metadata.get("adapter"),
                "requested_value": str(requested),
                "previous_value": str(current),
                "actual_value": str(actual_text),
                "slider_status": "applied" if applied else "not_applied",
                "slider_key": key,
                "slider_key_presses": step_count,
                "slider_contract": metadata,
                "mutation_executed": True,
            }
        )
        result = self._finish_action_execution(result)
        if not applied:
            result["error"] = "slider_value_not_applied"
        return result

    def _resolve_tree(self, tree=None, exact=True):
        candidates = (
            self.page.get_by_role("tree", name=tree, exact=exact)
            if tree
            else self.page.get_by_role("tree")
        )
        visible = []
        for index in range(min(candidates.count(), 50)):
            candidate = candidates.nth(index)
            try:
                if candidate.is_visible():
                    visible.append(candidate)
            except Exception:
                continue
        if len(visible) == 1:
            return visible[0], None
        return None, {
            "error": "tree_not_found" if not visible else "ambiguous_tree",
            "tree": tree,
            "matches": len(visible),
            "executed": False,
        }

    @staticmethod
    def _tree_snapshot(tree_locator):
        return tree_locator.evaluate(
            """
            tree => {
                const clean = value => String(value || '').replace(/\s+/g, ' ').trim();
                return Array.from(tree.querySelectorAll('[role="treeitem"]'))
                    .filter(item => {
                        const style = window.getComputedStyle(item);
                        return !item.hidden && style.display !== 'none'
                            && style.visibility !== 'hidden'
                            && item.getClientRects().length > 0;
                    }).slice(0, 500).map(item => {
                        const clone = item.cloneNode(true);
                        clone.querySelectorAll('[role="group"]').forEach(node => node.remove());
                        return {
                            name: clean(item.getAttribute('aria-label') || clone.textContent),
                            level: Number(item.getAttribute('aria-level')) || null,
                            expanded: item.hasAttribute('aria-expanded')
                                ? item.getAttribute('aria-expanded') === 'true' : null,
                            selected: item.hasAttribute('aria-selected')
                                ? item.getAttribute('aria-selected') === 'true' : null,
                            checked: item.hasAttribute('aria-checked')
                                ? item.getAttribute('aria-checked') : null,
                            disabled: item.getAttribute('aria-disabled') === 'true'
                        };
                    });
            }
            """
        )

    def inspect_tree_semantic(self, tree: str = None, exact: bool = True):
        self._ensure_started()
        self._reset_diagnostics()
        tree_locator, error = self._resolve_tree(tree, exact)
        if error:
            return error
        items = self._tree_snapshot(tree_locator)
        result = self._capture_state("inspect-tree-semantic")
        result.update(
            {
                "tree_name": tree,
                "tree_items": items,
                "visible_tree_item_count": len(items),
                "tree_inspection_status": "observed",
                "mutation_executed": False,
            }
        )
        return result

    def set_tree_item_expanded(
        self,
        item: str,
        expanded: bool,
        tree: str = None,
        exact: bool = True,
    ):
        self._ensure_started()
        self._reset_diagnostics()
        tree_locator, error = self._resolve_tree(tree, exact)
        if error:
            return error
        locator = tree_locator.get_by_role("treeitem", name=item, exact=exact)
        matches = []
        for index in range(min(locator.count(), 100)):
            candidate = locator.nth(index)
            try:
                if candidate.is_visible():
                    matches.append(candidate)
            except Exception:
                continue
        if len(matches) != 1:
            return {
                "error": (
                    "tree_item_not_found"
                    if not matches
                    else "ambiguous_tree_item"
                ),
                "tree": tree,
                "item": item,
                "matches": len(matches),
                "executed": False,
            }
        target = matches[0]
        raw_expanded = target.get_attribute("aria-expanded")
        if raw_expanded not in {"true", "false"}:
            return {
                "error": "tree_item_not_expandable",
                "tree": tree,
                "item": item,
                "executed": False,
            }
        if (
            target.get_attribute("aria-disabled") == "true"
            or not target.is_enabled()
        ):
            return {
                "error": "tree_item_not_enabled",
                "tree": tree,
                "item": item,
                "executed": False,
            }
        previous = raw_expanded == "true"
        desired = bool(expanded)
        before = self._tree_snapshot(tree_locator)
        if previous == desired:
            result = self._capture_state("set-tree-item-expanded")
            result.update(
                {
                    "tree_name": tree,
                    "tree_item": item,
                    "previous_expanded": previous,
                    "expanded": previous,
                    "tree_expand_status": "already_satisfied",
                    "tree_before": before,
                    "tree_after": before,
                    "mutation_executed": False,
                }
            )
            return result
        key = "ArrowRight" if desired else "ArrowLeft"
        self._reset_diagnostics()
        self._begin_action_execution()
        target.focus()
        target.press(key)
        self.page.wait_for_timeout(300)
        actual = target.get_attribute("aria-expanded") == "true"
        after = self._tree_snapshot(tree_locator)
        result = self._capture_state("set-tree-item-expanded")
        result.update(
            {
                "tree_name": tree,
                "tree_item": item,
                "previous_expanded": previous,
                "expanded": actual,
                "tree_expand_status": "applied" if actual == desired else "not_applied",
                "tree_key": key,
                "tree_before": before,
                "tree_after": after,
                "mutation_executed": True,
            }
        )
        result = self._finish_action_execution(result)
        if actual != desired:
            result["error"] = "tree_item_expand_not_applied"
        return result

    def set_tree_item_selected(
        self,
        item: str,
        selected: bool,
        tree: str = None,
        exact: bool = True,
    ):
        """Set an explicit aria-selected/aria-checked treeitem contract."""
        self._ensure_started()
        self._reset_diagnostics()
        tree_locator, error = self._resolve_tree(tree, exact)
        if error:
            return error
        locator = tree_locator.get_by_role("treeitem", name=item, exact=exact)
        matches = []
        for index in range(min(locator.count(), 100)):
            candidate = locator.nth(index)
            try:
                if candidate.is_visible():
                    matches.append(candidate)
            except Exception:
                continue
        if len(matches) != 1:
            return {
                "error": (
                    "tree_item_not_found"
                    if not matches
                    else "ambiguous_tree_item"
                ),
                "tree": tree,
                "item": item,
                "matches": len(matches),
                "executed": False,
            }
        target = matches[0]
        selected_attr = target.get_attribute("aria-selected")
        checked_attr = target.get_attribute("aria-checked")
        if selected_attr in {"true", "false"}:
            state_attribute = "aria-selected"
            previous = selected_attr == "true"
        elif checked_attr in {"true", "false"}:
            state_attribute = "aria-checked"
            previous = checked_attr == "true"
        else:
            return {
                "error": "tree_item_selection_contract_missing",
                "tree": tree,
                "item": item,
                "executed": False,
            }
        if (
            target.get_attribute("aria-disabled") == "true"
            or not target.is_enabled()
        ):
            return {
                "error": "tree_item_not_enabled",
                "tree": tree,
                "item": item,
                "executed": False,
            }
        desired = bool(selected)
        before = self._tree_snapshot(tree_locator)
        if previous == desired:
            result = self._capture_state("set-tree-item-selected")
            result.update(
                {
                    "tree_name": tree,
                    "tree_item": item,
                    "tree_selection_attribute": state_attribute,
                    "previous_selected": previous,
                    "selected": previous,
                    "tree_selection_status": "already_satisfied",
                    "tree_before": before,
                    "tree_after": before,
                    "mutation_executed": False,
                }
            )
            return result
        self._reset_diagnostics()
        self._begin_action_execution()
        target.focus()
        target.press("Space")
        self.page.wait_for_timeout(300)
        actual = target.get_attribute(state_attribute) == "true"
        after = self._tree_snapshot(tree_locator)
        result = self._capture_state("set-tree-item-selected")
        result.update(
            {
                "tree_name": tree,
                "tree_item": item,
                "tree_selection_attribute": state_attribute,
                "previous_selected": previous,
                "selected": actual,
                "tree_selection_status": (
                    "applied" if actual == desired else "not_applied"
                ),
                "tree_key": "Space",
                "tree_before": before,
                "tree_after": after,
                "mutation_executed": True,
            }
        )
        result = self._finish_action_execution(result)
        if actual != desired:
            result["error"] = "tree_item_selection_not_applied"
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
            "Control+A",
            "Control+Z",
            "Control+Y",
            "Control+Shift+Z",
            "Shift+Enter",
            "Alt+ArrowDown",
        }
        normalized = str(key or "").strip().replace("Ctrl+", "Control+")
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

        if canonical.startswith("Control+") and not target:
            return {
                "error": "keyboard_chord_target_required",
                "key": canonical,
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

    @staticmethod
    def _clipboard_target_is_sensitive(locator, semantic_name):
        attributes = [str(semantic_name or "")]
        for attribute in (
            "type",
            "name",
            "id",
            "autocomplete",
            "aria-label",
            "placeholder",
        ):
            try:
                attributes.append(locator.get_attribute(attribute) or "")
            except Exception:
                continue
        normalized = " ".join(attributes).casefold()
        sensitive_markers = (
            "password",
            "passwd",
            "passphrase",
            "token",
            "secret",
            "credential",
            "api-key",
            "apikey",
            "парол",
            "токен",
            "секрет",
        )
        return (
            str(locator.get_attribute("type") or "").casefold()
            == "password"
            or any(marker in normalized for marker in sensitive_markers)
        )

    def copy_value_semantic(
        self,
        source: str,
        exact: bool = True,
        role: str = None,
    ):
        """Copy a non-secret control value to session-private memory."""
        self._ensure_started()
        self._reset_diagnostics()
        locator, strategy, error = self._keyboard_target(
            source,
            exact,
            role,
        )
        if error:
            return error
        if self._clipboard_target_is_sensitive(locator, source):
            return {
                "error": "private_clipboard_sensitive_source_blocked",
                "source": source,
                "executed": False,
            }
        payload = locator.evaluate(
            """
            el => {
                const tag = el.tagName.toLowerCase();
                if (tag === 'input' || tag === 'textarea') {
                    const value = String(el.value || '');
                    const start = Number.isInteger(el.selectionStart)
                        ? el.selectionStart : 0;
                    const end = Number.isInteger(el.selectionEnd)
                        ? el.selectionEnd : 0;
                    return {
                        supported: true,
                        text: end > start ? value.slice(start, end) : value,
                        mode: end > start ? 'selection' : 'value'
                    };
                }
                if (el.isContentEditable) {
                    const selection = window.getSelection();
                    const selected = selection ? selection.toString() : '';
                    return {
                        supported: true,
                        text: selected || el.innerText || '',
                        mode: selected ? 'selection' : 'contenteditable'
                    };
                }
                return {supported: false, text: '', mode: null};
            }
            """
        )
        if not payload.get("supported"):
            return {
                "error": "private_clipboard_source_not_editable",
                "source": source,
                "executed": False,
            }
        text = str(payload.get("text") or "")
        if len(text) > 4096:
            return {
                "error": "private_clipboard_value_too_large",
                "source": source,
                "character_count": len(text),
                "maximum_characters": 4096,
                "executed": False,
            }
        self._private_clipboard_text = text
        self._private_clipboard_source = source
        return {
            "status": "copied_to_private_clipboard",
            "source": source,
            "source_strategy": strategy,
            "copy_mode": payload.get("mode"),
            "character_count": len(text),
            "clipboard_scope": "browser_session_private",
            "clipboard_content_exposed": False,
            "mutation_executed": False,
            "executed": True,
        }

    def paste_private_semantic(
        self,
        target: str,
        replace: bool = False,
        exact: bool = True,
        role: str = None,
    ):
        """Insert the private clipboard without touching the OS clipboard."""
        self._ensure_started()
        self._reset_diagnostics()
        if self._private_clipboard_text is None:
            return {
                "error": "private_clipboard_empty",
                "target": target,
                "executed": False,
            }
        locator, strategy, error = self._keyboard_target(
            target,
            exact,
            role,
        )
        if error:
            return error
        if self._clipboard_target_is_sensitive(locator, target):
            return {
                "error": "private_clipboard_sensitive_target_blocked",
                "target": target,
                "executed": False,
            }
        editable = locator.evaluate(
            "el => !el.disabled && !el.readOnly && "
            "(el.matches('input, textarea') || el.isContentEditable)"
        )
        if not editable:
            return {
                "error": "private_clipboard_target_not_editable",
                "target": target,
                "executed": False,
            }

        self._begin_action_execution()
        locator.focus()
        if replace:
            locator.fill(self._private_clipboard_text)
        else:
            self.page.keyboard.insert_text(self._private_clipboard_text)
        self.page.wait_for_timeout(300)
        result = self._capture_state("paste-private-semantic")
        result.update(
            {
                "status": "pasted_from_private_clipboard",
                "clipboard_source": self._private_clipboard_source,
                "clipboard_target": target,
                "clipboard_target_strategy": strategy,
                "replace": bool(replace),
                "character_count": len(self._private_clipboard_text),
                "clipboard_scope": "browser_session_private",
                "clipboard_content_exposed": False,
                "mutation_executed": True,
                "post_action_wait_ms": 300,
            }
        )
        return self._finish_action_execution(result)

    def clear_private_clipboard(self):
        had_value = self._private_clipboard_text is not None
        self._private_clipboard_text = None
        self._private_clipboard_source = None
        return {
            "status": "private_clipboard_cleared",
            "had_value": had_value,
            "clipboard_scope": "browser_session_private",
            "mutation_executed": False,
            "executed": True,
        }

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

    @staticmethod
    def _ordered_semantic_items(container_locator):
        return container_locator.evaluate(
            """
            root => {
                const selector = [
                    '[role="listitem"]', 'li', '[role="row"]', 'tr',
                    '[role="option"]', '[role="treeitem"]', '[role="tab"]',
                    '[draggable="true"]', '[aria-grabbed]'
                ].join(',');
                const visible = el => {
                    const style = window.getComputedStyle(el);
                    const box = el.getBoundingClientRect();
                    return !el.hidden
                        && style.display !== 'none'
                        && style.visibility !== 'hidden'
                        && box.width > 0
                        && box.height > 0;
                };
                const name = el => {
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
                        || ''
                    ).replace(/\s+/g, ' ').trim();
                };
                return Array.from(root.querySelectorAll(selector))
                    .filter(visible)
                    .filter(el => {
                        const parentItem = el.parentElement
                            ? el.parentElement.closest(selector)
                            : null;
                        return !parentItem || !root.contains(parentItem);
                    })
                    .slice(0, 200)
                    .map(el => ({
                        name: name(el),
                        role: el.getAttribute('role') || el.tagName.toLowerCase()
                    }))
                    .filter(item => item.name);
            }
            """
        )

    @staticmethod
    def _order_comparison(actual, expected, mode):
        actual_keys = [str(value).casefold() for value in actual]
        expected_keys = [str(value).casefold() for value in expected]
        if mode == "subsequence":
            cursor = 0
            for expected_index, wanted in enumerate(expected_keys):
                try:
                    actual_index = actual_keys.index(wanted, cursor)
                except ValueError:
                    return False, {
                        "expected_index": expected_index,
                        "expected": expected[expected_index],
                        "actual_index": None,
                    }
                cursor = actual_index + 1
            return True, None

        limit = max(len(actual_keys), len(expected_keys))
        for index in range(limit):
            actual_value = actual[index] if index < len(actual) else None
            expected_value = expected[index] if index < len(expected) else None
            if (
                index >= len(actual_keys)
                or index >= len(expected_keys)
                or actual_keys[index] != expected_keys[index]
            ):
                return False, {
                    "index": index,
                    "expected": expected_value,
                    "actual": actual_value,
                }
        return True, None

    def inspect_order_semantic(
        self,
        container: str,
        expected_order: list = None,
        mode: str = "exact",
        exact: bool = True,
        role: str = None,
    ):
        """Read the visual/DOM order of top-level semantic items."""
        self._ensure_started()
        self._reset_diagnostics()
        canonical_mode = str(mode or "exact").strip().casefold()
        if canonical_mode not in {"exact", "subsequence"}:
            return {
                "error": "unsupported_order_comparison_mode",
                "mode": mode,
                "executed": False,
            }
        expected = [
            str(value or "").strip()
            for value in (expected_order or [])
            if str(value or "").strip()
        ]
        if expected_order is not None and len(expected) < 2:
            return {
                "error": "expected_order_requires_two_items",
                "executed": False,
            }
        if len(expected) > 100:
            return {
                "error": "expected_order_too_large",
                "item_count": len(expected),
                "executed": False,
            }
        locator, strategy, error = self._pointer_target(
            container,
            exact,
            role,
        )
        if error:
            error["order_endpoint"] = "container"
            return error
        items = self._ordered_semantic_items(locator)
        observed = [item["name"] for item in items]
        if not observed:
            return {
                "error": "ordered_items_not_found",
                "container": container,
                "executed": False,
            }
        matched = None
        mismatch = None
        if expected_order is not None:
            matched, mismatch = self._order_comparison(
                observed,
                expected,
                canonical_mode,
            )
        result = self._capture_state("inspect-order-semantic")
        result.update(
            {
                "order_container": container,
                "container_match_strategy": strategy,
                "observed_order": observed,
                "ordered_items": items,
                "expected_order": expected if expected_order is not None else None,
                "order_comparison_mode": canonical_mode,
                "order_status": (
                    "observed"
                    if expected_order is None
                    else "matched"
                    if matched
                    else "mismatch"
                ),
                "order_mismatch": mismatch,
                "mutation_executed": False,
                "executed": True,
            }
        )
        return result

    def drag_semantic(
        self,
        source: str,
        target: str,
        exact: bool = True,
        source_role: str = None,
        target_role: str = None,
        order_container: str = None,
        expected_order: list = None,
        order_mode: str = "exact",
        container_role: str = None,
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
        if expected_order is not None and not order_container:
            return {
                "error": "drag_order_container_required",
                "executed": False,
            }

        order_locator = None
        order_before = None
        order_strategy = None
        canonical_order_mode = str(order_mode or "exact").strip().casefold()
        if canonical_order_mode not in {"exact", "subsequence"}:
            return {
                "error": "unsupported_order_comparison_mode",
                "mode": order_mode,
                "executed": False,
            }
        normalized_expected_order = [
            str(value or "").strip()
            for value in (expected_order or [])
            if str(value or "").strip()
        ]
        if expected_order is not None and len(normalized_expected_order) < 2:
            return {
                "error": "expected_order_requires_two_items",
                "executed": False,
            }
        if order_container:
            order_locator, order_strategy, error = self._pointer_target(
                order_container,
                exact,
                container_role,
            )
            if error:
                error["drag_endpoint"] = "order_container"
                return error
            order_before = [
                item["name"]
                for item in self._ordered_semantic_items(order_locator)
            ]
            if not order_before:
                return {
                    "error": "ordered_items_not_found",
                    "container": order_container,
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
        order_after = (
            [
                item["name"]
                for item in self._ordered_semantic_items(order_locator)
            ]
            if order_locator is not None
            else None
        )
        order_matched = None
        order_mismatch = None
        if expected_order is not None:
            order_matched, order_mismatch = self._order_comparison(
                order_after or [],
                normalized_expected_order,
                canonical_order_mode,
            )
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
                "order_container": order_container,
                "order_container_match_strategy": order_strategy,
                "order_before": order_before,
                "order_after": order_after,
                "expected_order": (
                    normalized_expected_order
                    if expected_order is not None
                    else None
                ),
                "order_comparison_mode": canonical_order_mode,
                "order_status": (
                    None
                    if expected_order is None
                    else "matched"
                    if order_matched
                    else "mismatch"
                ),
                "order_mismatch": order_mismatch,
                "mutation_executed": True,
                "post_action_wait_ms": 500,
            }
        )
        result = self._finish_action_execution(result)
        if expected_order is not None and not order_matched:
            result["error"] = "drag_order_not_applied"
        return result

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

    def _table_selection_identity(
        self,
        table_locator,
        table_name,
        snapshot,
    ):
        """Return a pagination-stable, case-local table identity."""
        resolved_name = str(table_name or "").strip()
        if not resolved_name:
            resolved_name = table_locator.evaluate(
                """
                table => {
                    const clean = value => String(value || '')
                        .replace(/\\s+/g, ' ').trim();
                    const labelledBy = clean(
                        table.getAttribute('aria-labelledby')
                    );
                    const label = labelledBy
                        ? clean(document.getElementById(labelledBy)?.textContent)
                        : '';
                    return clean(
                        table.getAttribute('aria-label')
                        || label
                        || table.querySelector('caption')?.textContent
                        || ''
                    );
                }
                """
            )
        resolved_name = resolved_name or "unnamed-table"
        parsed = urlsplit(str(self.page.url or ""))
        if parsed.scheme in {"http", "https"}:
            page_scope = (
                f"{parsed.scheme}://{parsed.netloc}{parsed.path or '/'}"
            )
        else:
            page_scope = str(self.page.url or "").split("?", 1)[0]
        header_names = [
            str(item.get("name") or "").strip()
            for item in snapshot.get("headers", [])
            if isinstance(item, dict)
        ]
        payload = {
            "page_scope": page_scope,
            "table_name": resolved_name,
            "headers": header_names,
        }
        key = "tbl-" + hashlib.sha256(
            json.dumps(
                payload,
                ensure_ascii=False,
                sort_keys=True,
            ).encode("utf-8")
        ).hexdigest()[:16]
        return key, resolved_name, page_scope, header_names

    @staticmethod
    def _table_page_signature(snapshot):
        return "page-" + hashlib.sha256(
            json.dumps(
                snapshot.get("row_signature") or [],
                ensure_ascii=False,
                sort_keys=True,
            ).encode("utf-8")
        ).hexdigest()[:16]

    def inspect_table_semantic(
        self,
        table: str = None,
        exact: bool = True,
    ):
        """Return a bounded structured snapshot of one visible table."""
        self._ensure_started()
        self._reset_diagnostics()
        locator, error = self._resolve_table(table, exact)

        resolution = "named" if table else "unique_visible"

        # Read-only inspection may safely recover when the model supplied a
        # visual section name but the page exposes one unlabeled HTML table.
        # Mutating table helpers intentionally keep strict named resolution.
        if error and table and error.get("error") == "table_not_found":
            fallback, fallback_error = self._resolve_table(None, exact)

            if fallback_error is None:
                locator = fallback
                error = None
                resolution = "unique_visible_fallback"

        if error:
            return error
        summary = self._table_snapshot(locator)
        result = self._capture_state("inspect-table-semantic")
        result.update(
            {
                "table_name": table,
                "table_resolution": resolution,
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
        if not headers:
            raw_headers = table_locator.locator(
                'thead th, [role="columnheader"]'
            )
            for index in range(min(raw_headers.count(), 100)):
                candidate = raw_headers.nth(index)
                if not candidate.is_visible():
                    continue
                plain_name = candidate.evaluate(
                    """
                    el => {
                        const clone = el.cloneNode(true);
                        clone.querySelectorAll(
                            'button, input, select, textarea, '
                            + '[role="button"], [role="combobox"]'
                        ).forEach(node => node.remove());
                        return (clone.innerText || clone.textContent || '')
                            .replace(/\s+/g, ' ').trim();
                    }
                    """
                )
                matched = (
                    plain_name.casefold() == str(column).casefold()
                    if exact
                    else str(column).casefold() in plain_name.casefold()
                )
                if matched:
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
        table: str = None,
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
        table_locator, error = self._resolve_table(table, exact)
        if error:
            return error
        table_snapshot = self._table_snapshot(table_locator)
        (
            table_selection_key,
            resolved_table_name,
            table_page_scope,
            table_header_names,
        ) = self._table_selection_identity(
            table_locator,
            table,
            table_snapshot,
        )
        table_page_signature = self._table_page_signature(table_snapshot)
        row_matches = []
        rows = table_locator.locator("tr")
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
                "table": table,
                "matches": len(row_matches),
                "executed": False,
            }

        row = row_matches[0]
        selected_row_cells = [
            " ".join(value.split())
            for value in row.locator(
                ":scope > td, :scope > th"
            ).all_inner_texts()
        ]
        table_row_key = "row-" + hashlib.sha256(
            json.dumps(
                selected_row_cells,
                ensure_ascii=False,
            ).encode("utf-8")
        ).hexdigest()[:16]
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
                "table": table,
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
                    "table_row_key": table_row_key,
                    "table_row_cells": selected_row_cells[:50],
                    "table_name": resolved_table_name,
                    "table_selection_key": table_selection_key,
                    "table_page_scope": table_page_scope,
                    "table_page_signature": table_page_signature,
                    "table_header_names": table_header_names,
                    "table_visible_row_count": table_snapshot.get(
                        "visible_row_count"
                    ),
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
                "table_row_key": table_row_key,
                "table_row_cells": selected_row_cells[:50],
                "table_name": resolved_table_name,
                "table_selection_key": table_selection_key,
                "table_page_scope": table_page_scope,
                "table_page_signature": table_page_signature,
                "table_header_names": table_header_names,
                "table_visible_row_count": table_snapshot.get(
                    "visible_row_count"
                ),
                "previous_selected": previous,
                "selected": actual,
                "row_selection_status": (
                    (
                        "selected" if actual else "deselected"
                    )
                    if actual == desired
                    else "not_applied"
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

    def _controlled_popover(self, trigger, exact=True):
        buttons = self.page.get_by_role("button", name=trigger, exact=exact)
        visible = [
            buttons.nth(i)
            for i in range(min(buttons.count(), 50))
            if buttons.nth(i).is_visible()
        ]
        if len(visible) != 1:
            return None, None, {
                "error": "popover_trigger_not_unique",
                "matches": len(visible), "executed": False,
            }
        button = visible[0]
        controlled_id = str(button.get_attribute("aria-controls") or "").strip()
        if not controlled_id or any(ch.isspace() for ch in controlled_id):
            return None, None, {
                "error": "popover_missing_aria_controls", "executed": False,
            }
        popup = self.page.locator("[id=" + json.dumps(controlled_id) + "]")
        if popup.count() != 1:
            return None, None, {
                "error": "popover_target_not_unique",
                "matches": popup.count(), "executed": False,
            }
        return button, popup, None

    @staticmethod
    def _popover_snapshot(popup):
        return popup.evaluate(
            """
            root => {
                const clean = x => String(x || '').replace(/\s+/g, ' ').trim();
                const controls = Array.from(root.querySelectorAll(
                    'button, input, select, textarea, [role="menuitem"], '
                    + '[role="option"], [role="checkbox"]'
                )).filter(el => {
                    const style = getComputedStyle(el);
                    return !el.hidden && style.display !== 'none'
                        && style.visibility !== 'hidden'
                        && el.getClientRects().length > 0;
                }).slice(0, 100).map(el => ({
                    role: el.getAttribute('role'),
                    type: el.getAttribute('type'),
                    selected: el.hasAttribute('aria-selected')
                        ? el.getAttribute('aria-selected') === 'true' : null,
                    name: clean(el.getAttribute('aria-label') || el.innerText
                        || el.getAttribute('placeholder') || el.textContent).slice(0, 200),
                    disabled: el.matches(':disabled') || el.getAttribute('aria-disabled') === 'true'
                }));
                return {
                    role: root.getAttribute('role'),
                    name: clean(root.getAttribute('aria-label')).slice(0, 200),
                    text: clean(root.innerText || root.textContent).slice(0, 2000),
                    controls
                };
            }
            """
        )

    def inspect_popover_semantic(self, trigger, exact=True):
        self._ensure_started()
        self._reset_diagnostics()
        _, popup, error = self._controlled_popover(trigger, exact)
        if error:
            return error
        if not popup.is_visible():
            return {"error": "popover_not_open", "executed": False}
        result = self._capture_state("inspect-popover-semantic")
        result.update({
            "popover_trigger": trigger,
            "popover_id": popup.get_attribute("id"),
            "popover_snapshot": self._popover_snapshot(popup),
            "popover_status": "observed", "mutation_executed": False,
        })
        return result

    def open_popover_semantic(self, trigger, exact=True):
        self._ensure_started()
        self._reset_diagnostics()
        button, popup, error = self._controlled_popover(trigger, exact)
        if error:
            return error
        if popup.is_visible():
            result = self.inspect_popover_semantic(trigger, exact)
            result["popover_status"] = "already_open"
            return result
        self._begin_action_execution()
        button.click()
        self.page.wait_for_timeout(200)
        opened = popup.is_visible()
        result = self._capture_state("open-popover-semantic")
        result.update({
            "popover_trigger": trigger, "popover_id": popup.get_attribute("id"),
            "popover_status": "opened" if opened else "not_opened",
            "popover_snapshot": self._popover_snapshot(popup) if opened else None,
            "mutation_executed": False,
        })
        result = self._finish_action_execution(result)
        if not opened:
            result["error"] = "popover_open_not_observed"
        return result

    def select_popover_option_semantic(
        self, trigger, option, exact=True,
    ):
        """Select one explicit ARIA option inside an already-open popup."""
        self._ensure_started()
        self._reset_diagnostics()
        _, popup, error = self._controlled_popover(trigger, exact)
        if error:
            return error
        if not popup.is_visible():
            return {"error": "popover_not_open", "executed": False}
        candidates = popup.get_by_role("option", name=option, exact=exact)
        visible = [
            candidates.nth(i)
            for i in range(min(candidates.count(), 100))
            if candidates.nth(i).is_visible()
        ]
        if len(visible) != 1:
            return {
                "error": "popover_option_not_unique",
                "option": option,
                "matches": len(visible),
                "executed": False,
            }
        target = visible[0]
        prior = target.get_attribute("aria-selected")
        if prior not in {"true", "false"}:
            return {
                "error": "popover_option_selection_contract_missing",
                "option": option,
                "executed": False,
            }
        if target.get_attribute("aria-disabled") == "true" or not target.is_enabled():
            return {
                "error": "popover_option_disabled",
                "option": option,
                "executed": False,
            }
        if prior == "true":
            result = self._capture_state("select-popover-option-semantic")
            result.update({
                "popover_trigger": trigger,
                "popover_option": option,
                "popover_option_status": "already_selected",
                "selected": True,
                "mutation_executed": False,
            })
            return result
        before = self._popover_snapshot(popup)
        self._reset_diagnostics()
        self._begin_action_execution()
        target.click()
        self.page.wait_for_timeout(200)
        selected = target.get_attribute("aria-selected") == "true"
        result = self._capture_state("select-popover-option-semantic")
        result.update({
            "popover_trigger": trigger,
            "popover_option": option,
            "popover_option_status": "selected" if selected else "not_selected",
            "selected": selected,
            "popover_before": before,
            "popover_after": self._popover_snapshot(popup) if popup.is_visible() else None,
            "mutation_executed": True,
        })
        result = self._finish_action_execution(result)
        if not selected:
            result["error"] = "popover_option_selection_not_observed"
        return result

    def click_popover_button_semantic(
        self, trigger, button, exact=True,
    ):
        """Click one enabled button in an already-open controlled popup."""
        self._ensure_started()
        self._reset_diagnostics()
        _, popup, error = self._controlled_popover(trigger, exact)
        if error:
            return error
        if not popup.is_visible():
            return {"error": "popover_not_open", "executed": False}
        candidates = popup.get_by_role("button", name=button, exact=exact)
        visible = [
            candidates.nth(i)
            for i in range(min(candidates.count(), 100))
            if candidates.nth(i).is_visible()
        ]
        if len(visible) != 1:
            return {
                "error": "popover_button_not_unique",
                "button": button,
                "matches": len(visible),
                "executed": False,
            }
        target = visible[0]
        if target.get_attribute("aria-disabled") == "true" or not target.is_enabled():
            return {
                "error": "popover_button_disabled",
                "button": button,
                "executed": False,
            }
        before = self._popover_snapshot(popup)
        self._begin_action_execution()
        target.click()
        self.page.wait_for_timeout(200)
        still_open = popup.is_visible()
        result = self._capture_state("click-popover-button-semantic")
        result.update({
            "popover_trigger": trigger,
            "popover_button": button,
            "popover_button_status": "clicked",
            "popover_before": before,
            "popover_after": self._popover_snapshot(popup) if still_open else None,
            "popover_open_after": still_open,
            "mutation_executed": True,
        })
        return self._finish_action_execution(result)

    def close_popover_semantic(self, trigger, exact=True):
        self._ensure_started()
        self._reset_diagnostics()
        button, popup, error = self._controlled_popover(trigger, exact)
        if error:
            return error
        if not popup.is_visible():
            result = self._capture_state("close-popover-semantic")
            result.update({"popover_status": "already_closed", "mutation_executed": False})
            return result
        before = self._popover_snapshot(popup)
        self._begin_action_execution()
        button.focus()
        button.press("Escape")
        self.page.wait_for_timeout(200)
        closed = not popup.is_visible()
        result = self._capture_state("close-popover-semantic")
        result.update({
            "popover_trigger": trigger, "popover_id": popup.get_attribute("id"),
            "popover_before": before,
            "popover_status": "closed" if closed else "not_closed",
            "mutation_executed": False,
        })
        result = self._finish_action_execution(result)
        if not closed:
            result["error"] = "popover_close_not_observed"
        return result

    @staticmethod
    def _calendar_snapshot(popup):
        return popup.evaluate(
            """
            root => {
                const clean = value => String(value || '')
                    .replace(/\s+/g, ' ').trim();
                const visible = el => {
                    const style = getComputedStyle(el);
                    return !el.hidden && style.display !== 'none'
                        && style.visibility !== 'hidden'
                        && el.getClientRects().length > 0;
                };
                const options = Array.from(root.querySelectorAll(
                    '[role="gridcell"], [data-date], time[datetime]'
                )).filter(visible).slice(0, 100).map(el => ({
                    name: clean(
                        el.getAttribute('aria-label')
                        || el.getAttribute('data-date')
                        || el.getAttribute('datetime')
                        || el.innerText || el.textContent
                    ).slice(0, 200),
                    date: clean(
                        el.getAttribute('data-date')
                        || el.getAttribute('datetime')
                    ).slice(0, 100),
                    selected: el.getAttribute('aria-selected') === 'true'
                        || el.getAttribute('data-selected') === 'true',
                    disabled: el.matches(':disabled')
                        || el.getAttribute('aria-disabled') === 'true'
                }));
                return {
                    role: root.getAttribute('role') || '',
                    name: clean(root.getAttribute('aria-label')).slice(0, 200),
                    grid_count: root.querySelectorAll('[role="grid"]').length,
                    options
                };
            }
            """
        )

    def inspect_calendar_semantic(self, trigger, exact=True):
        self._ensure_started()
        self._reset_diagnostics()
        _, popup, error = self._controlled_popover(trigger, exact)
        if error:
            return error
        if not popup.is_visible():
            return {"error": "calendar_not_open", "executed": False}
        snapshot = self._calendar_snapshot(popup)
        if snapshot.get("grid_count", 0) < 1:
            return {
                "error": "calendar_grid_not_found",
                "executed": False,
                "calendar_snapshot": snapshot,
            }
        result = self._capture_state("inspect-calendar-semantic")
        result.update({
            "calendar_trigger": trigger,
            "calendar_status": "observed",
            "calendar_snapshot": snapshot,
            "mutation_executed": False,
        })
        return result

    def open_calendar_semantic(self, trigger, exact=True):
        result = self.open_popover_semantic(trigger, exact)
        if result.get("error"):
            return result
        _, popup, error = self._controlled_popover(trigger, exact)
        if error:
            return error
        snapshot = self._calendar_snapshot(popup)
        if snapshot.get("grid_count", 0) < 1:
            result.update({
                "error": "calendar_grid_not_found",
                "calendar_status": "contract_not_observed",
                "calendar_snapshot": snapshot,
            })
            return result
        result.update({
            "calendar_trigger": trigger,
            "calendar_status": (
                "already_open"
                if result.get("popover_status") == "already_open"
                else "opened"
            ),
            "calendar_snapshot": snapshot,
        })
        return result

    def select_calendar_option_semantic(
        self, trigger, option, exact=True,
    ):
        self._ensure_started()
        self._reset_diagnostics()
        button, popup, error = self._controlled_popover(trigger, exact)
        if error:
            return error
        if not popup.is_visible():
            return {"error": "calendar_not_open", "executed": False}
        snapshot = self._calendar_snapshot(popup)
        if snapshot.get("grid_count", 0) < 1:
            return {"error": "calendar_grid_not_found", "executed": False}

        wanted = str(option or "").strip()
        candidates = popup.locator(
            '[role="gridcell"], [data-date], time[datetime]'
        )
        matches = []
        for index in range(min(candidates.count(), 100)):
            candidate = candidates.nth(index)
            try:
                if not candidate.is_visible():
                    continue
                names = candidate.evaluate(
                    """
                    el => [
                        el.getAttribute('aria-label') || '',
                        el.getAttribute('data-date') || '',
                        el.getAttribute('datetime') || '',
                        el.innerText || el.textContent || ''
                    ].map(value => String(value).replace(/\s+/g, ' ').trim())
                     .filter(Boolean)
                    """
                )
                matched = (
                    any(name == wanted for name in names)
                    if exact
                    else any(wanted.casefold() in name.casefold() for name in names)
                )
                if matched:
                    matches.append(candidate)
            except Exception:
                continue
        if len(matches) != 1:
            return {
                "error": (
                    "calendar_option_not_found"
                    if not matches
                    else "ambiguous_calendar_option"
                ),
                "option": wanted,
                "matches": len(matches),
                "executed": False,
            }
        target = matches[0]
        if (
            not target.is_enabled()
            or target.get_attribute("aria-disabled") == "true"
        ):
            return {
                "error": "calendar_option_disabled",
                "option": wanted,
                "executed": False,
            }
        before = button.evaluate(
            "el => ({text: (el.innerText || '').trim(), value: el.value || ''})"
        )
        self._begin_action_execution()
        target.click()
        self.page.wait_for_timeout(200)
        after = button.evaluate(
            "el => ({text: (el.innerText || '').trim(), value: el.value || ''})"
        )
        popup_open = popup.is_visible()
        selected = False
        try:
            selected = target.evaluate(
                """
                el => el.getAttribute('aria-selected') === 'true'
                    || el.getAttribute('data-selected') === 'true'
                """
            )
        except Exception:
            selected = False
        trigger_changed = before != after
        verified = bool(selected or trigger_changed or not popup_open)
        result = self._capture_state("select-calendar-option-semantic")
        result.update({
            "calendar_trigger": trigger,
            "calendar_option": wanted,
            "calendar_status": "selected" if verified else "not_verified",
            "selection_verified": verified,
            "selected_state_observed": selected,
            "trigger_changed": trigger_changed,
            "calendar_open_after": popup_open,
            "mutation_executed": True,
        })
        result = self._finish_action_execution(result)
        if not verified:
            result["error"] = "calendar_selection_not_verified"
        return result

    @staticmethod
    def _time_picker_snapshot(popup):
        return popup.evaluate(
            """
            root => {
                const clean = value => String(value || '')
                    .replace(/\s+/g, ' ').trim();
                const visible = el => {
                    const style = getComputedStyle(el);
                    return !el.hidden && style.display !== 'none'
                        && style.visibility !== 'hidden'
                        && el.getClientRects().length > 0;
                };
                const options = Array.from(root.querySelectorAll(
                    '[role="option"], [data-time], time[datetime]'
                )).filter(visible).slice(0, 100).map(el => ({
                    name: clean(
                        el.getAttribute('aria-label')
                        || el.getAttribute('data-time')
                        || el.getAttribute('datetime')
                        || el.innerText || el.textContent
                    ).slice(0, 200),
                    time: clean(
                        el.getAttribute('data-time')
                        || el.getAttribute('datetime')
                    ).slice(0, 100),
                    selected: el.getAttribute('aria-selected') === 'true'
                        || el.getAttribute('data-selected') === 'true',
                    disabled: el.matches(':disabled')
                        || el.getAttribute('aria-disabled') === 'true'
                }));
                return {
                    role: root.getAttribute('role') || '',
                    name: clean(root.getAttribute('aria-label')).slice(0, 200),
                    listbox_count: root.querySelectorAll('[role="listbox"]').length,
                    options
                };
            }
            """
        )

    def inspect_time_picker_semantic(self, trigger, exact=True):
        self._ensure_started()
        self._reset_diagnostics()
        _, popup, error = self._controlled_popover(trigger, exact)
        if error:
            return error
        if not popup.is_visible():
            return {"error": "time_picker_not_open", "executed": False}
        snapshot = self._time_picker_snapshot(popup)
        if snapshot.get("listbox_count", 0) < 1:
            return {
                "error": "time_picker_listbox_not_found",
                "executed": False,
                "time_picker_snapshot": snapshot,
            }
        result = self._capture_state("inspect-time-picker-semantic")
        result.update({
            "time_picker_trigger": trigger,
            "time_picker_status": "observed",
            "time_picker_snapshot": snapshot,
            "mutation_executed": False,
        })
        return result

    def open_time_picker_semantic(self, trigger, exact=True):
        result = self.open_popover_semantic(trigger, exact)
        if result.get("error"):
            return result
        _, popup, error = self._controlled_popover(trigger, exact)
        if error:
            return error
        snapshot = self._time_picker_snapshot(popup)
        if snapshot.get("listbox_count", 0) < 1:
            result.update({
                "error": "time_picker_listbox_not_found",
                "time_picker_status": "contract_not_observed",
                "time_picker_snapshot": snapshot,
            })
            return result
        result.update({
            "time_picker_trigger": trigger,
            "time_picker_status": (
                "already_open"
                if result.get("popover_status") == "already_open"
                else "opened"
            ),
            "time_picker_snapshot": snapshot,
        })
        return result

    def select_time_picker_option_semantic(
        self, trigger, option, exact=True,
    ):
        self._ensure_started()
        self._reset_diagnostics()
        button, popup, error = self._controlled_popover(trigger, exact)
        if error:
            return error
        if not popup.is_visible():
            return {"error": "time_picker_not_open", "executed": False}
        snapshot = self._time_picker_snapshot(popup)
        if snapshot.get("listbox_count", 0) < 1:
            return {
                "error": "time_picker_listbox_not_found",
                "executed": False,
            }

        wanted = str(option or "").strip()
        candidates = popup.locator(
            '[role="option"], [data-time], time[datetime]'
        )
        matches = []
        for index in range(min(candidates.count(), 100)):
            candidate = candidates.nth(index)
            try:
                if not candidate.is_visible():
                    continue
                names = candidate.evaluate(
                    """
                    el => [
                        el.getAttribute('aria-label') || '',
                        el.getAttribute('data-time') || '',
                        el.getAttribute('datetime') || '',
                        el.innerText || el.textContent || ''
                    ].map(value => String(value).replace(/\s+/g, ' ').trim())
                     .filter(Boolean)
                    """
                )
                matched = (
                    any(name == wanted for name in names)
                    if exact
                    else any(wanted.casefold() in name.casefold() for name in names)
                )
                if matched:
                    matches.append(candidate)
            except Exception:
                continue
        if len(matches) != 1:
            return {
                "error": (
                    "time_picker_option_not_found"
                    if not matches
                    else "ambiguous_time_picker_option"
                ),
                "option": wanted,
                "matches": len(matches),
                "executed": False,
            }
        target = matches[0]
        if (
            not target.is_enabled()
            or target.get_attribute("aria-disabled") == "true"
        ):
            return {
                "error": "time_picker_option_disabled",
                "option": wanted,
                "executed": False,
            }
        before = button.evaluate(
            "el => ({text: (el.innerText || '').trim(), value: el.value || ''})"
        )
        self._begin_action_execution()
        target.click()
        self.page.wait_for_timeout(200)
        after = button.evaluate(
            "el => ({text: (el.innerText || '').trim(), value: el.value || ''})"
        )
        popup_open = popup.is_visible()
        selected = False
        try:
            selected = target.evaluate(
                """
                el => el.getAttribute('aria-selected') === 'true'
                    || el.getAttribute('data-selected') === 'true'
                """
            )
        except Exception:
            selected = False
        trigger_changed = before != after
        verified = bool(selected or trigger_changed or not popup_open)
        result = self._capture_state("select-time-picker-option-semantic")
        result.update({
            "time_picker_trigger": trigger,
            "time_picker_option": wanted,
            "time_picker_status": "selected" if verified else "not_verified",
            "selection_verified": verified,
            "selected_state_observed": selected,
            "trigger_changed": trigger_changed,
            "time_picker_open_after": popup_open,
            "mutation_executed": True,
        })
        result = self._finish_action_execution(result)
        if not verified:
            result["error"] = "time_picker_selection_not_verified"
        return result

    def _visible_dialog(self, name, exact=True):
        matches = []
        for role in ("dialog", "alertdialog"):
            locator = self.page.get_by_role(role, name=name, exact=exact)
            for index in range(min(locator.count(), 50)):
                candidate = locator.nth(index)
                try:
                    if candidate.is_visible():
                        matches.append(candidate)
                except Exception:
                    continue
        if len(matches) != 1:
            return None, {
                "error": (
                    "dialog_not_found"
                    if not matches
                    else "ambiguous_dialog"
                ),
                "dialog": name,
                "matches": len(matches),
                "executed": False,
            }
        return matches[0], None

    @staticmethod
    def _dialog_snapshot(dialog):
        return dialog.evaluate(
            """
            root => {
                const clean = value => String(value || '')
                    .replace(/\s+/g, ' ').trim();
                const visible = el => {
                    const style = getComputedStyle(el);
                    return !el.hidden && style.display !== 'none'
                        && style.visibility !== 'hidden'
                        && el.getClientRects().length > 0;
                };
                const activeSteps = Array.from(root.querySelectorAll(
                    '[aria-current="step"], [data-current="true"], '
                    + '[data-step].active'
                )).filter(visible).map(el => clean(
                    el.getAttribute('aria-label')
                    || el.getAttribute('data-step')
                    || el.innerText || el.textContent
                ).slice(0, 200)).filter(Boolean);
                const buttons = Array.from(root.querySelectorAll(
                    'button, [role="button"]'
                )).filter(visible).slice(0, 100).map(el => ({
                    name: clean(
                        el.getAttribute('aria-label')
                        || el.innerText || el.textContent
                    ).slice(0, 200),
                    disabled: el.matches(':disabled')
                        || el.getAttribute('aria-disabled') === 'true'
                }));
                return {
                    role: root.getAttribute('role') || '',
                    name: clean(root.getAttribute('aria-label')).slice(0, 200),
                    text: clean(root.innerText || root.textContent).slice(0, 5000),
                    active_steps: activeSteps,
                    buttons,
                    visible_field_count: Array.from(root.querySelectorAll(
                        'input:not([type="hidden"]), select, textarea, '
                        + '[role="textbox"], [role="combobox"]'
                    )).filter(visible).length
                };
            }
            """
        )

    def inspect_dialog_semantic(self, dialog, exact=True):
        self._ensure_started()
        self._reset_diagnostics()
        target, error = self._visible_dialog(dialog, exact)
        if error:
            return error
        result = self._capture_state("inspect-dialog-semantic")
        result.update({
            "dialog_name": dialog,
            "dialog_status": "observed",
            "dialog_snapshot": self._dialog_snapshot(target),
            "mutation_executed": False,
        })
        return result

    def click_dialog_button_semantic(
        self, dialog, button, exact=True,
    ):
        self._ensure_started()
        self._reset_diagnostics()
        target, error = self._visible_dialog(dialog, exact)
        if error:
            return error
        controls = target.get_by_role("button", name=button, exact=exact)
        matches = []
        for index in range(min(controls.count(), 50)):
            candidate = controls.nth(index)
            try:
                if candidate.is_visible():
                    matches.append(candidate)
            except Exception:
                continue
        if len(matches) != 1:
            return {
                "error": (
                    "dialog_button_not_found"
                    if not matches
                    else "ambiguous_dialog_button"
                ),
                "dialog": dialog,
                "button": button,
                "matches": len(matches),
                "executed": False,
            }
        control = matches[0]
        if (
            not control.is_enabled()
            or control.get_attribute("aria-disabled") == "true"
        ):
            return {
                "error": "dialog_button_disabled",
                "dialog": dialog,
                "button": button,
                "executed": False,
            }
        before = self._dialog_snapshot(target)
        self._begin_action_execution()
        control.click()
        self.page.wait_for_timeout(200)
        try:
            dialog_open = target.is_visible()
        except Exception:
            dialog_open = False
        after = self._dialog_snapshot(target) if dialog_open else None
        step_changed = bool(
            dialog_open
            and before.get("active_steps") != after.get("active_steps")
        )
        result = self._capture_state("click-dialog-button-semantic")
        result.update({
            "dialog_name": dialog,
            "dialog_button": button,
            "dialog_button_status": "clicked",
            "dialog_open_after": dialog_open,
            "dialog_closed": not dialog_open,
            "step_changed": step_changed,
            "dialog_before": before,
            "dialog_after": after,
            "interaction_executed": True,
        })
        return self._finish_action_execution(result)

    def apply_table_filter_popover_semantic(
        self,
        column: str,
        value: str,
        table: str = None,
        trigger: str = None,
        operator: str = None,
        apply_button: str = None,
        exact: bool = True,
    ):
        """Submit one explicit filter popover scoped to an exact column."""
        self._ensure_started()
        self._reset_diagnostics()
        table_locator, error = self._resolve_table(table, exact)
        if error:
            return error
        headers = []
        header_locator = table_locator.get_by_role(
            "columnheader",
            name=column,
            exact=exact,
        )
        for index in range(min(header_locator.count(), 50)):
            candidate = header_locator.nth(index)
            if candidate.is_visible():
                headers.append(candidate)
        if not headers:
            raw_headers = table_locator.locator(
                'thead th, [role="columnheader"]'
            )
            for index in range(min(raw_headers.count(), 100)):
                candidate = raw_headers.nth(index)
                if not candidate.is_visible():
                    continue
                plain_name = candidate.evaluate(
                    """
                    el => {
                        const clone = el.cloneNode(true);
                        clone.querySelectorAll(
                            'button, input, select, textarea, '
                            + '[role="button"], [role="combobox"]'
                        ).forEach(node => node.remove());
                        return (clone.innerText || clone.textContent || '')
                            .replace(/\s+/g, ' ').trim();
                    }
                    """
                )
                matched = (
                    plain_name.casefold() == str(column).casefold()
                    if exact
                    else str(column).casefold() in plain_name.casefold()
                )
                if matched:
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
        trigger_locator = (
            header.get_by_role("button", name=trigger, exact=exact)
            if trigger
            else header.get_by_role("button")
        )
        triggers = []
        for index in range(min(trigger_locator.count(), 20)):
            candidate = trigger_locator.nth(index)
            if candidate.is_visible():
                triggers.append(candidate)
        if len(triggers) != 1:
            return {
                "error": (
                    "table_filter_trigger_not_found"
                    if not triggers
                    else "ambiguous_table_filter_trigger"
                ),
                "column": column,
                "trigger": trigger,
                "matches": len(triggers),
                "executed": False,
            }
        filter_trigger = triggers[0]
        controlled_id = str(
            filter_trigger.get_attribute("aria-controls") or ""
        ).strip()
        before = self._table_snapshot(table_locator)

        self._reset_diagnostics()
        self._begin_action_execution()
        filter_trigger.click()
        self.page.wait_for_timeout(200)

        popup = None
        popup_strategy = None
        if controlled_id:
            controlled = self.page.locator(
                "[id=" + json.dumps(controlled_id) + "]"
            )
            visible = [
                controlled.nth(index)
                for index in range(min(controlled.count(), 10))
                if controlled.nth(index).is_visible()
            ]
            if len(visible) == 1:
                popup = visible[0]
                popup_strategy = "aria-controls"

        if popup is None:
            overlays = self.page.locator(
                '[role="dialog"], [role="menu"], [popover]'
            )
            visible = []
            for index in range(min(overlays.count(), 50)):
                candidate = overlays.nth(index)
                if candidate.is_visible():
                    visible.append(candidate)
            if len(visible) == 1:
                popup = visible[0]
                popup_strategy = "single-visible-overlay"

        if popup is None:
            result = self._capture_state("apply-table-filter-popover")
            result.update(
                {
                    "error": "table_filter_popover_not_unique",
                    "column": column,
                    "trigger": trigger,
                    "mutation_executed": False,
                }
            )
            return self._finish_action_execution(result)

        operator_observed = None
        if operator is not None:
            selects = popup.locator("select")
            matching_selects = []
            for index in range(min(selects.count(), 20)):
                candidate = selects.nth(index)
                if not candidate.is_visible():
                    continue
                options = [
                    (candidate.locator("option").nth(option_index).inner_text() or "").strip()
                    for option_index in range(
                        min(candidate.locator("option").count(), 100)
                    )
                ]
                matches = [
                    item
                    for item in options
                    if (
                        item.casefold() == str(operator).casefold()
                        if exact
                        else str(operator).casefold() in item.casefold()
                    )
                ]
                if len(matches) == 1:
                    matching_selects.append((candidate, matches[0]))
            if len(matching_selects) != 1:
                result = self._capture_state("apply-table-filter-popover")
                result.update(
                    {
                        "error": (
                            "table_filter_operator_not_found"
                            if not matching_selects
                            else "ambiguous_table_filter_operator"
                        ),
                        "column": column,
                        "operator": operator,
                        "matches": len(matching_selects),
                        "mutation_executed": False,
                    }
                )
                return self._finish_action_execution(result)
            operator_control, operator_observed = matching_selects[0]
            operator_control.select_option(label=operator_observed)

        inputs = popup.locator(
            'input:not([type="hidden"]):not([type="button"]):not([type="submit"]), '
            'textarea, [contenteditable="true"], [role="textbox"], '
            '[role="searchbox"]'
        )
        editable = []
        seen = set()
        for index in range(min(inputs.count(), 30)):
            candidate = inputs.nth(index)
            try:
                if not candidate.is_visible():
                    continue
                key = candidate.evaluate("el => el.id || el.name || el.outerHTML")
                if key not in seen:
                    seen.add(key)
                    editable.append(candidate)
            except Exception:
                continue
        if len(editable) != 1:
            result = self._capture_state("apply-table-filter-popover")
            result.update(
                {
                    "error": (
                        "table_filter_value_control_not_found"
                        if not editable
                        else "ambiguous_table_filter_value_control"
                    ),
                    "column": column,
                    "matches": len(editable),
                    "mutation_executed": False,
                }
            )
            return self._finish_action_execution(result)
        value_control = editable[0]
        if (value_control.get_attribute("type") or "").casefold() == "password":
            result = self._capture_state("apply-table-filter-popover")
            result.update(
                {
                    "error": "table_filter_password_forbidden",
                    "column": column,
                    "mutation_executed": False,
                }
            )
            return self._finish_action_execution(result)
        wanted = str(value or "")
        value_control.fill(wanted)
        observed_value = value_control.input_value()

        button_locator = (
            popup.get_by_role("button", name=apply_button, exact=exact)
            if apply_button
            else popup.get_by_role("button")
        )
        buttons = []
        for index in range(min(button_locator.count(), 20)):
            candidate = button_locator.nth(index)
            if candidate.is_visible() and candidate.is_enabled():
                buttons.append(candidate)
        if len(buttons) != 1:
            result = self._capture_state("apply-table-filter-popover")
            result.update(
                {
                    "error": (
                        "table_filter_apply_button_not_found"
                        if not buttons
                        else "ambiguous_table_filter_apply_button"
                    ),
                    "column": column,
                    "apply_button": apply_button,
                    "matches": len(buttons),
                    "observed_filter_value": observed_value,
                    "mutation_executed": False,
                }
            )
            return self._finish_action_execution(result)

        buttons[0].click()
        self.page.wait_for_timeout(500)
        after = self._table_snapshot(table_locator)
        result = self._capture_state("apply-table-filter-popover")
        result.update(
            {
                "table_name": table,
                "filtered_column": column,
                "filter_trigger": trigger,
                "filter_operator": operator_observed,
                "filter_value": wanted,
                "observed_filter_value": observed_value,
                "filter_apply_button": apply_button,
                "filter_popover_strategy": popup_strategy,
                "filter_submission_status": "submitted",
                "rows_changed": (
                    before.get("row_signature")
                    != after.get("row_signature")
                ),
                "table_before": before,
                "table_after": after,
                "mutation_executed": False,
                "post_action_wait_ms": 500,
            }
        )
        return self._finish_action_execution(result)

    def inspect_table_pagination_semantic(
        self,
        table: str = None,
        exact: bool = True,
    ):
        """Read total/range/current-page metadata without activating controls."""
        self._ensure_started()
        self._reset_diagnostics()
        table_locator, error = self._resolve_table(table, exact)
        if error:
            return error
        snapshot = self._table_snapshot(table_locator)
        metadata = table_locator.evaluate(
            """
            table => {
                const scope = table.parentElement || table;
                const text = (scope.innerText || '').replace(/\s+/g, ' ').trim();
                const integer = value => {
                    const parsed = Number.parseInt(String(value || ''), 10);
                    return Number.isFinite(parsed) ? parsed : null;
                };
                let total = null;
                let totalSource = null;
                for (const [name, value] of [
                    ['aria-rowcount', table.getAttribute('aria-rowcount')],
                    ['data-total-count', table.getAttribute('data-total-count')],
                    ['data-total', table.getAttribute('data-total')],
                    ['data-count', table.getAttribute('data-count')]
                ]) {
                    const parsed = integer(value);
                    if (parsed !== null && parsed >= 0) {
                        total = parsed;
                        totalSource = name;
                        break;
                    }
                }
                let rangeStart = null;
                let rangeEnd = null;
                const range = text.match(/(\d+)\s*[-–]\s*(\d+)\s*(?:of|из)\s*(\d+)/i);
                if (range) {
                    rangeStart = integer(range[1]);
                    rangeEnd = integer(range[2]);
                    if (total === null) {
                        total = integer(range[3]);
                        totalSource = 'visible-range-text';
                    }
                }
                if (total === null) {
                    const labelled = text.match(/(?:total|всего)\s*:?\s*(\d+)/i);
                    if (labelled) {
                        total = integer(labelled[1]);
                        totalSource = 'visible-total-text';
                    }
                }
                const current = scope.querySelector('[aria-current="page"]');
                const currentPage = current
                    ? integer(current.innerText || current.textContent || current.getAttribute('aria-label'))
                    : null;
                const controls = Array.from(scope.querySelectorAll('button, a[href]'))
                    .filter(el => {
                        const style = window.getComputedStyle(el);
                        const box = el.getBoundingClientRect();
                        return style.display !== 'none'
                            && style.visibility !== 'hidden'
                            && box.width > 0 && box.height > 0;
                    })
                    .slice(0, 50)
                    .map(el => ({
                        name: (el.getAttribute('aria-label') || el.innerText || el.textContent || '').trim(),
                        current: el.getAttribute('aria-current') === 'page',
                        disabled: Boolean(el.disabled) || el.getAttribute('aria-disabled') === 'true'
                    }))
                    .filter(item => item.name);
                return {
                    total,
                    total_source: totalSource,
                    range_start: rangeStart,
                    range_end: rangeEnd,
                    current_page: currentPage,
                    pagination_controls: controls
                };
            }
            """
        )
        result = self._capture_state("inspect-table-pagination")
        result.update(
            {
                "table_name": table,
                "visible_row_count": snapshot.get("visible_row_count"),
                "row_signature": snapshot.get("row_signature"),
                "total_row_count": metadata.get("total"),
                "total_source": metadata.get("total_source"),
                "visible_range_start": metadata.get("range_start"),
                "visible_range_end": metadata.get("range_end"),
                "current_page": metadata.get("current_page"),
                "pagination_controls": metadata.get("pagination_controls"),
                "pagination_status": "observed",
                "mutation_executed": False,
                "executed": True,
            }
        )
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
        self._last_inspected_exact_row = None

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
        if exact:
            self._last_inspected_exact_row = {
                "name": name,
                "url": self.page.url,
            }
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

    def open_exact_table_row_details_semantic(self, name: str):
        """Open one uniquely inspected row and verify the resulting identity."""
        self._ensure_started()
        inspected = self.inspect_table_row(name, exact=True)
        if inspected.get("error") or inspected.get("row_match_count") != 1:
            return {
                "error": inspected.get("error") or "table_row_not_unique",
                "executed": False,
                "mutation_executed": False,
                "details_identity_status": "blocked",
                "failed_stage": "exact_row_inspection",
                "name": name,
                "row_match_count": inspected.get("row_match_count"),
                "current_url": inspected.get("current_url"),
                "screenshot": inspected.get("screenshot"),
            }

        identity_script = """
            wanted => {
                const clean = value => String(value || '')
                    .replace(/\\s+/g, ' ').trim();
                const visible = el => {
                    const style = getComputedStyle(el);
                    return !el.hidden && style.display !== 'none'
                        && style.visibility !== 'hidden'
                        && el.getClientRects().length > 0;
                };
                const anchors = [];
                const selectors = [
                    'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
                    '[role="heading"]', '[aria-current="page"]'
                ];
                for (const el of document.querySelectorAll(selectors.join(','))) {
                    if (visible(el) && clean(el.innerText || el.textContent) === wanted) {
                        anchors.push(
                            el.matches('[aria-current="page"]')
                                ? 'aria-current'
                                : (el.getAttribute('role') || el.tagName.toLowerCase())
                        );
                    }
                }
                let exactVisibleCount = 0;
                for (const el of document.querySelectorAll('body *')) {
                    if (
                        el.children.length === 0 && visible(el)
                        && clean(el.innerText || el.textContent) === wanted
                    ) exactVisibleCount += 1;
                }
                return {
                    anchor_types: Array.from(new Set(anchors)),
                    anchor_match_count: anchors.length,
                    exact_visible_count: exactVisibleCount,
                    document_title_match: clean(document.title) === wanted,
                };
            }
        """
        normalized_name = " ".join(str(name or "").split())
        before_url = str(self.page.url or "")
        before_identity = self.page.evaluate(identity_script, normalized_name)
        clicked = self.click_semantic(name, exact=True, role="row")
        if clicked.get("error") or clicked.get("click_status") != "executed":
            return {
                "error": clicked.get("error") or "table_row_open_failed",
                "executed": False,
                "mutation_executed": False,
                "details_identity_status": "blocked",
                "failed_stage": "exact_row_open",
                "name": name,
                "current_url": clicked.get("current_url"),
                "screenshot": clicked.get("screenshot"),
            }

        self.page.wait_for_timeout(250)
        after_url = str(self.page.url or "")
        before = urlsplit(before_url)
        after = urlsplit(after_url)
        if (
            before.scheme.casefold(), before.netloc.casefold()
        ) != (
            after.scheme.casefold(), after.netloc.casefold()
        ):
            return {
                "error": "details_origin_mismatch",
                "executed": False,
                "mutation_executed": False,
                "details_identity_status": "blocked",
                "failed_stage": "same_origin_verification",
                "name": name,
                "current_url": after_url,
                "screenshot": clicked.get("screenshot"),
            }

        identity = self.page.evaluate(identity_script, normalized_name)
        url_changed = before_url != after_url
        exact_visible_count_increased = (
            identity.get("exact_visible_count", 0)
            > before_identity.get("exact_visible_count", 0)
        )
        identity_passed = bool(
            identity.get("anchor_match_count")
            or identity.get("document_title_match")
            or (url_changed and identity.get("exact_visible_count", 0) > 0)
            or exact_visible_count_increased
        )
        result = self._capture_state("open-exact-table-row-details")
        result.update({
            "status": "ready" if identity_passed else "blocked",
            "executed": True,
            "mutation_executed": False,
            "name": name,
            "row_match_count": 1,
            "row_opened": True,
            "url_changed": url_changed,
            "before_identity": before_identity,
            "identity": identity,
            "exact_visible_count_increased": exact_visible_count_increased,
            "details_identity_status": (
                "verified" if identity_passed else "not_confirmed"
            ),
            "details_identity_passed": identity_passed,
            "observation_result": "PASS" if identity_passed else "BLOCKED",
            "observation_reason": (
                "exact_table_row_details_identity_verified"
                if identity_passed
                else "details_identity_not_confirmed"
            ),
            "next_step_hint": (
                "Do not re-inspect the source table or pagination. Continue "
                "with requested detail-surface checks, or finalize the verdict."
            ),
        })
        if not identity_passed:
            result["error"] = "details_identity_not_confirmed"
        return result

    def verify_exact_table_row_tabs_semantic(
        self, name: str, tabs: list, tablist: str = None,
    ):
        """Open one exact row and verify selected tab/panel contracts in order."""
        self._ensure_started()
        if (
            not isinstance(tabs, list)
            or not 1 <= len(tabs) <= 20
            or any(not isinstance(tab, str) or not tab.strip() for tab in tabs)
        ):
            return {
                "error": "requested_tabs_invalid",
                "executed": False,
                "mutation_executed": False,
                "observation_result": "BLOCKED",
            }
        requested_tabs = [" ".join(tab.split()) for tab in tabs]
        if len({tab.casefold() for tab in requested_tabs}) != len(requested_tabs):
            return {
                "error": "requested_tabs_not_unique",
                "executed": False,
                "mutation_executed": False,
                "observation_result": "BLOCKED",
            }

        details = self.open_exact_table_row_details_semantic(name)
        if details.get("error") or not details.get("details_identity_passed"):
            result = dict(details)
            result.update({
                "error": details.get("error") or "details_identity_not_confirmed",
                "failed_stage": "exact_row_details",
                "requested_tabs": requested_tabs,
                "tabs_verified": [],
                "observation_result": "BLOCKED",
                "mutation_executed": False,
            })
            return result

        allowed_origin = urlsplit(str(self.page.url or ""))
        verified = []
        for tab_name in requested_tabs:
            inspected = self.inspect_semantic(tab_name, exact=True, role="tab")
            if inspected.get("error"):
                return {
                    "error": inspected.get("error"),
                    "status": "blocked",
                    "executed": True,
                    "mutation_executed": False,
                    "failed_stage": "exact_tab_inspection",
                    "failed_tab": tab_name,
                    "requested_tabs": requested_tabs,
                    "tabs_verified": verified,
                    "details_identity_passed": True,
                    "observation_result": "BLOCKED",
                    "current_url": str(self.page.url or ""),
                }

            clicked = self.click_semantic(tab_name, exact=True, role="tab")
            if clicked.get("error") or clicked.get("click_status") != "executed":
                return {
                    "error": clicked.get("error") or "exact_tab_open_failed",
                    "status": "blocked",
                    "executed": True,
                    "mutation_executed": False,
                    "failed_stage": "exact_tab_open",
                    "failed_tab": tab_name,
                    "requested_tabs": requested_tabs,
                    "tabs_verified": verified,
                    "details_identity_passed": True,
                    "observation_result": "BLOCKED",
                    "current_url": str(self.page.url or ""),
                }

            self.page.wait_for_timeout(150)
            current_url = str(self.page.url or "")
            current_origin = urlsplit(current_url)
            if (
                allowed_origin.scheme.casefold(), allowed_origin.netloc.casefold()
            ) != (
                current_origin.scheme.casefold(), current_origin.netloc.casefold()
            ):
                return {
                    "error": "tab_navigation_origin_mismatch",
                    "status": "blocked",
                    "executed": True,
                    "mutation_executed": False,
                    "failed_stage": "same_origin_verification",
                    "failed_tab": tab_name,
                    "requested_tabs": requested_tabs,
                    "tabs_verified": verified,
                    "details_identity_passed": True,
                    "observation_result": "BLOCKED",
                    "current_url": current_url,
                }

            contract = self.inspect_tabs_contract_semantic(tablist, exact=True)
            audit = contract.get("tabs_audit") or {}
            selected = [item for item in audit.get("tabs", []) if item.get("selected")]
            selected_name = (
                " ".join(str(selected[0].get("label") or "").split())
                if len(selected) == 1
                else ""
            )
            tab_passed = bool(
                not contract.get("error")
                and len(selected) == 1
                and selected_name.casefold() == tab_name.casefold()
                and bool(selected[0].get("controls"))
                and selected[0].get("panel_exists") is True
                and selected[0].get("panel_visible") is True
            )
            verification = {
                "tab": tab_name,
                "selected_tab": selected_name,
                "selected_count": audit.get("selected_count"),
                "panel_visible": (
                    selected[0].get("panel_visible")
                    if len(selected) == 1
                    else False
                ),
                "controls": (
                    selected[0].get("controls")
                    if len(selected) == 1
                    else ""
                ),
                "panel_exists": (
                    selected[0].get("panel_exists")
                    if len(selected) == 1
                    else False
                ),
                "tabs_contract_passed": bool(audit.get("tabs_contract_passed")),
                "passed": tab_passed,
            }
            verified.append(verification)
            if not tab_passed:
                return {
                    "error": contract.get("error") or "selected_tab_panel_mismatch",
                    "status": "blocked",
                    "executed": True,
                    "mutation_executed": False,
                    "failed_stage": "tab_panel_contract",
                    "failed_tab": tab_name,
                    "requested_tabs": requested_tabs,
                    "tabs_verified": verified,
                    "details_identity_passed": True,
                    "observation_result": "BLOCKED",
                    "current_url": current_url,
                }

        result = self._capture_state("verify-exact-table-row-tabs")
        result.update({
            "status": "ready",
            "executed": True,
            "mutation_executed": False,
            "name": name,
            "row_match_count": 1,
            "details_identity_passed": True,
            "requested_tabs": requested_tabs,
            "tabs_verified": verified,
            "verified_tab_count": len(verified),
            "tabs_workflow_passed": True,
            "observation_result": "PASS",
            "observation_reason": "exact_row_tabs_and_panels_verified",
        })
        return result

    def inspect_semantic(
        self,
        name: str,
        exact: bool = True,
        role: str = None,
    ):
        self._ensure_started()
        self._reset_diagnostics()
        self._last_inspected_exact_target = None
        self._last_inspected_exact_row = None

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
            "dialog",
            "alertdialog",
            "alert",
            "status",
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

                    const computed = getComputedStyle(el);
                    const computedStyle = {
                        display: computed.display,
                        visibility: computed.visibility,
                        opacity: computed.opacity,
                        pointer_events: computed.pointerEvents,
                        cursor: computed.cursor,
                        color: computed.color,
                        background_color: computed.backgroundColor,
                        border_color: computed.borderColor,
                        border_style: computed.borderStyle,
                        border_width: computed.borderWidth,
                        outline_color: computed.outlineColor,
                        outline_style: computed.outlineStyle,
                        outline_width: computed.outlineWidth,
                        font_size: computed.fontSize,
                        font_weight: computed.fontWeight,
                        text_decoration_line: computed.textDecorationLine
                    };

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
                        aria_checked:
                            el.getAttribute(
                                "aria-checked"
                            ),
                        aria_selected:
                            el.getAttribute(
                                "aria-selected"
                            ),
                        aria_required:
                            el.getAttribute(
                                "aria-required"
                            ),
                        aria_invalid:
                            el.getAttribute(
                                "aria-invalid"
                            ),
                        aria_readonly:
                            el.getAttribute(
                                "aria-readonly"
                            ),
                        required_attribute:
                            el.hasAttribute("required"),
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
                        visual_state: {
                            focused: el.matches(":focus"),
                            focus_visible: el.matches(":focus-visible"),
                            hovered: el.matches(":hover"),
                            checked: el.matches(":checked"),
                            selected: (
                                el.matches(":checked")
                                || el.getAttribute("aria-selected") === "true"
                            ),
                            invalid: el.matches(":invalid")
                        },
                        computed_style: computedStyle,
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

        try:
            layout = target.evaluate(
                """
                el => {
                    const rect = el.getBoundingClientRect();
                    const viewportWidth = document.documentElement.clientWidth;
                    const viewportHeight = document.documentElement.clientHeight;
                    let left = Math.max(0, rect.left);
                    let top = Math.max(0, rect.top);
                    let right = Math.min(viewportWidth, rect.right);
                    let bottom = Math.min(viewportHeight, rect.bottom);

                    for (
                        let parent = el.parentElement;
                        parent;
                        parent = parent.parentElement
                    ) {
                        const style = getComputedStyle(parent);
                        const parentRect = parent.getBoundingClientRect();
                        const clipsX = ["auto", "hidden", "clip", "scroll"]
                            .includes(style.overflowX);
                        const clipsY = ["auto", "hidden", "clip", "scroll"]
                            .includes(style.overflowY);
                        if (clipsX) {
                            left = Math.max(left, parentRect.left);
                            right = Math.min(right, parentRect.right);
                        }
                        if (clipsY) {
                            top = Math.max(top, parentRect.top);
                            bottom = Math.min(bottom, parentRect.bottom);
                        }
                    }

                    const visibleWidth = Math.max(0, right - left);
                    const visibleHeight = Math.max(0, bottom - top);
                    const area = Math.max(0, rect.width * rect.height);
                    const visibleArea = visibleWidth * visibleHeight;
                    const centerX = left + visibleWidth / 2;
                    const centerY = top + visibleHeight / 2;
                    const hit = (
                        visibleArea > 0
                        ? document.elementFromPoint(centerX, centerY)
                        : null
                    );
                    const centerUnobscured = Boolean(
                        hit && (hit === el || el.contains(hit))
                    );
                    const round = value => Math.round(value * 100) / 100;
                    const style = getComputedStyle(el);

                    return {
                        x: round(rect.x),
                        y: round(rect.y),
                        width: round(rect.width),
                        height: round(rect.height),
                        viewport_width: viewportWidth,
                        viewport_height: viewportHeight,
                        intersects_viewport: visibleArea > 0,
                        fully_in_viewport: (
                            rect.left >= 0
                            && rect.top >= 0
                            && rect.right <= viewportWidth
                            && rect.bottom <= viewportHeight
                        ),
                        visible_area_ratio: (
                            area > 0 ? round(visibleArea / area) : 0
                        ),
                        center_unobscured: centerUnobscured,
                        geometry_actionable: Boolean(
                            visibleArea > 0 && centerUnobscured
                        ),
                        touch_target_44px: (
                            rect.width >= 44 && rect.height >= 44
                        ),
                        position: style.position
                    };
                }
                """
            )
        except Exception:
            layout = {}

        result = self._capture_state(
            "inspect-semantic"
        )

        def aria_boolean(value):
            normalized = str(value or "").strip().lower()

            if normalized == "true":
                return True

            if normalized == "false":
                return False

            return None

        element_role = str(
            metadata.get("role")
            or requested_role
            or ""
        ).strip().lower()
        element_tag = str(metadata.get("tag") or "").strip().lower()
        element_type = str(metadata.get("type") or "").strip().lower()
        visual_state = metadata.get("visual_state") or {}
        checkable = (
            element_role in {"checkbox", "radio", "switch", "menuitemcheckbox", "menuitemradio"}
            or element_type in {"checkbox", "radio"}
        )
        selectable = (
            element_role in {"option", "tab", "treeitem", "row"}
            or element_tag == "option"
            or metadata.get("aria_selected") is not None
        )
        form_control = (
            element_tag in {"input", "select", "textarea"}
            or element_role in {"textbox", "combobox", "spinbutton", "checkbox", "radio", "switch"}
        )
        checked = aria_boolean(metadata.get("aria_checked"))

        if checked is None and checkable:
            checked = bool(visual_state.get("checked"))

        selected = aria_boolean(metadata.get("aria_selected"))

        if selected is None and selectable:
            selected = bool(visual_state.get("selected"))

        expanded = aria_boolean(metadata.get("aria_expanded"))
        required = aria_boolean(metadata.get("aria_required"))

        if required is None and form_control:
            required = bool(metadata.get("required_attribute"))

        invalid = aria_boolean(metadata.get("aria_invalid"))

        if invalid is None and form_control:
            invalid = bool(visual_state.get("invalid"))

        read_only = aria_boolean(metadata.get("aria_readonly"))

        if read_only is None and form_control:
            read_only = bool(metadata.get("readonly_attribute"))

        result.update(
            {
                "semantic_name": name,
                "semantic_strategy": strategy,
                "visible": visible,
                "enabled": enabled,
                "editable": editable,
                "checked": checked,
                "selected": selected,
                "expanded": expanded,
                "required": required,
                "invalid": invalid,
                "read_only": read_only,
                "disabled": (
                    not enabled
                    if enabled is not None
                    else None
                ),
                "element": metadata,
                "layout": layout,
                "geometry_actionable": layout.get("geometry_actionable"),
                "inspection_status": "observed",
                "requested_role": requested_role or None,
                "role_constraint_matched": role_constraint_matched,
                "semantic_role_fallback": (
                    bool(requested_role)
                    and role_constraint_matched is False
                ),
            }
        )

        if visible and enabled and exact:
            self._last_inspected_exact_target = {
                "name": name,
                "exact": exact,
                "url": self.page.url,
            }

        return result

    @staticmethod
    def _download_format(path):
        with Path(path).open("rb") as source:
            prefix = source.read(4096)
        if prefix.startswith(b"%PDF-"):
            return "pdf"
        if prefix.startswith(b"\x89PNG\r\n\x1a\n"):
            return "png"
        if prefix.startswith(b"\xff\xd8\xff"):
            return "jpeg"
        if prefix and b"\x00" not in prefix:
            try:
                prefix.decode("utf-8")
                return "text"
            except UnicodeDecodeError:
                pass
        return "unknown"

    def download_semantic(
        self, name, expected_filename, expected_format=None,
        expected_sha256=None, exact=True,
    ):
        """Capture one exact UI download without exposing file contents."""
        self._ensure_started()
        self._reset_diagnostics()
        if not isinstance(expected_filename, str) or not expected_filename.strip():
            return {"error": "download_expected_filename_required", "executed": False}
        if expected_format not in {None, "text", "pdf", "png", "jpeg"}:
            return {"error": "download_expected_format_invalid", "executed": False}
        if expected_sha256 is not None and not re.fullmatch(
            r"[0-9a-fA-F]{64}", str(expected_sha256)
        ):
            return {"error": "download_expected_sha256_invalid", "executed": False}
        candidates = []
        for role in ("button", "link"):
            locator = self.page.get_by_role(role, name=name, exact=exact)
            for index in range(min(locator.count(), 50)):
                target = locator.nth(index)
                if target.is_visible():
                    candidates.append((role, target))
        if len(candidates) != 1:
            return {
                "error": "download_trigger_not_unique",
                "name": name,
                "matches": len(candidates),
                "executed": False,
            }
        role, target = candidates[0]
        if target.get_attribute("aria-disabled") == "true" or not target.is_enabled():
            return {"error": "download_trigger_disabled", "executed": False}
        self._begin_action_execution()
        try:
            with self.page.expect_download(timeout=10000) as event:
                target.click()
            download = event.value
        except PlaywrightTimeoutError:
            result = self._capture_state("download-not-observed")
            result.update({
                "download_trigger": name,
                "download_status": "not_observed",
                "mutation_executed": True,
                "error": "download_not_observed_after_click",
            })
            return self._finish_action_execution(result)
        failure = download.failure()
        if failure:
            result = self._capture_state("download-failed")
            result.update({
                "download_trigger": name,
                "download_status": "failed",
                "mutation_executed": True,
                "error": "download_failed",
            })
            return self._finish_action_execution(result)
        source = Path(download.path())
        size = source.stat().st_size
        if size > 10 * 1024 * 1024:
            result = self._capture_state("download-too-large")
            result.update({
                "download_trigger": name,
                "download_status": "too_large",
                "download_bytes": size,
                "mutation_executed": True,
                "error": "download_size_limit_exceeded",
            })
            return self._finish_action_execution(result)
        artifact = self.session_dir / f"download-{uuid.uuid4().hex}.bin"
        download.save_as(str(artifact))
        artifact.chmod(0o600)
        digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
        detected_format = self._download_format(artifact)
        download_id = f"d{uuid.uuid4().hex[:12]}"
        self.download_artifacts[download_id] = {
            "path": artifact,
            "format": detected_format,
            "sha256": digest,
        }
        name_matches = download.suggested_filename == expected_filename
        format_matches = (
            expected_format is None or detected_format == expected_format
        )
        hash_matches = (
            expected_sha256 is None
            or digest == str(expected_sha256).casefold()
        )
        verified = (
            name_matches and format_matches and hash_matches
            and expected_sha256 is not None
        )
        result = self._capture_state("download-semantic")
        result.update({
            "download_trigger": name,
            "download_trigger_role": role,
            "download_suggested_filename": download.suggested_filename,
            "download_expected_filename": expected_filename,
            "download_name_matches": name_matches,
            "download_detected_format": detected_format,
            "download_format_matches": format_matches,
            "download_bytes": size,
            "download_sha256": digest,
            "download_hash_matches": hash_matches,
            "download_id": download_id,
            "download_status": (
                "verified" if verified else
                "mismatch" if not (name_matches and format_matches and hash_matches)
                else "metadata_only"
            ),
            "mutation_executed": True,
        })
        return self._finish_action_execution(result)

    def verify_download_structure_semantic(
        self, download_id, format, expected_headers=None,
        min_rows=None, max_rows=None, expected_pages=None,
        expected_json_type=None, required_keys=None,
        min_items=None, max_items=None,
        expected_width=None, expected_height=None,
    ):
        """Inspect only a download captured in this browser case."""
        record = self.download_artifacts.get(str(download_id or ""))
        if record is None:
            return {"error": "download_id_unknown", "executed": False}
        path = record["path"]
        if not path.resolve().is_relative_to(self.session_dir.resolve()):
            return {"error": "download_artifact_outside_session", "executed": False}
        if format == "csv":
            if record["format"] != "text":
                return {"error": "download_not_text", "executed": False}
            if (
                not isinstance(expected_headers, list)
                or not expected_headers
                or len(expected_headers) > 100
                or any(not isinstance(x, str) or not x or len(x) > 200 for x in expected_headers)
            ):
                return {"error": "csv_expected_headers_invalid", "executed": False}
            if (
                min_rows is not None and
                (type(min_rows) is not int or min_rows < 0)
            ) or (
                max_rows is not None and
                (type(max_rows) is not int or max_rows < 0)
            ) or (
                min_rows is not None and max_rows is not None
                and min_rows > max_rows
            ):
                return {"error": "csv_row_bounds_invalid", "executed": False}
            try:
                with path.open("r", encoding="utf-8-sig", newline="") as source:
                    reader = csv.reader(source, strict=True)
                    headers = next(reader)
                    header_matches = headers == expected_headers
                    row_count = 0
                    widths_valid = True
                    for row in reader:
                        row_count += 1
                        if row_count > 100000:
                            return {"error": "csv_row_limit_exceeded", "executed": False}
                        if len(row) != len(headers):
                            widths_valid = False
            except (UnicodeDecodeError, csv.Error, StopIteration):
                return {"error": "csv_parse_failed", "executed": False}
            row_count_matches = (
                (min_rows is None or row_count >= min_rows)
                and (max_rows is None or row_count <= max_rows)
            )
            verified = header_matches and widths_valid and row_count_matches
            return {
                "download_id": download_id,
                "format": "csv",
                "header_matches": header_matches,
                "row_count": row_count,
                "row_count_matches": row_count_matches,
                "row_widths_valid": widths_valid,
                "verification_status": "verified" if verified else "mismatch",
                "mutation_executed": False,
            }
        if format == "pdf":
            if record["format"] != "pdf":
                return {"error": "download_not_pdf", "executed": False}
            if type(expected_pages) is not int or not 1 <= expected_pages <= 1000:
                return {"error": "pdf_expected_pages_invalid", "executed": False}
            try:
                from pypdf import PdfReader
                reader = PdfReader(str(path), strict=True)
                if reader.is_encrypted:
                    return {"error": "pdf_encrypted", "executed": False}
                page_count = len(reader.pages)
            except Exception:
                return {"error": "pdf_parse_failed", "executed": False}
            verified = page_count == expected_pages
            return {
                "download_id": download_id,
                "format": "pdf",
                "page_count": page_count,
                "page_count_matches": verified,
                "verification_status": "verified" if verified else "mismatch",
                "mutation_executed": False,
            }
        if format == "json":
            if record["format"] != "text":
                return {"error": "download_not_text", "executed": False}
            if expected_json_type not in {"object", "array"}:
                return {
                    "error": "json_expected_type_invalid",
                    "executed": False,
                }
            if required_keys is None:
                required_keys = []
            if (
                not isinstance(required_keys, list)
                or len(required_keys) > 100
                or any(
                    not isinstance(key, str)
                    or not key
                    or len(key) > 200
                    for key in required_keys
                )
            ):
                return {
                    "error": "json_required_keys_invalid",
                    "executed": False,
                }
            if required_keys and expected_json_type != "object":
                return {
                    "error": "json_required_keys_need_object",
                    "executed": False,
                }
            if (
                min_items is not None
                and (type(min_items) is not int or min_items < 0)
            ) or (
                max_items is not None
                and (type(max_items) is not int or max_items < 0)
            ) or (
                min_items is not None
                and max_items is not None
                and min_items > max_items
            ):
                return {
                    "error": "json_item_bounds_invalid",
                    "executed": False,
                }
            try:
                with path.open("r", encoding="utf-8-sig") as source:
                    payload = json.load(source)
            except (UnicodeDecodeError, json.JSONDecodeError, OSError):
                return {"error": "json_parse_failed", "executed": False}
            actual_type = (
                "object" if isinstance(payload, dict)
                else "array" if isinstance(payload, list)
                else "other"
            )
            type_matches = actual_type == expected_json_type
            missing_required_keys = (
                [key for key in required_keys if key not in payload]
                if isinstance(payload, dict)
                else list(required_keys)
            )
            required_keys_match = not missing_required_keys
            item_count = (
                len(payload)
                if isinstance(payload, (dict, list))
                else None
            )
            item_count_matches = bool(
                item_count is not None
                and (min_items is None or item_count >= min_items)
                and (max_items is None or item_count <= max_items)
            )
            verified = bool(
                type_matches
                and required_keys_match
                and item_count_matches
            )
            return {
                "download_id": download_id,
                "format": "json",
                "json_type": actual_type,
                "json_type_matches": type_matches,
                "required_keys_match": required_keys_match,
                "missing_required_keys": missing_required_keys,
                "item_count": item_count,
                "item_count_matches": item_count_matches,
                "verification_status": (
                    "verified" if verified else "mismatch"
                ),
                "mutation_executed": False,
            }
        if format in {"png", "jpeg"}:
            if record["format"] != format:
                return {
                    "error": "download_not_expected_image_format",
                    "executed": False,
                }
            if (
                type(expected_width) is not int
                or not 1 <= expected_width <= 32768
                or type(expected_height) is not int
                or not 1 <= expected_height <= 32768
            ):
                return {
                    "error": "image_expected_dimensions_invalid",
                    "executed": False,
                }
            try:
                data = path.read_bytes()
            except OSError:
                return {"error": "image_read_failed", "executed": False}
            width = height = None
            if format == "png":
                if (
                    len(data) < 24
                    or data[:8] != b"\x89PNG\r\n\x1a\n"
                    or data[12:16] != b"IHDR"
                ):
                    return {"error": "png_parse_failed", "executed": False}
                width = int.from_bytes(data[16:20], "big")
                height = int.from_bytes(data[20:24], "big")
            else:
                if len(data) < 4 or data[:2] != b"\xff\xd8":
                    return {"error": "jpeg_parse_failed", "executed": False}
                offset = 2
                sof_markers = {
                    0xC0, 0xC1, 0xC2, 0xC3,
                    0xC5, 0xC6, 0xC7,
                    0xC9, 0xCA, 0xCB,
                    0xCD, 0xCE, 0xCF,
                }
                while offset < len(data):
                    while offset < len(data) and data[offset] != 0xFF:
                        offset += 1
                    while offset < len(data) and data[offset] == 0xFF:
                        offset += 1
                    if offset >= len(data):
                        break
                    marker = data[offset]
                    offset += 1
                    if marker == 0xD9:
                        break
                    if marker == 0x01 or 0xD0 <= marker <= 0xD8:
                        continue
                    if offset + 2 > len(data):
                        break
                    segment_length = int.from_bytes(data[offset:offset + 2], "big")
                    if segment_length < 2 or offset + segment_length > len(data):
                        break
                    if marker in sof_markers:
                        if segment_length < 7:
                            break
                        height = int.from_bytes(data[offset + 3:offset + 5], "big")
                        width = int.from_bytes(data[offset + 5:offset + 7], "big")
                        break
                    offset += segment_length
                if width is None or height is None:
                    return {"error": "jpeg_parse_failed", "executed": False}
            dimensions_match = (
                width == expected_width and height == expected_height
            )
            return {
                "download_id": download_id,
                "format": format,
                "width": width,
                "height": height,
                "dimensions_match": dimensions_match,
                "verification_status": (
                    "verified" if dimensions_match else "mismatch"
                ),
                "mutation_executed": False,
            }
        return {"error": "download_verification_format_unsupported", "executed": False}

    def inspect_new_tab_semantic(
        self, name, expected_url_prefix, exact=True,
    ):
        """Open one exact target=_blank link, inspect it, and restore parent."""
        self._ensure_started()
        self._reset_diagnostics()
        if not isinstance(name, str) or not name.strip() or len(name) > 300:
            return {"error": "new_tab_link_name_invalid", "executed": False}
        if (
            not isinstance(expected_url_prefix, str)
            or not expected_url_prefix.strip()
            or len(expected_url_prefix) > 2000
        ):
            return {"error": "new_tab_expected_url_invalid", "executed": False}
        expected_url_prefix = expected_url_prefix.strip()
        expected_parts = urlsplit(expected_url_prefix)
        if (
            expected_parts.scheme not in {"http", "https"}
            or not expected_parts.netloc
            or expected_parts.username is not None
            or expected_parts.password is not None
            or expected_parts.query
            or expected_parts.fragment
        ):
            return {"error": "new_tab_expected_url_unsafe", "executed": False}

        locator = self.page.get_by_role("link", name=name, exact=exact)
        matches = []
        for index in range(min(locator.count(), 50)):
            candidate = locator.nth(index)
            if candidate.is_visible():
                matches.append(candidate)
        if len(matches) != 1:
            return {
                "error": "new_tab_link_not_unique",
                "matches": len(matches),
                "executed": False,
            }
        target = matches[0]
        if str(target.get_attribute("target") or "").casefold() != "_blank":
            return {"error": "new_tab_target_blank_required", "executed": False}
        href = target.evaluate("el => el.href")
        href_parts = urlsplit(str(href or ""))
        if href_parts.scheme not in {"http", "https"} or not href_parts.netloc:
            return {"error": "new_tab_href_unsafe", "executed": False}
        expected_origin = (
            expected_parts.scheme.casefold(), expected_parts.netloc.casefold()
        )
        href_origin = (href_parts.scheme.casefold(), href_parts.netloc.casefold())
        if href_origin != expected_origin:
            return {"error": "new_tab_href_origin_mismatch", "executed": False}

        parent = self.page
        parent_url = parent.url
        self._begin_action_execution()
        popup = None
        try:
            with parent.expect_popup(timeout=10000) as popup_info:
                target.click(timeout=10000)
            popup = popup_info.value
            popup.wait_for_load_state("domcontentloaded", timeout=10000)
            final_url = popup.url
            title = popup.title()[:300]
            try:
                text_preview = popup.locator("body").inner_text(timeout=3000)[:2000]
            except Exception:
                text_preview = ""
            url_matches = final_url.startswith(expected_url_prefix)
        except Exception as exc:
            result = self._capture_state("inspect-new-tab-semantic")
            result.update({
                "error": "new_tab_open_failed",
                "error_type": type(exc).__name__,
                "new_tab_link": name,
                "mutation_executed": False,
            })
            return self._finish_action_execution(result)
        finally:
            if popup is not None and not popup.is_closed():
                popup.close()

        parent_restored = (
            self.page is parent
            and not parent.is_closed()
            and parent.url == parent_url
            and len(self.context.pages) == 1
        )
        verified = bool(url_matches and parent_restored)
        result = self._capture_state("inspect-new-tab-semantic")
        result.update({
            "new_tab_link": name,
            "new_tab_url": self._safe_network_url(final_url),
            "new_tab_expected_url_prefix": self._safe_network_url(
                expected_url_prefix
            ),
            "new_tab_url_matches": url_matches,
            "new_tab_title": title,
            "new_tab_text_preview": text_preview,
            "parent_context_restored": parent_restored,
            "new_tab_status": "verified" if verified else "mismatch",
            "mutation_executed": False,
        })
        if not verified:
            result["error"] = "new_tab_verification_failed"
        return self._finish_action_execution(result)

    def navigate_history_semantic(
        self, direction, expected_url_prefix,
    ):
        """Navigate one same-origin history step and verify the destination."""
        self._ensure_started()
        self._reset_diagnostics()
        if direction not in {"back", "forward"}:
            return {"error": "history_direction_invalid", "executed": False}
        if (
            not isinstance(expected_url_prefix, str)
            or not expected_url_prefix.strip()
            or len(expected_url_prefix) > 2000
        ):
            return {"error": "history_expected_url_invalid", "executed": False}
        expected_url_prefix = expected_url_prefix.strip()
        expected_parts = urlsplit(expected_url_prefix)
        current_parts = urlsplit(self.page.url)
        if (
            expected_parts.scheme not in {"http", "https"}
            or not expected_parts.netloc
            or expected_parts.username is not None
            or expected_parts.password is not None
            or expected_parts.query
            or expected_parts.fragment
        ):
            return {"error": "history_expected_url_unsafe", "executed": False}
        if (
            expected_parts.scheme.casefold(), expected_parts.netloc.casefold()
        ) != (
            current_parts.scheme.casefold(), current_parts.netloc.casefold()
        ):
            return {"error": "history_cross_origin_blocked", "executed": False}

        self._begin_action_execution()
        try:
            response = (
                self.page.go_back(wait_until="domcontentloaded", timeout=10000)
                if direction == "back"
                else self.page.go_forward(
                    wait_until="domcontentloaded", timeout=10000,
                )
            )
        except Exception as exc:
            result = self._capture_state("navigate-history-semantic")
            result.update({
                "error": "history_navigation_failed",
                "error_type": type(exc).__name__,
                "history_direction": direction,
                "mutation_executed": False,
            })
            return self._finish_action_execution(result)
        if response is None:
            result = self._capture_state("navigate-history-semantic")
            result.update({
                "error": "history_entry_unavailable",
                "history_direction": direction,
                "mutation_executed": False,
            })
            return self._finish_action_execution(result)

        self.page.wait_for_timeout(250)
        actual_url = self.page.url
        url_matches = actual_url.startswith(expected_url_prefix)
        result = self._capture_state("navigate-history-semantic")
        result.update({
            "history_direction": direction,
            "history_url": self._safe_network_url(actual_url),
            "history_expected_url_prefix": self._safe_network_url(
                expected_url_prefix
            ),
            "history_url_matches": url_matches,
            "history_http_status": response.status,
            "history_status": "verified" if url_matches else "mismatch",
            "mutation_executed": False,
        })
        if not url_matches:
            result["error"] = "history_destination_mismatch"
        return self._finish_action_execution(result)

    def inspect_iframe_semantic(
        self, name, expected_url_prefix, exact=True,
    ):
        """Inspect one named iframe without changing the top-level page."""
        self._ensure_started()
        self._reset_diagnostics()
        if not isinstance(name, str) or not name.strip() or len(name) > 300:
            return {"error": "iframe_name_invalid", "executed": False}
        if (
            not isinstance(expected_url_prefix, str)
            or not expected_url_prefix.strip()
            or len(expected_url_prefix) > 2000
        ):
            return {"error": "iframe_expected_url_invalid", "executed": False}
        expected_url_prefix = expected_url_prefix.strip()
        expected_parts = urlsplit(expected_url_prefix)
        if (
            expected_parts.scheme not in {"http", "https"}
            or not expected_parts.netloc
            or expected_parts.username is not None
            or expected_parts.password is not None
            or expected_parts.query
            or expected_parts.fragment
        ):
            return {"error": "iframe_expected_url_unsafe", "executed": False}

        frames = self.page.locator("iframe")
        matches = []
        expected_name = name if exact else name.casefold()
        for index in range(min(frames.count(), 50)):
            candidate = frames.nth(index)
            if not candidate.is_visible():
                continue
            candidate_names = [
                str(candidate.get_attribute(key) or "").strip()
                for key in ("title", "aria-label", "name")
            ]
            matched = (
                expected_name in candidate_names
                if exact
                else any(
                    expected_name in value.casefold()
                    for value in candidate_names if value
                )
            )
            if matched:
                matches.append(candidate)
        if len(matches) != 1:
            return {
                "error": "iframe_not_unique",
                "matches": len(matches),
                "executed": False,
            }

        iframe = matches[0]
        iframe_handle = iframe.element_handle()
        frame = iframe_handle.content_frame() if iframe_handle is not None else None
        if frame is None:
            return {"error": "iframe_content_unavailable", "executed": False}
        try:
            frame.wait_for_load_state("domcontentloaded", timeout=10000)
        except Exception:
            pass
        frame_url = frame.url
        frame_parts = urlsplit(frame_url)
        expected_origin = (
            expected_parts.scheme.casefold(), expected_parts.netloc.casefold()
        )
        frame_origin = (
            frame_parts.scheme.casefold(), frame_parts.netloc.casefold()
        )
        origin_matches = frame_origin == expected_origin
        url_matches = origin_matches and frame_url.startswith(expected_url_prefix)
        try:
            frame_title = frame.title()[:300]
        except Exception:
            frame_title = ""
        try:
            text_preview = frame.locator("body").inner_text(timeout=3000)[:2000]
        except Exception:
            text_preview = ""
        try:
            interactive_count = min(
                frame.locator(
                    "a, button, input, select, textarea, "
                    "[role='button'], [role='link'], [role='textbox'], "
                    "[role='combobox']"
                ).count(),
                1000,
            )
        except Exception:
            interactive_count = None
        try:
            surface = frame.evaluate(
                """
                () => {
                    const canvases = Array.from(
                        document.querySelectorAll("canvas")
                    );
                    const videos = Array.from(
                        document.querySelectorAll("video")
                    );
                    const canvasMetrics = canvases.slice(0, 20).map(canvas => {
                        const rect = canvas.getBoundingClientRect();
                        return {
                            width: canvas.width,
                            height: canvas.height,
                            display_width: Math.round(rect.width * 100) / 100,
                            display_height: Math.round(rect.height * 100) / 100,
                            visible: Boolean(
                                rect.width > 0
                                && rect.height > 0
                                && getComputedStyle(canvas).visibility !== "hidden"
                                && getComputedStyle(canvas).display !== "none"
                            )
                        };
                    });
                    const videoMetrics = videos.slice(0, 20).map(video => {
                        const rect = video.getBoundingClientRect();
                        return {
                            video_width: video.videoWidth,
                            video_height: video.videoHeight,
                            display_width: Math.round(rect.width * 100) / 100,
                            display_height: Math.round(rect.height * 100) / 100,
                            ready_state: video.readyState,
                            paused: video.paused,
                            visible: Boolean(
                                rect.width > 0
                                && rect.height > 0
                                && getComputedStyle(video).visibility !== "hidden"
                                && getComputedStyle(video).display !== "none"
                            )
                        };
                    });
                    const canvasReady = canvasMetrics.some(item => (
                        item.visible
                        && item.width > 0
                        && item.height > 0
                        && item.display_width > 0
                        && item.display_height > 0
                    ));
                    const videoReady = videoMetrics.some(item => (
                        item.visible
                        && item.ready_state >= 2
                        && item.video_width > 0
                        && item.video_height > 0
                    ));
                    return {
                        document_ready_state: document.readyState,
                        canvas_count: canvases.length,
                        video_count: videos.length,
                        canvases: canvasMetrics,
                        videos: videoMetrics,
                        surface_present: canvases.length + videos.length > 0,
                        surface_ready: canvasReady || videoReady
                    };
                }
                """
            )
        except Exception:
            surface = {
                "document_ready_state": None,
                "canvas_count": None,
                "video_count": None,
                "canvases": [],
                "videos": [],
                "surface_present": None,
                "surface_ready": None,
            }

        result = self._capture_state("inspect-iframe-semantic")
        result.update({
            "iframe_name": name,
            "iframe_url": self._safe_network_url(frame_url),
            "iframe_expected_url_prefix": self._safe_network_url(
                expected_url_prefix
            ),
            "iframe_origin_matches": origin_matches,
            "iframe_url_matches": url_matches,
            "iframe_title": frame_title,
            "iframe_text_preview": text_preview,
            "iframe_interactive_count": interactive_count,
            "iframe_surface": surface,
            "iframe_status": "verified" if url_matches else "mismatch",
            "mutation_executed": False,
        })
        if not url_matches:
            result["error"] = "iframe_url_mismatch"
        return result

    def observe_iframe_surface_change_semantic(
        self, name, expected_url_prefix, expect_change,
        wait_ms=1000, exact=True,
    ):
        """Compare two private iframe screenshots without exposing pixels."""
        if type(expect_change) is not bool:
            return {"error": "iframe_expect_change_invalid", "executed": False}
        if type(wait_ms) is not int or not 100 <= wait_ms <= 5000:
            return {"error": "iframe_change_wait_invalid", "executed": False}
        inspected = self.inspect_iframe_semantic(
            name, expected_url_prefix, exact,
        )
        if inspected.get("iframe_status") != "verified":
            inspected["surface_change_status"] = "not_observed"
            return inspected

        frames = self.page.locator("iframe")
        matches = []
        expected_name = name if exact else name.casefold()
        for index in range(min(frames.count(), 50)):
            candidate = frames.nth(index)
            if not candidate.is_visible():
                continue
            candidate_names = [
                str(candidate.get_attribute(key) or "").strip()
                for key in ("title", "aria-label", "name")
            ]
            matched = (
                expected_name in candidate_names
                if exact
                else any(
                    expected_name in value.casefold()
                    for value in candidate_names if value
                )
            )
            if matched:
                matches.append(candidate)
        if len(matches) != 1:
            return {
                "error": "iframe_not_unique",
                "matches": len(matches),
                "executed": False,
            }

        iframe = matches[0]
        before_path = self.session_dir / (
            f"iframe-before-{uuid.uuid4().hex}.png"
        )
        after_path = self.session_dir / (
            f"iframe-after-{uuid.uuid4().hex}.png"
        )
        try:
            iframe.screenshot(path=str(before_path))
            before_path.chmod(0o600)
            self.page.wait_for_timeout(wait_ms)
            iframe.screenshot(path=str(after_path))
            after_path.chmod(0o600)
            before_hash = hashlib.sha256(before_path.read_bytes()).hexdigest()
            after_hash = hashlib.sha256(after_path.read_bytes()).hexdigest()
        except Exception as exc:
            return {
                "error": "iframe_surface_capture_failed",
                "error_type": type(exc).__name__,
                "executed": False,
            }

        changed = before_hash != after_hash
        matches_expectation = changed is expect_change
        result = self._capture_state("observe-iframe-surface-change")
        result.update({
            "iframe_name": name,
            "iframe_expected_url_prefix": self._safe_network_url(
                expected_url_prefix
            ),
            "surface_wait_ms": wait_ms,
            "surface_expected_change": expect_change,
            "surface_changed": changed,
            "surface_change_matches": matches_expectation,
            "surface_before_sha256": before_hash,
            "surface_after_sha256": after_hash,
            "surface_change_status": (
                "verified" if matches_expectation else "mismatch"
            ),
            "mutation_executed": False,
        })
        if not matches_expectation:
            result["error"] = "iframe_surface_change_mismatch"
        return result

    def click_iframe_surface_semantic(
        self, name, expected_url_prefix, x_ratio, y_ratio,
        expect_change, wait_ms=1000, exact=True,
    ):
        """Click one normalized point in a verified iframe surface."""
        if (
            type(x_ratio) not in {int, float}
            or type(y_ratio) not in {int, float}
            or not 0.0 <= float(x_ratio) <= 1.0
            or not 0.0 <= float(y_ratio) <= 1.0
        ):
            return {"error": "iframe_click_ratio_invalid", "executed": False}
        if type(expect_change) is not bool:
            return {"error": "iframe_expect_change_invalid", "executed": False}
        if type(wait_ms) is not int or not 100 <= wait_ms <= 5000:
            return {"error": "iframe_click_wait_invalid", "executed": False}
        inspected = self.inspect_iframe_semantic(
            name, expected_url_prefix, exact,
        )
        if inspected.get("iframe_status") != "verified":
            inspected["iframe_click_status"] = "not_executed"
            return inspected
        surface = inspected.get("iframe_surface") or {}
        if surface.get("surface_ready") is not True:
            inspected.update({
                "error": "iframe_surface_not_ready",
                "iframe_click_status": "not_executed",
            })
            return inspected

        frames = self.page.locator("iframe")
        matches = []
        expected_name = name if exact else name.casefold()
        for index in range(min(frames.count(), 50)):
            candidate = frames.nth(index)
            if not candidate.is_visible():
                continue
            candidate_names = [
                str(candidate.get_attribute(key) or "").strip()
                for key in ("title", "aria-label", "name")
            ]
            matched = (
                expected_name in candidate_names
                if exact
                else any(
                    expected_name in value.casefold()
                    for value in candidate_names if value
                )
            )
            if matched:
                matches.append(candidate)
        if len(matches) != 1:
            return {
                "error": "iframe_not_unique",
                "matches": len(matches),
                "executed": False,
            }

        iframe = matches[0]
        box = iframe.bounding_box()
        if not box or box["width"] <= 0 or box["height"] <= 0:
            return {"error": "iframe_surface_geometry_invalid", "executed": False}
        click_x = min(
            max(box["width"] * float(x_ratio), 1),
            max(box["width"] - 1, 1),
        )
        click_y = min(
            max(box["height"] * float(y_ratio), 1),
            max(box["height"] - 1, 1),
        )
        before_path = self.session_dir / (
            f"iframe-click-before-{uuid.uuid4().hex}.png"
        )
        after_path = self.session_dir / (
            f"iframe-click-after-{uuid.uuid4().hex}.png"
        )
        self._begin_action_execution()
        try:
            iframe.screenshot(path=str(before_path))
            before_path.chmod(0o600)
            iframe.click(
                position={"x": click_x, "y": click_y},
                timeout=10000,
            )
            self.page.wait_for_timeout(wait_ms)
            iframe.screenshot(path=str(after_path))
            after_path.chmod(0o600)
            before_hash = hashlib.sha256(before_path.read_bytes()).hexdigest()
            after_hash = hashlib.sha256(after_path.read_bytes()).hexdigest()
        except Exception as exc:
            result = self._capture_state("click-iframe-surface")
            result.update({
                "error": "iframe_surface_click_failed",
                "error_type": type(exc).__name__,
                "iframe_click_status": "failed",
                "mutation_executed": False,
            })
            return self._finish_action_execution(result)

        changed = before_hash != after_hash
        matches_expectation = changed is expect_change
        result = self._capture_state("click-iframe-surface")
        result.update({
            "iframe_name": name,
            "iframe_expected_url_prefix": self._safe_network_url(
                expected_url_prefix
            ),
            "iframe_click_x_ratio": float(x_ratio),
            "iframe_click_y_ratio": float(y_ratio),
            "surface_wait_ms": wait_ms,
            "surface_expected_change": expect_change,
            "surface_changed": changed,
            "surface_change_matches": matches_expectation,
            "surface_before_sha256": before_hash,
            "surface_after_sha256": after_hash,
            "iframe_click_status": (
                "verified" if matches_expectation else "mismatch"
            ),
            "mutation_executed": True,
        })
        if not matches_expectation:
            result["error"] = "iframe_click_result_mismatch"
        return self._finish_action_execution(result)

    def press_iframe_surface_key_semantic(
        self, name, expected_url_prefix, key, x_ratio, y_ratio,
        expect_change, focus_expect_change=False, wait_ms=500, exact=True,
    ):
        """Focus a verified iframe point, then press one allowlisted key."""
        allowed = {
            "Tab", "Shift+Tab", "Escape", "Enter", "Space",
            "ArrowUp", "ArrowDown", "ArrowLeft", "ArrowRight",
            "Home", "End", "PageUp", "PageDown", "Shift+Enter",
            "Alt+ArrowDown",
        }
        normalized = str(key or "").strip()
        canonical = next(
            (item for item in allowed if item.casefold() == normalized.casefold()),
            None,
        )
        if canonical is None:
            return {
                "error": "unsupported_iframe_keyboard_key",
                "key": key,
                "allowed_keys": sorted(allowed),
                "executed": False,
            }
        if type(focus_expect_change) is not bool or type(expect_change) is not bool:
            return {"error": "iframe_key_expect_change_invalid", "executed": False}
        if type(wait_ms) is not int or not 100 <= wait_ms <= 5000:
            return {"error": "iframe_key_wait_invalid", "executed": False}

        focused = self.click_iframe_surface_semantic(
            name, expected_url_prefix, x_ratio, y_ratio,
            focus_expect_change, 100, exact,
        )
        if focused.get("iframe_click_status") != "verified":
            focused["iframe_key_status"] = "not_executed"
            return focused

        frames = self.page.locator("iframe")
        matches = []
        expected_name = name if exact else name.casefold()
        for index in range(min(frames.count(), 50)):
            candidate = frames.nth(index)
            if not candidate.is_visible():
                continue
            names = [
                str(candidate.get_attribute(attr) or "").strip()
                for attr in ("title", "aria-label", "name")
            ]
            if (
                expected_name in names
                if exact
                else any(expected_name in value.casefold() for value in names if value)
            ):
                matches.append(candidate)
        if len(matches) != 1:
            return {"error": "iframe_not_unique", "matches": len(matches), "executed": False}
        iframe = matches[0]
        before_path = self.session_dir / f"iframe-key-before-{uuid.uuid4().hex}.png"
        after_path = self.session_dir / f"iframe-key-after-{uuid.uuid4().hex}.png"
        self._begin_action_execution()
        try:
            iframe.screenshot(path=str(before_path))
            before_path.chmod(0o600)
            self.page.keyboard.press(canonical)
            self.page.wait_for_timeout(wait_ms)
            iframe.screenshot(path=str(after_path))
            after_path.chmod(0o600)
            before_hash = hashlib.sha256(before_path.read_bytes()).hexdigest()
            after_hash = hashlib.sha256(after_path.read_bytes()).hexdigest()
        except Exception as exc:
            result = self._capture_state("press-iframe-surface-key")
            result.update({
                "error": "iframe_surface_key_failed",
                "error_type": type(exc).__name__,
                "iframe_key_status": "failed",
                "mutation_executed": False,
            })
            return self._finish_action_execution(result)
        changed = before_hash != after_hash
        matches_expectation = changed is expect_change
        result = self._capture_state("press-iframe-surface-key")
        result.update({
            "iframe_name": name,
            "pressed_key": canonical,
            "surface_expected_change": expect_change,
            "surface_changed": changed,
            "surface_change_matches": matches_expectation,
            "surface_before_sha256": before_hash,
            "surface_after_sha256": after_hash,
            "iframe_key_status": "verified" if matches_expectation else "mismatch",
            "mutation_executed": True,
        })
        if not matches_expectation:
            result["error"] = "iframe_key_result_mismatch"
        return self._finish_action_execution(result)

    def inspect_hover_tooltip_semantic(
        self, target, target_role, expected_tooltip, exact=True,
    ):
        """Hover one exact semantic target and verify one ARIA tooltip."""
        self._ensure_started()
        self._reset_diagnostics()
        allowed_roles = {
            "button", "link", "img", "checkbox", "radio",
            "textbox", "combobox", "tab", "menuitem",
        }
        target_role = str(target_role or "").strip().casefold()
        if target_role not in allowed_roles:
            return {
                "error": "hover_target_role_invalid",
                "supported_roles": sorted(allowed_roles),
                "executed": False,
            }
        if (
            not isinstance(expected_tooltip, str)
            or not expected_tooltip.strip()
            or len(expected_tooltip) > 500
        ):
            return {"error": "expected_tooltip_invalid", "executed": False}
        candidates = self.page.get_by_role(
            target_role, name=target, exact=exact,
        )
        visible_targets = []
        for index in range(min(candidates.count(), 50)):
            candidate = candidates.nth(index)
            if candidate.is_visible():
                visible_targets.append(candidate)
        if len(visible_targets) != 1:
            return {
                "error": "hover_target_not_unique",
                "matches": len(visible_targets),
                "executed": False,
            }
        tooltip_locator = self.page.get_by_role(
            "tooltip", name=expected_tooltip, exact=exact,
        )
        if any(
            tooltip_locator.nth(index).is_visible()
            for index in range(min(tooltip_locator.count(), 50))
        ):
            return {"error": "tooltip_already_visible", "executed": False}

        self._begin_action_execution()
        visible_tooltips = []
        try:
            visible_targets[0].hover(timeout=10000)
            self.page.wait_for_timeout(350)
            for index in range(min(tooltip_locator.count(), 50)):
                candidate = tooltip_locator.nth(index)
                if candidate.is_visible():
                    visible_tooltips.append(candidate)
        except Exception as exc:
            result = self._capture_state("inspect-hover-tooltip")
            result.update({
                "error": "hover_tooltip_failed",
                "error_type": type(exc).__name__,
                "tooltip_status": "failed",
                "mutation_executed": False,
            })
            return self._finish_action_execution(result)

        opened = len(visible_tooltips) == 1
        tooltip_text = (
            visible_tooltips[0].inner_text()[:500] if opened else ""
        )
        result = self._capture_state("inspect-hover-tooltip")
        viewport = self.page.viewport_size or {"width": 1920, "height": 1080}
        self.page.mouse.move(
            max(viewport["width"] - 1, 0),
            max(viewport["height"] - 1, 0),
        )
        self.page.wait_for_timeout(150)
        closed_after = not any(
            tooltip_locator.nth(index).is_visible()
            for index in range(min(tooltip_locator.count(), 50))
        )
        verified = opened and closed_after
        result.update({
            "hover_target": target,
            "hover_target_role": target_role,
            "expected_tooltip": expected_tooltip,
            "tooltip_match_count": len(visible_tooltips),
            "tooltip_text": tooltip_text,
            "tooltip_opened": opened,
            "tooltip_closed_after_hover": closed_after,
            "tooltip_status": "verified" if verified else "mismatch",
            "mutation_executed": False,
        })
        if not verified:
            result["error"] = "hover_tooltip_verification_failed"
        return self._finish_action_execution(result)

    def handle_native_dialog_semantic(
        self, target, expected_type, expected_message,
        decision="dismiss", prompt_text=None, exact=True,
    ):
        """Trigger and safely handle one expected native browser dialog."""
        self._ensure_started()
        self._reset_diagnostics()
        if expected_type not in {"alert", "confirm", "prompt", "beforeunload"}:
            return {"error": "native_dialog_type_invalid", "executed": False}
        if decision not in {"accept", "dismiss"}:
            return {"error": "native_dialog_decision_invalid", "executed": False}
        if not isinstance(expected_message, str) or len(expected_message) > 1000:
            return {"error": "native_dialog_message_invalid", "executed": False}
        if prompt_text is not None and (
            expected_type != "prompt"
            or not isinstance(prompt_text, str)
            or len(prompt_text) > 500
        ):
            return {"error": "native_dialog_prompt_invalid", "executed": False}
        candidates = self.page.get_by_role("button", name=target, exact=exact)
        visible = [
            candidates.nth(i) for i in range(min(candidates.count(), 50))
            if candidates.nth(i).is_visible()
        ]
        if len(visible) != 1:
            return {"error": "native_dialog_target_not_unique", "matches": len(visible), "executed": False}

        observed = []
        def handle(dialog):
            type_matches = dialog.type == expected_type
            message_matches = dialog.message == expected_message
            safe_match = type_matches and message_matches
            applied = "dismiss"
            if safe_match and decision == "accept":
                dialog.accept(prompt_text or "")
                applied = "accept"
            else:
                dialog.dismiss()
            observed.append({
                "type": dialog.type,
                "message": dialog.message[:1000],
                "default_value_present": bool(dialog.default_value),
                "type_matches": type_matches,
                "message_matches": message_matches,
                "decision_applied": applied,
                "fail_closed": not safe_match,
            })

        self.page.once("dialog", handle)
        self._begin_action_execution()
        try:
            visible[0].click(timeout=10000)
            self.page.wait_for_timeout(300)
        except Exception as exc:
            result = self._capture_state("handle-native-dialog")
            result.update({"error": "native_dialog_trigger_failed", "error_type": type(exc).__name__, "mutation_executed": False})
            return self._finish_action_execution(result)
        verified = len(observed) == 1 and observed[0]["type_matches"] and observed[0]["message_matches"] and observed[0]["decision_applied"] == decision
        result = self._capture_state("handle-native-dialog")
        result.update({
            "native_dialog_target": target,
            "native_dialog_expected_type": expected_type,
            "native_dialog_expected_message": expected_message,
            "native_dialog_expected_decision": decision,
            "native_dialog_observed": observed,
            "native_dialog_status": "verified" if verified else "mismatch",
            "prompt_text_supplied": prompt_text is not None,
            "mutation_executed": bool(verified and decision == "accept"),
        })
        if not verified:
            result["error"] = "native_dialog_verification_failed"
        return self._finish_action_execution(result)

    def inspect_form_validation_semantic(self, form=None, exact=True):
        """Read native constraint-validation state without submitting."""
        self._ensure_started()
        self._reset_diagnostics()
        scope = self.page.locator("body")
        form_identity = None
        if form:
            forms = self.page.locator("form")
            matches = []
            expected = form if exact else str(form).casefold()
            for index in range(min(forms.count(), 50)):
                candidate = forms.nth(index)
                names = [
                    str(candidate.get_attribute(attr) or "").strip()
                    for attr in ("aria-label", "name", "id")
                ]
                matched = expected in names if exact else any(
                    expected in value.casefold() for value in names if value
                )
                if matched and candidate.is_visible():
                    matches.append(candidate)
            if len(matches) != 1:
                return {"error": "validation_form_not_unique", "matches": len(matches), "executed": False}
            scope = matches[0]
            form_identity = form
        audit = scope.evaluate(
            """
            root => {
              const controls = Array.from(root.querySelectorAll('input, select, textarea'));
              const visible = controls.filter(el => {
                const rect = el.getBoundingClientRect();
                const style = getComputedStyle(el);
                return rect.width > 0 && rect.height > 0
                  && style.display !== 'none' && style.visibility !== 'hidden';
              }).slice(0, 200);
              const invalid = visible.filter(el => el.willValidate && !el.validity.valid)
                .slice(0, 50).map(el => {
                  const label = (
                    (el.labels && el.labels[0] && el.labels[0].innerText)
                    || el.getAttribute('aria-label')
                    || el.getAttribute('placeholder')
                    || el.getAttribute('name')
                    || el.id || ''
                  ).trim().slice(0, 200);
                  const v = el.validity;
                  return {
                    label,
                    tag: el.tagName.toLowerCase(),
                    type: el.getAttribute('type') || '',
                    required: el.required,
                    value_missing: v.valueMissing,
                    type_mismatch: v.typeMismatch,
                    pattern_mismatch: v.patternMismatch,
                    range_underflow: v.rangeUnderflow,
                    range_overflow: v.rangeOverflow,
                    step_mismatch: v.stepMismatch,
                    too_short: v.tooShort,
                    too_long: v.tooLong,
                    bad_input: v.badInput,
                    custom_error: v.customError,
                    validation_message: String(el.validationMessage || '').slice(0, 300)
                  };
                });
              return {
                visible_control_count: visible.length,
                invalid_control_count: invalid.length,
                invalid_controls: invalid,
                validation_passed: invalid.length === 0,
                truncated: controls.length > 200 || invalid.length > 50
              };
            }
            """
        )
        result = self._capture_state("inspect-form-validation")
        result.update({
            "validation_form": form_identity,
            "validation_audit": audit,
            "mutation_executed": False,
        })
        return result

    def inspect_loading_state_semantic(
        self,
        scope=None,
        expected_state="ready",
        wait_ms=2000,
        require_transition=False,
        exact=True,
    ):
        """Observe an ARIA loading lifecycle without changing page state."""
        self._ensure_started()
        self._reset_diagnostics()
        if expected_state not in {"busy", "ready"}:
            return {"error": "loading_expected_state_invalid", "executed": False}
        if not isinstance(wait_ms, int) or isinstance(wait_ms, bool) or not 0 <= wait_ms <= 10000:
            return {"error": "loading_wait_ms_invalid", "executed": False}

        root = self.page.locator("body")
        scope_identity = None
        if scope:
            candidates = self.page.locator("[aria-label], [name], [id]")
            matches = []
            expected = scope if exact else str(scope).casefold()
            for index in range(min(candidates.count(), 500)):
                candidate = candidates.nth(index)
                names = [
                    str(candidate.get_attribute(attr) or "").strip()
                    for attr in ("aria-label", "name", "id")
                ]
                matched = expected in names if exact else any(
                    expected in value.casefold() for value in names if value
                )
                if matched and candidate.is_visible():
                    matches.append(candidate)
            if len(matches) != 1:
                return {"error": "loading_scope_not_unique", "matches": len(matches), "executed": False}
            root = matches[0]
            scope_identity = scope

        def sample():
            return root.evaluate(
                """
                root => {
                  const visible = el => {
                    const rect = el.getBoundingClientRect();
                    const style = getComputedStyle(el);
                    return rect.width > 0 && rect.height > 0
                      && style.display !== 'none' && style.visibility !== 'hidden'
                      && Number(style.opacity || 1) > 0;
                  };
                  const all = [root, ...root.querySelectorAll('[aria-busy="true"], [role="progressbar"]')];
                  const unique = [...new Set(all)].filter(el =>
                    visible(el) && (
                      el.getAttribute('aria-busy') === 'true'
                      || el.getAttribute('role') === 'progressbar'
                    )
                  );
                  const busyContainers = unique.filter(el => el.getAttribute('aria-busy') === 'true');
                  const progressbars = unique.filter(el => el.getAttribute('role') === 'progressbar');
                  const describe = el => ({
                    role: el.getAttribute('role') || '',
                    label: String(
                      el.getAttribute('aria-label') || el.getAttribute('title') || ''
                    ).trim().slice(0, 160)
                  });
                  return {
                    busy: busyContainers.length > 0 || progressbars.length > 0,
                    aria_busy_count: busyContainers.length,
                    progressbar_count: progressbars.length,
                    indicators: unique.slice(0, 20).map(describe),
                    truncated: unique.length > 20
                  };
                }
                """
            )

        first = sample()
        current = first
        observed_busy = bool(first["busy"])
        observed_ready = not observed_busy
        sample_count = 1
        remaining = wait_ms
        while remaining > 0:
            verified = (
                current["busy"] if expected_state == "busy"
                else (not current["busy"] and (not require_transition or observed_busy))
            )
            if verified:
                break
            delay = min(100, remaining)
            self.page.wait_for_timeout(delay)
            remaining -= delay
            current = sample()
            sample_count += 1
            observed_busy = observed_busy or bool(current["busy"])
            observed_ready = observed_ready or not bool(current["busy"])

        verified = (
            current["busy"] if expected_state == "busy"
            else (not current["busy"] and (not require_transition or observed_busy))
        )
        result = self._capture_state("inspect-loading-state")
        result.update({
            "loading_scope": scope_identity,
            "loading_expected_state": expected_state,
            "loading_require_transition": bool(require_transition),
            "loading_initial": first,
            "loading_final": current,
            "loading_observed_busy": observed_busy,
            "loading_observed_ready": observed_ready,
            "loading_sample_count": sample_count,
            "loading_status": "verified" if verified else "mismatch",
            "mutation_executed": False,
        })
        if not verified:
            result["error"] = "loading_state_verification_failed"
        return result

    def inspect_notification_lifecycle_semantic(
        self,
        expected_text,
        role="alert",
        expected_state="visible",
        wait_ms=2000,
        require_seen=False,
        exact=True,
    ):
        """Observe one transient ARIA alert/status without interacting."""
        self._ensure_started()
        self._reset_diagnostics()
        if role not in {"alert", "status"}:
            return {"error": "notification_role_invalid", "executed": False}
        if expected_state not in {"visible", "dismissed"}:
            return {"error": "notification_expected_state_invalid", "executed": False}
        if (
            not isinstance(expected_text, str)
            or not expected_text.strip()
            or len(expected_text) > 500
        ):
            return {"error": "notification_text_invalid", "executed": False}
        if not isinstance(wait_ms, int) or isinstance(wait_ms, bool) or not 0 <= wait_ms <= 10000:
            return {"error": "notification_wait_ms_invalid", "executed": False}

        def sample():
            return self.page.evaluate(
                """
                ({role, expectedText, exact}) => {
                  const visible = el => {
                    const rect = el.getBoundingClientRect();
                    const style = getComputedStyle(el);
                    return rect.width > 0 && rect.height > 0
                      && style.display !== 'none' && style.visibility !== 'hidden'
                      && Number(style.opacity || 1) > 0;
                  };
                  const normalize = value => String(value || '').trim().replace(/\\s+/g, ' ');
                  const wanted = exact ? expectedText : expectedText.toLocaleLowerCase();
                  const matches = Array.from(document.querySelectorAll(`[role="${role}"]`))
                    .filter(visible)
                    .filter(el => {
                      const label = normalize(el.getAttribute('aria-label') || el.innerText);
                      return exact ? label === wanted : label.toLocaleLowerCase().includes(wanted);
                    });
                  return {
                    match_count: matches.length,
                    visible: matches.length === 1,
                    ambiguous: matches.length > 1
                  };
                }
                """,
                {"role": role, "expectedText": expected_text.strip(), "exact": bool(exact)},
            )

        first = sample()
        current = first
        observed_visible = bool(first["visible"])
        sample_count = 1
        remaining = wait_ms
        while remaining > 0 and not current["ambiguous"]:
            verified = (
                current["visible"] if expected_state == "visible"
                else (
                    current["match_count"] == 0
                    and (not require_seen or observed_visible)
                )
            )
            if verified:
                break
            delay = min(100, remaining)
            self.page.wait_for_timeout(delay)
            remaining -= delay
            current = sample()
            sample_count += 1
            observed_visible = observed_visible or bool(current["visible"])

        verified = (
            current["visible"] if expected_state == "visible"
            else (
                current["match_count"] == 0
                and (not require_seen or observed_visible)
            )
        )
        result = self._capture_state("inspect-notification-lifecycle")
        result.update({
            "notification_role": role,
            "notification_expected_text": expected_text.strip(),
            "notification_expected_state": expected_state,
            "notification_require_seen": bool(require_seen),
            "notification_initial": first,
            "notification_final": current,
            "notification_observed_visible": observed_visible,
            "notification_sample_count": sample_count,
            "notification_status": "verified" if verified else "mismatch",
            "mutation_executed": False,
        })
        if current["ambiguous"]:
            result["error"] = "notification_not_unique"
        elif not verified:
            result["error"] = "notification_lifecycle_verification_failed"
        return result

    def inspect_aria_field_errors_semantic(self, form=None, exact=True):
        """Audit visible ARIA field errors without returning control values."""
        self._ensure_started()
        self._reset_diagnostics()
        root = self.page.locator("body")
        if form:
            forms = self.page.locator("form")
            matches = []
            expected = form if exact else str(form).casefold()
            for index in range(min(forms.count(), 50)):
                candidate = forms.nth(index)
                names = [str(candidate.get_attribute(a) or "").strip() for a in ("aria-label", "name", "id")]
                matched = expected in names if exact else any(expected in v.casefold() for v in names if v)
                if matched and candidate.is_visible():
                    matches.append(candidate)
            if len(matches) != 1:
                return {"error": "aria_error_form_not_unique", "matches": len(matches), "executed": False}
            root = matches[0]
        audit = root.evaluate("""
          root => {
            const controls = Array.from(root.querySelectorAll('[aria-invalid="true"]')).slice(0, 100);
            const items = controls.map(el => {
              const ids = `${el.getAttribute('aria-errormessage') || ''} ${el.getAttribute('aria-describedby') || ''}`.trim().split(/\s+/).filter(Boolean);
              const messages = ids.map(id => document.getElementById(id)).filter(Boolean);
              const label = ((el.labels && el.labels[0] && el.labels[0].innerText) || el.getAttribute('aria-label') || el.getAttribute('name') || el.id || '').trim().slice(0, 160);
              return {label, role: el.getAttribute('role') || '', message_ids: ids.slice(0, 20), messages: messages.map(x => String(x.innerText || '').trim().slice(0, 300)).filter(Boolean).slice(0, 20), broken_reference_count: ids.length - messages.length};
            });
            return {invalid_control_count: items.length, invalid_controls: items, aria_errors_passed: items.length === 0, truncated: controls.length > 100};
          }
        """)
        result = self._capture_state("inspect-aria-field-errors")
        result.update({"aria_error_form": form, "aria_error_audit": audit, "mutation_executed": False})
        return result

    def inspect_control_state_lifecycle_semantic(self, target, role, expected_state, wait_ms=2000, require_seen=False, exact=True):
        """Wait for one exact semantic control to reach a UI state."""
        self._ensure_started()
        self._reset_diagnostics()
        allowed_roles = {"button", "link", "textbox", "combobox", "checkbox", "radio", "switch", "tab", "menuitem"}
        allowed_states = {"visible", "hidden", "enabled", "disabled", "checked", "unchecked"}
        if role not in allowed_roles or expected_state not in allowed_states:
            return {"error": "control_state_contract_invalid", "executed": False}
        if not isinstance(wait_ms, int) or isinstance(wait_ms, bool) or not 0 <= wait_ms <= 10000:
            return {"error": "control_state_wait_ms_invalid", "executed": False}
        def sample():
            locator = self.page.get_by_role(role, name=target, exact=exact)
            count = min(locator.count(), 50)
            if count > 1:
                return {"matches": count, "ambiguous": True, "visible": False, "enabled": False, "checked": None}
            if count == 0:
                return {"matches": 0, "ambiguous": False, "visible": False, "enabled": False, "checked": None}
            item = locator.first
            visible = item.is_visible()
            enabled = item.is_enabled() if visible else False
            checked = item.is_checked() if role in {"checkbox", "radio", "switch"} and visible else None
            return {"matches": 1, "ambiguous": False, "visible": visible, "enabled": enabled, "checked": checked}
        def matches_state(state):
            return {"visible": state["visible"], "hidden": not state["visible"], "enabled": state["visible"] and state["enabled"], "disabled": state["visible"] and not state["enabled"], "checked": state["checked"] is True, "unchecked": state["checked"] is False}[expected_state]
        first = sample(); current = first; observed_opposite = not matches_state(first); remaining = wait_ms; samples = 1
        while remaining > 0 and not current["ambiguous"] and not (matches_state(current) and (not require_seen or observed_opposite)):
            delay = min(100, remaining); self.page.wait_for_timeout(delay); remaining -= delay
            current = sample(); samples += 1; observed_opposite = observed_opposite or not matches_state(current)
        verified = not current["ambiguous"] and matches_state(current) and (not require_seen or observed_opposite)
        result = self._capture_state("inspect-control-state-lifecycle")
        result.update({"control_target": target, "control_role": role, "control_expected_state": expected_state, "control_initial": first, "control_final": current, "control_observed_opposite": observed_opposite, "control_sample_count": samples, "control_state_status": "verified" if verified else "mismatch", "mutation_executed": False})
        if current["ambiguous"]: result["error"] = "control_state_target_not_unique"
        elif not verified: result["error"] = "control_state_verification_failed"
        return result

    def track_form_dirty_state_semantic(self, form, operation="compare", exact=True):
        """Capture or compare a private form-value fingerprint."""
        self._ensure_started(); self._reset_diagnostics()
        if operation not in {"capture", "compare", "clear"}:
            return {"error": "form_dirty_operation_invalid", "executed": False}
        forms = self.page.locator("form"); matches = []; expected = form if exact else str(form).casefold()
        for index in range(min(forms.count(), 50)):
            candidate = forms.nth(index)
            names = [str(candidate.get_attribute(a) or "").strip() for a in ("aria-label", "name", "id")]
            matched = expected in names if exact else any(expected in v.casefold() for v in names if v)
            if matched and candidate.is_visible(): matches.append(candidate)
        if len(matches) != 1:
            return {"error": "form_dirty_form_not_unique", "matches": len(matches), "executed": False}
        key = f"{self.page.url}|{form}"
        if operation == "clear":
            existed = self._form_state_baselines.pop(key, None) is not None
            return {"form": form, "form_dirty_operation": operation, "baseline_cleared": existed, "mutation_executed": False}
        snapshot = matches[0].evaluate("""root => Array.from(root.querySelectorAll('input,select,textarea')).slice(0,200).map((el,i) => ({i, tag:el.tagName, type:el.type || '', name:el.name || el.id || '', value:el.type === 'file' ? Array.from(el.files || []).map(f => [f.name,f.size,f.type]) : el.value, checked:Boolean(el.checked), selected:Array.from(el.selectedOptions || []).map(x => x.value)}))""")
        digest = hashlib.sha256(json.dumps(snapshot, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()
        if operation == "capture":
            self._form_state_baselines[key] = digest
            dirty = False
        else:
            if key not in self._form_state_baselines:
                return {"error": "form_dirty_baseline_missing", "executed": False}
            dirty = digest != self._form_state_baselines[key]
        result = self._capture_state("track-form-dirty-state")
        result.update({"form": form, "form_dirty_operation": operation, "form_dirty": dirty, "form_control_count": len(snapshot), "baseline_present": key in self._form_state_baselines, "mutation_executed": False})
        return result

    def inspect_tabs_contract_semantic(self, tablist=None, exact=True):
        """Audit one ARIA tablist and its controlled tabpanels."""
        self._ensure_started(); self._reset_diagnostics()
        lists = self.page.get_by_role("tablist", name=tablist, exact=exact) if tablist else self.page.get_by_role("tablist")
        visible = [lists.nth(i) for i in range(min(lists.count(), 50)) if lists.nth(i).is_visible()]
        if len(visible) != 1:
            return {"error": "tablist_not_unique", "matches": len(visible), "executed": False}
        audit = visible[0].evaluate("""root => {
          const shown = el => { const r=el.getBoundingClientRect(),s=getComputedStyle(el); return r.width>0&&r.height>0&&s.display!=='none'&&s.visibility!=='hidden'; };
          const tabs=Array.from(root.querySelectorAll('[role="tab"]')).slice(0,100).map(el=>{const id=el.getAttribute('aria-controls')||''; const panel=id?document.getElementById(id):null; return {label:String(el.getAttribute('aria-label')||el.innerText||'').trim().slice(0,160),selected:el.getAttribute('aria-selected')==='true',controls:id,panel_exists:Boolean(panel),panel_visible:Boolean(panel&&shown(panel))};});
          const selected=tabs.filter(x=>x.selected); const broken=tabs.filter(x=>!x.controls||!x.panel_exists);
          return {tab_count:tabs.length,selected_count:selected.length,tabs,broken_reference_count:broken.length,tabs_contract_passed:tabs.length>0&&selected.length===1&&selected[0].panel_visible&&broken.length===0,truncated:root.querySelectorAll('[role="tab"]').length>100};
        }""")
        result=self._capture_state("inspect-tabs-contract"); result.update({"tablist":tablist,"tabs_audit":audit,"mutation_executed":False}); return result

    def inspect_disclosure_contract_semantic(self, target, exact=True):
        """Audit aria-expanded/aria-controls consistency for one button."""
        self._ensure_started(); self._reset_diagnostics()
        buttons=self.page.get_by_role("button",name=target,exact=exact)
        visible=[buttons.nth(i) for i in range(min(buttons.count(),50)) if buttons.nth(i).is_visible()]
        if len(visible)!=1: return {"error":"disclosure_target_not_unique","matches":len(visible),"executed":False}
        audit=visible[0].evaluate("""el=>{const expanded=el.getAttribute('aria-expanded');const id=el.getAttribute('aria-controls')||'';const panel=id?document.getElementById(id):null;const shown=x=>{if(!x)return false;const r=x.getBoundingClientRect(),s=getComputedStyle(x);return r.width>0&&r.height>0&&s.display!=='none'&&s.visibility!=='hidden';};const panelVisible=shown(panel);return {expanded,controls:id,panel_exists:Boolean(panel),panel_visible:panelVisible,disclosure_contract_passed:(expanded==='true'||expanded==='false')&&Boolean(id)&&Boolean(panel)&&((expanded==='true')===panelVisible)};}""")
        result=self._capture_state("inspect-disclosure-contract"); result.update({"disclosure_target":target,"disclosure_audit":audit,"mutation_executed":False}); return result

    def inspect_dialog_focus_trap_semantic(self, dialog, cycles=1, exact=True):
        """Exercise Tab focus inside one dialog and verify it never escapes."""
        self._ensure_started(); self._reset_diagnostics()
        if not isinstance(cycles,int) or isinstance(cycles,bool) or not 1<=cycles<=5: return {"error":"focus_trap_cycles_invalid","executed":False}
        target,error=self._visible_dialog(dialog,exact)
        if error:return error
        focusables=target.locator('button:not([disabled]),a[href],input:not([disabled]),select:not([disabled]),textarea:not([disabled]),[tabindex]:not([tabindex="-1"])')
        usable=[focusables.nth(i) for i in range(min(focusables.count(),100)) if focusables.nth(i).is_visible()]
        if not usable:return {"error":"focus_trap_no_focusable_controls","executed":False}
        usable[0].focus(); escaped=False; samples=[]
        self._begin_action_execution()
        for _ in range(len(usable)*cycles+1):
            self.page.keyboard.press("Tab")
            state=target.evaluate("root=>({inside:root.contains(document.activeElement),role:document.activeElement&&document.activeElement.getAttribute('role')||'',tag:document.activeElement&&document.activeElement.tagName.toLowerCase()||''})")
            samples.append(state); escaped=escaped or not state["inside"]
        result=self._capture_state("inspect-dialog-focus-trap"); result.update({"dialog_name":dialog,"focusable_count":len(usable),"focus_samples":samples[:30],"focus_escaped":escaped,"focus_trap_passed":not escaped,"interaction_executed":True}); return self._finish_action_execution(result)

    def inspect_heading_structure_semantic(self):
        """Audit the visible heading outline without changing the page."""
        self._ensure_started(); self._reset_diagnostics()
        audit=self.page.evaluate("""()=>{const shown=e=>{const r=e.getBoundingClientRect(),s=getComputedStyle(e);return r.width>0&&r.height>0&&s.display!=='none'&&s.visibility!=='hidden';};const all=Array.from(document.querySelectorAll('h1,h2,h3,h4,h5,h6,[role="heading"]')).filter(shown);const headings=all.slice(0,200).map(e=>({level:e.matches('h1,h2,h3,h4,h5,h6')?Number(e.tagName[1]):Number(e.getAttribute('aria-level')||0),name:String(e.getAttribute('aria-label')||e.innerText||'').trim().replace(/\s+/g,' ').slice(0,200)}));const skips=[];for(let i=1;i<headings.length;i++){if(headings[i].level>headings[i-1].level+1)skips.push({from:headings[i-1].level,to:headings[i].level,index:i});}const empty=headings.filter(x=>!x.name||x.level<1||x.level>6).length;const h1=headings.filter(x=>x.level===1).length;return {heading_count:headings.length,h1_count:h1,empty_or_invalid_count:empty,skipped_level_count:skips.length,skipped_levels:skips.slice(0,30),headings,heading_structure_passed:empty===0&&skips.length===0&&h1<=1,truncated:all.length>200};}""")
        result=self._capture_state("inspect-heading-structure");result.update({"heading_audit":audit,"mutation_executed":False});return result

    def inspect_landmark_structure_semantic(self):
        """Audit visible document landmarks and repeated-label contracts."""
        self._ensure_started(); self._reset_diagnostics()
        audit=self.page.evaluate("""()=>{const shown=e=>{const r=e.getBoundingClientRect(),s=getComputedStyle(e);return r.width>0&&r.height>0&&s.display!=='none'&&s.visibility!=='hidden';};const role=e=>e.getAttribute('role')||({MAIN:'main',NAV:'navigation',HEADER:'banner',FOOTER:'contentinfo',ASIDE:'complementary'}[e.tagName]||'');const all=Array.from(document.querySelectorAll('main,nav,header,footer,aside,[role="main"],[role="navigation"],[role="banner"],[role="contentinfo"],[role="complementary"],[role="region"]')).filter(shown);const items=all.slice(0,100).map(e=>({role:role(e),label:String(e.getAttribute('aria-label')||'').trim().slice(0,160)}));const counts={};items.forEach(x=>counts[x.role]=(counts[x.role]||0)+1);const unlabeledRepeated=items.filter(x=>(counts[x.role]||0)>1&&!x.label).length;const keys=items.filter(x=>x.label).map(x=>`${x.role}|${x.label.toLocaleLowerCase()}`);const duplicateLabels=keys.length-new Set(keys).size;const singletonOverflow=['main','banner','contentinfo'].reduce((n,r)=>n+Math.max(0,(counts[r]||0)-1),0);return {landmark_count:items.length,landmarks:items,role_counts:counts,unlabeled_repeated_count:unlabeledRepeated,duplicate_label_count:duplicateLabels,singleton_overflow_count:singletonOverflow,landmark_structure_passed:(counts.main||0)===1&&unlabeledRepeated===0&&duplicateLabels===0&&singletonOverflow===0,truncated:all.length>100};}""")
        result=self._capture_state("inspect-landmark-structure");result.update({"landmark_audit":audit,"mutation_executed":False});return result

    def inspect_link_contracts_semantic(self):
        """Audit visible links, names, schemes and new-tab rel protection."""
        self._ensure_started(); self._reset_diagnostics()
        audit=self.page.evaluate("""()=>{const shown=e=>{const r=e.getBoundingClientRect(),s=getComputedStyle(e);return r.width>0&&r.height>0&&s.display!=='none'&&s.visibility!=='hidden';};const all=Array.from(document.querySelectorAll('a[href],[role="link"]')).filter(shown);return all.slice(0,200).map(e=>{const href=e.href||e.getAttribute('href')||'';const name=String(e.getAttribute('aria-label')||e.innerText||e.getAttribute('title')||'').trim().replace(/\s+/g,' ').slice(0,160);const target=e.getAttribute('target')||'';const rel=(e.getAttribute('rel')||'').toLowerCase().split(/\s+/).filter(Boolean);let scheme='';try{scheme=new URL(href,document.baseURI).protocol.replace(':','');}catch(_){scheme='invalid';}return {name,href,target,scheme,missing_name:!name,unsafe_scheme:!['http','https','mailto','tel'].includes(scheme),new_tab_unprotected:target==='_blank'&&!rel.includes('noopener')&&!rel.includes('noreferrer')};});}""")
        for item in audit:
            item["href"] = self._safe_network_url(item.get("href", ""))
        failures=sum(1 for x in audit if x["missing_name"] or x["unsafe_scheme"] or x["new_tab_unprotected"])
        result=self._capture_state("inspect-link-contracts");result.update({"link_audit":{"link_count":len(audit),"links":audit,"failure_count":failures,"link_contracts_passed":failures==0,"truncated":len(audit)>=200},"mutation_executed":False});return result

    def inspect_combobox_contract_semantic(self, target, exact=True):
        """Audit one ARIA combobox and its controlled popup."""
        self._ensure_started(); self._reset_diagnostics()
        loc=self.page.get_by_role("combobox",name=target,exact=exact); visible=[loc.nth(i) for i in range(min(loc.count(),50)) if loc.nth(i).is_visible()]
        if len(visible)!=1:return {"error":"combobox_not_unique","matches":len(visible),"executed":False}
        audit=visible[0].evaluate("""el=>{const shown=x=>{if(!x)return false;const r=x.getBoundingClientRect(),s=getComputedStyle(x);return r.width>0&&r.height>0&&s.display!=='none'&&s.visibility!=='hidden';};const expanded=el.getAttribute('aria-expanded');const id=el.getAttribute('aria-controls')||'';const popup=id?document.getElementById(id):null;const activeId=el.getAttribute('aria-activedescendant')||'';const active=activeId?document.getElementById(activeId):null;const popupRole=popup&&popup.getAttribute('role')||'';return {expanded,controls:id,autocomplete:el.getAttribute('aria-autocomplete')||'',popup_exists:Boolean(popup),popup_role:popupRole,popup_visible:shown(popup),active_descendant:activeId,active_descendant_exists:Boolean(active),combobox_contract_passed:(expanded==='true'||expanded==='false')&&Boolean(id)&&Boolean(popup)&&['listbox','grid','tree','dialog'].includes(popupRole)&&((expanded==='true')===shown(popup))&&(!activeId||Boolean(active))};}""")
        result=self._capture_state("inspect-combobox-contract");result.update({"combobox_target":target,"combobox_audit":audit,"mutation_executed":False});return result

    def inspect_listbox_contract_semantic(self, target, exact=True):
        """Audit one visible ARIA listbox and option selection rules."""
        self._ensure_started(); self._reset_diagnostics()
        loc=self.page.get_by_role("listbox",name=target,exact=exact); visible=[loc.nth(i) for i in range(min(loc.count(),50)) if loc.nth(i).is_visible()]
        if len(visible)!=1:return {"error":"listbox_not_unique","matches":len(visible),"executed":False}
        audit=visible[0].evaluate("""root=>{const all=Array.from(root.querySelectorAll('[role="option"],option'));const options=all.slice(0,200).map(e=>({name:String(e.getAttribute('aria-label')||e.innerText||e.textContent||'').trim().replace(/\s+/g,' ').slice(0,160),selected:e.getAttribute('aria-selected')==='true'||e.selected===true,disabled:e.getAttribute('aria-disabled')==='true'||e.disabled===true}));const multi=root.getAttribute('aria-multiselectable')==='true'||root.multiple===true;const selected=options.filter(x=>x.selected).length;const empty=options.filter(x=>!x.name).length;return {option_count:options.length,selected_count:selected,disabled_count:options.filter(x=>x.disabled).length,multiselectable:multi,empty_name_count:empty,options,listbox_contract_passed:options.length>0&&empty===0&&(multi||selected<=1),truncated:all.length>200};}""")
        result=self._capture_state("inspect-listbox-contract");result.update({"listbox_target":target,"listbox_audit":audit,"mutation_executed":False});return result

    def inspect_menu_contract_semantic(self, target, exact=True):
        """Audit one visible ARIA menu and named menuitems."""
        self._ensure_started(); self._reset_diagnostics()
        loc=self.page.get_by_role("menu",name=target,exact=exact); visible=[loc.nth(i) for i in range(min(loc.count(),50)) if loc.nth(i).is_visible()]
        if len(visible)!=1:return {"error":"menu_not_unique","matches":len(visible),"executed":False}
        audit=visible[0].evaluate("""root=>{const all=Array.from(root.querySelectorAll('[role="menuitem"],[role="menuitemcheckbox"],[role="menuitemradio"]'));const items=all.slice(0,200).map(e=>({role:e.getAttribute('role')||'',name:String(e.getAttribute('aria-label')||e.innerText||'').trim().replace(/\s+/g,' ').slice(0,160),disabled:e.getAttribute('aria-disabled')==='true',has_popup:e.getAttribute('aria-haspopup')||''}));const empty=items.filter(x=>!x.name).length;return {item_count:items.length,empty_name_count:empty,disabled_count:items.filter(x=>x.disabled).length,items,menu_contract_passed:items.length>0&&empty===0,truncated:all.length>200};}""")
        result=self._capture_state("inspect-menu-contract");result.update({"menu_target":target,"menu_audit":audit,"mutation_executed":False});return result

    def _inspect_numeric_role_contract(self, role, target, exact=True):
        self._ensure_started(); self._reset_diagnostics()
        loc=self.page.get_by_role(role,name=target,exact=exact); visible=[loc.nth(i) for i in range(min(loc.count(),50)) if loc.nth(i).is_visible()]
        if len(visible)!=1:return {"error":f"{role}_not_unique","matches":len(visible),"executed":False}
        audit=visible[0].evaluate("""(el,role)=>{const number=a=>{const raw=el.getAttribute(a);return raw===null?null:Number(raw);};const min=number('aria-valuemin'),max=number('aria-valuemax'),now=number('aria-valuenow');const name=String(el.getAttribute('aria-label')||el.getAttribute('title')||'').trim().slice(0,160);const finite=x=>x===null||Number.isFinite(x);const ordered=min===null||max===null||min<=max;const bounded=now===null||((min===null||now>=min)&&(max===null||now<=max));const nowRequired=role==='meter'||role==='spinbutton';return {name,value_min:min,value_max:max,value_now:now,value_text:String(el.getAttribute('aria-valuetext')||'').trim().slice(0,160),numeric_values_valid:finite(min)&&finite(max)&&finite(now),range_ordered:ordered,value_in_range:bounded,indeterminate:now===null,numeric_contract_passed:Boolean(name)&&finite(min)&&finite(max)&&finite(now)&&ordered&&bounded&&(!nowRequired||now!==null)};}""",role)
        result=self._capture_state(f"inspect-{role}-contract");result.update({f"{role}_target":target,f"{role}_audit":audit,"mutation_executed":False});return result

    def inspect_progressbar_contract_semantic(self, target, exact=True):
        return self._inspect_numeric_role_contract("progressbar",target,exact)

    def inspect_meter_contract_semantic(self, target, exact=True):
        return self._inspect_numeric_role_contract("meter",target,exact)

    def inspect_spinbutton_contract_semantic(self, target, exact=True):
        return self._inspect_numeric_role_contract("spinbutton",target,exact)

    def inspect_text_contrast_semantic(self):
        """Audit WCAG contrast for visible direct text on solid backgrounds."""
        self._ensure_started(); self._reset_diagnostics()
        audit=self.page.evaluate("""()=>{const rgb=v=>{const m=String(v).match(/rgba?\((\d+)[, ]+(\d+)[, ]+(\d+)(?:[, /]+([\d.]+))?\)/);return m?[+m[1],+m[2],+m[3],m[4]===undefined?1:+m[4]]:null;};const lum=c=>{const f=x=>{x/=255;return x<=.04045?x/12.92:Math.pow((x+.055)/1.055,2.4);};return .2126*f(c[0])+.7152*f(c[1])+.0722*f(c[2]);};const shown=e=>{const r=e.getBoundingClientRect(),s=getComputedStyle(e);return r.width>0&&r.height>0&&s.display!=='none'&&s.visibility!=='hidden'&&+s.opacity>0;};const nodes=Array.from(document.querySelectorAll('body *')).filter(e=>shown(e)&&Array.from(e.childNodes).some(n=>n.nodeType===3&&n.textContent.trim()));const rows=[];let unsupported=0;for(const e of nodes.slice(0,400)){const s=getComputedStyle(e),fg=rgb(s.color);let p=e,bg=null;while(p&&!bg){const ps=getComputedStyle(p);if(ps.backgroundImage!=='none'){unsupported++;break;}const c=rgb(ps.backgroundColor);if(c&&c[3]>0)bg=c;p=p.parentElement;}if(!fg||!bg||fg[3]<1)continue;const ratio=(Math.max(lum(fg),lum(bg))+.05)/(Math.min(lum(fg),lum(bg))+.05);const size=parseFloat(s.fontSize)||0,weight=parseInt(s.fontWeight)||400,large=size>=24||(size>=18.66&&weight>=700),threshold=large?3:4.5;rows.push({text:String(e.innerText||e.textContent||'').trim().replace(/\s+/g,' ').slice(0,120),ratio:Math.round(ratio*100)/100,threshold,passed:ratio>=threshold});}const failed=rows.filter(x=>!x.passed);return {checked_count:rows.length,failure_count:failed.length,unsupported_background_count:unsupported,failures:failed.slice(0,100),contrast_passed:failed.length===0,truncated:nodes.length>400||failed.length>100};}""")
        result=self._capture_state("inspect-text-contrast");result.update({"text_contrast_audit":audit,"mutation_executed":False});return result

    def inspect_text_clipping_semantic(self):
        """Find visible direct text clipped by overflow constraints."""
        self._ensure_started(); self._reset_diagnostics()
        audit=self.page.evaluate("""()=>{const shown=e=>{const r=e.getBoundingClientRect(),s=getComputedStyle(e);return r.width>0&&r.height>0&&s.display!=='none'&&s.visibility!=='hidden';};const all=Array.from(document.querySelectorAll('body *')).filter(e=>shown(e)&&Array.from(e.childNodes).some(n=>n.nodeType===3&&n.textContent.trim()));const clipped=[];for(const e of all.slice(0,500)){const s=getComputedStyle(e);const x=(e.scrollWidth>e.clientWidth+1)&&['hidden','clip'].includes(s.overflowX);const y=(e.scrollHeight>e.clientHeight+1)&&['hidden','clip'].includes(s.overflowY);if(x||y)clipped.push({text:String(e.innerText||e.textContent||'').trim().replace(/\s+/g,' ').slice(0,120),horizontal:x,vertical:y,client_width:e.clientWidth,scroll_width:e.scrollWidth,client_height:e.clientHeight,scroll_height:e.scrollHeight});}return {checked_count:Math.min(all.length,500),clipped_count:clipped.length,clipped:clipped.slice(0,100),text_clipping_passed:clipped.length===0,truncated:all.length>500||clipped.length>100};}""")
        result=self._capture_state("inspect-text-clipping");result.update({"text_clipping_audit":audit,"mutation_executed":False});return result

    def inspect_target_size_semantic(self, minimum_px=24):
        """Audit visible non-inline interactive targets against a minimum size."""
        self._ensure_started(); self._reset_diagnostics()
        if not isinstance(minimum_px,int) or isinstance(minimum_px,bool) or not 16<=minimum_px<=44:return {"error":"target_size_minimum_invalid","executed":False}
        audit=self.page.evaluate("""minimum=>{const shown=e=>{const r=e.getBoundingClientRect(),s=getComputedStyle(e);return r.width>0&&r.height>0&&s.display!=='none'&&s.visibility!=='hidden';};const selector='button,input:not([type="hidden"]),select,textarea,[role="button"],[role="checkbox"],[role="radio"],[role="switch"],[role="tab"],[role="menuitem"]';const all=Array.from(document.querySelectorAll(selector)).filter(shown);const rows=all.slice(0,300).map(e=>{const r=e.getBoundingClientRect();const name=String(e.getAttribute('aria-label')||e.innerText||e.getAttribute('name')||e.id||'').trim().replace(/\s+/g,' ').slice(0,120);return {name,role:e.getAttribute('role')||e.tagName.toLowerCase(),width:Math.round(r.width*10)/10,height:Math.round(r.height*10)/10,too_small:r.width<minimum||r.height<minimum};});const failed=rows.filter(x=>x.too_small);return {minimum_px:minimum,checked_count:rows.length,too_small_count:failed.length,too_small:failed.slice(0,100),target_size_passed:failed.length===0,truncated:all.length>300||failed.length>100};}""",minimum_px)
        result=self._capture_state("inspect-target-size");result.update({"target_size_audit":audit,"mutation_executed":False});return result

    def inspect_live_region_contract_semantic(self):
        self._ensure_started();self._reset_diagnostics();audit=self.page.evaluate("""()=>{const all=Array.from(document.querySelectorAll('[aria-live],[role="alert"],[role="status"],[role="log"]'));const rows=all.slice(0,100).map(e=>{const role=e.getAttribute('role')||'';const live=e.getAttribute('aria-live')||({alert:'assertive',status:'polite',log:'polite'}[role]||'');return {role,live,atomic:e.getAttribute('aria-atomic')||'',label:String(e.getAttribute('aria-label')||'').trim().slice(0,120),valid:['off','polite','assertive'].includes(live)};});return {region_count:rows.length,invalid_count:rows.filter(x=>!x.valid).length,regions:rows,live_region_contract_passed:rows.every(x=>x.valid),truncated:all.length>100};}""");r=self._capture_state("inspect-live-regions");r.update({"live_region_audit":audit,"mutation_executed":False});return r

    def inspect_dialog_contract_semantic(self):
        self._ensure_started();self._reset_diagnostics();audit=self.page.evaluate("""()=>{const all=Array.from(document.querySelectorAll('[role="dialog"],[role="alertdialog"]'));const rows=all.slice(0,100).map(e=>{const label=String(e.getAttribute('aria-label')||'').trim();const labelled=e.getAttribute('aria-labelledby')||'';const labelNode=labelled?document.getElementById(labelled):null;return {role:e.getAttribute('role'),modal:e.getAttribute('aria-modal')||'',has_name:Boolean(label||labelNode),broken_label_reference:Boolean(labelled&&!labelNode)};});return {dialog_count:rows.length,dialogs:rows,failure_count:rows.filter(x=>!x.has_name||x.broken_label_reference).length,dialog_contract_passed:rows.every(x=>x.has_name&&!x.broken_label_reference),truncated:all.length>100};}""");r=self._capture_state("inspect-dialog-contracts");r.update({"dialog_contract_audit":audit,"mutation_executed":False});return r

    def inspect_field_label_contract_semantic(self, form=None, exact=True):
        self._ensure_started();self._reset_diagnostics();root=self.page.locator('body')
        if form:
            forms=self.page.locator('form');m=[forms.nth(i) for i in range(min(forms.count(),50)) if forms.nth(i).is_visible() and form in [str(forms.nth(i).get_attribute(a) or '').strip() for a in ('aria-label','name','id')]]
            if len(m)!=1:return {"error":"field_label_form_not_unique","matches":len(m),"executed":False}
            root=m[0]
        audit=root.evaluate("""root=>{const all=Array.from(root.querySelectorAll('input:not([type="hidden"]),select,textarea'));const rows=all.slice(0,200).map(e=>{const label=String((e.labels&&e.labels[0]&&e.labels[0].innerText)||e.getAttribute('aria-label')||'').trim().slice(0,160);const ids=(e.getAttribute('aria-describedby')||'').split(/\s+/).filter(Boolean);return {label,has_label:Boolean(label),description_ids:ids.slice(0,20),broken_description_count:ids.filter(id=>!document.getElementById(id)).length};});return {field_count:rows.length,unlabeled_count:rows.filter(x=>!x.has_label).length,broken_description_count:rows.reduce((n,x)=>n+x.broken_description_count,0),fields:rows,field_label_contract_passed:rows.every(x=>x.has_label&&x.broken_description_count===0),truncated:all.length>200};}""");r=self._capture_state("inspect-field-label-contract");r.update({"field_label_form":form,"field_label_audit":audit,"mutation_executed":False});return r

    def inspect_document_metadata_semantic(self):
        """Audit title, document language and responsive viewport metadata."""
        self._ensure_started(); self._reset_diagnostics()
        audit=self.page.evaluate("""()=>{const title=String(document.title||'').trim();const lang=String(document.documentElement.lang||'').trim();const viewports=Array.from(document.querySelectorAll('meta[name="viewport" i]')).map(x=>x.content||'');const langValid=/^[A-Za-z]{2,3}(?:-[A-Za-z0-9]{2,8})*$/.test(lang);const viewport=viewports[0]||'';const normalized=viewport.toLocaleLowerCase().replaceAll(' ','');const responsive=normalized.split(',').includes('width=device-width')||normalized.startsWith('width=device-width,');return {title,title_present:Boolean(title),language:lang,language_valid:langValid,viewport_count:viewports.length,viewport,viewport_has_width_device:responsive,document_metadata_passed:Boolean(title)&&langValid&&viewports.length===1&&responsive};}""")
        result=self._capture_state("inspect-document-metadata");result.update({"document_metadata_audit":audit,"mutation_executed":False});return result

    def inspect_keyboard_shortcuts_semantic(self):
        """Audit named accesskey/aria-keyshortcuts declarations and duplicates."""
        self._ensure_started(); self._reset_diagnostics()
        audit=self.page.evaluate("""()=>{const all=Array.from(document.querySelectorAll('[accesskey],[aria-keyshortcuts]'));const rows=all.slice(0,200).map(e=>{const name=String(e.getAttribute('aria-label')||e.innerText||e.getAttribute('title')||'').trim().replace(/\s+/g,' ').slice(0,160);const accesskey=String(e.getAttribute('accesskey')||'').trim().toLocaleLowerCase();const aria=String(e.getAttribute('aria-keyshortcuts')||'').trim().replace(/\s+/g,' ');return {name,accesskey,aria_keyshortcuts:aria,has_name:Boolean(name),valid_accesskey:!accesskey||Array.from(accesskey).length===1};});const keys=[];rows.forEach(x=>{if(x.accesskey)keys.push(`access:${x.accesskey}`);if(x.aria_keyshortcuts)x.aria_keyshortcuts.toLocaleLowerCase().split(' ').forEach(k=>keys.push(`aria:${k}`));});const duplicateKeys=[...new Set(keys.filter((x,i)=>keys.indexOf(x)!==i))];const invalid=rows.filter(x=>!x.has_name||!x.valid_accesskey).length;return {shortcut_count:rows.length,shortcuts:rows,duplicate_shortcuts:duplicateKeys,duplicate_count:duplicateKeys.length,invalid_count:invalid,keyboard_shortcuts_passed:duplicateKeys.length===0&&invalid===0,truncated:all.length>200};}""")
        result=self._capture_state("inspect-keyboard-shortcuts");result.update({"keyboard_shortcut_audit":audit,"mutation_executed":False});return result

    def inspect_autofill_contract_semantic(self, form=None, exact=True):
        """Audit autocomplete declarations without returning field values."""
        self._ensure_started(); self._reset_diagnostics(); root=self.page.locator("body")
        if form:
            forms=self.page.locator("form"); expected=form if exact else str(form).casefold(); matches=[]
            for i in range(min(forms.count(),50)):
                item=forms.nth(i); names=[str(item.get_attribute(a) or "").strip() for a in ("aria-label","name","id")]; matched=expected in names if exact else any(expected in x.casefold() for x in names if x)
                if matched and item.is_visible(): matches.append(item)
            if len(matches)!=1:return {"error":"autofill_form_not_unique","matches":len(matches),"executed":False}
            root=matches[0]
        audit=root.evaluate("""root=>{const known=new Set(['on','off','name','honorific-prefix','given-name','additional-name','family-name','honorific-suffix','nickname','username','new-password','current-password','one-time-code','organization-title','organization','street-address','address-line1','address-line2','address-line3','address-level4','address-level3','address-level2','address-level1','country','country-name','postal-code','cc-name','cc-given-name','cc-additional-name','cc-family-name','cc-number','cc-exp','cc-exp-month','cc-exp-year','cc-csc','cc-type','transaction-currency','transaction-amount','language','bday','bday-day','bday-month','bday-year','sex','url','photo','tel','tel-country-code','tel-national','tel-area-code','tel-local','tel-local-prefix','tel-local-suffix','tel-extension','email','impp']);const all=Array.from(root.querySelectorAll('input:not([type="hidden"]),textarea,select'));const rows=all.slice(0,200).map(e=>{const raw=String(e.getAttribute('autocomplete')||'').trim().toLocaleLowerCase();const tokens=raw.split(/\s+/).filter(Boolean);const purpose=tokens[tokens.length-1]||'';const type=String(e.getAttribute('type')||e.tagName).toLocaleLowerCase();const label=String((e.labels&&e.labels[0]&&e.labels[0].innerText)||e.getAttribute('aria-label')||e.name||e.id||'').trim().slice(0,160);return {label,type,autocomplete:raw,autocomplete_valid:!raw||known.has(purpose),password_purpose_present:type!=='password'||['current-password','new-password'].includes(purpose)};});return {field_count:rows.length,invalid_autocomplete_count:rows.filter(x=>!x.autocomplete_valid).length,password_missing_purpose_count:rows.filter(x=>!x.password_purpose_present).length,fields:rows,autofill_contract_passed:rows.every(x=>x.autocomplete_valid&&x.password_purpose_present),truncated:all.length>200};}""")
        result=self._capture_state("inspect-autofill-contract");result.update({"autofill_form":form,"autofill_audit":audit,"mutation_executed":False});return result

    def inspect_form_submission_contract_semantic(self):
        """Audit form destinations and methods without reading values."""
        self._ensure_started(); self._reset_diagnostics()
        rows=self.page.evaluate("""()=>Array.from(document.forms).slice(0,100).map(f=>{const action=f.action||document.URL;const method=String(f.method||'get').toLowerCase();const password=Boolean(f.querySelector('input[type="password"]'));let protocol='';try{protocol=new URL(action,document.baseURI).protocol.replace(':','');}catch(_){protocol='invalid';}const base=new URL(document.baseURI);const resolved=new URL(action,document.baseURI);return {name:String(f.getAttribute('aria-label')||f.name||f.id||'').trim().slice(0,160),action:resolved.href,method,password_present:password,target:f.target||'',protocol,mixed_content:base.protocol==='https:'&&resolved.protocol==='http:',password_uses_get:password&&method==='get'};})""")
        for item in rows:item["action"]=self._safe_network_url(item["action"])
        failures=sum(1 for x in rows if x["protocol"] not in {"http","https"} or x["mixed_content"] or x["password_uses_get"])
        result=self._capture_state("inspect-form-submission-contract");result.update({"form_submission_audit":{"form_count":len(rows),"forms":rows,"failure_count":failures,"form_submission_contract_passed":failures==0,"truncated":len(rows)>=100},"mutation_executed":False});return result

    def inspect_script_security_semantic(self):
        """Audit external scripts for mixed content and cross-origin integrity."""
        self._ensure_started(); self._reset_diagnostics()
        rows=self.page.evaluate("""()=>{const base=new URL(document.baseURI);return Array.from(document.scripts).slice(0,200).map(s=>{if(!s.src)return {external:false,type:s.type||'',async:s.async,defer:s.defer};const u=new URL(s.src,document.baseURI);const cross=u.origin!==base.origin;return {external:true,src:u.href,type:s.type||'',async:s.async,defer:s.defer,cross_origin:cross,mixed_content:base.protocol==='https:'&&u.protocol==='http:',integrity_present:Boolean(s.integrity),crossorigin:s.crossOrigin||'',cross_origin_without_integrity:cross&&!s.integrity};});}""")
        for item in rows:
            if item.get("src"):item["src"]=self._safe_network_url(item["src"])
        failures=sum(1 for x in rows if x.get("mixed_content") or x.get("cross_origin_without_integrity"))
        result=self._capture_state("inspect-script-security");result.update({"script_security_audit":{"script_count":len(rows),"external_count":sum(1 for x in rows if x["external"]),"scripts":rows,"failure_count":failures,"script_security_passed":failures==0,"truncated":len(rows)>=200},"mutation_executed":False});return result

    def inspect_media_resource_semantic(self):
        """Audit visible image/media sources without downloading content."""
        self._ensure_started(); self._reset_diagnostics()
        rows=self.page.evaluate("""()=>{const base=new URL(document.baseURI);const all=Array.from(document.querySelectorAll('img,video,audio')).slice(0,200);return all.map(e=>{const raw=e.currentSrc||e.src||'';let u=null;try{u=new URL(raw,document.baseURI);}catch(_){}const tag=e.tagName.toLowerCase();return {tag,source:u?u.href:'',mixed_content:Boolean(u&&base.protocol==='https:'&&u.protocol==='http:'),image_broken:tag==='img'&&e.complete&&e.naturalWidth===0,autoplay_unmuted:(tag==='video'||tag==='audio')&&e.autoplay&&!e.muted,has_controls:(tag==='video'||tag==='audio')?e.controls:null};});}""")
        for item in rows:
            if item.get("source"):item["source"]=self._safe_network_url(item["source"])
        failures=sum(1 for x in rows if x["mixed_content"] or x["image_broken"] or x["autoplay_unmuted"])
        result=self._capture_state("inspect-media-resource");result.update({"media_resource_audit":{"resource_count":len(rows),"resources":rows,"failure_count":failures,"media_resource_passed":failures==0,"truncated":len(rows)>=200},"mutation_executed":False});return result

    def inspect_lazy_media_contract_semantic(self):
        """Audit offscreen images/iframes for lazy loading and stable dimensions."""
        self._ensure_started(); self._reset_diagnostics()
        audit=self.page.evaluate("""()=>{const all=Array.from(document.querySelectorAll('img,iframe'));const rows=all.slice(0,200).map(e=>{const r=e.getBoundingClientRect();const offscreen=r.top>innerHeight;const loading=String(e.getAttribute('loading')||'').toLowerCase();const stable=Boolean((e.getAttribute('width')&&e.getAttribute('height'))||getComputedStyle(e).aspectRatio!=='auto');return {tag:e.tagName.toLowerCase(),label:String(e.getAttribute('alt')||e.getAttribute('title')||e.getAttribute('aria-label')||'').trim().slice(0,120),offscreen,loading,stable_dimensions:stable,lazy_missing:offscreen&&loading!=='lazy',dimensions_missing:!stable};});const failures=rows.filter(x=>x.lazy_missing||x.dimensions_missing);return {resource_count:rows.length,failure_count:failures.length,failures:failures.slice(0,100),lazy_media_contract_passed:failures.length===0,truncated:all.length>200||failures.length>100};}""")
        result=self._capture_state("inspect-lazy-media-contract");result.update({"lazy_media_audit":audit,"mutation_executed":False});return result

    def inspect_font_readiness_semantic(self, wait_ms=2000):
        """Wait for the CSS Font Loading API without exposing font files."""
        self._ensure_started(); self._reset_diagnostics()
        if not isinstance(wait_ms,int) or isinstance(wait_ms,bool) or not 0<=wait_ms<=10000:return {"error":"font_wait_ms_invalid","executed":False}
        audit=self.page.evaluate("""async wait=>{if(!document.fonts)return {supported:false,status:'unsupported',font_readiness_passed:false};let timedOut=false;await Promise.race([document.fonts.ready,new Promise(r=>setTimeout(()=>{timedOut=true;r();},wait))]);const family=getComputedStyle(document.body).fontFamily.slice(0,300);return {supported:true,status:document.fonts.status,timed_out:timedOut,body_font_family:family,font_readiness_passed:!timedOut&&document.fonts.status==='loaded'};}""",wait_ms)
        result=self._capture_state("inspect-font-readiness");result.update({"font_readiness_audit":audit,"mutation_executed":False});return result

    def inspect_reduced_motion_contract_semantic(self):
        """Audit long CSS motion and presence of prefers-reduced-motion rules."""
        self._ensure_started(); self._reset_diagnostics()
        audit=self.page.evaluate("""()=>{const seconds=v=>String(v).split(',').reduce((m,x)=>{x=x.trim();const n=parseFloat(x)||0;return Math.max(m,x.endsWith('ms')?n/1000:n);},0);const all=Array.from(document.querySelectorAll('body *'));const moving=all.slice(0,500).map(e=>{const s=getComputedStyle(e);return {label:String(e.getAttribute('aria-label')||e.innerText||e.id||'').trim().replace(/\s+/g,' ').slice(0,100),animation_seconds:seconds(s.animationDuration),transition_seconds:seconds(s.transitionDuration)};}).filter(x=>x.animation_seconds>.5||x.transition_seconds>.5);let reduced=false,inaccessible=0;for(const sheet of Array.from(document.styleSheets)){try{for(const rule of Array.from(sheet.cssRules||[])){if(String(rule.cssText||'').toLowerCase().includes('prefers-reduced-motion'))reduced=true;}}catch(_){inaccessible++;}}return {long_motion_count:moving.length,long_motion:moving.slice(0,100),reduced_motion_rule_present:reduced,inaccessible_stylesheet_count:inaccessible,reduced_motion_contract_passed:moving.length===0||reduced,truncated:all.length>500||moving.length>100};}""")
        result=self._capture_state("inspect-reduced-motion-contract");result.update({"reduced_motion_audit":audit,"mutation_executed":False});return result

    def inspect_details_contract_semantic(self):
        """Audit native details/summary structure and open visibility."""
        self._ensure_started(); self._reset_diagnostics()
        audit=self.page.evaluate("""()=>{const all=Array.from(document.querySelectorAll('details'));const rows=all.slice(0,100).map(e=>{const summary=e.querySelector(':scope > summary');const name=String(summary&&summary.innerText||'').trim().replace(/\s+/g,' ').slice(0,160);const contentVisible=e.open&&e.getBoundingClientRect().height>(summary?summary.getBoundingClientRect().height:0);return {open:e.open,summary_present:Boolean(summary),summary_name:name,content_visible_when_open:!e.open||contentVisible,valid:Boolean(summary&&name)&&(!e.open||contentVisible)};});return {details_count:rows.length,failure_count:rows.filter(x=>!x.valid).length,details:rows,details_contract_passed:rows.every(x=>x.valid),truncated:all.length>100};}""")
        result=self._capture_state("inspect-details-contract");result.update({"details_audit":audit,"mutation_executed":False});return result

    def inspect_popover_contract_semantic(self):
        """Audit HTML Popover API targets and invokers without toggling them."""
        self._ensure_started(); self._reset_diagnostics()
        audit=self.page.evaluate("""()=>{const pops=Array.from(document.querySelectorAll('[popover]')).slice(0,100).map(e=>({id:e.id||'',mode:e.getAttribute('popover')||'auto',has_id:Boolean(e.id)}));const inv=Array.from(document.querySelectorAll('[popovertarget]')).slice(0,200).map(e=>{const id=e.getAttribute('popovertarget')||'';const target=id?document.getElementById(id):null;const action=e.getAttribute('popovertargetaction')||'toggle';const name=String(e.getAttribute('aria-label')||e.innerText||'').trim().slice(0,160);return {name,target:id,target_exists:Boolean(target&&target.hasAttribute('popover')),action,valid:Boolean(name)&&Boolean(target&&target.hasAttribute('popover'))&&['show','hide','toggle'].includes(action)};});const ids=pops.map(x=>x.id).filter(Boolean);const dup=[...new Set(ids.filter((x,i)=>ids.indexOf(x)!==i))];const failures=pops.filter(x=>!x.has_id).length+inv.filter(x=>!x.valid).length+dup.length;return {popover_count:pops.length,invoker_count:inv.length,popovers:pops,invokers:inv,duplicate_ids:dup,failure_count:failures,popover_contract_passed:failures===0,truncated:document.querySelectorAll('[popover]').length>100||document.querySelectorAll('[popovertarget]').length>200};}""")
        result=self._capture_state("inspect-popover-contract");result.update({"popover_api_audit":audit,"mutation_executed":False});return result

    def inspect_native_dialog_element_semantic(self):
        """Audit native dialog names and open/rendered consistency."""
        self._ensure_started(); self._reset_diagnostics()
        audit=self.page.evaluate("""()=>{const all=Array.from(document.querySelectorAll('dialog'));const shown=e=>{const r=e.getBoundingClientRect(),s=getComputedStyle(e);return r.width>0&&r.height>0&&s.display!=='none'&&s.visibility!=='hidden';};const rows=all.slice(0,100).map(e=>{const labelled=e.getAttribute('aria-labelledby')||'';const node=labelled?document.getElementById(labelled):null;const name=String(e.getAttribute('aria-label')||(node&&node.innerText)||'').trim().replace(/\s+/g,' ').slice(0,160);const visible=shown(e);return {open:e.open,visible,name,broken_label_reference:Boolean(labelled&&!node),valid:Boolean(name)&&!Boolean(labelled&&!node)&&(e.open===visible)};});return {dialog_count:rows.length,failure_count:rows.filter(x=>!x.valid).length,dialogs:rows,native_dialog_contract_passed:rows.every(x=>x.valid),truncated:all.length>100};}""")
        result=self._capture_state("inspect-native-dialog-element");result.update({"native_dialog_element_audit":audit,"mutation_executed":False});return result

    def inspect_fieldset_contract_semantic(self):
        """Audit fieldset/legend grouping and disabled propagation metadata."""
        self._ensure_started(); self._reset_diagnostics()
        audit=self.page.evaluate("""()=>{const all=Array.from(document.querySelectorAll('fieldset'));const rows=all.slice(0,100).map(e=>{const legend=e.querySelector(':scope > legend');const name=String(legend&&legend.innerText||'').trim().replace(/\s+/g,' ').slice(0,160);const controls=e.querySelectorAll('input:not([type="hidden"]),select,textarea,button').length;return {legend_present:Boolean(legend),legend_name:name,control_count:controls,disabled:e.disabled,valid:Boolean(legend&&name)&&controls>0};});return {fieldset_count:rows.length,failure_count:rows.filter(x=>!x.valid).length,fieldsets:rows,fieldset_contract_passed:rows.every(x=>x.valid),truncated:all.length>100};}""")
        result=self._capture_state("inspect-fieldset-contract");result.update({"fieldset_audit":audit,"mutation_executed":False});return result

    def inspect_radio_group_contract_semantic(self):
        """Audit radio names, labels and one-selected-per-group behavior."""
        self._ensure_started(); self._reset_diagnostics()
        audit=self.page.evaluate("""()=>{const all=Array.from(document.querySelectorAll('input[type="radio"],[role="radio"]'));const rows=all.slice(0,200).map(e=>({group:String(e.name||e.closest('[role="radiogroup"]')?.getAttribute('aria-label')||'').trim().slice(0,160),label:String((e.labels&&e.labels[0]&&e.labels[0].innerText)||e.getAttribute('aria-label')||'').trim().slice(0,160),checked:e.checked===true||e.getAttribute('aria-checked')==='true',disabled:e.disabled===true||e.getAttribute('aria-disabled')==='true'}));const groups={};rows.forEach(x=>(groups[x.group]||(groups[x.group]=[])).push(x));const summary=Object.entries(groups).map(([name,items])=>({name,item_count:items.length,checked_count:items.filter(x=>x.checked).length,unlabeled_count:items.filter(x=>!x.label).length,valid:Boolean(name)&&items.filter(x=>x.checked).length<=1&&items.every(x=>Boolean(x.label))}));return {radio_count:rows.length,group_count:summary.length,groups:summary,failure_count:summary.filter(x=>!x.valid).length,radio_group_contract_passed:summary.every(x=>x.valid),truncated:all.length>200};}""")
        result=self._capture_state("inspect-radio-group-contract");result.update({"radio_group_audit":audit,"mutation_executed":False});return result

    def inspect_button_type_contract_semantic(self):
        """Audit form buttons for names and explicit accidental-submit protection."""
        self._ensure_started(); self._reset_diagnostics()
        audit=self.page.evaluate("""()=>{const all=Array.from(document.querySelectorAll('form button,form input[type="button"],form input[type="submit"],form input[type="reset"]'));const rows=all.slice(0,200).map(e=>{const tag=e.tagName.toLowerCase();const raw=e.getAttribute('type');const effective=String(e.type||'').toLowerCase();const name=String(e.getAttribute('aria-label')||e.innerText||e.value||'').trim().replace(/\s+/g,' ').slice(0,160);const implicitSubmit=tag==='button'&&raw===null;return {name,type:effective,explicit_type:raw!==null,implicit_submit:implicitSubmit,valid:Boolean(name)&&!implicitSubmit&&['button','submit','reset'].includes(effective)};});return {button_count:rows.length,implicit_submit_count:rows.filter(x=>x.implicit_submit).length,unnamed_count:rows.filter(x=>!x.name).length,buttons:rows,failure_count:rows.filter(x=>!x.valid).length,button_type_contract_passed:rows.every(x=>x.valid),truncated:all.length>200};}""")
        result=self._capture_state("inspect-button-type-contract");result.update({"button_type_audit":audit,"mutation_executed":False});return result

    def inspect_contenteditable_contract_semantic(self):
        """Audit editable regions for valid modes and stable accessible names."""
        self._ensure_started(); self._reset_diagnostics()
        audit=self.page.evaluate("""()=>{const all=Array.from(document.querySelectorAll('[contenteditable]'));const text=e=>String(e&&e.innerText||'').trim().replace(/\s+/g,' ').slice(0,160);const rows=all.slice(0,100).map(e=>{const raw=String(e.getAttribute('contenteditable')||'').toLowerCase();const labelled=e.getAttribute('aria-labelledby')||'';const ref=labelled?document.getElementById(labelled):null;const name=String(e.getAttribute('aria-label')||text(ref)||e.getAttribute('title')||'').trim().replace(/\s+/g,' ').slice(0,160);const mode=raw===''?'true':raw;const explicitRole=String(e.getAttribute('role')||'').toLowerCase();const validMode=['true','plaintext-only'].includes(mode);const roleCompatible=!explicitRole||['textbox','searchbox'].includes(explicitRole);return {name,mode,role:explicitRole||'implicit-textbox',multiline:e.getAttribute('aria-multiline'),broken_label_reference:Boolean(labelled&&!ref),valid:Boolean(name)&&validMode&&roleCompatible&&!Boolean(labelled&&!ref)};});return {editable_count:rows.length,unnamed_count:rows.filter(x=>!x.name).length,invalid_mode_count:rows.filter(x=>!['true','plaintext-only'].includes(x.mode)).length,regions:rows,failure_count:rows.filter(x=>!x.valid).length,contenteditable_contract_passed:rows.every(x=>x.valid),truncated:all.length>100};}""")
        result=self._capture_state("inspect-contenteditable-contract");result.update({"contenteditable_audit":audit,"mutation_executed":False});return result

    def inspect_search_contract_semantic(self):
        """Audit searchboxes and search landmarks without submitting a query."""
        self._ensure_started(); self._reset_diagnostics()
        audit=self.page.evaluate("""()=>{const text=e=>String(e&&e.innerText||'').trim().replace(/\s+/g,' ').slice(0,160);const name=e=>{const labelled=e.getAttribute('aria-labelledby')||'';const ref=labelled?document.getElementById(labelled):null;const label=e.labels&&e.labels[0];return {value:String(e.getAttribute('aria-label')||text(ref)||text(label)||e.getAttribute('placeholder')||'').trim().slice(0,160),broken:Boolean(labelled&&!ref)};};const all=Array.from(document.querySelectorAll('input[type="search"],[role="searchbox"]'));const boxes=all.slice(0,100).map(e=>{const n=name(e);const form=e.closest('form');const submit=Boolean(form&&form.querySelector('button[type="submit"],input[type="submit"],button:not([type])'));return {name:n.value,broken_label_reference:n.broken,inside_form:Boolean(form),submit_control_present:submit,live_filter:!form,valid:Boolean(n.value)&&!n.broken};});const landmarks=Array.from(document.querySelectorAll('[role="search"],search')).slice(0,50).map(e=>{const n=name(e);return {name:n.value,broken_label_reference:n.broken,valid:!n.broken};});const landmarkNamesRequired=landmarks.length>1;landmarks.forEach(x=>x.valid=x.valid&&(!landmarkNamesRequired||Boolean(x.name)));const failures=boxes.filter(x=>!x.valid).length+landmarks.filter(x=>!x.valid).length;return {searchbox_count:boxes.length,search_landmark_count:landmarks.length,searchboxes:boxes,landmarks,form_submit_count:boxes.filter(x=>x.inside_form&&x.submit_control_present).length,live_filter_count:boxes.filter(x=>x.live_filter).length,failure_count:failures,search_contract_passed:failures===0,truncated:all.length>100||document.querySelectorAll('[role="search"],search').length>50};}""")
        result=self._capture_state("inspect-search-contract");result.update({"search_audit":audit,"mutation_executed":False});return result

    def inspect_breadcrumb_contract_semantic(self):
        """Audit breadcrumb navigation names, links and current-page marker."""
        self._ensure_started(); self._reset_diagnostics()
        audit=self.page.evaluate("""()=>{const text=e=>String(e&&e.innerText||'').trim().replace(/\s+/g,' ').slice(0,160);const all=Array.from(document.querySelectorAll('nav,[role="navigation"]')).filter(e=>{const labelled=e.getAttribute('aria-labelledby')||'';const ref=labelled?document.getElementById(labelled):null;const name=String(e.getAttribute('aria-label')||text(ref)||'').toLowerCase();return name.includes('breadcrumb')||name.includes('хлебн');});const rows=all.slice(0,50).map(e=>{const labelled=e.getAttribute('aria-labelledby')||'';const ref=labelled?document.getElementById(labelled):null;const name=String(e.getAttribute('aria-label')||text(ref)||'').trim().slice(0,160);const links=Array.from(e.querySelectorAll('a')).map(a=>({name:String(a.getAttribute('aria-label')||text(a)).trim().slice(0,160),current:a.getAttribute('aria-current')||''}));const currentCount=e.querySelectorAll('[aria-current="page"]').length;return {name,link_count:links.length,current_page_count:currentCount,unnamed_link_count:links.filter(x=>!x.name).length,links:links.slice(0,50),valid:Boolean(name)&&links.length>0&&currentCount===1&&links.every(x=>Boolean(x.name))};});return {breadcrumb_count:rows.length,breadcrumbs:rows,failure_count:rows.filter(x=>!x.valid).length,breadcrumb_contract_passed:rows.every(x=>x.valid),truncated:all.length>50};}""")
        result=self._capture_state("inspect-breadcrumb-contract");result.update({"breadcrumb_audit":audit,"mutation_executed":False});return result

    def inspect_table_structure_contract_semantic(self):
        """Audit native data-table headers and row geometry."""
        self._ensure_started(); self._reset_diagnostics()
        audit=self.page.evaluate("""()=>{const text=e=>String(e&&e.innerText||'').trim().replace(/\s+/g,' ').slice(0,160);const all=Array.from(document.querySelectorAll('table')).filter(e=>!['presentation','none'].includes(String(e.getAttribute('role')||'').toLowerCase()));const rows=all.slice(0,50).map(t=>{const caption=t.querySelector(':scope > caption');const labelled=t.getAttribute('aria-labelledby')||'';const ref=labelled?document.getElementById(labelled):null;const name=String(t.getAttribute('aria-label')||text(ref)||text(caption)||'').trim().slice(0,160);const trs=Array.from(t.rows||[]);const widths=trs.map(r=>Array.from(r.cells||[]).reduce((n,c)=>n+(Number(c.colSpan)||1),0));const headerCount=t.querySelectorAll('th,[role="columnheader"],[role="rowheader"]').length;const dataCount=t.querySelectorAll('td,[role="cell"],[role="gridcell"]').length;const rectangular=widths.length<2||new Set(widths).size===1;const broken=Boolean(labelled&&!ref);return {name,row_count:trs.length,header_count:headerCount,data_cell_count:dataCount,column_counts:widths.slice(0,100),rectangular,broken_label_reference:broken,valid:trs.length>0&&headerCount>0&&rectangular&&!broken};});return {table_count:rows.length,named_table_count:rows.filter(x=>x.name).length,tables:rows,failure_count:rows.filter(x=>!x.valid).length,table_structure_contract_passed:rows.every(x=>x.valid),truncated:all.length>50};}""")
        result=self._capture_state("inspect-table-structure-contract");result.update({"table_structure_audit":audit,"mutation_executed":False});return result

    def inspect_list_structure_contract_semantic(self):
        """Audit native and ARIA list ownership without reading application data."""
        self._ensure_started(); self._reset_diagnostics()
        audit=self.page.evaluate("""()=>{const all=Array.from(document.querySelectorAll('ul,ol,[role="list"]'));const rows=all.slice(0,100).map(e=>{const native=['UL','OL'].includes(e.tagName);const children=Array.from(e.children);const items=children.filter(x=>native?x.tagName==='LI':x.getAttribute('role')==='listitem');const invalid=children.filter(x=>native?x.tagName!=='LI':x.getAttribute('role')!=='listitem');return {kind:native?e.tagName.toLowerCase():'aria-list',child_count:children.length,item_count:items.length,invalid_direct_child_count:invalid.length,valid:items.length>0&&invalid.length===0};});return {list_count:rows.length,lists:rows,failure_count:rows.filter(x=>!x.valid).length,list_structure_contract_passed:rows.every(x=>x.valid),truncated:all.length>100};}""")
        result=self._capture_state("inspect-list-structure-contract");result.update({"list_structure_audit":audit,"mutation_executed":False});return result

    def inspect_description_list_contract_semantic(self):
        """Audit definition-list term/description pairing."""
        self._ensure_started(); self._reset_diagnostics()
        audit=self.page.evaluate("""()=>{const text=e=>String(e&&e.innerText||'').trim().replace(/\s+/g,' ').slice(0,120);const all=Array.from(document.querySelectorAll('dl'));const rows=all.slice(0,100).map(e=>{const c=Array.from(e.children).filter(x=>['DT','DD'].includes(x.tagName));let terms=0,descriptions=0,orphan=0,empty=0,active=false,described=false;for(const x of c){if(!text(x))empty++;if(x.tagName==='DT'){if(active&&!described)orphan++;active=true;described=false;terms++;}else{descriptions++;if(!active)orphan++;else described=true;}}if(active&&!described)orphan++;return {term_count:terms,description_count:descriptions,orphan_count:orphan,empty_item_count:empty,valid:terms>0&&descriptions>0&&orphan===0&&empty===0};});return {description_list_count:rows.length,lists:rows,failure_count:rows.filter(x=>!x.valid).length,description_list_contract_passed:rows.every(x=>x.valid),truncated:all.length>100};}""")
        result=self._capture_state("inspect-description-list-contract");result.update({"description_list_audit":audit,"mutation_executed":False});return result

    def inspect_hash_link_contract_semantic(self):
        """Audit same-document links for names and existing targets."""
        self._ensure_started(); self._reset_diagnostics()
        audit=self.page.evaluate("""()=>{const all=Array.from(document.querySelectorAll('a[href^="#"]'));const rows=all.slice(0,200).map(e=>{const href=e.getAttribute('href')||'';let id='';try{id=decodeURIComponent(href.slice(1));}catch(_){id=href.slice(1);}const name=String(e.getAttribute('aria-label')||e.innerText||e.textContent||'').trim().replace(/\s+/g,' ').slice(0,160);const target=id?document.getElementById(id)||document.querySelector(`[name="${CSS.escape(id)}"]`):null;return {name,href,target_exists:Boolean(target),valid:Boolean(name)&&Boolean(id)&&Boolean(target)};});return {hash_link_count:rows.length,links:rows,failure_count:rows.filter(x=>!x.valid).length,hash_link_contract_passed:rows.every(x=>x.valid),truncated:all.length>200};}""")
        result=self._capture_state("inspect-hash-link-contract");result.update({"hash_link_audit":audit,"mutation_executed":False});return result

    def inspect_navigation_current_contract_semantic(self):
        """Audit navigation link names and aria-current tokens per landmark."""
        self._ensure_started(); self._reset_diagnostics()
        audit=self.page.evaluate("""()=>{const text=e=>String(e&&e.innerText||e&&e.textContent||'').trim().replace(/\s+/g,' ').slice(0,160);const allowed=['page','step','location','date','time','true'];const all=Array.from(document.querySelectorAll('nav,[role="navigation"]'));const rows=all.slice(0,100).map(e=>{const labelled=e.getAttribute('aria-labelledby')||'';const ref=labelled?document.getElementById(labelled):null;const name=String(e.getAttribute('aria-label')||text(ref)||'').trim().slice(0,160);const links=Array.from(e.querySelectorAll('a,[role="link"]'));const current=links.filter(x=>x.hasAttribute('aria-current'));const invalid=current.filter(x=>!allowed.includes(String(x.getAttribute('aria-current')||'').toLowerCase()));const unnamed=links.filter(x=>!String(x.getAttribute('aria-label')||text(x)).trim());return {name,link_count:links.length,current_count:current.length,invalid_current_count:invalid.length,unnamed_link_count:unnamed.length,broken_label_reference:Boolean(labelled&&!ref),valid:invalid.length===0&&current.length<=1&&unnamed.length===0&&!Boolean(labelled&&!ref)};});return {navigation_count:rows.length,named_navigation_count:rows.filter(x=>x.name).length,navigations:rows,failure_count:rows.filter(x=>!x.valid).length,navigation_current_contract_passed:rows.every(x=>x.valid),truncated:all.length>100};}""")
        result=self._capture_state("inspect-navigation-current-contract");result.update({"navigation_current_audit":audit,"mutation_executed":False});return result

    def inspect_skip_link_contract_semantic(self):
        """Audit early same-document links that bypass repeated navigation."""
        self._ensure_started(); self._reset_diagnostics()
        audit=self.page.evaluate("""()=>{const focusable=Array.from(document.querySelectorAll('a[href],button,input,select,textarea,[tabindex]:not([tabindex="-1"])')).slice(0,10);const rows=focusable.filter(e=>e.tagName==='A'&&String(e.getAttribute('href')||'').startsWith('#')).map(e=>{const href=e.getAttribute('href')||'';const id=href.slice(1);const target=id?document.getElementById(id):null;const name=String(e.getAttribute('aria-label')||e.innerText||e.textContent||'').trim().replace(/\s+/g,' ').slice(0,160);const bypasses=Boolean(target&&(target.tagName==='MAIN'||target.getAttribute('role')==='main'||target.querySelector('main,[role="main"]')));return {name,href,target_exists:Boolean(target),bypasses_to_main:bypasses,valid:Boolean(name)&&Boolean(target)&&bypasses};});return {skip_link_count:rows.length,skip_link_present:rows.length>0,links:rows,failure_count:rows.filter(x=>!x.valid).length,skip_link_contract_passed:rows.every(x=>x.valid)};}""")
        result=self._capture_state("inspect-skip-link-contract");result.update({"skip_link_audit":audit,"mutation_executed":False});return result

    def inspect_required_field_contract_semantic(self):
        """Audit explicit required fields for supported roles and accessible names."""
        self._ensure_started(); self._reset_diagnostics()
        audit=self.page.evaluate("""()=>{const text=e=>String(e&&e.innerText||e&&e.textContent||'').trim().replace(/\s+/g,' ').slice(0,160);const name=e=>{const labelled=e.getAttribute('aria-labelledby')||'';const ref=labelled?document.getElementById(labelled):null;const label=e.labels&&e.labels[0];return {value:String(e.getAttribute('aria-label')||text(ref)||text(label)||'').trim().slice(0,160),broken:Boolean(labelled&&!ref)};};const all=Array.from(document.querySelectorAll('[required],[aria-required="true"]'));const allowed=['INPUT','SELECT','TEXTAREA'];const roles=['textbox','combobox','listbox','radiogroup','checkbox','spinbutton','searchbox','tree'];const rows=all.slice(0,200).map(e=>{const n=name(e);const supported=allowed.includes(e.tagName)||roles.includes(String(e.getAttribute('role')||'').toLowerCase());return {name:n.value,tag:e.tagName.toLowerCase(),role:e.getAttribute('role')||'',native_required:e.required===true,aria_required:e.getAttribute('aria-required')==='true',broken_label_reference:n.broken,supported,valid:Boolean(n.value)&&supported&&!n.broken};});return {required_field_count:rows.length,fields:rows,unnamed_count:rows.filter(x=>!x.name).length,failure_count:rows.filter(x=>!x.valid).length,required_field_contract_passed:rows.every(x=>x.valid),truncated:all.length>200};}""")
        result=self._capture_state("inspect-required-field-contract");result.update({"required_field_audit":audit,"mutation_executed":False});return result

    def inspect_describedby_contract_semantic(self):
        """Audit aria-describedby references and non-empty descriptions."""
        self._ensure_started(); self._reset_diagnostics()
        audit=self.page.evaluate("""()=>{const all=Array.from(document.querySelectorAll('[aria-describedby]'));const rows=all.slice(0,200).map(e=>{const ids=String(e.getAttribute('aria-describedby')||'').trim().split(/\s+/).filter(Boolean);const refs=ids.map(id=>document.getElementById(id));const missing=ids.filter((id,i)=>!refs[i]);const empty=refs.filter(x=>x&&!String(x.innerText||x.textContent||'').trim()).length;const label=String(e.getAttribute('aria-label')||(e.labels&&e.labels[0]&&e.labels[0].innerText)||e.id||e.tagName).trim().replace(/\s+/g,' ').slice(0,160);return {label,reference_count:ids.length,missing_references:missing,empty_reference_count:empty,valid:ids.length>0&&missing.length===0&&empty===0};});return {described_element_count:rows.length,elements:rows,failure_count:rows.filter(x=>!x.valid).length,describedby_contract_passed:rows.every(x=>x.valid),truncated:all.length>200};}""")
        result=self._capture_state("inspect-describedby-contract");result.update({"describedby_audit":audit,"mutation_executed":False});return result

    def inspect_invalid_field_contract_semantic(self):
        """Audit explicitly invalid fields for names and linked error messages."""
        self._ensure_started(); self._reset_diagnostics()
        audit=self.page.evaluate("""()=>{const text=e=>String(e&&e.innerText||e&&e.textContent||'').trim().replace(/\s+/g,' ').slice(0,160);const all=Array.from(document.querySelectorAll('[aria-invalid="true"]'));const rows=all.slice(0,200).map(e=>{const labelled=e.getAttribute('aria-labelledby')||'';const labelRef=labelled?document.getElementById(labelled):null;const label=e.labels&&e.labels[0];const name=String(e.getAttribute('aria-label')||text(labelRef)||text(label)||'').trim().slice(0,160);const ids=String(e.getAttribute('aria-errormessage')||e.getAttribute('aria-describedby')||'').trim().split(/\s+/).filter(Boolean);const refs=ids.map(id=>document.getElementById(id));const messages=refs.filter(Boolean).map(text).filter(Boolean);return {name,message_reference_count:ids.length,existing_message_count:messages.length,messages:messages.slice(0,10),broken_label_reference:Boolean(labelled&&!labelRef),valid:Boolean(name)&&ids.length>0&&messages.length===ids.length&&!Boolean(labelled&&!labelRef)};});return {invalid_field_count:rows.length,fields:rows,failure_count:rows.filter(x=>!x.valid).length,invalid_field_contract_passed:rows.every(x=>x.valid),truncated:all.length>200};}""")
        result=self._capture_state("inspect-invalid-field-contract");result.update({"invalid_field_audit":audit,"mutation_executed":False});return result

    def inspect_text_length_contract_semantic(self):
        """Audit minlength/maxlength relationships on text-entry controls."""
        self._ensure_started(); self._reset_diagnostics()
        audit=self.page.evaluate("""()=>{const all=Array.from(document.querySelectorAll('input[minlength],input[maxlength],textarea[minlength],textarea[maxlength]'));const rows=all.slice(0,200).map(e=>{const min=e.hasAttribute('minlength')?Number(e.getAttribute('minlength')):null;const max=e.hasAttribute('maxlength')?Number(e.getAttribute('maxlength')):null;const minValid=min===null||(Number.isInteger(min)&&min>=0);const maxValid=max===null||(Number.isInteger(max)&&max>=0);const ordered=min===null||max===null||min<=max;return {tag:e.tagName.toLowerCase(),type:String(e.type||'').toLowerCase(),minlength:min,maxlength:max,current_length:String(e.value||'').length,valid:minValid&&maxValid&&ordered};});return {control_count:rows.length,controls:rows,failure_count:rows.filter(x=>!x.valid).length,text_length_contract_passed:rows.every(x=>x.valid),truncated:all.length>200};}""")
        result=self._capture_state("inspect-text-length-contract");result.update({"text_length_audit":audit,"mutation_executed":False});return result

    def inspect_range_constraint_contract_semantic(self):
        """Audit min/max/step syntax and ordering for constrained inputs."""
        self._ensure_started(); self._reset_diagnostics()
        audit=self.page.evaluate("""()=>{const all=Array.from(document.querySelectorAll('input[min],input[max],input[step]'));const parse=(type,v)=>{if(v===null)return null;const x=document.createElement('input');x.type=type;x.value=v;return Number.isFinite(x.valueAsNumber)?x.valueAsNumber:NaN;};const rows=all.slice(0,200).map(e=>{const type=String(e.type||'text').toLowerCase();const minRaw=e.getAttribute('min'),maxRaw=e.getAttribute('max'),stepRaw=e.getAttribute('step');const min=parse(type,minRaw),max=parse(type,maxRaw);const stepValid=stepRaw===null||stepRaw==='any'||(Number.isFinite(Number(stepRaw))&&Number(stepRaw)>0);const minValid=minRaw===null||Number.isFinite(min);const maxValid=maxRaw===null||Number.isFinite(max);const ordered=min===null||max===null||!Number.isFinite(min)||!Number.isFinite(max)||min<=max;return {type,min:minRaw,max:maxRaw,step:stepRaw,min_valid:minValid,max_valid:maxValid,step_valid:stepValid,ordered,valid:minValid&&maxValid&&stepValid&&ordered};});return {control_count:rows.length,controls:rows,failure_count:rows.filter(x=>!x.valid).length,range_constraint_contract_passed:rows.every(x=>x.valid),truncated:all.length>200};}""")
        result=self._capture_state("inspect-range-constraint-contract");result.update({"range_constraint_audit":audit,"mutation_executed":False});return result

    def inspect_inputmode_contract_semantic(self):
        """Audit inputmode tokens and names on virtual-keyboard hints."""
        self._ensure_started(); self._reset_diagnostics()
        audit=self.page.evaluate("""()=>{const allowed=['none','text','decimal','numeric','tel','search','email','url'];const all=Array.from(document.querySelectorAll('[inputmode]'));const rows=all.slice(0,200).map(e=>{const mode=String(e.getAttribute('inputmode')||'').toLowerCase();const label=e.labels&&e.labels[0];const name=String(e.getAttribute('aria-label')||(label&&label.innerText)||'').trim().replace(/\s+/g,' ').slice(0,160);const editable=['INPUT','TEXTAREA'].includes(e.tagName)||e.isContentEditable;return {name,tag:e.tagName.toLowerCase(),inputmode:mode,editable,valid:Boolean(name)&&editable&&allowed.includes(mode)};});return {control_count:rows.length,controls:rows,failure_count:rows.filter(x=>!x.valid).length,inputmode_contract_passed:rows.every(x=>x.valid),truncated:all.length>200};}""")
        result=self._capture_state("inspect-inputmode-contract");result.update({"inputmode_audit":audit,"mutation_executed":False});return result

    def inspect_new_tab_link_contract_semantic(self):
        """Audit target=_blank links for names, destinations and opener isolation."""
        self._ensure_started(); self._reset_diagnostics()
        audit=self.page.evaluate("""()=>{const all=Array.from(document.querySelectorAll('a[target="_blank"]'));const rows=all.slice(0,200).map(e=>{const href=e.getAttribute('href')||'';const name=String(e.getAttribute('aria-label')||e.innerText||e.textContent||'').trim().replace(/\s+/g,' ').slice(0,160);const rel=String(e.getAttribute('rel')||'').toLowerCase().split(/\s+/).filter(Boolean);let external=false;try{external=new URL(e.href,location.href).origin!==location.origin;}catch(_){}const isolated=rel.includes('noopener')||rel.includes('noreferrer');return {name,href,external,rel,opener_isolated:isolated,valid:Boolean(name)&&Boolean(href)&&(!external||isolated)};});return {new_tab_link_count:rows.length,external_count:rows.filter(x=>x.external).length,links:rows,failure_count:rows.filter(x=>!x.valid).length,new_tab_link_contract_passed:rows.every(x=>x.valid),truncated:all.length>200};}""")
        result=self._capture_state("inspect-new-tab-link-contract");result.update({"new_tab_link_audit":audit,"mutation_executed":False});return result

    def inspect_iframe_contract_semantic(self):
        """Audit iframe titles, source presence and sandbox metadata."""
        self._ensure_started(); self._reset_diagnostics()
        audit=self.page.evaluate("""()=>{const all=Array.from(document.querySelectorAll('iframe'));const rows=all.slice(0,100).map(e=>{const title=String(e.getAttribute('title')||e.getAttribute('aria-label')||'').trim().replace(/\s+/g,' ').slice(0,160);const src=e.getAttribute('src')||e.getAttribute('srcdoc')||'';let external=false;try{external=Boolean(e.src)&&new URL(e.src,location.href).origin!==location.origin;}catch(_){}return {title,source_present:Boolean(src),external,sandboxed:e.hasAttribute('sandbox'),loading:e.getAttribute('loading')||'',valid:Boolean(title)&&Boolean(src)};});return {iframe_count:rows.length,external_count:rows.filter(x=>x.external).length,sandboxed_count:rows.filter(x=>x.sandboxed).length,iframes:rows,failure_count:rows.filter(x=>!x.valid).length,iframe_contract_passed:rows.every(x=>x.valid),truncated:all.length>100};}""")
        result=self._capture_state("inspect-iframe-contract");result.update({"iframe_contract_audit":audit,"mutation_executed":False});return result

    def inspect_referrerpolicy_contract_semantic(self):
        """Audit referrerpolicy tokens on elements that declare them."""
        self._ensure_started(); self._reset_diagnostics()
        audit=self.page.evaluate("""()=>{const allowed=['no-referrer','no-referrer-when-downgrade','origin','origin-when-cross-origin','same-origin','strict-origin','strict-origin-when-cross-origin','unsafe-url'];const all=Array.from(document.querySelectorAll('[referrerpolicy]'));const rows=all.slice(0,200).map(e=>{const policy=String(e.getAttribute('referrerpolicy')||'').toLowerCase();const target=String(e.getAttribute('href')||e.getAttribute('src')||'').slice(0,300);return {tag:e.tagName.toLowerCase(),policy,target_present:Boolean(target),valid:allowed.includes(policy)&&Boolean(target)};});return {element_count:rows.length,elements:rows,failure_count:rows.filter(x=>!x.valid).length,referrerpolicy_contract_passed:rows.every(x=>x.valid),truncated:all.length>200};}""")
        result=self._capture_state("inspect-referrerpolicy-contract");result.update({"referrerpolicy_audit":audit,"mutation_executed":False});return result

    def inspect_tabindex_contract_semantic(self):
        """Audit explicit tabindex values and detect positive focus-order overrides."""
        self._ensure_started(); self._reset_diagnostics()
        audit=self.page.evaluate("""()=>{const all=Array.from(document.querySelectorAll('[tabindex]'));const rows=all.slice(0,300).map(e=>{const raw=e.getAttribute('tabindex')||'';const value=Number(raw);const numeric=/^-?\d+$/.test(raw.trim());const name=String(e.getAttribute('aria-label')||e.innerText||e.textContent||e.id||e.tagName).trim().replace(/\s+/g,' ').slice(0,120);return {name,tag:e.tagName.toLowerCase(),tabindex:raw,numeric,positive:numeric&&value>0,valid:numeric&&value<=0};});return {element_count:rows.length,positive_count:rows.filter(x=>x.positive).length,elements:rows,failure_count:rows.filter(x=>!x.valid).length,tabindex_contract_passed:rows.every(x=>x.valid),truncated:all.length>300};}""")
        result=self._capture_state("inspect-tabindex-contract");result.update({"tabindex_audit":audit,"mutation_executed":False});return result

    def inspect_disabled_control_contract_semantic(self):
        """Audit native and ARIA disabled controls for names and state metadata."""
        self._ensure_started(); self._reset_diagnostics()
        audit=self.page.evaluate("""()=>{const all=Array.from(document.querySelectorAll('[disabled],[aria-disabled="true"]'));const rows=all.slice(0,300).map(e=>{const label=e.labels&&e.labels[0];const name=String(e.getAttribute('aria-label')||(label&&label.innerText)||e.innerText||e.value||'').trim().replace(/\s+/g,' ').slice(0,160);const native=e.matches('button,input,select,textarea,fieldset,optgroup,option')&&e.disabled===true;const aria=e.getAttribute('aria-disabled')==='true';const actionable=e.matches('button,input,select,textarea,a[href],[role="button"],[role="menuitem"],[role="option"],[role="tab"],[role="checkbox"],[role="radio"]');return {name,tag:e.tagName.toLowerCase(),native_disabled:native,aria_disabled:aria,actionable,focusable:e.tabIndex>=0,valid:Boolean(name)&&actionable&&(native||aria)};});return {disabled_control_count:rows.length,native_count:rows.filter(x=>x.native_disabled).length,aria_count:rows.filter(x=>x.aria_disabled).length,controls:rows,failure_count:rows.filter(x=>!x.valid).length,disabled_control_contract_passed:rows.every(x=>x.valid),truncated:all.length>300};}""")
        result=self._capture_state("inspect-disabled-control-contract");result.update({"disabled_control_audit":audit,"mutation_executed":False});return result

    def inspect_readonly_contract_semantic(self):
        """Audit readonly states on native inputs and supported ARIA widgets."""
        self._ensure_started(); self._reset_diagnostics()
        audit=self.page.evaluate("""()=>{const all=Array.from(document.querySelectorAll('[readonly],[aria-readonly="true"]'));const roles=['textbox','searchbox','combobox','grid','gridcell','spinbutton'];const rows=all.slice(0,300).map(e=>{const label=e.labels&&e.labels[0];const name=String(e.getAttribute('aria-label')||(label&&label.innerText)||'').trim().replace(/\s+/g,' ').slice(0,160);const native=['INPUT','TEXTAREA'].includes(e.tagName)&&e.readOnly===true;const aria=e.getAttribute('aria-readonly')==='true';const role=String(e.getAttribute('role')||'').toLowerCase();const supported=native||(aria&&roles.includes(role));return {name,tag:e.tagName.toLowerCase(),role,native_readonly:native,aria_readonly:aria,supported,valid:Boolean(name)&&supported};});return {readonly_control_count:rows.length,controls:rows,failure_count:rows.filter(x=>!x.valid).length,readonly_contract_passed:rows.every(x=>x.valid),truncated:all.length>300};}""")
        result=self._capture_state("inspect-readonly-contract");result.update({"readonly_audit":audit,"mutation_executed":False});return result

    def inspect_aria_controls_contract_semantic(self):
        """Audit aria-controls ID references and duplicate targets."""
        self._ensure_started(); self._reset_diagnostics()
        audit=self.page.evaluate("""()=>{const all=Array.from(document.querySelectorAll('[aria-controls]'));const rows=all.slice(0,300).map(e=>{const ids=String(e.getAttribute('aria-controls')||'').trim().split(/\s+/).filter(Boolean);const missing=ids.filter(id=>!document.getElementById(id));const duplicate=[...new Set(ids.filter((id,i)=>ids.indexOf(id)!==i))];return {controller:String(e.getAttribute('aria-label')||e.innerText||e.id||e.tagName).trim().replace(/\s+/g,' ').slice(0,120),target_ids:ids,missing_targets:missing,duplicate_targets:duplicate,self_reference:Boolean(e.id&&ids.includes(e.id)),valid:ids.length>0&&missing.length===0&&duplicate.length===0&&!(e.id&&ids.includes(e.id))};});return {controller_count:rows.length,controllers:rows,failure_count:rows.filter(x=>!x.valid).length,aria_controls_contract_passed:rows.every(x=>x.valid),truncated:all.length>300};}""")
        result=self._capture_state("inspect-aria-controls-contract");result.update({"aria_controls_audit":audit,"mutation_executed":False});return result

    def inspect_aria_labelledby_contract_semantic(self):
        """Audit aria-labelledby references and resulting non-empty names."""
        self._ensure_started(); self._reset_diagnostics()
        audit=self.page.evaluate("""()=>{const all=Array.from(document.querySelectorAll('[aria-labelledby]'));const rows=all.slice(0,300).map(e=>{const ids=String(e.getAttribute('aria-labelledby')||'').trim().split(/\s+/).filter(Boolean);const refs=ids.map(id=>document.getElementById(id));const missing=ids.filter((id,i)=>!refs[i]);const duplicate=[...new Set(ids.filter((id,i)=>ids.indexOf(id)!==i))];const name=refs.filter(Boolean).map(x=>String(x.innerText||x.textContent||'').trim()).filter(Boolean).join(' ').replace(/\s+/g,' ').slice(0,200);return {target_ids:ids,resolved_name:name,missing_targets:missing,duplicate_targets:duplicate,self_reference:Boolean(e.id&&ids.includes(e.id)),valid:ids.length>0&&Boolean(name)&&missing.length===0&&duplicate.length===0&&!(e.id&&ids.includes(e.id))};});return {element_count:rows.length,elements:rows,failure_count:rows.filter(x=>!x.valid).length,aria_labelledby_contract_passed:rows.every(x=>x.valid),truncated:all.length>300};}""")
        result=self._capture_state("inspect-aria-labelledby-contract");result.update({"aria_labelledby_audit":audit,"mutation_executed":False});return result

    def inspect_aria_owns_contract_semantic(self):
        """Audit aria-owns references for existence, uniqueness and cycles."""
        self._ensure_started(); self._reset_diagnostics()
        audit=self.page.evaluate("""()=>{const all=Array.from(document.querySelectorAll('[aria-owns]'));const rows=all.slice(0,300).map(e=>{const ids=String(e.getAttribute('aria-owns')||'').trim().split(/\s+/).filter(Boolean);const refs=ids.map(id=>document.getElementById(id));const missing=ids.filter((id,i)=>!refs[i]);const duplicate=[...new Set(ids.filter((id,i)=>ids.indexOf(id)!==i))];const self=Boolean(e.id&&ids.includes(e.id));const ancestor=refs.some(x=>x&&x.contains(e));return {owner:String(e.getAttribute('aria-label')||e.id||e.tagName).trim().slice(0,120),target_ids:ids,missing_targets:missing,duplicate_targets:duplicate,self_reference:self,ancestor_cycle:ancestor,valid:ids.length>0&&missing.length===0&&duplicate.length===0&&!self&&!ancestor};});return {owner_count:rows.length,owners:rows,failure_count:rows.filter(x=>!x.valid).length,aria_owns_contract_passed:rows.every(x=>x.valid),truncated:all.length>300};}""")
        result=self._capture_state("inspect-aria-owns-contract");result.update({"aria_owns_audit":audit,"mutation_executed":False});return result

    def inspect_checkbox_contract_semantic(self):
        """Audit native and ARIA checkbox names and checked-state tokens."""
        self._ensure_started(); self._reset_diagnostics()
        audit=self.page.evaluate("""()=>{const all=Array.from(document.querySelectorAll('input[type="checkbox"],[role="checkbox"]'));const rows=all.slice(0,300).map(e=>{const native=e.matches('input[type="checkbox"]');const label=e.labels&&e.labels[0];const name=String(e.getAttribute('aria-label')||(label&&label.innerText)||e.innerText||'').trim().replace(/\s+/g,' ').slice(0,160);const raw=native?(e.indeterminate?'mixed':String(e.checked)):String(e.getAttribute('aria-checked')||'');const validState=['true','false','mixed'].includes(raw);return {name,native,state:raw,disabled:e.disabled===true||e.getAttribute('aria-disabled')==='true',valid:Boolean(name)&&validState};});return {checkbox_count:rows.length,checkboxes:rows,failure_count:rows.filter(x=>!x.valid).length,checkbox_contract_passed:rows.every(x=>x.valid),truncated:all.length>300};}""")
        result=self._capture_state("inspect-checkbox-contract");result.update({"checkbox_audit":audit,"mutation_executed":False});return result

    def inspect_switch_contract_semantic(self):
        """Audit ARIA switches for names and boolean checked state."""
        self._ensure_started(); self._reset_diagnostics()
        audit=self.page.evaluate("""()=>{const all=Array.from(document.querySelectorAll('[role="switch"]'));const rows=all.slice(0,300).map(e=>{const name=String(e.getAttribute('aria-label')||e.innerText||e.textContent||'').trim().replace(/\s+/g,' ').slice(0,160);const state=String(e.getAttribute('aria-checked')||'').toLowerCase();return {name,state,disabled:e.getAttribute('aria-disabled')==='true',valid:Boolean(name)&&['true','false'].includes(state)};});return {switch_count:rows.length,switches:rows,failure_count:rows.filter(x=>!x.valid).length,switch_contract_passed:rows.every(x=>x.valid),truncated:all.length>300};}""")
        result=self._capture_state("inspect-switch-contract");result.update({"switch_audit":audit,"mutation_executed":False});return result

    def inspect_toggle_button_contract_semantic(self):
        """Audit aria-pressed toggle buttons for names and valid states."""
        self._ensure_started(); self._reset_diagnostics()
        audit=self.page.evaluate("""()=>{const all=Array.from(document.querySelectorAll('[aria-pressed]'));const rows=all.slice(0,300).map(e=>{const name=String(e.getAttribute('aria-label')||e.innerText||e.value||'').trim().replace(/\s+/g,' ').slice(0,160);const state=String(e.getAttribute('aria-pressed')||'').toLowerCase();const button=e.tagName==='BUTTON'||e.getAttribute('role')==='button'||(e.tagName==='INPUT'&&['button','submit','reset'].includes(String(e.type).toLowerCase()));return {name,state,button,disabled:e.disabled===true||e.getAttribute('aria-disabled')==='true',valid:Boolean(name)&&button&&['true','false','mixed'].includes(state)};});return {toggle_button_count:rows.length,buttons:rows,failure_count:rows.filter(x=>!x.valid).length,toggle_button_contract_passed:rows.every(x=>x.valid),truncated:all.length>300};}""")
        result=self._capture_state("inspect-toggle-button-contract");result.update({"toggle_button_audit":audit,"mutation_executed":False});return result

    def inspect_expanded_contract_semantic(self):
        """Audit aria-expanded controls and optional controlled targets."""
        self._ensure_started(); self._reset_diagnostics()
        audit=self.page.evaluate("""()=>{const all=Array.from(document.querySelectorAll('[aria-expanded]'));const rows=all.slice(0,300).map(e=>{const name=String(e.getAttribute('aria-label')||e.innerText||e.textContent||'').trim().replace(/\s+/g,' ').slice(0,160);const state=String(e.getAttribute('aria-expanded')||'').toLowerCase();const ids=String(e.getAttribute('aria-controls')||'').trim().split(/\s+/).filter(Boolean);const missing=ids.filter(id=>!document.getElementById(id));return {name,state,controlled_ids:ids,missing_targets:missing,valid:Boolean(name)&&['true','false'].includes(state)&&missing.length===0};});return {expanded_control_count:rows.length,controls:rows,failure_count:rows.filter(x=>!x.valid).length,expanded_contract_passed:rows.every(x=>x.valid),truncated:all.length>300};}""")
        result=self._capture_state("inspect-expanded-contract");result.update({"expanded_audit":audit,"mutation_executed":False});return result

    def inspect_haspopup_contract_semantic(self):
        """Audit aria-haspopup tokens, names and controlled popup references."""
        self._ensure_started(); self._reset_diagnostics()
        audit=self.page.evaluate("""()=>{const allowed=['true','menu','listbox','tree','grid','dialog'];const all=Array.from(document.querySelectorAll('[aria-haspopup]'));const rows=all.slice(0,300).map(e=>{const name=String(e.getAttribute('aria-label')||e.innerText||e.textContent||'').trim().replace(/\s+/g,' ').slice(0,160);const popup=String(e.getAttribute('aria-haspopup')||'').toLowerCase();const ids=String(e.getAttribute('aria-controls')||'').trim().split(/\s+/).filter(Boolean);const missing=ids.filter(id=>!document.getElementById(id));return {name,popup,controlled_ids:ids,missing_targets:missing,expanded:e.getAttribute('aria-expanded'),valid:Boolean(name)&&allowed.includes(popup)&&missing.length===0};});return {popup_control_count:rows.length,controls:rows,failure_count:rows.filter(x=>!x.valid).length,haspopup_contract_passed:rows.every(x=>x.valid),truncated:all.length>300};}""")
        result=self._capture_state("inspect-haspopup-contract");result.update({"haspopup_audit":audit,"mutation_executed":False});return result

    def inspect_activedescendant_contract_semantic(self):
        """Audit aria-activedescendant references and ownership relation."""
        self._ensure_started(); self._reset_diagnostics()
        audit=self.page.evaluate("""()=>{const all=Array.from(document.querySelectorAll('[aria-activedescendant]'));const rows=all.slice(0,300).map(e=>{const id=String(e.getAttribute('aria-activedescendant')||'').trim();const target=id?document.getElementById(id):null;const owns=String(e.getAttribute('aria-owns')||'').trim().split(/\s+/).filter(Boolean);const related=Boolean(target&&(e.contains(target)||owns.includes(id)));const focusable=e.tabIndex>=0||['INPUT','TEXTAREA','SELECT'].includes(e.tagName);return {active_id:id,target_exists:Boolean(target),related,focusable,valid:Boolean(id)&&Boolean(target)&&related&&focusable};});return {container_count:rows.length,containers:rows,failure_count:rows.filter(x=>!x.valid).length,activedescendant_contract_passed:rows.every(x=>x.valid),truncated:all.length>300};}""")
        result=self._capture_state("inspect-activedescendant-contract");result.update({"activedescendant_audit":audit,"mutation_executed":False});return result

    def inspect_set_position_contract_semantic(self):
        """Audit aria-setsize/aria-posinset pairs for virtual collections."""
        self._ensure_started(); self._reset_diagnostics()
        audit=self.page.evaluate("""()=>{const all=Array.from(document.querySelectorAll('[aria-setsize],[aria-posinset]'));const rows=all.slice(0,500).map(e=>{const sizeRaw=e.getAttribute('aria-setsize'),posRaw=e.getAttribute('aria-posinset');const size=Number(sizeRaw),pos=Number(posRaw);const sizeValid=sizeRaw!==null&&Number.isInteger(size)&&(size===-1||size>0);const posValid=posRaw!==null&&Number.isInteger(pos)&&pos>0;const ordered=size===-1||!sizeValid||!posValid||pos<=size;return {role:e.getAttribute('role')||'',setsize:sizeRaw,posinset:posRaw,size_valid:sizeValid,position_valid:posValid,ordered,valid:sizeValid&&posValid&&ordered};});return {item_count:rows.length,items:rows,failure_count:rows.filter(x=>!x.valid).length,set_position_contract_passed:rows.every(x=>x.valid),truncated:all.length>500};}""")
        result=self._capture_state("inspect-set-position-contract");result.update({"set_position_audit":audit,"mutation_executed":False});return result

    def inspect_virtual_grid_contract_semantic(self):
        """Audit virtual grid row/column counts and indexed descendants."""
        self._ensure_started(); self._reset_diagnostics()
        audit=self.page.evaluate("""()=>{const all=Array.from(document.querySelectorAll('[aria-rowcount],[aria-colcount]'));const rows=all.slice(0,100).map(e=>{const rr=e.getAttribute('aria-rowcount'),cr=e.getAttribute('aria-colcount');const rc=rr===null?null:Number(rr),cc=cr===null?null:Number(cr);const rcValid=rr===null||(Number.isInteger(rc)&&(rc===-1||rc>0));const ccValid=cr===null||(Number.isInteger(cc)&&(cc===-1||cc>0));const rowIndexes=Array.from(e.querySelectorAll('[aria-rowindex]')).map(x=>Number(x.getAttribute('aria-rowindex')));const colIndexes=Array.from(e.querySelectorAll('[aria-colindex]')).map(x=>Number(x.getAttribute('aria-colindex')));const indexesValid=rowIndexes.every(x=>Number.isInteger(x)&&x>0&&(rc===-1||rc===null||x<=rc))&&colIndexes.every(x=>Number.isInteger(x)&&x>0&&(cc===-1||cc===null||x<=cc));return {role:e.getAttribute('role')||e.tagName.toLowerCase(),rowcount:rr,colcount:cr,indexed_rows:rowIndexes.length,indexed_columns:colIndexes.length,valid:(rr!==null||cr!==null)&&rcValid&&ccValid&&indexesValid};});return {grid_count:rows.length,grids:rows,failure_count:rows.filter(x=>!x.valid).length,virtual_grid_contract_passed:rows.every(x=>x.valid),truncated:all.length>100};}""")
        result=self._capture_state("inspect-virtual-grid-contract");result.update({"virtual_grid_audit":audit,"mutation_executed":False});return result

    def inspect_aria_level_contract_semantic(self):
        """Audit aria-level values on hierarchical roles."""
        self._ensure_started(); self._reset_diagnostics()
        audit=self.page.evaluate("""()=>{const allowed=['heading','treeitem','row','listitem'];const all=Array.from(document.querySelectorAll('[aria-level]'));const rows=all.slice(0,500).map(e=>{const raw=e.getAttribute('aria-level')||'';const level=Number(raw);const role=String(e.getAttribute('role')||'').toLowerCase();const implicit=/^H[1-6]$/.test(e.tagName)?'heading':'';const effective=role||implicit;return {role:effective,level:raw,valid:allowed.includes(effective)&&Number.isInteger(level)&&level>0};});return {element_count:rows.length,elements:rows,failure_count:rows.filter(x=>!x.valid).length,aria_level_contract_passed:rows.every(x=>x.valid),truncated:all.length>500};}""")
        result=self._capture_state("inspect-aria-level-contract");result.update({"aria_level_audit":audit,"mutation_executed":False});return result

    def inspect_svg_accessibility_contract_semantic(self):
        """Audit exposed SVG graphics for accessible names."""
        self._ensure_started(); self._reset_diagnostics()
        audit=self.page.evaluate("""()=>{const all=Array.from(document.querySelectorAll('svg')).filter(e=>e.getAttribute('role')==='img'||e.hasAttribute('tabindex')||e.hasAttribute('aria-label')||e.hasAttribute('aria-labelledby'));const rows=all.slice(0,300).map(e=>{const labelled=e.getAttribute('aria-labelledby')||'';const ref=labelled?document.getElementById(labelled):null;const title=e.querySelector(':scope > title');const name=String(e.getAttribute('aria-label')||(ref&&ref.textContent)||(title&&title.textContent)||'').trim().replace(/\s+/g,' ').slice(0,160);return {name,role:e.getAttribute('role')||'',focusable:e.tabIndex>=0,broken_label_reference:Boolean(labelled&&!ref),valid:Boolean(name)&&!Boolean(labelled&&!ref)};});return {exposed_svg_count:rows.length,graphics:rows,failure_count:rows.filter(x=>!x.valid).length,svg_accessibility_contract_passed:rows.every(x=>x.valid),truncated:all.length>300};}""")
        result=self._capture_state("inspect-svg-accessibility-contract");result.update({"svg_accessibility_audit":audit,"mutation_executed":False});return result

    def inspect_canvas_fallback_contract_semantic(self):
        """Audit canvas elements for accessible fallback or labeling."""
        self._ensure_started(); self._reset_diagnostics()
        audit=self.page.evaluate("""()=>{const all=Array.from(document.querySelectorAll('canvas'));const rows=all.slice(0,200).map(e=>{const labelled=e.getAttribute('aria-labelledby')||'';const ref=labelled?document.getElementById(labelled):null;const fallback=String(e.textContent||'').trim().replace(/\s+/g,' ').slice(0,200);const name=String(e.getAttribute('aria-label')||(ref&&ref.textContent)||'').trim().replace(/\s+/g,' ').slice(0,160);const hidden=e.getAttribute('aria-hidden')==='true';return {name,fallback,hidden,broken_label_reference:Boolean(labelled&&!ref),valid:hidden||(Boolean(name||fallback)&&!Boolean(labelled&&!ref))};});return {canvas_count:rows.length,canvases:rows,failure_count:rows.filter(x=>!x.valid).length,canvas_fallback_contract_passed:rows.every(x=>x.valid),truncated:all.length>200};}""")
        result=self._capture_state("inspect-canvas-fallback-contract");result.update({"canvas_fallback_audit":audit,"mutation_executed":False});return result

    def inspect_media_caption_contract_semantic(self):
        """Audit video caption tracks and track metadata without playback."""
        self._ensure_started(); self._reset_diagnostics()
        audit=self.page.evaluate("""()=>{const all=Array.from(document.querySelectorAll('video'));const rows=all.slice(0,100).map(e=>{const tracks=Array.from(e.querySelectorAll('track')).map(t=>({kind:String(t.kind||t.getAttribute('kind')||'').toLowerCase(),srclang:t.getAttribute('srclang')||'',label:t.getAttribute('label')||'',src:t.getAttribute('src')||''}));const captions=tracks.filter(t=>t.kind==='captions');const captionValid=captions.every(t=>Boolean(t.srclang&&t.label&&t.src));const exempt=e.muted===true||e.hasAttribute('muted');return {muted:exempt,track_count:tracks.length,caption_count:captions.length,tracks:tracks.slice(0,20),valid:(exempt||captions.length>0)&&captionValid};});return {video_count:rows.length,videos:rows,failure_count:rows.filter(x=>!x.valid).length,media_caption_contract_passed:rows.every(x=>x.valid),truncated:all.length>100};}""")
        result=self._capture_state("inspect-media-caption-contract");result.update({"media_caption_audit":audit,"mutation_executed":False});return result

    def inspect_language_contract_semantic(self):
        """Audit declared language tags and lang/xml:lang consistency."""
        self._ensure_started(); self._reset_diagnostics()
        audit=self.page.evaluate("""()=>{const all=Array.from(document.querySelectorAll('*')).filter(e=>e.hasAttribute('lang')||e.hasAttribute('xml:lang'));const tag=/^[A-Za-z]{2,8}(?:-[A-Za-z0-9]{1,8})*$/;const rows=all.slice(0,300).map(e=>{const lang=String(e.getAttribute('lang')||'').trim();const xml=String(e.getAttribute('xml:lang')||'').trim();const primary=lang||xml;const consistent=!lang||!xml||lang.toLowerCase()===xml.toLowerCase();return {tag:e.tagName.toLowerCase(),lang,xml_lang:xml,consistent,valid:tag.test(primary)&&consistent};});const documentLanguage=String(document.documentElement.getAttribute('lang')||'').trim();return {declared_count:rows.length,document_language:documentLanguage,elements:rows,failure_count:rows.filter(x=>!x.valid).length,language_contract_passed:Boolean(documentLanguage)&&tag.test(documentLanguage)&&rows.every(x=>x.valid),truncated:all.length>300};}""")
        result=self._capture_state("inspect-language-contract");result.update({"language_audit":audit,"mutation_executed":False});return result

    def inspect_direction_contract_semantic(self):
        """Audit explicit text-direction tokens."""
        self._ensure_started(); self._reset_diagnostics()
        audit=self.page.evaluate("""()=>{const allowed=['ltr','rtl','auto'];const all=Array.from(document.querySelectorAll('[dir]'));const rows=all.slice(0,300).map(e=>{const direction=String(e.getAttribute('dir')||'').toLowerCase();return {tag:e.tagName.toLowerCase(),direction,valid:allowed.includes(direction)};});const documentDirection=String(document.documentElement.getAttribute('dir')||'').toLowerCase();return {declared_count:rows.length,document_direction:documentDirection||'implicit-ltr',elements:rows,failure_count:rows.filter(x=>!x.valid).length,direction_contract_passed:rows.every(x=>x.valid),truncated:all.length>300};}""")
        result=self._capture_state("inspect-direction-contract");result.update({"direction_audit":audit,"mutation_executed":False});return result

    def inspect_time_contract_semantic(self):
        """Audit time elements for visible text and parseable datetime values."""
        self._ensure_started(); self._reset_diagnostics()
        audit=self.page.evaluate("""()=>{const all=Array.from(document.querySelectorAll('time'));const duration=/^P(?=\\d|T\\d)(?:\\d+Y)?(?:\\d+M)?(?:\\d+D)?(?:T(?:\\d+H)?(?:\\d+M)?(?:\\d+(?:\\.\\d+)?S)?)?$/i;const rows=all.slice(0,300).map(e=>{const text=String(e.innerText||e.textContent||'').trim().replace(/\s+/g,' ').slice(0,160);const value=String(e.getAttribute('datetime')||'').trim();const parseable=Boolean(value)&&(duration.test(value)||!Number.isNaN(Date.parse(value))||/^\\d{4}(?:-\\d{2})?$/.test(value)||/^\\d{2}:\\d{2}(?::\\d{2}(?:\\.\\d+)?)?$/.test(value));return {text,datetime:value,parseable,valid:Boolean(text)&&parseable};});return {time_count:rows.length,elements:rows,failure_count:rows.filter(x=>!x.valid).length,time_contract_passed:rows.every(x=>x.valid),truncated:all.length>300};}""")
        result=self._capture_state("inspect-time-contract");result.update({"time_audit":audit,"mutation_executed":False});return result

    def inspect_canonical_url_contract_semantic(self):
        """Audit canonical link uniqueness and absolute HTTP(S) target."""
        self._ensure_started(); self._reset_diagnostics()
        audit=self.page.evaluate("""()=>{const all=Array.from(document.querySelectorAll('link[rel~="canonical"]'));const rows=all.slice(0,20).map(e=>{const raw=String(e.getAttribute('href')||'').trim();let valid=false,resolved='';try{const u=new URL(raw,location.href);resolved=u.href;valid=['http:','https:'].includes(u.protocol)&&!u.hash;}catch(_){}return {href:raw,resolved,valid};});return {canonical_count:rows.length,links:rows,failure_count:rows.filter(x=>!x.valid).length+(rows.length>1?rows.length-1:0),canonical_url_contract_passed:rows.length<=1&&rows.every(x=>x.valid),truncated:all.length>20};}""")
        result=self._capture_state("inspect-canonical-url-contract");result.update({"canonical_url_audit":audit,"mutation_executed":False});return result

    def inspect_alternate_language_contract_semantic(self):
        """Audit alternate hreflang links for tags, targets and duplicates."""
        self._ensure_started(); self._reset_diagnostics()
        audit=self.page.evaluate("""()=>{const tag=/^(?:x-default|[A-Za-z]{2,8}(?:-[A-Za-z0-9]{1,8})*)$/;const all=Array.from(document.querySelectorAll('link[rel~="alternate"][hreflang]'));const rows=all.slice(0,100).map(e=>{const hreflang=String(e.getAttribute('hreflang')||'').trim();const href=String(e.getAttribute('href')||'').trim();let target=false;try{const u=new URL(href,location.href);target=['http:','https:'].includes(u.protocol);}catch(_){}return {hreflang,href,valid:tag.test(hreflang)&&target};});const langs=rows.map(x=>x.hreflang.toLowerCase());const duplicate=[...new Set(langs.filter((x,i)=>langs.indexOf(x)!==i))];return {alternate_count:rows.length,links:rows,duplicate_languages:duplicate,failure_count:rows.filter(x=>!x.valid).length+duplicate.length,alternate_language_contract_passed:rows.every(x=>x.valid)&&duplicate.length===0,truncated:all.length>100};}""")
        result=self._capture_state("inspect-alternate-language-contract");result.update({"alternate_language_audit":audit,"mutation_executed":False});return result

    def inspect_base_url_contract_semantic(self):
        """Audit base element uniqueness and safe absolute URL metadata."""
        self._ensure_started(); self._reset_diagnostics()
        audit=self.page.evaluate("""()=>{const all=Array.from(document.querySelectorAll('base'));const rows=all.slice(0,20).map(e=>{const href=String(e.getAttribute('href')||'').trim();const target=String(e.getAttribute('target')||'').trim();let validHref=true,resolved='';if(href){try{const u=new URL(href,location.href);resolved=u.href;validHref=['http:','https:'].includes(u.protocol);}catch(_){validHref=false;}}const validTarget=!target||['_self','_blank','_parent','_top'].includes(target)||/^[A-Za-z][\w.-]*$/.test(target);return {href,resolved,target,valid:validHref&&validTarget&&Boolean(href||target)};});return {base_count:rows.length,elements:rows,failure_count:rows.filter(x=>!x.valid).length+(rows.length>1?rows.length-1:0),base_url_contract_passed:rows.length<=1&&rows.every(x=>x.valid),truncated:all.length>20};}""")
        result=self._capture_state("inspect-base-url-contract");result.update({"base_url_audit":audit,"mutation_executed":False});return result

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
            "row",
        ]

        requested_role = str(role or "").strip().casefold()
        inspected_row = (
            requested_role == "row"
            and exact
            and self._last_inspected_exact_row == {
                "name": name,
                "url": self.page.url,
            }
        )
        self._last_inspected_exact_row = None
        inspected_role_fallback = bool(
            requested_role and exact
            and (not container or str(container).strip() == str(name).strip())
            and self._last_inspected_exact_target == {
                "name": name,
                "exact": exact,
                "url": self.page.url,
            }
        )
        self._last_inspected_exact_target = None

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

        if requested_role == "row":
            if not inspected_row:
                return {
                    "error": "row_click_requires_exact_inspection",
                    "name": name,
                    "executed": False,
                }
            if container and str(container).strip() != str(name).strip():
                return {
                    "error": "row_container_mismatch",
                    "name": name,
                    "container": container,
                    "executed": False,
                }
            # Re-resolve the inspected exact cell immediately before clicking.
            # A row's accessible name includes every cell, so get_by_role(row,
            # name=CI) cannot safely identify the intended target.
            matches = []
            rows = self.page.locator("tr")
            for index in range(min(rows.count(), 500)):
                row = rows.nth(index)
                if not row.is_visible():
                    continue
                cells = row.locator(":scope > th, :scope > td")
                for cell_index in range(cells.count()):
                    cell = cells.nth(cell_index)
                    if " ".join(cell.inner_text().split()) == " ".join(name.split()):
                        matches.append(cell)
            if len(matches) != 1:
                return {
                    "error": "row_exact_cell_missing_or_ambiguous",
                    "name": name,
                    "matches": len(matches),
                    "executed": False,
                }
            role_matches = [("row", matches[0])]
            roles = []
            explicit_role_fallback = True

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

        if container and requested_role != "row":
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
            if requested_role and not inspected_role_fallback:
                return {
                    "error": "semantic_element_not_found",
                    "name": name,
                    "role": requested_role,
                    "container": container,
                }

            icon_matches = (
                [] if inspected_role_fallback
                else self._visible_icon_matches(name)
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
        result["role_hint_ignored_after_inspection"] = inspected_role_fallback
        result["self_container_hint_ignored_after_inspection"] = bool(
            inspected_role_fallback and container
        )
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


def set_viewport_semantic(profile: str) -> dict:
    return _session.set_viewport_semantic(profile)


def inspect_accessibility_semantic() -> dict:
    return _session.inspect_accessibility_semantic()


def probe_capabilities() -> dict:
    return _session.probe_capabilities()


def get_network_detail(request_id: str) -> dict:
    return _session.get_network_detail(request_id)


def inspect_agent_telemetry_semantic(
    ci_name: str, max_age_seconds: int = 300,
) -> dict:
    return _session.inspect_agent_telemetry_semantic(ci_name, max_age_seconds)


def inspect_agent_plugins_semantic(
    ci_name: str, plugin_name: str = None, expected_version: str = None,
    max_age_seconds: int = 3600,
) -> dict:
    return _session.inspect_agent_plugins_semantic(
        ci_name, plugin_name, expected_version, max_age_seconds,
    )


def inspect_agent_tasks_semantic(
    ci_name: str, task_name: str = None, task_id: str = None,
) -> dict:
    return _session.inspect_agent_tasks_semantic(ci_name, task_name, task_id)


def inspect_agent_task_result_semantic(
    ci_name: str, task_id: str,
    expected_text: str = None, expected_error_code: int = None,
    verify_periodic: bool = False,
) -> dict:
    return _session.inspect_agent_task_result_semantic(
        ci_name, task_id, expected_text, expected_error_code, verify_periodic,
    )


def open_agent_tasks_semantic(ci_name: str) -> dict:
    return _session.open_agent_tasks_semantic(ci_name)


def create_managed_agent_task_semantic(
    ci_name: str, fixture_id: str,
) -> dict:
    return _session.create_managed_agent_task_semantic(ci_name, fixture_id)


def inspect_managed_agent_task_result_semantic(
    ci_name: str, task_id: str,
) -> dict:
    return _session.inspect_managed_agent_task_result_semantic(ci_name, task_id)


def disable_agent_task_semantic(ci_name: str, task_id: str) -> dict:
    return _session.disable_agent_task_semantic(ci_name, task_id)


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


def inspect_file_input_semantic(field: str, exact: bool = True) -> dict:
    return _session.inspect_file_input_semantic(field, exact)


def set_upload_fixture_semantic(
    field: str, fixture: str, exact: bool = True,
) -> dict:
    return _session.set_upload_fixture_semantic(field, fixture, exact)


def set_staged_file_semantic(
    artifact_id: str,
    filename: str,
    content: bytes,
    field: str = None,
    trigger: str = None,
    exact: bool = True,
) -> dict:
    return _session.set_staged_file_semantic(
        artifact_id, filename, content, field, trigger, exact,
    )


def set_temporal_semantic(
    field: str,
    value: str,
    exact: bool = True,
) -> dict:
    return _session.set_temporal_semantic(field, value, exact)


def set_slider_semantic(
    field: str,
    value,
    exact: bool = True,
) -> dict:
    return _session.set_slider_semantic(field, value, exact)


def inspect_tree_semantic(tree: str = None, exact: bool = True) -> dict:
    return _session.inspect_tree_semantic(tree, exact)


def set_tree_item_expanded(
    item: str,
    expanded: bool,
    tree: str = None,
    exact: bool = True,
) -> dict:
    return _session.set_tree_item_expanded(item, expanded, tree, exact)


def set_tree_item_selected(
    item: str,
    selected: bool,
    tree: str = None,
    exact: bool = True,
) -> dict:
    return _session.set_tree_item_selected(item, selected, tree, exact)


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


def copy_value_semantic(
    source: str,
    exact: bool = True,
    role: str = None,
) -> dict:
    return _session.copy_value_semantic(source, exact, role)


def paste_private_semantic(
    target: str,
    replace: bool = False,
    exact: bool = True,
    role: str = None,
) -> dict:
    return _session.paste_private_semantic(target, replace, exact, role)


def clear_private_clipboard() -> dict:
    return _session.clear_private_clipboard()


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
    order_container: str = None,
    expected_order: list = None,
    order_mode: str = "exact",
    container_role: str = None,
) -> dict:
    return _session.drag_semantic(
        source,
        target,
        exact,
        source_role,
        target_role,
        order_container,
        expected_order,
        order_mode,
        container_role,
    )


def inspect_order_semantic(
    container: str,
    expected_order: list = None,
    mode: str = "exact",
    exact: bool = True,
    role: str = None,
) -> dict:
    return _session.inspect_order_semantic(
        container,
        expected_order,
        mode,
        exact,
        role,
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
    table: str = None,
) -> dict:
    return _session.set_table_row_selected(name, selected, exact, table)


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


def inspect_popover_semantic(trigger: str, exact: bool = True) -> dict:
    return _session.inspect_popover_semantic(trigger, exact)


def open_popover_semantic(trigger: str, exact: bool = True) -> dict:
    return _session.open_popover_semantic(trigger, exact)


def select_popover_option_semantic(
    trigger: str, option: str, exact: bool = True,
) -> dict:
    return _session.select_popover_option_semantic(trigger, option, exact)


def click_popover_button_semantic(
    trigger: str, button: str, exact: bool = True,
) -> dict:
    return _session.click_popover_button_semantic(trigger, button, exact)


def close_popover_semantic(trigger: str, exact: bool = True) -> dict:
    return _session.close_popover_semantic(trigger, exact)


def inspect_calendar_semantic(trigger: str, exact: bool = True) -> dict:
    return _session.inspect_calendar_semantic(trigger, exact)


def open_calendar_semantic(trigger: str, exact: bool = True) -> dict:
    return _session.open_calendar_semantic(trigger, exact)


def select_calendar_option_semantic(
    trigger: str, option: str, exact: bool = True,
) -> dict:
    return _session.select_calendar_option_semantic(trigger, option, exact)


def inspect_time_picker_semantic(trigger: str, exact: bool = True) -> dict:
    return _session.inspect_time_picker_semantic(trigger, exact)


def open_time_picker_semantic(trigger: str, exact: bool = True) -> dict:
    return _session.open_time_picker_semantic(trigger, exact)


def select_time_picker_option_semantic(
    trigger: str, option: str, exact: bool = True,
) -> dict:
    return _session.select_time_picker_option_semantic(trigger, option, exact)


def inspect_dialog_semantic(dialog: str, exact: bool = True) -> dict:
    return _session.inspect_dialog_semantic(dialog, exact)


def click_dialog_button_semantic(
    dialog: str, button: str, exact: bool = True,
) -> dict:
    return _session.click_dialog_button_semantic(dialog, button, exact)


def apply_table_filter_popover_semantic(
    column: str,
    value: str,
    table: str = None,
    trigger: str = None,
    operator: str = None,
    apply_button: str = None,
    exact: bool = True,
) -> dict:
    return _session.apply_table_filter_popover_semantic(
        column,
        value,
        table,
        trigger,
        operator,
        apply_button,
        exact,
    )


def inspect_table_pagination_semantic(
    table: str = None,
    exact: bool = True,
) -> dict:
    return _session.inspect_table_pagination_semantic(table, exact)


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


def download_semantic(
    name: str,
    expected_filename: str,
    expected_format: str = None,
    expected_sha256: str = None,
    exact: bool = True,
) -> dict:
    return _session.download_semantic(
        name, expected_filename, expected_format, expected_sha256, exact,
    )


def verify_download_structure_semantic(
    download_id: str,
    format: str,
    expected_headers=None,
    min_rows=None,
    max_rows=None,
    expected_pages=None,
    expected_json_type=None,
    required_keys=None,
    min_items=None,
    max_items=None,
    expected_width=None,
    expected_height=None,
) -> dict:
    return _session.verify_download_structure_semantic(
        download_id, format, expected_headers, min_rows, max_rows,
        expected_pages, expected_json_type, required_keys, min_items, max_items,
        expected_width, expected_height,
    )


def inspect_new_tab_semantic(
    name: str,
    expected_url_prefix: str,
    exact: bool = True,
) -> dict:
    return _session.inspect_new_tab_semantic(
        name, expected_url_prefix, exact,
    )


def navigate_history_semantic(
    direction: str,
    expected_url_prefix: str,
) -> dict:
    return _session.navigate_history_semantic(
        direction, expected_url_prefix,
    )


def inspect_iframe_semantic(
    name: str,
    expected_url_prefix: str,
    exact: bool = True,
) -> dict:
    return _session.inspect_iframe_semantic(
        name, expected_url_prefix, exact,
    )


def observe_iframe_surface_change_semantic(
    name: str,
    expected_url_prefix: str,
    expect_change: bool,
    wait_ms: int = 1000,
    exact: bool = True,
) -> dict:
    return _session.observe_iframe_surface_change_semantic(
        name, expected_url_prefix, expect_change, wait_ms, exact,
    )


def click_iframe_surface_semantic(
    name: str,
    expected_url_prefix: str,
    x_ratio: float,
    y_ratio: float,
    expect_change: bool,
    wait_ms: int = 1000,
    exact: bool = True,
) -> dict:
    return _session.click_iframe_surface_semantic(
        name, expected_url_prefix, x_ratio, y_ratio,
        expect_change, wait_ms, exact,
    )


def press_iframe_surface_key_semantic(
    name: str, expected_url_prefix: str, key: str,
    x_ratio: float, y_ratio: float, expect_change: bool,
    focus_expect_change: bool = False, wait_ms: int = 500,
    exact: bool = True,
) -> dict:
    return _session.press_iframe_surface_key_semantic(
        name, expected_url_prefix, key, x_ratio, y_ratio,
        expect_change, focus_expect_change, wait_ms, exact,
    )


def inspect_hover_tooltip_semantic(
    target: str,
    target_role: str,
    expected_tooltip: str,
    exact: bool = True,
) -> dict:
    return _session.inspect_hover_tooltip_semantic(
        target, target_role, expected_tooltip, exact,
    )


def handle_native_dialog_semantic(
    target: str, expected_type: str, expected_message: str,
    decision: str = "dismiss", prompt_text: str = None,
    exact: bool = True,
) -> dict:
    return _session.handle_native_dialog_semantic(
        target, expected_type, expected_message, decision, prompt_text, exact,
    )


def inspect_form_validation_semantic(form: str = None, exact: bool = True) -> dict:
    return _session.inspect_form_validation_semantic(form, exact)


def inspect_loading_state_semantic(
    scope: str = None,
    expected_state: str = "ready",
    wait_ms: int = 2000,
    require_transition: bool = False,
    exact: bool = True,
) -> dict:
    return _session.inspect_loading_state_semantic(
        scope, expected_state, wait_ms, require_transition, exact,
    )


def inspect_notification_lifecycle_semantic(
    expected_text: str,
    role: str = "alert",
    expected_state: str = "visible",
    wait_ms: int = 2000,
    require_seen: bool = False,
    exact: bool = True,
) -> dict:
    return _session.inspect_notification_lifecycle_semantic(
        expected_text, role, expected_state, wait_ms, require_seen, exact,
    )

def inspect_aria_field_errors_semantic(form: str = None, exact: bool = True) -> dict:
    return _session.inspect_aria_field_errors_semantic(form, exact)

def inspect_control_state_lifecycle_semantic(target: str, role: str, expected_state: str, wait_ms: int = 2000, require_seen: bool = False, exact: bool = True) -> dict:
    return _session.inspect_control_state_lifecycle_semantic(target, role, expected_state, wait_ms, require_seen, exact)

def track_form_dirty_state_semantic(form: str, operation: str = "compare", exact: bool = True) -> dict:
    return _session.track_form_dirty_state_semantic(form, operation, exact)

def inspect_tabs_contract_semantic(tablist: str = None, exact: bool = True) -> dict:
    return _session.inspect_tabs_contract_semantic(tablist, exact)

def inspect_disclosure_contract_semantic(target: str, exact: bool = True) -> dict:
    return _session.inspect_disclosure_contract_semantic(target, exact)

def inspect_dialog_focus_trap_semantic(dialog: str, cycles: int = 1, exact: bool = True) -> dict:
    return _session.inspect_dialog_focus_trap_semantic(dialog, cycles, exact)

def inspect_heading_structure_semantic() -> dict:
    return _session.inspect_heading_structure_semantic()

def inspect_landmark_structure_semantic() -> dict:
    return _session.inspect_landmark_structure_semantic()

def inspect_link_contracts_semantic() -> dict:
    return _session.inspect_link_contracts_semantic()

def inspect_combobox_contract_semantic(target: str, exact: bool = True) -> dict:
    return _session.inspect_combobox_contract_semantic(target, exact)

def inspect_listbox_contract_semantic(target: str, exact: bool = True) -> dict:
    return _session.inspect_listbox_contract_semantic(target, exact)

def inspect_menu_contract_semantic(target: str, exact: bool = True) -> dict:
    return _session.inspect_menu_contract_semantic(target, exact)

def inspect_progressbar_contract_semantic(target: str, exact: bool = True) -> dict:
    return _session.inspect_progressbar_contract_semantic(target, exact)

def inspect_meter_contract_semantic(target: str, exact: bool = True) -> dict:
    return _session.inspect_meter_contract_semantic(target, exact)

def inspect_spinbutton_contract_semantic(target: str, exact: bool = True) -> dict:
    return _session.inspect_spinbutton_contract_semantic(target, exact)

def inspect_text_contrast_semantic() -> dict:
    return _session.inspect_text_contrast_semantic()

def inspect_text_clipping_semantic() -> dict:
    return _session.inspect_text_clipping_semantic()

def inspect_target_size_semantic(minimum_px: int = 24) -> dict:
    return _session.inspect_target_size_semantic(minimum_px)

def inspect_live_region_contract_semantic() -> dict:
    return _session.inspect_live_region_contract_semantic()

def inspect_dialog_contract_semantic() -> dict:
    return _session.inspect_dialog_contract_semantic()

def inspect_field_label_contract_semantic(form: str = None, exact: bool = True) -> dict:
    return _session.inspect_field_label_contract_semantic(form, exact)

def inspect_document_metadata_semantic() -> dict:
    return _session.inspect_document_metadata_semantic()

def inspect_keyboard_shortcuts_semantic() -> dict:
    return _session.inspect_keyboard_shortcuts_semantic()

def inspect_autofill_contract_semantic(form: str = None, exact: bool = True) -> dict:
    return _session.inspect_autofill_contract_semantic(form, exact)

def inspect_form_submission_contract_semantic() -> dict:
    return _session.inspect_form_submission_contract_semantic()

def inspect_script_security_semantic() -> dict:
    return _session.inspect_script_security_semantic()

def inspect_media_resource_semantic() -> dict:
    return _session.inspect_media_resource_semantic()

def inspect_lazy_media_contract_semantic() -> dict:
    return _session.inspect_lazy_media_contract_semantic()

def inspect_font_readiness_semantic(wait_ms: int = 2000) -> dict:
    return _session.inspect_font_readiness_semantic(wait_ms)

def inspect_reduced_motion_contract_semantic() -> dict:
    return _session.inspect_reduced_motion_contract_semantic()

def inspect_details_contract_semantic() -> dict:
    return _session.inspect_details_contract_semantic()

def inspect_popover_contract_semantic() -> dict:
    return _session.inspect_popover_contract_semantic()

def inspect_native_dialog_element_semantic() -> dict:
    return _session.inspect_native_dialog_element_semantic()

def inspect_fieldset_contract_semantic() -> dict:
    return _session.inspect_fieldset_contract_semantic()

def inspect_radio_group_contract_semantic() -> dict:
    return _session.inspect_radio_group_contract_semantic()

def inspect_button_type_contract_semantic() -> dict:
    return _session.inspect_button_type_contract_semantic()

def inspect_contenteditable_contract_semantic() -> dict:
    return _session.inspect_contenteditable_contract_semantic()

def inspect_search_contract_semantic() -> dict:
    return _session.inspect_search_contract_semantic()

def inspect_breadcrumb_contract_semantic() -> dict:
    return _session.inspect_breadcrumb_contract_semantic()

def inspect_table_structure_contract_semantic() -> dict:
    return _session.inspect_table_structure_contract_semantic()

def inspect_list_structure_contract_semantic() -> dict:
    return _session.inspect_list_structure_contract_semantic()

def inspect_description_list_contract_semantic() -> dict:
    return _session.inspect_description_list_contract_semantic()

def inspect_hash_link_contract_semantic() -> dict:
    return _session.inspect_hash_link_contract_semantic()

def inspect_navigation_current_contract_semantic() -> dict:
    return _session.inspect_navigation_current_contract_semantic()

def inspect_skip_link_contract_semantic() -> dict:
    return _session.inspect_skip_link_contract_semantic()

def inspect_required_field_contract_semantic() -> dict:
    return _session.inspect_required_field_contract_semantic()

def inspect_describedby_contract_semantic() -> dict:
    return _session.inspect_describedby_contract_semantic()

def inspect_invalid_field_contract_semantic() -> dict:
    return _session.inspect_invalid_field_contract_semantic()

def inspect_text_length_contract_semantic() -> dict:
    return _session.inspect_text_length_contract_semantic()

def inspect_range_constraint_contract_semantic() -> dict:
    return _session.inspect_range_constraint_contract_semantic()

def inspect_inputmode_contract_semantic() -> dict:
    return _session.inspect_inputmode_contract_semantic()

def inspect_new_tab_link_contract_semantic() -> dict:
    return _session.inspect_new_tab_link_contract_semantic()

def inspect_iframe_contract_semantic() -> dict:
    return _session.inspect_iframe_contract_semantic()

def inspect_referrerpolicy_contract_semantic() -> dict:
    return _session.inspect_referrerpolicy_contract_semantic()

def inspect_tabindex_contract_semantic() -> dict:
    return _session.inspect_tabindex_contract_semantic()

def inspect_disabled_control_contract_semantic() -> dict:
    return _session.inspect_disabled_control_contract_semantic()

def inspect_readonly_contract_semantic() -> dict:
    return _session.inspect_readonly_contract_semantic()

def inspect_aria_controls_contract_semantic() -> dict:
    return _session.inspect_aria_controls_contract_semantic()

def inspect_aria_labelledby_contract_semantic() -> dict:
    return _session.inspect_aria_labelledby_contract_semantic()

def inspect_aria_owns_contract_semantic() -> dict:
    return _session.inspect_aria_owns_contract_semantic()

def inspect_checkbox_contract_semantic() -> dict:
    return _session.inspect_checkbox_contract_semantic()

def inspect_switch_contract_semantic() -> dict:
    return _session.inspect_switch_contract_semantic()

def inspect_toggle_button_contract_semantic() -> dict:
    return _session.inspect_toggle_button_contract_semantic()

def inspect_expanded_contract_semantic() -> dict:
    return _session.inspect_expanded_contract_semantic()

def inspect_haspopup_contract_semantic() -> dict:
    return _session.inspect_haspopup_contract_semantic()

def inspect_activedescendant_contract_semantic() -> dict:
    return _session.inspect_activedescendant_contract_semantic()

def inspect_set_position_contract_semantic() -> dict:
    return _session.inspect_set_position_contract_semantic()

def inspect_virtual_grid_contract_semantic() -> dict:
    return _session.inspect_virtual_grid_contract_semantic()

def inspect_aria_level_contract_semantic() -> dict:
    return _session.inspect_aria_level_contract_semantic()

def inspect_svg_accessibility_contract_semantic() -> dict:
    return _session.inspect_svg_accessibility_contract_semantic()

def inspect_canvas_fallback_contract_semantic() -> dict:
    return _session.inspect_canvas_fallback_contract_semantic()

def inspect_media_caption_contract_semantic() -> dict:
    return _session.inspect_media_caption_contract_semantic()

def inspect_language_contract_semantic() -> dict:
    return _session.inspect_language_contract_semantic()

def inspect_direction_contract_semantic() -> dict:
    return _session.inspect_direction_contract_semantic()

def inspect_time_contract_semantic() -> dict:
    return _session.inspect_time_contract_semantic()

def inspect_canonical_url_contract_semantic() -> dict:
    return _session.inspect_canonical_url_contract_semantic()

def inspect_alternate_language_contract_semantic() -> dict:
    return _session.inspect_alternate_language_contract_semantic()

def inspect_base_url_contract_semantic() -> dict:
    return _session.inspect_base_url_contract_semantic()


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


def open_exact_table_row_details_semantic(name: str) -> dict:
    return _session.open_exact_table_row_details_semantic(name)


def verify_exact_table_row_tabs_semantic(
    name: str, tabs: list, tablist: str = None,
) -> dict:
    return _session.verify_exact_table_row_tabs_semantic(name, tabs, tablist)


def reset_case_context() -> dict:
    return _session.reset_case_context()


def close_browser_session():
    _session.close()


atexit.register(close_browser_session)

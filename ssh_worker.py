import re

import paramiko

from stands import (
    get_stand,
    mark_verified,
    mark_error,
)


MAX_LOG_CHARS = 16000


def _get_info(stand: str):
    info = get_stand(
        stand,
        include_password=True,
    )

    if not info:
        raise RuntimeError(
            f"Stand not found: {stand}"
        )

    if not info.get("has_ssh_credentials"):
        raise RuntimeError(
            f"SSH credentials missing: {stand}"
        )

    return info


def _connect(stand: str):
    info = _get_info(stand)

    client = paramiko.SSHClient()

    # MVP: новые стенды принимаем автоматически.
    # Позже добавим fingerprint/known_hosts.
    client.set_missing_host_key_policy(
        paramiko.AutoAddPolicy()
    )

    client.connect(
        hostname=info["ssh_host"],
        username=info["ssh_username"],
        password=info["ssh_password"],
        timeout=7,
        auth_timeout=7,
        banner_timeout=7,
        allow_agent=False,
        look_for_keys=False,
    )

    return client, info


def _redact(text: str, password: str | None = None):
    if not text:
        return ""

    if password:
        text = text.replace(
            password,
            "<redacted>",
        )

    text = re.sub(
        r'(?i)\bBearer\s+[A-Za-z0-9._~+/=-]+',
        'Bearer <redacted>',
        text,
    )

    text = re.sub(
        r'(?i)\bs_i=[^;\s]+',
        's_i=<redacted>',
        text,
    )

    text = re.sub(
        r'(?i)\b'
        r'(password|passwd|token|secret|authorization|cookie)'
        r'\s*[:=]\s*'
        r'([^\s,;]+)',
        r'\1=<redacted>',
        text,
    )

    return text


def _run(
    stand: str,
    command: str,
    sudo: bool = False,
    timeout: int = 20,
):
    client, info = _connect(stand)

    try:
        if sudo:
            command = (
                "sudo -S -p '' "
                + command
            )

        stdin, stdout, stderr = client.exec_command(
            command,
            timeout=timeout,
        )

        if sudo:
            stdin.write(
                info["ssh_password"] + "\n"
            )
            stdin.flush()

        out = stdout.read().decode(
            "utf-8",
            errors="replace",
        )

        err = stderr.read().decode(
            "utf-8",
            errors="replace",
        )

        code = stdout.channel.recv_exit_status()

        out = _redact(
            out,
            info["ssh_password"],
        )

        err = _redact(
            err,
            info["ssh_password"],
        )

        if code == 0:
            mark_verified(stand)
        else:
            mark_error(
                stand,
                f"Command exit={code}",
            )

        return {
            "exit_code": code,
            "stdout": out,
            "stderr": err,
        }

    finally:
        client.close()


def probe_stand(stand: str) -> dict:
    try:
        result = _run(
            stand,
            (
                'printf "HOST="; hostname; '
                'printf "USER="; whoami; '
                'printf "KERNEL="; uname -sr'
            ),
        )

        if result["exit_code"] != 0:
            return {
                "status": "probe_failed",
                "stand": stand,
                **result,
            }

        return {
            "status": "ok",
            "stand": stand,
            "output": result["stdout"].strip(),
        }

    except paramiko.AuthenticationException:
        mark_error(
            stand,
            "SSH authentication failed",
        )

        return {
            "status": "authentication_failed",
            "stand": stand,
        }

    except Exception as exc:
        mark_error(
            stand,
            str(exc),
        )

        return {
            "status": "connection_failed",
            "stand": stand,
            "error": str(exc)[:1000],
        }


def docker_ps(stand: str) -> dict:
    result = _run(
        stand,
        (
            "docker ps "
            "--format "
            "'{{.Names}}\\t{{.Image}}\\t{{.Status}}'"
        ),
        sudo=True,
    )

    containers = []

    if result["exit_code"] == 0:
        for line in result["stdout"].splitlines():
            parts = line.split(
                "\t",
                2,
            )

            if len(parts) != 3:
                continue

            name, image, status = parts

            containers.append(
                {
                    "name": name,
                    "image": image,
                    "status": status,
                }
            )

    return {
        "status": (
            "ok"
            if result["exit_code"] == 0
            else "error"
        ),
        "stand": stand,
        "exit_code": result["exit_code"],
        "containers": containers,
        "stderr": result["stderr"][:2000],
    }


def docker_logs(
    stand: str,
    container: str,
    since: str = "2m",
    tail: int = 200,
) -> dict:
    if not re.fullmatch(
        r"[A-Za-z0-9_.-]+",
        container,
    ):
        return {
            "status": "invalid_container",
            "container": container,
        }

    if not re.fullmatch(
        r"\d+[smhdw]",
        since,
    ):
        return {
            "status": "invalid_since",
            "since": since,
        }

    try:
        tail = int(tail)
    except Exception:
        return {
            "status": "invalid_tail",
            "tail": tail,
        }

    if tail < 1 or tail > 1000:
        return {
            "status": "invalid_tail",
            "tail": tail,
        }

    command = (
        "docker logs "
        "--timestamps "
        f"--since {since} "
        f"--tail {tail} "
        f"{container}"
    )

    result = _run(
        stand,
        command,
        sudo=True,
        timeout=30,
    )

    combined = ""

    if result["stdout"]:
        combined += result["stdout"]

    if result["stderr"]:
        if combined:
            combined += "\n"

        combined += result["stderr"]

    truncated = False

    if len(combined) > MAX_LOG_CHARS:
        combined = (
            "...<truncated, showing newest data>\n"
            + combined[-MAX_LOG_CHARS:]
        )
        truncated = True

    return {
        "status": (
            "ok"
            if result["exit_code"] == 0
            else "error"
        ),
        "stand": stand,
        "container": container,
        "since": since,
        "tail": tail,
        "exit_code": result["exit_code"],
        "logs": combined,
        "truncated": truncated,
    }


def find_backend_request(
    stand: str,
    container: str,
    method: str,
    endpoint_contains: str,
    query_contains=None,
    since: str = "2m",
    tail: int = 500,
    max_matches: int = 10,
) -> dict:
    """
    Ищет релевантные HTTP-запросы в Docker logs локально,
    чтобы не передавать LLM большой объём логов.
    """

    method = str(method).strip().upper()
    endpoint_contains = str(
        endpoint_contains
    ).strip()

    if not re.fullmatch(
        r"[A-Z]+",
        method,
    ):
        return {
            "status": "invalid_method",
            "method": method,
        }

    if not endpoint_contains:
        return {
            "status": "invalid_endpoint",
        }

    if query_contains is None:
        query_contains = []

    if isinstance(query_contains, str):
        query_contains = [
            query_contains
        ]

    if not isinstance(
        query_contains,
        (list, tuple),
    ):
        return {
            "status": "invalid_query_contains",
        }

    query_contains = [
        str(item).strip()
        for item in query_contains
        if str(item).strip()
    ]

    try:
        max_matches = int(max_matches)
    except Exception:
        return {
            "status": "invalid_max_matches",
        }

    if max_matches < 1 or max_matches > 20:
        return {
            "status": "invalid_max_matches",
            "max_matches": max_matches,
        }

    logs_result = docker_logs(
        stand=stand,
        container=container,
        since=since,
        tail=tail,
    )

    if logs_result.get("status") != "ok":
        return {
            "status": "log_read_failed",
            "stand": stand,
            "container": container,
            "details": logs_result,
        }

    matches = []

    method_needle = (
        f'"{method} '
    ).lower()

    endpoint_needle = (
        endpoint_contains.lower()
    )

    query_needles = [
        item.lower()
        for item in query_contains
    ]

    for line in logs_result.get(
        "logs",
        "",
    ).splitlines():

        lowered = line.lower()

        if method_needle not in lowered:
            continue

        if endpoint_needle not in lowered:
            continue

        if not all(
            needle in lowered
            for needle in query_needles
        ):
            continue

        matches.append(line)

    # Берём самые свежие совпадения.
    matches = matches[-max_matches:]

    return {
        "status": "ok",
        "stand": stand,
        "container": container,
        "method": method,
        "endpoint_contains": endpoint_contains,
        "query_contains": query_contains,
        "since": since,
        "scanned_tail": tail,
        "match_count": len(matches),
        "matches": matches,
        "correlation_note": (
            "Совпадения найдены по содержимому backend logs. "
            "Без общего request/correlation id это корреляция, "
            "а не абсолютное доказательство идентичности запросов."
        ),
    }


def detect_deployment_version(stand: str) -> dict:
    """
    Определяет активную версию Ansible-поставки U-Connect
    по install-state manifest на целевом стенде.

    Read-only.
    """

    source = (
        "/var/lib/uconnect/"
        "install-state/active-release.yml"
    )

    result = _run(
        stand,
        (
            "grep -E "
            "'^(product|product_version|"
            "desired_product_version|"
            "desired_state_digest|"
            "active_state_digest|partial):' "
            + source
        ),
        sudo=True,
    )

    if result["exit_code"] != 0:
        return {
            "status": "unknown",
            "stand": stand,
            "product_version": None,
            "source": source,
            "reason": "active_release_unavailable",
        }

    values = {}

    for line in result["stdout"].splitlines():
        if ":" not in line:
            continue

        key, value = line.split(":", 1)

        values[key.strip()] = value.strip()

    deployment_version = values.get(
        "product_version"
    )

    desired_deployment_version = values.get(
        "desired_product_version"
    )

    partial_raw = values.get(
        "partial"
    )

    if partial_raw is None:
        partial = None
    else:
        partial = (
            partial_raw.lower() == "true"
        )

    if not deployment_version:
        return {
            "status": "unknown",
            "stand": stand,
            "product": values.get("product"),
            "deployment_version": None,
            "source": source,
            "reason": "deployment_version_missing",
        }

    return {
        "status": "ok",
        "stand": stand,
        "product": values.get("product"),
        "deployment_version": deployment_version,
        "desired_deployment_version": (
            desired_deployment_version
        ),
        "partial": partial,
        "desired_state_digest": values.get(
            "desired_state_digest"
        ),
        "active_state_digest": values.get(
            "active_state_digest"
        ),
        "source": source,
    }


def detect_server_version(stand: str) -> dict:
    """
    Определяет версию серверной сборки U-Connect
    по Docker image tag контейнера u-backend.

    Read-only.
    """

    candidates = [
        "u_backend",
        "u-backend",
    ]

    for container in candidates:
        result = _run(
            stand,
            (
                "docker inspect "
                + container
                + " --format '{{.Config.Image}}'"
            ),
            sudo=True,
        )

        if result["exit_code"] != 0:
            continue

        image = result["stdout"].strip()

        if not image:
            continue

        if ":" not in image:
            return {
                "status": "unknown",
                "stand": stand,
                "container": container,
                "image": image,
                "server_version": None,
                "reason": "image_tag_missing",
            }

        tag = image.rsplit(":", 1)[1].strip()

        if not tag:
            return {
                "status": "unknown",
                "stand": stand,
                "container": container,
                "image": image,
                "server_version": None,
                "reason": "image_tag_empty",
            }

        return {
            "status": "ok",
            "stand": stand,
            "container": container,
            "image": image,
            "server_version": tag,
            "source": "u-backend_image_tag",
        }

    return {
        "status": "unknown",
        "stand": stand,
        "server_version": None,
        "reason": "u_backend_container_not_found",
    }


def detect_installation_architecture(stand: str) -> dict:
    """
    Определяет архитектуру установки U-Connect.

    ansible:
        присутствует install-state active-release.yml

    legacy:
        install-state отсутствует, но найден runtime u-backend
    """

    ansible_check = _run(
        stand,
        (
            "test -f "
            "/var/lib/uconnect/install-state/"
            "active-release.yml"
        ),
        sudo=False,
    )

    if ansible_check["exit_code"] == 0:
        return {
            "status": "ok",
            "stand": stand,
            "installation_architecture": "ansible",
            "source": (
                "/var/lib/uconnect/install-state/"
                "active-release.yml"
            ),
        }

    server = detect_server_version(stand)

    if server.get("status") == "ok":
        return {
            "status": "ok",
            "stand": stand,
            "installation_architecture": "legacy",
            "source": (
                "ansible_release_state_absent_"
                "and_u_backend_present"
            ),
        }

    return {
        "status": "unknown",
        "stand": stand,
        "installation_architecture": None,
        "reason": "installation_architecture_not_detected",
    }


def detect_stand_identity(stand: str) -> dict:
    """
    Собирает единый runtime-паспорт стенда U-Connect.
    """

    architecture = detect_installation_architecture(
        stand
    )

    server = detect_server_version(
        stand
    )

    result = {
        "status": "ok",
        "stand": stand,
        "installation_architecture": (
            architecture.get(
                "installation_architecture"
            )
        ),
        "server_version": server.get(
            "server_version"
        ),
        "server_version_source": server.get(
            "source"
        ),
    }

    if architecture.get("status") != "ok":
        result["status"] = "partial"

    if server.get("status") != "ok":
        result["status"] = "partial"

    if (
        architecture.get(
            "installation_architecture"
        )
        == "ansible"
    ):
        deployment = detect_deployment_version(
            stand
        )

        result["deployment_version"] = (
            deployment.get(
                "deployment_version"
            )
        )

        result[
            "desired_deployment_version"
        ] = deployment.get(
            "desired_deployment_version"
        )

        result["deployment_partial"] = (
            deployment.get("partial")
        )

        result[
            "deployment_version_source"
        ] = deployment.get("source")

        result[
            "desired_state_digest"
        ] = deployment.get(
            "desired_state_digest"
        )

        result[
            "active_state_digest"
        ] = deployment.get(
            "active_state_digest"
        )

        if deployment.get("status") != "ok":
            result["status"] = "partial"

    else:
        result["deployment_version"] = None
        result[
            "desired_deployment_version"
        ] = None
        result["deployment_partial"] = None
        result[
            "deployment_version_source"
        ] = None

    return result

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from cryptography.fernet import Fernet


STANDS_FILE = Path(
    os.getenv(
        "UQA_STANDS_FILE",
        "/opt/uqa/state/stands.json",
    )
)

KEY_FILE = Path(
    os.getenv(
        "UQA_STAND_KEY_FILE",
        "/opt/uqa/secrets/stand_store.key",
    )
)


def _now():
    return datetime.now(timezone.utc).isoformat()


def normalize_stand(value: str) -> str:
    value = value.strip()

    # URL/hostname часто приходит из обычного предложения:
    # "проверь https://uc.lab.local."
    # Конечная пунктуация не является частью имени стенда.
    value = value.rstrip(".,;:!?)]}>\\\"'")

    if not value:
        raise ValueError("Stand cannot be empty")

    if "://" in value:
        parsed = urlparse(value)
        host = parsed.hostname
    else:
        parsed = urlparse("//" + value)
        host = parsed.hostname

    if host:
        return host.lower()

    return value.lower()


def _ensure_storage():
    STANDS_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    KEY_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )


    if not KEY_FILE.exists():
        KEY_FILE.write_bytes(
            Fernet.generate_key()
        )
        os.chmod(KEY_FILE, 0o640)

    if not STANDS_FILE.exists():
        STANDS_FILE.write_text(
            "{}",
            encoding="utf-8",
        )
        os.chmod(STANDS_FILE, 0o660)


def _fernet():
    _ensure_storage()

    key = KEY_FILE.read_bytes().strip()
    return Fernet(key)


def _load():
    _ensure_storage()

    try:
        data = json.loads(
            STANDS_FILE.read_text(
                encoding="utf-8"
            )
        )
    except Exception:
        data = {}

    if not isinstance(data, dict):
        raise RuntimeError(
            "Invalid stands database format"
        )

    return data


def _save(data):
    tmp = STANDS_FILE.with_suffix(".tmp")

    tmp.write_text(
        json.dumps(
            data,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    os.chmod(tmp, 0o660)
    tmp.replace(STANDS_FILE)
    os.chmod(STANDS_FILE, 0o660)


def save_credentials(
    stand: str,
    username: str,
    password: str,
    ssh_host: str | None = None,
    web_url: str | None = None,
):
    stand_id = normalize_stand(stand)

    if not username.strip():
        raise ValueError("Username cannot be empty")

    if not password:
        raise ValueError("Password cannot be empty")

    if ssh_host is None:
        ssh_host = stand_id

    data = _load()

    existing = data.get(
        stand_id,
        {},
    )

    encrypted_password = (
        _fernet()
        .encrypt(
            password.encode("utf-8")
        )
        .decode("ascii")
    )

    data[stand_id] = {
        "stand_id": stand_id,
        "aliases": existing.get("aliases", []),
        "web_url": (
            web_url
            or existing.get("web_url")
            or (
                stand
                if "://" in stand
                else f"https://{stand_id}"
            )
        ),
        "ssh_host": ssh_host,
        "ssh_username": username.strip(),
        "ssh_password_enc": encrypted_password,
        "created_at": existing.get(
            "created_at",
            _now(),
        ),
        "updated_at": _now(),
        "last_verified_at": existing.get(
            "last_verified_at"
        ),
        "last_error": None,
    }

    _save(data)

    return get_stand(stand_id)


def _normalize_alias(alias: str) -> str:
    alias = str(alias).strip().lower()
    alias = alias.rstrip(".,;:!?)]}>\\\"'")

    if not alias:
        raise ValueError("Alias cannot be empty")

    return alias


def resolve_stand(value: str):
    candidate = normalize_stand(value)
    data = _load()

    # Сначала canonical stand_id.
    if candidate in data:
        return candidate

    # Потом aliases.
    candidate_alias = _normalize_alias(value)

    for stand_id, item in data.items():
        aliases = item.get("aliases", [])

        for alias in aliases:
            if _normalize_alias(alias) == candidate_alias:
                return stand_id

    return None


def add_alias(stand: str, alias: str):
    stand_id = resolve_stand(stand)

    if stand_id is None:
        stand_id = normalize_stand(stand)

    data = _load()

    if stand_id not in data:
        return False

    alias = _normalize_alias(alias)

    # Не разрешаем алиасу затереть другой canonical stand.
    if alias in data and alias != stand_id:
        raise ValueError(
            f"Alias conflicts with existing stand: {alias}"
        )

    # Не разрешаем один alias назначить двум стендам.
    for other_id, item in data.items():
        if other_id == stand_id:
            continue

        other_aliases = [
            _normalize_alias(value)
            for value in item.get("aliases", [])
        ]

        if alias in other_aliases:
            raise ValueError(
                f"Alias already belongs to {other_id}: {alias}"
            )

    aliases = [
        _normalize_alias(value)
        for value in data[stand_id].get("aliases", [])
    ]

    if alias not in aliases:
        aliases.append(alias)

    data[stand_id]["aliases"] = aliases
    data[stand_id]["updated_at"] = _now()

    _save(data)

    return True


def get_stand(
    stand: str,
    include_password: bool = False,
):
    stand_id = resolve_stand(stand)

    if stand_id is None:
        return None

    data = _load()
    item = data.get(stand_id)

    if item is None:
        return None

    result = {
        key: value
        for key, value in item.items()
        if key != "ssh_password_enc"
    }

    result["has_ssh_credentials"] = bool(
        item.get("ssh_username")
        and item.get("ssh_password_enc")
    )

    if include_password:
        token = item.get(
            "ssh_password_enc"
        )

        if token:
            password = (
                _fernet()
                .decrypt(
                    token.encode("ascii")
                )
                .decode("utf-8")
            )

            result["ssh_password"] = password

    return result


def has_credentials(stand: str) -> bool:
    item = get_stand(stand)

    return bool(
        item
        and item.get(
            "has_ssh_credentials"
        )
    )


def mark_verified(stand: str):
    stand_id = normalize_stand(stand)
    data = _load()

    if stand_id not in data:
        return False

    data[stand_id][
        "last_verified_at"
    ] = _now()

    data[stand_id][
        "last_error"
    ] = None

    _save(data)
    return True


def mark_error(
    stand: str,
    error: str,
):
    stand_id = normalize_stand(stand)
    data = _load()

    if stand_id not in data:
        return False

    data[stand_id][
        "last_error"
    ] = str(error)[:500]

    _save(data)
    return True


def delete_stand(stand: str):
    stand_id = normalize_stand(stand)
    data = _load()

    if stand_id not in data:
        return False

    del data[stand_id]
    _save(data)

    return True


def list_stands():
    data = _load()

    result = []

    for stand_id in sorted(data):
        item = get_stand(stand_id)

        if item:
            result.append(item)

    return result

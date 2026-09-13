from urllib.parse import parse_qsl, urlsplit
import hashlib
import json
from job_store import (
    get_job,
    upsert_candidate_fact,
)


def _make_fact_key(
    fact_type,
    ui_path,
    ui_action,
    ui_field,
    api_method,
    api_endpoint,
    query_parameter,
):
    identity = {
        "fact_type": fact_type,
        "ui_path": ui_path,
        "ui_action": ui_action,
        "ui_field": ui_field,
        "api_method": api_method,
        "api_endpoint": api_endpoint,
        "query_parameter": query_parameter,
    }

    raw = json.dumps(
        identity,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )

    digest = hashlib.sha256(
        raw.encode("utf-8")
    ).hexdigest()[:20]

    return (
        f"{fact_type}:{digest}"
    )



def _make_subject_key(
    fact_type,
    ui_path,
    ui_action,
    ui_field,
):
    """
    Идентичность предмета знания,
    независимо от конкретной API-реализации.
    """

    identity = {
        "ui_path": ui_path,
        "ui_action": ui_action,
        "ui_field": ui_field,
    }

    raw = json.dumps(
        identity,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )

    digest = hashlib.sha256(
        raw.encode("utf-8")
    ).hexdigest()[:20]

    return (
        f"{fact_type}_subject:{digest}"
    )


def _find_case(
    job,
    case_id,
):
    for case in job.get(
        "test_cases",
        []
    ):
        if case.get("case_id") == case_id:
            return case

    return None


def _normalized_api_endpoint(
    api_path,
    backend_observations,
    method,
):
    api_path = str(
        api_path or ""
    )

    method = str(
        method or ""
    ).upper()

    for obs in backend_observations:
        data = obs.get(
            "data",
            {}
        )

        backend_method = str(
            data.get("method")
            or ""
        ).upper()

        endpoint = str(
            data.get("endpoint")
            or ""
        )

        if (
            backend_method == method
            and endpoint
            and api_path.endswith(
                endpoint
            )
        ):
            return endpoint

    return api_path



def evaluate_claim_in_ui_observation(
    claim,
    ui_observation,
):
    """
    Read-only проверка конкретного API claim
    в network window конкретного UI action.

    Возвращает:
      observed
      absent_in_closed_window
      indeterminate
    """

    if not isinstance(ui_observation, dict):
        return {
            "decision": "indeterminate",
            "reason": "ui_observation_missing",
        }

    if ui_observation.get("type") == "ui_state":
        ui = ui_observation.get("data", {})
    else:
        ui = ui_observation

    execution_id = ui.get("action_execution_id")

    if not execution_id:
        return {
            "decision": "indeterminate",
            "reason": "action_execution_id_missing",
        }

    if ui.get("network_window_closed") is not True:
        return {
            "decision": "indeterminate",
            "reason": "network_window_not_closed",
            "action_execution_id": execution_id,
        }

    if (
        ui.get("network_capture_scope")
        != "fetch_xhr_until_capture_state"
    ):
        return {
            "decision": "indeterminate",
            "reason": "unsupported_network_capture_scope",
            "action_execution_id": execution_id,
        }

    if "network_requests" not in ui:
        return {
            "decision": "indeterminate",
            "reason": "network_requests_missing",
            "action_execution_id": execution_id,
        }

    requests = ui.get("network_requests") or []

    claim_method = str(
        claim.get("api_method") or ""
    ).upper()

    claim_endpoint = str(
        claim.get("api_endpoint") or ""
    )

    claim_parameter = claim.get(
        "query_parameter"
    )

    if not claim_method or not claim_endpoint:
        return {
            "decision": "indeterminate",
            "reason": "claim_incomplete",
            "action_execution_id": execution_id,
        }

    examined_request_ids = []
    matched_request_ids = []

    for request in requests:
        if (
            request.get("action_execution_id")
            != execution_id
        ):
            continue

        request_id = request.get("request_id")

        if request_id:
            examined_request_ids.append(
                request_id
            )

        method = str(
            request.get("method") or ""
        ).upper()

        if method != claim_method:
            continue

        raw_url = str(
            request.get("url") or ""
        )

        parsed = urlsplit(raw_url)

        request_path = (
            parsed.path
            or raw_url.split("?", 1)[0]
        )

        if not (
            request_path == claim_endpoint
            or request_path.endswith(
                claim_endpoint
            )
        ):
            continue

        if claim_parameter:
            query_keys = {
                key
                for key, _ in parse_qsl(
                    parsed.query,
                    keep_blank_values=True,
                )
            }

            if claim_parameter not in query_keys:
                continue

        if request_id:
            matched_request_ids.append(
                request_id
            )

    if matched_request_ids:
        return {
            "decision": "observed",
            "action_execution_id": execution_id,
            "claim": {
                "api_method": claim_method,
                "api_endpoint": claim_endpoint,
                "query_parameter": claim_parameter,
            },
            "matched_request_ids": matched_request_ids,
            "examined_request_ids": examined_request_ids,
        }

    return {
        "decision": "absent_in_closed_window",
        "action_execution_id": execution_id,
        "claim": {
            "api_method": claim_method,
            "api_endpoint": claim_endpoint,
            "query_parameter": claim_parameter,
        },
        "matched_request_ids": [],
        "examined_request_ids": examined_request_ids,
        "network_request_count": len(requests),
        "capture_scope": ui.get(
            "network_capture_scope"
        ),
    }

def _match_backend(
    api_path,
    method,
    backend_observations,
):
    method = str(
        method or ""
    ).upper()

    for obs in backend_observations:
        data = obs.get(
            "data",
            {}
        )

        endpoint = str(
            data.get("endpoint")
            or ""
        )

        backend_method = str(
            data.get("method")
            or ""
        ).upper()

        match_count = (
            data.get("match_count")
            or 0
        )

        if (
            backend_method == method
            and endpoint
            and str(api_path).endswith(
                endpoint
            )
            and match_count > 0
        ):
            return obs

    return None


def _documentation_support(
    endpoint,
    query_parameter,
    documentation_observations,
):
    endpoint = str(
        endpoint or ""
    ).casefold()

    query_parameter = str(
        query_parameter or ""
    ).casefold()

    endpoint_supported = False
    query_parameter_supported = False
    same_reference_supported = False

    for obs in documentation_observations:
        refs = (
            obs.get("data", {})
            .get("references", [])
        )

        for ref in refs:
            content = str(
                ref.get(
                    "content_excerpt"
                )
                or ""
            ).casefold()

            has_endpoint = bool(
                endpoint
                and endpoint in content
            )

            has_query_parameter = bool(
                query_parameter
                and query_parameter in content
            )

            if has_endpoint:
                endpoint_supported = True

            if has_query_parameter:
                query_parameter_supported = True

            if (
                has_endpoint
                and has_query_parameter
            ):
                same_reference_supported = True

    return {
        "api_endpoint": endpoint_supported,
        "query_parameter": (
            query_parameter_supported
        ),
        "same_reference": (
            same_reference_supported
        ),
    }


def _find_previous_ui_action(
    observations,
    api_index,
):
    """
    Связывает api_exchange с UI action.

    Новые observations:
    строго по action_execution_id.

    Старые исторические observations,
    где execution id ещё не существовал:
    fallback на предыдущий semantic action.
    """

    api_obs = observations[api_index]

    api_data = api_obs.get(
        "data",
        {},
    )

    execution_id = api_data.get(
        "action_execution_id"
    )

    # Новый доказательный путь.
    if execution_id:
        for index in range(
            api_index - 1,
            -1,
            -1,
        ):
            obs = observations[index]

            if obs.get("type") != "ui_state":
                continue

            data = obs.get(
                "data",
                {},
            )

            if (
                data.get(
                    "action_execution_id"
                )
                != execution_id
            ):
                continue

            action = data.get(
                "action"
            )

            if action in {
                "fill-semantic",
                "click-semantic",
            }:
                return obs

        # В новом формате нельзя тихо
        # привязывать API к другому action.
        return None

    # Legacy fallback для старых Job.
    for index in range(
        api_index - 1,
        -1,
        -1,
    ):
        obs = observations[index]

        if obs.get("type") != "ui_state":
            continue

        data = obs.get(
            "data",
            {},
        )

        action = data.get(
            "action"
        )

        if action in {
            "fill-semantic",
            "click-semantic",
        }:
            return obs

    return None


def generate_candidate_facts_for_case(
    job_id,
    case_id,
):
    job = get_job(job_id)

    if job is None:
        raise FileNotFoundError(
            job_id
        )

    case = _find_case(
        job,
        case_id,
    )

    if case is None:
        raise FileNotFoundError(
            case_id
        )

    # Пока кандидатные продуктовые факты
    # строим только из успешного тест-кейса.
    if case.get("status") != "passed":
        return []

    observations = case.get(
        "observations",
        []
    )

    documentation = [
        obs
        for obs in observations
        if obs.get("type")
        == "documentation_search"
    ]

    backend = [
        obs
        for obs in observations
        if obs.get("type")
        == "backend_request"
    ]

    created = []

    for api_index, api_obs in enumerate(
        observations
    ):
        if api_obs.get(
            "type"
        ) != "api_exchange":
            continue

        api = api_obs.get(
            "data",
            {}
        )

        method = api.get(
            "method"
        )

        api_path = api.get(
            "path"
        )

        query = api.get(
            "query"
        ) or {}

        ui_obs = _find_previous_ui_action(
            observations,
            api_index,
        )

        if ui_obs is None:
            continue

        ui = ui_obs.get(
            "data",
            {}
        )

        ui_input = ui.get(
            "input"
        ) or {}

        field = ui_input.get(
            "field"
        )

        input_text = ui_input.get(
            "text"
        )

        query_parameter = None

        if input_text is not None:
            for key, value in query.items():
                if str(value) == str(
                    input_text
                ):
                    query_parameter = key
                    break

        backend_obs = _match_backend(
            api_path,
            method,
            backend,
        )

        normalized_endpoint = (
            _normalized_api_endpoint(
                api_path,
                backend,
                method,
            )
        )

        docs_support = (
            _documentation_support(
                normalized_endpoint,
                query_parameter,
                documentation,
            )
        )

        backend_supported = (
            backend_obs is not None
        )

        source_ids = [
            ui_obs.get(
                "observation_id"
            ),
            api_obs.get(
                "observation_id"
            ),
        ]

        if backend_obs:
            source_ids.append(
                backend_obs.get(
                    "observation_id"
                )
            )

        if (
            docs_support["api_endpoint"]
            or docs_support["query_parameter"]
        ):
            for doc_obs in documentation:
                source_ids.append(
                    doc_obs.get(
                        "observation_id"
                    )
                )

        source_ids = [
            item
            for item in source_ids
            if item
        ]

        statement_parts = [
            f"UI action on {ui.get('path')}",
        ]

        if field:
            statement_parts.append(
                f"field '{field}'"
            )

        statement_parts.append(
            f"uses {method} "
            f"{normalized_endpoint}"
        )

        if query_parameter:
            statement_parts.append(
                f"with query parameter "
                f"'{query_parameter}'"
            )

        statement = " ".join(
            statement_parts
        )

        subject_key = _make_subject_key(
            fact_type="ui_api_binding",
            ui_path=ui.get("path"),
            ui_action=ui.get("action"),
            ui_field=field,
        )

        fact_key = _make_fact_key(
            fact_type="ui_api_binding",
            ui_path=ui.get("path"),
            ui_action=ui.get("action"),
            ui_field=field,
            api_method=method,
            api_endpoint=normalized_endpoint,
            query_parameter=query_parameter,
        )

        candidate = upsert_candidate_fact(
            job_id=job_id,
            case_id=case_id,
            fact_key=fact_key,
            fact_type="ui_api_binding",
            subject_key=subject_key,
            statement=statement,
            data={
                "ui_path": ui.get(
                    "path"
                ),
                "ui_action": ui.get(
                    "action"
                ),
                "ui_field": field,
                "api_method": method,
                "api_endpoint": (
                    normalized_endpoint
                ),
                "query_parameter": (
                    query_parameter
                ),
                "backend_container": (
                    backend_obs
                    .get("data", {})
                    .get("container")
                    if backend_obs
                    else None
                ),
            },
            source_observation_ids=(
                source_ids
            ),
            verification={
                "runtime_ui_action_observed": True,
                "runtime_api_exchange_observed": True,
                "backend_request_correlated": (
                    backend_supported
                ),
                "documentation_api_endpoint_supported": (
                    docs_support[
                        "api_endpoint"
                    ]
                ),
                "documentation_query_parameter_supported": (
                    docs_support[
                        "query_parameter"
                    ]
                ),
                "documentation_same_reference_supported": (
                    docs_support[
                        "same_reference"
                    ]
                ),
                # Пока не утверждаем, что руководство
                # напрямую документирует именно связь
                # этого UI-поля с этим API.
                "documentation_ui_binding_supported": False,
            },
        )

        created.append(
            candidate
        )

    return created

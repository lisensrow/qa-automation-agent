import json

from product_knowledge_store import (
    _connect,
    migrate_fact_scopes_schema,
    set_fact_scope_status,
)


RUNTIME_FLAGS_UI_API_BINDING = (
    "runtime_ui_action_observed",
    "runtime_api_exchange_observed",
    "backend_request_correlated",
)

DOC_FLAGS_UI_API_BINDING = (
    "documentation_api_endpoint_supported",
    "documentation_query_parameter_supported",
    "documentation_same_reference_supported",
)


def _all_true(data, keys):
    return all(
        data.get(key) is True
        for key in keys
    )


def evaluate_ui_api_binding_scope(
    fact_key: str,
    installation_architecture: str,
    server_version: str,
):
    """
    Read-only validator.

    Ничего в Product Knowledge не изменяет.
    Только решает, достаточно ли evidence
    для candidate -> verified.
    """

    migrate_fact_scopes_schema()

    installation_architecture = (
        str(installation_architecture)
        .strip()
        .lower()
    )

    server_version = (
        str(server_version)
        .strip()
    )

    with _connect() as conn:
        fact = conn.execute(
            """
            SELECT
                fact_key,
                fact_type,
                statement
            FROM facts
            WHERE fact_key = ?
            """,
            (fact_key,),
        ).fetchone()

        if fact is None:
            return {
                "decision": "not_found",
                "fact_key": fact_key,
            }

        if fact["fact_type"] != "ui_api_binding":
            return {
                "decision": "unsupported_fact_type",
                "fact_key": fact_key,
                "fact_type": fact["fact_type"],
            }

        scope = conn.execute(
            """
            SELECT *
            FROM fact_scopes
            WHERE fact_key = ?
              AND installation_architecture = ?
              AND server_version = ?
            """,
            (
                fact_key,
                installation_architecture,
                server_version,
            ),
        ).fetchone()

        if scope is None:
            return {
                "decision": "scope_not_found",
                "fact_key": fact_key,
                "installation_architecture":
                    installation_architecture,
                "server_version":
                    server_version,
            }

        rows = conn.execute(
            """
            SELECT
                job_id,
                case_id,
                stand,
                deployment_version,
                verification_json,
                source_observation_ids_json,
                created_at
            FROM confirmations
            WHERE fact_key = ?
              AND installation_architecture = ?
              AND server_version = ?
            ORDER BY created_at
            """,
            (
                fact_key,
                installation_architecture,
                server_version,
            ),
        ).fetchall()

    confirmations = []

    for row in rows:
        verification = json.loads(
            row["verification_json"]
        )

        source_ids = json.loads(
            row["source_observation_ids_json"]
        )

        runtime_flags_ok = _all_true(
            verification,
            RUNTIME_FLAGS_UI_API_BINDING,
        )

        # Для ui_api_binding ожидаем как минимум
        # UI + API + backend observation.
        traceable = (
            isinstance(source_ids, list)
            and len(set(source_ids)) >= 3
        )

        runtime_ok = (
            runtime_flags_ok
            and traceable
        )

        docs_ok = _all_true(
            verification,
            DOC_FLAGS_UI_API_BINDING,
        )

        confirmations.append(
            {
                "job_id": row["job_id"],
                "case_id": row["case_id"],
                "stand": row["stand"],
                "deployment_version":
                    row["deployment_version"],
                "created_at": row["created_at"],
                "runtime_ok": runtime_ok,
                "docs_ok": docs_ok,
                "source_observation_count":
                    len(source_ids),
                "source_observation_ids":
                    list(source_ids),
            }
        )

    strong_runtime = [
        item
        for item in confirmations
        if item["runtime_ok"]
    ]

    distinct_jobs = {
        item["job_id"]
        for item in strong_runtime
        if item["job_id"]
    }

    distinct_stands = {
        item["stand"]
        for item in strong_runtime
        if item["stand"]
    }

    docs_supported = [
        item
        for item in strong_runtime
        if item["docs_ok"]
    ]

    repeated_runtime = (
        len(distinct_jobs) >= 2
    )

    docs_corroborated = (
        len(docs_supported) >= 1
    )

    cross_stand_runtime = (
        len(distinct_stands) >= 2
    )

    eligible = (
        repeated_runtime
        and (
            docs_corroborated
            or cross_stand_runtime
        )
    )

    if eligible:
        if docs_corroborated:
            route = (
                "repeated_runtime_plus_docs"
            )
        else:
            route = (
                "cross_stand_runtime"
            )

        decision = (
            "eligible_for_verified"
        )

    else:
        route = None
        decision = "keep_candidate"

    reasons = []

    if not repeated_runtime:
        reasons.append(
            "need_at_least_2_distinct_jobs_with_strong_runtime"
        )

    if (
        repeated_runtime
        and not docs_corroborated
        and not cross_stand_runtime
    ):
        reasons.append(
            "need_docs_corroboration_or_second_stand"
        )

    return {
        "validator_policy":
            "ui_api_binding_v1",
        "policy_version": 1,
        "decision": decision,
        "route": route,
        "fact_key": fact_key,
        "fact_type": fact["fact_type"],
        "statement": fact["statement"],
        "scope": {
            "installation_architecture":
                installation_architecture,
            "server_version":
                server_version,
            "current_status":
                scope["status"],
        },
        "metrics": {
            "scoped_confirmations":
                len(confirmations),
            "strong_runtime_confirmations":
                len(strong_runtime),
            "distinct_jobs":
                len(distinct_jobs),
            "distinct_stands":
                len(distinct_stands),
            "docs_corroborated_confirmations":
                len(docs_supported),
        },
        "reasons": reasons,
        "confirmations": confirmations,
    }



def promote_ui_api_binding_scope_if_eligible(
    fact_key: str,
    installation_architecture: str,
    server_version: str,
):
    """
    Безопасная автоматическая promotion.

    Может делать только:
        candidate -> verified

    Никогда автоматически не меняет:
        verified
        conflict
        deprecated

    Решение и supporting evidence полностью
    сохраняются в status history.
    """

    decision = evaluate_ui_api_binding_scope(
        fact_key=fact_key,
        installation_architecture=(
            installation_architecture
        ),
        server_version=server_version,
    )

    if decision.get(
        "decision"
    ) != "eligible_for_verified":
        return {
            "action": "keep_candidate",
            "changed": False,
            "decision": decision,
        }

    scope = decision.get(
        "scope"
    ) or {}

    current_status = scope.get(
        "current_status"
    )

    if current_status == "verified":
        return {
            "action": "already_verified",
            "changed": False,
            "decision": decision,
        }

    if current_status in (
        "conflict",
        "deprecated",
    ):
        return {
            "action": (
                "promotion_blocked_by_status"
            ),
            "changed": False,
            "current_status":
                current_status,
            "decision": decision,
        }

    if current_status != "candidate":
        return {
            "action": (
                "promotion_blocked_unknown_status"
            ),
            "changed": False,
            "current_status":
                current_status,
            "decision": decision,
        }

    result = set_fact_scope_status(
        fact_key=fact_key,
        installation_architecture=(
            installation_architecture
        ),
        server_version=server_version,
        status="verified",
        source="validator",
        reason=(
            "ui_api_binding_v1: "
            + str(
                decision.get("route")
            )
        ),
        decision=decision,
    )

    return {
        "action": "promoted",
        "changed": bool(
            result.get("changed")
        ),
        "event_id": result.get(
            "event_id"
        ),
        "status": result.get(
            "status"
        ),
        "decision": decision,
    }


def promote_candidate_scope_if_eligible(
    fact_key: str,
    fact_type: str,
    installation_architecture: str,
    server_version: str,
):
    """
    Общая точка входа автоматического validator/promotion.

    Пока поддерживается только:
        ui_api_binding

    Неизвестные типы фактов безопасно пропускаются.
    """

    if fact_type == "ui_api_binding":
        return (
            promote_ui_api_binding_scope_if_eligible(
                fact_key=fact_key,
                installation_architecture=(
                    installation_architecture
                ),
                server_version=server_version,
            )
        )

    return {
        "action": "unsupported_fact_type",
        "changed": False,
        "fact_key": fact_key,
        "fact_type": fact_type,
    }


def evaluate_subject_claims(
    subject_key: str,
    installation_architecture: str,
    server_version: str,
):
    """
    Анализирует разные claims одного subject
    в одном version scope.

    ВАЖНО:
    несколько fact_key != автоматический conflict.

    Эта функция read-only.
    """

    migrate_fact_scopes_schema()

    installation_architecture = (
        str(installation_architecture)
        .strip()
        .lower()
    )

    server_version = (
        str(server_version)
        .strip()
    )

    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT
                f.fact_key,
                f.fact_type,
                f.subject_key,
                f.statement,
                f.data_json,
                s.status
            FROM facts AS f
            JOIN fact_scopes AS s
              ON s.fact_key = f.fact_key
            WHERE f.subject_key = ?
              AND s.installation_architecture = ?
              AND s.server_version = ?
            ORDER BY f.fact_key
            """,
            (
                subject_key,
                installation_architecture,
                server_version,
            ),
        ).fetchall()

        claims = []

        for row in rows:
            data = json.loads(
                row["data_json"]
            )

            confirmations = conn.execute(
                """
                SELECT
                    job_id,
                    case_id,
                    stand,
                    deployment_version
                FROM confirmations
                WHERE fact_key = ?
                  AND installation_architecture = ?
                  AND server_version = ?
                ORDER BY created_at
                """,
                (
                    row["fact_key"],
                    installation_architecture,
                    server_version,
                ),
            ).fetchall()

            job_ids = sorted({
                item["job_id"]
                for item in confirmations
                if item["job_id"]
            })

            claims.append(
                {
                    "fact_key":
                        row["fact_key"],
                    "status":
                        row["status"],
                    "statement":
                        row["statement"],
                    "claim": {
                        "api_method":
                            data.get(
                                "api_method"
                            ),
                        "api_endpoint":
                            data.get(
                                "api_endpoint"
                            ),
                        "query_parameter":
                            data.get(
                                "query_parameter"
                            ),
                    },
                    "confirmation_count":
                        len(confirmations),
                    "job_ids":
                        job_ids,
                }
            )

    if not claims:
        return {
            "decision":
                "subject_scope_not_found",
            "subject_key":
                subject_key,
            "claim_count": 0,
            "claims": [],
        }

    if len(claims) == 1:
        return {
            "decision":
                "single_claim",
            "subject_key":
                subject_key,
            "claim_count": 1,
            "claims":
                claims,
            "requires_review":
                False,
        }

    pair_analysis = []

    for index, left in enumerate(
        claims
    ):
        for right in claims[
            index + 1:
        ]:
            left_jobs = set(
                left["job_ids"]
            )

            right_jobs = set(
                right["job_ids"]
            )

            shared_jobs = sorted(
                left_jobs
                & right_jobs
            )

            pair_analysis.append(
                {
                    "left_fact_key":
                        left["fact_key"],
                    "right_fact_key":
                        right["fact_key"],
                    "same_claim":
                        left["claim"]
                        == right["claim"],
                    "shared_jobs":
                        shared_jobs,
                    "coobserved":
                        bool(shared_jobs),
                }
            )

    coobserved_pairs = [
        item
        for item in pair_analysis
        if item["coobserved"]
    ]

    competing_pairs = [
        item
        for item in pair_analysis
        if (
            not item["coobserved"]
            and not item["same_claim"]
        )
    ]

    if competing_pairs:
        decision = (
            "potential_competing_claims"
        )
        requires_review = True

    else:
        decision = (
            "multiple_coexisting_claims"
        )
        requires_review = False

    return {
        "decision": decision,
        "subject_key": subject_key,
        "scope": {
            "installation_architecture":
                installation_architecture,
            "server_version":
                server_version,
        },
        "claim_count":
            len(claims),
        "coobserved_pair_count":
            len(coobserved_pairs),
        "competing_pair_count":
            len(competing_pairs),
        "requires_review":
            requires_review,
        "claims":
            claims,
        "pair_analysis":
            pair_analysis,
    }


# ============================================================
# Conflict Detection v1
# ============================================================

def _conflict_json_dict(raw):
    if isinstance(raw, dict):
        return raw

    try:
        value = json.loads(raw or "{}")
    except Exception:
        return {}

    return value if isinstance(value, dict) else {}


def _conflict_json_list(raw):
    if isinstance(raw, list):
        return raw

    try:
        value = json.loads(raw or "[]")
    except Exception:
        return []

    return value if isinstance(value, list) else []


def _conflict_parse_time(value):
    from datetime import datetime

    if not value:
        return None

    try:
        return datetime.fromisoformat(
            str(value).replace(
                "Z",
                "+00:00",
            )
        )
    except Exception:
        return None


def _conflict_is_after(
    value,
    threshold,
):
    left = _conflict_parse_time(
        value
    )

    right = _conflict_parse_time(
        threshold
    )

    if (
        left is not None
        and right is not None
    ):
        return left > right

    return str(value or "") > str(
        threshold or ""
    )


def _conflict_find_ui_observation(
    job_id,
    case_id,
    source_observation_ids,
):
    """
    Находит именно тот ui_state,
    который использовался как evidence
    конкретного candidate confirmation.
    """

    from job_store import get_job

    job = get_job(job_id)

    if not job:
        return None

    case = None

    for item in job.get(
        "test_cases",
        [],
    ):
        if (
            item.get("case_id")
            == case_id
        ):
            case = item
            break

    if case is None:
        return None

    source_ids = set(
        source_observation_ids or []
    )

    candidates = []

    for obs in case.get(
        "observations",
        [],
    ):
        if (
            obs.get("type")
            != "ui_state"
        ):
            continue

        if (
            obs.get("observation_id")
            not in source_ids
        ):
            continue

        candidates.append(obs)

    # Новый доказательный формат
    # всегда предпочтительнее legacy.
    for obs in candidates:
        data = obs.get(
            "data",
            {},
        )

        if data.get(
            "action_execution_id"
        ):
            return obs

    return (
        candidates[0]
        if candidates
        else None
    )


def evaluate_ui_api_binding_conflict_scope(
    fact_key: str,
    installation_architecture: str,
    server_version: str,
):
    """
    Read-only Conflict Detection v1.

    НИЧЕГО в Product Knowledge
    не изменяет.

    VERIFIED fact считается eligible
    для conflict только если:

      - существует другой fact
        того же subject;
      - scope тот же:
        architecture + server_version;
      - один и тот же competing fact
        имеет strong runtime evidence
        минимум из 2 разных Job;
      - оба evidence появились ПОСЛЕ
        последнего strong confirmation
        старого verified fact;
      - в каждом execution:
          competing claim = observed
          verified claim =
              absent_in_closed_window
    """

    from candidate_facts import (
        evaluate_claim_in_ui_observation,
    )

    migrate_fact_scopes_schema()

    architecture = str(
        installation_architecture
        or ""
    ).strip().lower()

    version = str(
        server_version
        or ""
    ).strip()

    with _connect() as conn:
        target = conn.execute(
            """
            SELECT
                f.fact_key,
                f.fact_type,
                f.subject_key,
                f.statement,
                f.data_json,
                s.status
            FROM facts AS f
            JOIN fact_scopes AS s
              ON s.fact_key = f.fact_key
            WHERE f.fact_key = ?
              AND s.installation_architecture = ?
              AND s.server_version = ?
            """,
            (
                fact_key,
                architecture,
                version,
            ),
        ).fetchone()

        if target is None:
            return {
                "decision": "not_found",
                "fact_key": fact_key,
            }

        if (
            target["fact_type"]
            != "ui_api_binding"
        ):
            return {
                "decision":
                    "unsupported_fact_type",
                "fact_key":
                    fact_key,
                "fact_type":
                    target["fact_type"],
            }

        if target["status"] != "verified":
            return {
                "decision":
                    "scope_not_verified",
                "fact_key":
                    fact_key,
                "current_status":
                    target["status"],
            }

        subject_key = target[
            "subject_key"
        ]

        if not subject_key:
            return {
                "decision":
                    "subject_key_missing",
                "fact_key":
                    fact_key,
            }

        target_claim = (
            _conflict_json_dict(
                target["data_json"]
            )
        )

        target_confirmations = (
            conn.execute(
                """
                SELECT
                    job_id,
                    case_id,
                    verification_json,
                    created_at
                FROM confirmations
                WHERE fact_key = ?
                  AND installation_architecture = ?
                  AND server_version = ?
                ORDER BY created_at
                """,
                (
                    fact_key,
                    architecture,
                    version,
                ),
            ).fetchall()
        )

        strong_target = []

        for row in target_confirmations:
            verification = (
                _conflict_json_dict(
                    row[
                        "verification_json"
                    ]
                )
            )

            if _all_true(
                verification,
                RUNTIME_FLAGS_UI_API_BINDING,
            ):
                strong_target.append(row)

        if not strong_target:
            return {
                "decision":
                    "verified_without_strong_runtime_history",
                "fact_key":
                    fact_key,
            }

        last_target_observed_at = max(
            row["created_at"]
            for row in strong_target
        )

        competing_rows = conn.execute(
            """
            SELECT
                f.fact_key,
                f.statement,
                f.data_json,
                s.status
            FROM facts AS f
            JOIN fact_scopes AS s
              ON s.fact_key = f.fact_key
            WHERE f.subject_key = ?
              AND f.fact_key <> ?
              AND f.fact_type = 'ui_api_binding'
              AND s.installation_architecture = ?
              AND s.server_version = ?
              AND s.status IN (
                  'candidate',
                  'verified'
              )
            ORDER BY f.fact_key
            """,
            (
                subject_key,
                fact_key,
                architecture,
                version,
            ),
        ).fetchall()

        if not competing_rows:
            return {
                "decision":
                    "no_competing_claims",
                "fact_key":
                    fact_key,
                "subject_key":
                    subject_key,
                "scope": {
                    "installation_architecture":
                        architecture,
                    "server_version":
                        version,
                    "current_status":
                        target["status"],
                },
                "last_target_observed_at":
                    last_target_observed_at,
                "competing_claim_count": 0,
            }

        competing_results = []

        for competing in competing_rows:
            competing_key = (
                competing["fact_key"]
            )

            competing_claim = (
                _conflict_json_dict(
                    competing["data_json"]
                )
            )

            confirmations = conn.execute(
                """
                SELECT
                    job_id,
                    case_id,
                    verification_json,
                    source_observation_ids_json,
                    created_at
                FROM confirmations
                WHERE fact_key = ?
                  AND installation_architecture = ?
                  AND server_version = ?
                ORDER BY created_at
                """,
                (
                    competing_key,
                    architecture,
                    version,
                ),
            ).fetchall()

            qualifying = []
            diagnostics = []

            for confirmation in confirmations:
                verification = (
                    _conflict_json_dict(
                        confirmation[
                            "verification_json"
                        ]
                    )
                )

                if not _all_true(
                    verification,
                    RUNTIME_FLAGS_UI_API_BINDING,
                ):
                    diagnostics.append(
                        {
                            "job_id":
                                confirmation[
                                    "job_id"
                                ],
                            "result":
                                "weak_runtime_evidence",
                        }
                    )
                    continue

                if not _conflict_is_after(
                    confirmation[
                        "created_at"
                    ],
                    last_target_observed_at,
                ):
                    diagnostics.append(
                        {
                            "job_id":
                                confirmation[
                                    "job_id"
                                ],
                            "result":
                                "not_after_last_target_observation",
                        }
                    )
                    continue

                source_ids = (
                    _conflict_json_list(
                        confirmation[
                            "source_observation_ids_json"
                        ]
                    )
                )

                ui_obs = (
                    _conflict_find_ui_observation(
                        job_id=confirmation[
                            "job_id"
                        ],
                        case_id=confirmation[
                            "case_id"
                        ],
                        source_observation_ids=(
                            source_ids
                        ),
                    )
                )

                if ui_obs is None:
                    diagnostics.append(
                        {
                            "job_id":
                                confirmation[
                                    "job_id"
                                ],
                            "result":
                                "ui_observation_not_found",
                        }
                    )
                    continue

                competing_eval = (
                    evaluate_claim_in_ui_observation(
                        competing_claim,
                        ui_obs,
                    )
                )

                target_eval = (
                    evaluate_claim_in_ui_observation(
                        target_claim,
                        ui_obs,
                    )
                )

                if (
                    competing_eval.get(
                        "decision"
                    )
                    == "observed"
                    and target_eval.get(
                        "decision"
                    )
                    == (
                        "absent_in_closed_window"
                    )
                ):
                    ui_data = ui_obs.get(
                        "data",
                        {},
                    )

                    qualifying.append(
                        {
                            "job_id":
                                confirmation[
                                    "job_id"
                                ],
                            "case_id":
                                confirmation[
                                    "case_id"
                                ],
                            "created_at":
                                confirmation[
                                    "created_at"
                                ],
                            "ui_observation_id":
                                ui_obs.get(
                                    "observation_id"
                                ),
                            "action_execution_id":
                                ui_data.get(
                                    "action_execution_id"
                                ),
                            "competing_claim":
                                competing_eval,
                            "verified_claim":
                                target_eval,
                        }
                    )
                else:
                    diagnostics.append(
                        {
                            "job_id":
                                confirmation[
                                    "job_id"
                                ],
                            "competing_decision":
                                competing_eval.get(
                                    "decision"
                                ),
                            "target_decision":
                                target_eval.get(
                                    "decision"
                                ),
                        }
                    )

            distinct_jobs = sorted({
                item["job_id"]
                for item in qualifying
                if item.get("job_id")
            })

            competing_results.append(
                {
                    "fact_key":
                        competing_key,
                    "status":
                        competing["status"],
                    "statement":
                        competing[
                            "statement"
                        ],
                    "qualifying_evidence_count":
                        len(qualifying),
                    "distinct_jobs":
                        distinct_jobs,
                    "distinct_job_count":
                        len(distinct_jobs),
                    "eligible":
                        len(distinct_jobs) >= 2,
                    "evidence":
                        qualifying,
                    "diagnostics":
                        diagnostics,
                }
            )

    eligible = [
        item
        for item in competing_results
        if item["eligible"]
    ]

    if eligible:
        selected = max(
            eligible,
            key=lambda item: (
                item[
                    "distinct_job_count"
                ],
                item[
                    "qualifying_evidence_count"
                ],
            ),
        )

        return {
            "decision":
                "eligible_for_conflict",
            "policy":
                "ui_api_binding_conflict_v1",
            "fact_key":
                fact_key,
            "subject_key":
                subject_key,
            "scope": {
                "installation_architecture":
                    architecture,
                "server_version":
                    version,
                "current_status":
                    "verified",
            },
            "last_target_observed_at":
                last_target_observed_at,
            "selected_competing_fact_key":
                selected["fact_key"],
            "selected_distinct_jobs":
                selected[
                    "distinct_jobs"
                ],
            "competing_claims":
                competing_results,
        }

    return {
        "decision": "keep_verified",
        "policy":
            "ui_api_binding_conflict_v1",
        "fact_key":
            fact_key,
        "subject_key":
            subject_key,
        "scope": {
            "installation_architecture":
                architecture,
            "server_version":
                version,
            "current_status":
                "verified",
        },
        "last_target_observed_at":
            last_target_observed_at,
        "reason": (
            "no single competing claim has "
            "qualifying absence evidence "
            "from at least 2 distinct later jobs"
        ),
        "competing_claims":
            competing_results,
    }


def mark_ui_api_binding_scope_conflict_if_eligible(
    fact_key: str,
    installation_architecture: str,
    server_version: str,
):
    """
    Безопасный переход:
        verified -> conflict

    Только по решению
    evaluate_ui_api_binding_conflict_scope().

    Никакие candidate/deprecated/unknown
    статусы эта функция не меняет.
    """

    decision = (
        evaluate_ui_api_binding_conflict_scope(
            fact_key=fact_key,
            installation_architecture=(
                installation_architecture
            ),
            server_version=server_version,
        )
    )

    if (
        decision.get("decision")
        != "eligible_for_conflict"
    ):
        return {
            "action": "keep_verified",
            "changed": False,
            "decision": decision,
        }

    scope = decision.get("scope") or {}

    current_status = scope.get(
        "current_status"
    )

    if current_status != "verified":
        return {
            "action":
                "conflict_transition_blocked",
            "changed": False,
            "current_status":
                current_status,
            "decision":
                decision,
        }

    competing_fact_key = (
        decision.get(
            "selected_competing_fact_key"
        )
    )

    result = set_fact_scope_status(
        fact_key=fact_key,
        installation_architecture=(
            installation_architecture
        ),
        server_version=server_version,
        status="conflict",
        source="validator",
        reason=(
            "ui_api_binding_conflict_v1: "
            "verified claim was absent in "
            "at least 2 later closed action "
            "windows while the same competing "
            "claim was observed; competing_fact="
            + str(competing_fact_key)
        ),
        decision=decision,
    )

    return {
        "action": "marked_conflict",
        "changed": True,
        "competing_fact_key":
            competing_fact_key,
        "status_result":
            result,
        "decision":
            decision,
    }


def mark_verified_subject_conflicts_for_candidate(
    fact_key: str,
    fact_type: str,
    installation_architecture: str,
    server_version: str,
):
    """
    После ingest нового fact проверяет старые VERIFIED
    claims того же subject и scope.

    Сам новый fact не проверяет против себя.
    """

    if fact_type != "ui_api_binding":
        return {
            "action": "unsupported_fact_type",
            "checked": 0,
            "marked": 0,
        }

    architecture = str(
        installation_architecture or ""
    ).strip().lower()

    version = str(
        server_version or ""
    ).strip()

    migrate_fact_scopes_schema()

    with _connect() as conn:
        current = conn.execute(
            """
            SELECT
                fact_key,
                subject_key
            FROM facts
            WHERE fact_key = ?
            """,
            (fact_key,),
        ).fetchone()

        if current is None:
            return {
                "action": "fact_not_found",
                "checked": 0,
                "marked": 0,
            }

        subject_key = current[
            "subject_key"
        ]

        if not subject_key:
            return {
                "action": "subject_key_missing",
                "checked": 0,
                "marked": 0,
            }

        rows = conn.execute(
            """
            SELECT f.fact_key
            FROM facts AS f
            JOIN fact_scopes AS s
              ON s.fact_key = f.fact_key
            WHERE f.subject_key = ?
              AND f.fact_key <> ?
              AND f.fact_type = 'ui_api_binding'
              AND s.installation_architecture = ?
              AND s.server_version = ?
              AND s.status = 'verified'
            ORDER BY f.fact_key
            """,
            (
                subject_key,
                fact_key,
                architecture,
                version,
            ),
        ).fetchall()

    results = []

    for row in rows:
        target_fact_key = row[
            "fact_key"
        ]

        result = (
            mark_ui_api_binding_scope_conflict_if_eligible(
                fact_key=target_fact_key,
                installation_architecture=architecture,
                server_version=version,
            )
        )

        results.append(
            {
                "fact_key":
                    target_fact_key,
                "action":
                    result.get("action"),
                "changed":
                    result.get("changed"),
                "decision":
                    (
                        result.get("decision")
                        or {}
                    ).get("decision"),
            }
        )

    marked = sum(
        1
        for item in results
        if item.get("changed") is True
    )

    return {
        "action": (
            "subject_conflict_check_complete"
        ),
        "subject_key": subject_key,
        "checked": len(results),
        "marked": marked,
        "results": results,
    }

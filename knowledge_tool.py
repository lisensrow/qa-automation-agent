from knowledge_index import search
import re


MAX_RESULTS = 5
MAX_CHARS_PER_RESULT = 3500
MAX_TOTAL_CHARS = 12000
MAX_SEARCH_CANDIDATES = 20


def _normalized(value: str) -> str:
    return " ".join(
        str(value or "").split()
    ).strip()


def _is_useless_chunk(
    heading: str,
    content: str,
) -> bool:
    heading_norm = _normalized(
        heading
    ).casefold()

    content_norm = _normalized(
        content
    ).casefold()

    if not content_norm:
        return True

    # Чанк содержит только свой заголовок:
    # "CMDB" -> "CMDB"
    if (
        heading_norm
        and content_norm == heading_norm
    ):
        return True

    return False


def knowledge_search(
    query: str,
    limit: int = 5,
    source_namespace: str = "all",
    required_term: str | None = None,
) -> dict:
    if required_term is not None and (not isinstance(required_term,str) or not re.fullmatch(r'[A-Za-z0-9]{2,80}',required_term)):
        return {'status':'invalid_required_term','results':[]}
    if not isinstance(source_namespace,str) or source_namespace not in {'all','product_docs','experience'}:
        return {'status':'invalid_source_namespace','results':[]}
    query = str(query).strip()

    if not query:
        return {
            "status": "invalid_query",
            "results": [],
        }

    try:
        limit = int(limit)
    except Exception:
        limit = 5

    limit = max(
        1,
        min(limit, MAX_RESULTS),
    )

    # Берём больше кандидатов, потому что часть
    # может оказаться heading-only чанками.
    candidate_limit = min(
        MAX_SEARCH_CANDIDATES,
        max(limit * 4, limit),
    )

    filters={}
    if source_namespace != 'all':filters['source_namespace']=source_namespace
    if required_term is not None:filters['required_term']=required_term
    raw = search(query,limit=candidate_limit,**filters)

    results = []
    total_chars = 0

    for item in raw:
        heading = (
            item.get("heading")
            or ""
        ).strip()

        content = (
            item.get("content")
            or ""
        ).strip()

        if _is_useless_chunk(
            heading,
            content,
        ):
            continue

        truncated = False

        if len(content) > MAX_CHARS_PER_RESULT:
            content = (
                content[:MAX_CHARS_PER_RESULT]
                + "\n...<truncated>"
            )
            truncated = True

        if (
            total_chars + len(content)
            > MAX_TOTAL_CHARS
        ):
            remaining = (
                MAX_TOTAL_CHARS
                - total_chars
            )

            if remaining < 300:
                break

            content = (
                content[:remaining]
                + "\n...<truncated>"
            )
            truncated = True

        results.append(
            {
                "source": item.get("source"),
                "chunk_no": item.get("chunk_no"),
                "heading": heading,
                "content": content,
                "truncated": truncated,
            }
        )

        total_chars += len(content)

        if len(results) >= limit:
            break

        if total_chars >= MAX_TOTAL_CHARS:
            break

    output = {
        "status": "ok",
        "query": query,
        "result_count": len(results),
        "results": results,
    }
    if source_namespace != 'all' or required_term is not None:
        output.update(source_namespace=source_namespace,indexed_excerpts_only=True,
            current_source_bytes_rechecked=False,execution_permission_granted=False)
    if required_term is not None:
        output.update(required_term=required_term,anchor_is_retrieval_filter_not_specification=True)
    return output

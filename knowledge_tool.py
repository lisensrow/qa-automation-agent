from knowledge_index import search


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
) -> dict:
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

    raw = search(
        query,
        limit=candidate_limit,
    )

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

    return {
        "status": "ok",
        "query": query,
        "result_count": len(results),
        "results": results,
    }

import httpx

import uqa


class FakeResponse:
    def __init__(self, payload, status_code=200):
        self.payload = payload
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise httpx.HTTPStatusError(
                "fake failure", request=None, response=None,
            )

    def json(self):
        return self.payload


class FakeClient:
    calls = []
    installed_models = [uqa.MODEL]
    warmup_error = None

    def __init__(self, timeout=None):
        self.timeout = timeout

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def get(self, url):
        self.calls.append(("GET", url))
        return FakeResponse({
            "models": [{"name": name} for name in self.installed_models],
        })

    def post(self, url, json):
        self.calls.append(("POST", url, json))
        if self.warmup_error is not None:
            raise self.warmup_error
        return FakeResponse({"done": True, "response": "O"})


original_client = uqa.httpx.Client
original_acquire = uqa.acquire_llm_gate
original_release = uqa.release_llm_gate
original_ttl = uqa.OLLAMA_READINESS_TTL_SECONDS
try:
    uqa.httpx.Client = FakeClient
    uqa.acquire_llm_gate = lambda call_id=None: (object(), 0.0)
    uqa.release_llm_gate = lambda lock: None
    uqa.OLLAMA_READINESS_TTL_SECONDS = 600
    uqa._OLLAMA_READY_UNTIL = 0.0

    ready = uqa.ensure_ollama_ready(force=True)
    assert ready["status"] == "ready", ready
    assert ready["cached"] is False, ready
    assert [call[0] for call in FakeClient.calls] == ["GET", "POST"]
    warmup_payload = FakeClient.calls[1][2]
    assert warmup_payload["model"] == uqa.MODEL
    assert warmup_payload["options"]["num_predict"] == 1
    assert warmup_payload["options"]["num_ctx"] <= 2048

    call_count = len(FakeClient.calls)
    cached = uqa.ensure_ollama_ready()
    assert cached["cached"] is True, cached
    assert len(FakeClient.calls) == call_count

    uqa._OLLAMA_READY_UNTIL = 0.0
    FakeClient.installed_models = ["different-model"]
    try:
        uqa.ensure_ollama_ready(force=True)
        raise AssertionError("missing configured model must fail")
    except RuntimeError as exc:
        assert "not installed" in str(exc)
    assert uqa._OLLAMA_READY_UNTIL == 0.0

    FakeClient.installed_models = [uqa.MODEL]
    FakeClient.warmup_error = httpx.ReadTimeout("warmup timeout")
    try:
        uqa.ensure_ollama_ready(force=True)
        raise AssertionError("warmup timeout must fail")
    except httpx.ReadTimeout:
        pass
    assert uqa._OLLAMA_READY_UNTIL == 0.0
finally:
    uqa.httpx.Client = original_client
    uqa.acquire_llm_gate = original_acquire
    uqa.release_llm_gate = original_release
    uqa.OLLAMA_READINESS_TTL_SECONDS = original_ttl
    uqa._OLLAMA_READY_UNTIL = 0.0


print("ollama readiness smoke: PASS")

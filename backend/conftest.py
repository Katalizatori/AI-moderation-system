"""Shared test fixtures.

The moderation code calls the OpenAI HTTP API through ``requests.post``. Every
``Review.save()`` triggers that call via a ``pre_save`` signal, so tests must
block outbound HTTP globally rather than per-test.
"""

import pytest


class NetworkAccessAttempted(BaseException):
    """Raised when a test attempts a real HTTP request.

    Deliberately inherits from ``BaseException`` rather than ``Exception``:
    both service methods wrap their request in ``except Exception``, which
    would otherwise swallow this guard and silently return the fallback
    result instead of failing the test.
    """


@pytest.fixture(autouse=True)
def block_network(monkeypatch):
    """Fail loudly on any HTTP call a test did not explicitly mock."""

    def _fail(*args, **kwargs):
        raise NetworkAccessAttempted(
            f"Unmocked HTTP request in test: args={args!r} kwargs={kwargs!r}"
        )

    monkeypatch.setattr("requests.post", _fail)
    monkeypatch.setattr("requests.get", _fail)
    monkeypatch.setattr("requests.request", _fail)


@pytest.fixture
def moderation_api_response():
    """Builder for an OpenAI /v1/moderations response body."""

    def _build(flagged=False, category_scores=None):
        scores = category_scores or {"harassment": 0.01, "violence": 0.02}
        return {
            "results": [
                {
                    "flagged": flagged,
                    "categories": {name: score > 0.5 for name, score in scores.items()},
                    "category_scores": scores,
                }
            ]
        }

    return _build


@pytest.fixture
def mock_post(monkeypatch):
    """Replace ``requests.post`` with a stub returning a canned JSON body.

    ``moderation_service`` imports ``requests`` as a module and calls
    ``requests.post(...)``, so patching the attribute on the module object
    covers both service classes.
    """

    class _Response:
        def __init__(self, payload, status_code=200, error=None):
            self._payload = payload
            self.status_code = status_code
            self._error = error

        def json(self):
            return self._payload

        def raise_for_status(self):
            if self._error is not None:
                raise self._error

    def _install(payload, status_code=200, error=None):
        calls = []

        def _post(url, **kwargs):
            calls.append({"url": url, **kwargs})
            body = payload(url) if callable(payload) else payload
            return _Response(body, status_code, error)

        monkeypatch.setattr("reviews.services.moderation_service.requests.post", _post)
        return calls

    return _install


@pytest.fixture
def stub_moderation(monkeypatch):
    """Replace the module-level service instance used by the ``pre_save`` signal.

    ``reviews/signals.py`` builds ``OpenAIModerationService()`` at import time,
    so patching the class has no effect on the already-constructed singleton —
    the instance attribute itself has to be replaced.
    """

    def _install(result=None, raises=None):
        calls = []

        class _Stub:
            def moderate(self, text):
                calls.append(text)
                if raises is not None:
                    raise raises
                return result or {
                    "status": "allowed",
                    "risk_category": "appropriate",
                    "risk_score": 0.0,
                    "moderation_data_full": {"flagged": False},
                }

        monkeypatch.setattr("reviews.signals.moderation_service", _Stub())
        return calls

    return _install

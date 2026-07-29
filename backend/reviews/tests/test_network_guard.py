"""Tests for the autouse network guard in conftest.

The suite's hermeticity depends on this guard, and on it surviving the broad
`except Exception` handlers in the moderation services. If either property
breaks, an unmocked test would silently pass while making a real API call.
"""

import pytest
import requests

from conftest import NetworkAccessAttempted
from reviews.services.moderation_service import OpenAIModerationService


def test_unmocked_post_is_blocked():
    with pytest.raises(NetworkAccessAttempted):
        requests.post("https://api.openai.com/v1/moderations", json={})


def test_unmocked_get_is_blocked():
    with pytest.raises(NetworkAccessAttempted):
        requests.get("https://example.com")


def test_guard_is_not_swallowed_by_service_error_handling():
    """OpenAIModerationService.moderate() wraps everything in `except Exception`.

    The guard inherits from BaseException precisely so an unmocked call
    surfaces as a test failure instead of the 'pending' fallback result.
    """
    with pytest.raises(NetworkAccessAttempted):
        OpenAIModerationService().moderate("this must not reach the network")

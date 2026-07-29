"""Tests for OpenAIModerationService.moderate() routing logic.

All outbound HTTP is mocked. The spam detector is injected as a stub so each
test exercises exactly one decision path.
"""

import pytest

from reviews.services.moderation_service import OpenAIModerationService


class StubSpamDetector:
    def __init__(self, score=0.0):
        self.score = score
        self.calls = []

    def detect_spam(self, text):
        self.calls.append(text)
        return self.score


UNAVAILABLE = None  # what detect_spam returns when the check could not run


def make_service(spam_score=0.0):
    return OpenAIModerationService(spam_detector=StubSpamDetector(spam_score))


def test_not_flagged_low_spam_is_allowed(mock_post, moderation_api_response):
    mock_post(moderation_api_response(flagged=False))
    service = make_service(spam_score=0.1)

    result = service.moderate("A perfectly ordinary review.")

    assert result["status"] == "allowed"
    assert result["risk_category"] == "appropriate"
    # risk_score is the spam score itself: low means safe, in every branch.
    assert result["risk_score"] == pytest.approx(0.1)


def test_not_flagged_high_spam_is_deleted(mock_post, moderation_api_response):
    mock_post(moderation_api_response(flagged=False))
    service = make_service(spam_score=0.95)

    result = service.moderate("BUY CHEAP WATCHES AT example.com")

    assert result["status"] == "to_be_deleted"
    assert result["risk_category"] == "spam"
    assert result["risk_score"] == pytest.approx(0.95)


def test_flagged_high_score_is_deleted(mock_post, moderation_api_response):
    mock_post(
        moderation_api_response(flagged=True, category_scores={"hate": 0.97, "violence": 0.2})
    )
    service = make_service()

    result = service.moderate("something hateful")

    assert result["status"] == "to_be_deleted"
    assert result["risk_category"] == "hate"
    assert result["risk_score"] == pytest.approx(0.97)


def test_flagged_low_score_is_held_not_allowed(mock_post, moderation_api_response):
    """Flagged content is never auto-allowed on the strength of a low score.

    OpenAI's `flagged` is calibrated per category, and those thresholds are
    deliberately not uniform -- low-base-rate, high-harm categories flag well
    below 0.3. Overriding that with a flat threshold auto-approved exactly the
    categories most worth catching. Scores now only choose between deleting
    and holding.
    """
    mock_post(
        moderation_api_response(flagged=True, category_scores={"harassment": 0.25, "hate": 0.1})
    )
    service = make_service(spam_score=0.0)

    result = service.moderate("mildly rude")

    assert result["status"] == "pending"
    assert result["risk_category"] == "harassment"
    assert result["risk_score"] == pytest.approx(0.25)


def test_flagged_very_low_score_is_still_held(mock_post, moderation_api_response):
    """The dangerous case: a category OpenAI flags at a low raw score."""
    mock_post(
        moderation_api_response(flagged=True, category_scores={"sexual/minors": 0.06})
    )
    service = make_service(spam_score=0.0)

    result = service.moderate("content OpenAI flagged despite a low score")

    assert result["status"] == "pending"
    assert result["risk_category"] == "sexual/minors"


def test_flagged_mid_score_with_spam_is_deleted(mock_post, moderation_api_response):
    mock_post(moderation_api_response(flagged=True, category_scores={"harassment": 0.5}))
    service = make_service(spam_score=0.9)

    result = service.moderate("borderline promo text")

    assert result["status"] == "to_be_deleted"
    assert result["risk_category"] == "spam"
    assert result["risk_score"] == pytest.approx(0.9)


def test_flagged_mid_score_without_spam_is_pending(mock_post, moderation_api_response):
    mock_post(moderation_api_response(flagged=True, category_scores={"harassment": 0.5}))
    service = make_service(spam_score=0.1)

    result = service.moderate("borderline text")

    assert result["status"] == "pending"
    assert result["risk_category"] == "harassment"
    assert result["risk_score"] == pytest.approx(0.5)


@pytest.mark.parametrize(
    "score,expected_status",
    [
        (0.8, "to_be_deleted"),  # HIGH_RISK_THRESHOLD is inclusive (>=)
        (0.79, "pending"),  # just below it, a human decides
    ],
)
def test_high_risk_threshold_is_inclusive(
    mock_post, moderation_api_response, score, expected_status
):
    mock_post(moderation_api_response(flagged=True, category_scores={"violence": score}))
    service = make_service(spam_score=0.0)

    result = service.moderate("boundary case")

    assert result["status"] == expected_status


def test_spam_threshold_is_exclusive(mock_post, moderation_api_response):
    """SPAM_THRESHOLD uses `>`, so a score of exactly 0.8 must not delete."""
    mock_post(moderation_api_response(flagged=False))
    service = make_service(spam_score=0.8)

    result = service.moderate("exactly at the spam threshold")

    assert result["status"] == "allowed"


def test_unavailable_spam_check_holds_non_flagged_content(mock_post, moderation_api_response):
    """A failed spam check must not approve content by default.

    Regression test: detect_spam used to return 0.0 on failure, which made an
    outage produce `allowed` at risk_score 0.0 -- maximum confidence that the
    content was fine, derived from no signal at all.
    """
    mock_post(moderation_api_response(flagged=False))
    service = make_service(spam_score=UNAVAILABLE)

    result = service.moderate("unremarkable text")

    assert result["status"] == "pending"
    assert result["risk_category"] == "unknown"
    assert result["risk_score"] == 0.0
    assert result["moderation_data_full"]["spam_check"] == "unavailable"


def test_unavailable_spam_check_holds_borderline_flagged_content(
    mock_post, moderation_api_response
):
    mock_post(moderation_api_response(flagged=True, category_scores={"harassment": 0.5}))
    service = make_service(spam_score=UNAVAILABLE)

    result = service.moderate("borderline text")

    assert result["status"] == "pending"
    assert result["risk_category"] == "harassment"


def test_http_error_falls_back_to_pending(mock_post, moderation_api_response):
    mock_post(moderation_api_response(), error=RuntimeError("500 Server Error"))
    service = make_service()

    result = service.moderate("anything")

    assert result["status"] == "pending"
    assert result["risk_category"] == "unknown"
    assert result["risk_score"] == 0.0
    assert "500 Server Error" in result["moderation_data_full"]["error"]


def test_malformed_response_falls_back_to_pending(mock_post):
    mock_post({"unexpected": "shape"})
    service = make_service()

    result = service.moderate("anything")

    assert result["status"] == "pending"
    assert result["risk_category"] == "unknown"
    assert "error" in result["moderation_data_full"]


def test_moderate_posts_to_the_moderations_endpoint(mock_post, moderation_api_response):
    calls = mock_post(moderation_api_response(flagged=False))
    service = make_service()

    service.moderate("check the wire format")

    assert len(calls) == 1
    assert calls[0]["url"] == "https://api.openai.com/v1/moderations"
    assert calls[0]["json"]["input"] == "check the wire format"

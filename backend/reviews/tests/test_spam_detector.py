"""Tests for GPTSpamDetectorService.detect_spam().

The service asks GPT for a bare float and parses it out of the chat
completion body, so the interesting cases are all about parsing and clamping
untrusted model output.
"""

import pytest

from reviews.services.moderation_service import GPTSpamDetectorService


def chat_response(content):
    return {"choices": [{"message": {"content": content}}]}


def test_parses_valid_score(mock_post):
    mock_post(chat_response("0.42"))

    assert GPTSpamDetectorService().detect_spam("some text") == pytest.approx(0.42)


def test_strips_whitespace_around_score(mock_post):
    mock_post(chat_response("  0.75\n"))

    assert GPTSpamDetectorService().detect_spam("some text") == pytest.approx(0.75)


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("1.7", 1.0),
        ("-0.5", 0.0),
    ],
)
def test_clamps_out_of_range_scores(mock_post, raw, expected):
    mock_post(chat_response(raw))

    assert GPTSpamDetectorService().detect_spam("some text") == pytest.approx(expected)


def test_non_numeric_reply_returns_unknown(mock_post):
    """An unparseable reply is unknown, not "not spam"."""
    mock_post(chat_response("definitely spam"))

    assert GPTSpamDetectorService().detect_spam("some text") is None


def test_api_error_returns_unknown(mock_post):
    """A failed check must not be reported as a clean score of 0.0."""
    mock_post(chat_response("0.9"), error=RuntimeError("503 Service Unavailable"))

    assert GPTSpamDetectorService().detect_spam("some text") is None


def test_posts_to_chat_completions_endpoint(mock_post):
    calls = mock_post(chat_response("0.1"))

    GPTSpamDetectorService().detect_spam("check the wire format")

    assert len(calls) == 1
    assert calls[0]["url"] == "https://api.openai.com/v1/chat/completions"
    assert "check the wire format" in calls[0]["json"]["messages"][1]["content"]

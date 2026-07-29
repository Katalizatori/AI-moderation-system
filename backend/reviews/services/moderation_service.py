import logging
from typing import Dict, Optional, TypedDict

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


class ModerationResult(TypedDict):
    status: str  # 'allowed'|'pending'|'to_be_deleted'
    risk_category: str
    risk_score: float  # always "how dangerous": higher is worse, in every branch
    moderation_data_full: Optional[Dict]


class OpenAIModerationService:
    """Routes review text to allowed / pending / to_be_deleted.

    Division of labour: OpenAI's ``flagged`` boolean decides *whether* the text
    is a problem, because it is calibrated per category and those thresholds
    are deliberately not uniform. The raw scores only decide *how bad* --
    whether a flagged item is deleted outright or held for a human. Flagged
    content is never auto-allowed on the strength of a low score.
    """

    HIGH_RISK_THRESHOLD = 0.8
    SPAM_THRESHOLD = 0.8

    def __init__(self, spam_detector: Optional["GPTSpamDetectorService"] = None):
        self.api_key = settings.OPENAI_API_KEY
        self.api_url = "https://api.openai.com/v1/moderations"
        self.spam_detector = spam_detector or GPTSpamDetectorService()

    def moderate(self, text: str) -> ModerationResult:
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }
            payload = {"input": text, "model": "text-moderation-latest"}

            response = requests.post(
                self.api_url, headers=headers, json=payload, timeout=30
            )
            response.raise_for_status()

            return self._parse_moderation_response(response.json(), text)

        except Exception as e:
            logger.error(f"Moderation API failed: {e}")
            return {
                "status": "pending",
                "risk_category": "unknown",
                "risk_score": 0.0,
                "moderation_data_full": {"error": str(e)},
            }

    def _parse_moderation_response(
        self, api_response: Dict, text: str
    ) -> ModerationResult:
        result = api_response["results"][0]
        moderation_data_full = {
            "flagged": result["flagged"],
            "categories": result["categories"],
            "category_scores": result["category_scores"],
        }

        if not result["flagged"]:
            return self._handle_non_flagged_content(text, moderation_data_full)

        highest_risk_category, risk_score = max(
            result["category_scores"].items(), key=lambda x: x[1]
        )

        if risk_score >= self.HIGH_RISK_THRESHOLD:
            return {
                "status": "to_be_deleted",
                "risk_category": highest_risk_category,
                "risk_score": risk_score,
                "moderation_data_full": moderation_data_full,
            }

        spam_score = self.spam_detector.detect_spam(text)
        if spam_score is not None and spam_score > self.SPAM_THRESHOLD:
            return {
                "status": "to_be_deleted",
                "risk_category": "spam",
                "risk_score": spam_score,
                "moderation_data_full": moderation_data_full,
            }

        # Flagged, but not confidently enough to delete outright. A human
        # decides. Note there is no path back to "allowed" from here: OpenAI
        # already flagged this, and a low raw score does not overturn that.
        return {
            "status": "pending",
            "risk_category": highest_risk_category,
            "risk_score": risk_score,
            "moderation_data_full": moderation_data_full,
        }

    def _handle_non_flagged_content(
        self, text: str, moderation_data: Dict
    ) -> ModerationResult:
        spam_score = self.spam_detector.detect_spam(text)

        if spam_score is None:
            # The spam check is the only signal left once OpenAI has declined
            # to flag the text. Without it there is no basis to approve, so
            # hold for review rather than defaulting to "clean".
            return {
                "status": "pending",
                "risk_category": "unknown",
                "risk_score": 0.0,
                "moderation_data_full": {**moderation_data, "spam_check": "unavailable"},
            }

        if spam_score > self.SPAM_THRESHOLD:
            return {
                "status": "to_be_deleted",
                "risk_category": "spam",
                "risk_score": spam_score,
                "moderation_data_full": moderation_data,
            }

        return {
            "status": "allowed",
            "risk_category": "appropriate",
            "risk_score": spam_score,
            "moderation_data_full": moderation_data,
        }


class GPTSpamDetectorService:
    """
    Helper class that prompts GPT to detect whether a review is spam or not.

    Returns a spam score between 0 and 1, or None if the check could not be
    completed. None means "unknown", which callers must not read as "clean":
    a failed check is not evidence that the text is fine.
    """

    def __init__(self):
        self.api_key = settings.OPENAI_API_KEY
        self.api_url = "https://api.openai.com/v1/chat/completions"

    def detect_spam(self, text: str) -> Optional[float]:
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }

            prompt = f"""
            Analyze the following text and determine if it's spam. Consider:
            - Promotional content;
            - Irrelevant links;
            - Ads;
            - Repetitive content;
            - Misinformation.

            Text: "{text}"

            Respond with ONLY a single float point number between 0 and 1
            depending on how confident you are that a text is spam.

            """

            payload = {
                "model": "gpt-3.5-turbo",
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "You are a spam detection system. Always respond "
                            "with only a float point number between 0 and 1."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                "max_tokens": 10,
                "temperature": 0.1,
            }

            response = requests.post(
                self.api_url,
                headers=headers,
                json=payload,
                timeout=30,
            )

            response.raise_for_status()

            result = response.json()
            raw_score = result["choices"][0]["message"]["content"].strip()

        except Exception as e:
            logger.error(f"GPT prompt failed: {e}")
            return None

        try:
            spam_score = float(raw_score)
        except (TypeError, ValueError):
            logger.error(f"Unparseable spam score from GPT: {raw_score!r}")
            return None

        return max(0.0, min(1.0, spam_score))

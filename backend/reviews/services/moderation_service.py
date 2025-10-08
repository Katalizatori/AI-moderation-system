import requests
from typing import Dict, Any, Optional, TypedDict
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


class ModerationResult(TypedDict):
    status: str  # 'allowed'|'pending'|'to_be_deleted'
    risk_category: str
    confidence: float
    moderation_data_full: Optional[Dict]


class OpenAIModerationService:
    HIGH_RISK_THRESHOLD = 0.8
    LOW_RISK_THRESHOLD = 0.3
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
                "confidence": 0.0,
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
                "confidence": risk_score,
                "moderation_data_full": moderation_data_full,
            }

        if risk_score <= self.LOW_RISK_THRESHOLD:
            return {
                "status": "allowed",
                "risk_category": highest_risk_category,
                "confidence": risk_score,
                "moderation_data_full": moderation_data_full,
            }

        spam_score = self.spam_detector.detect_spam(text)
        if spam_score > self.SPAM_THRESHOLD:
            return {
                "status": "to_be_deleted",
                "risk_category": "spam",
                "confidence": spam_score,
                "moderation_data_full": moderation_data_full,
            }

        return {
            "status": "pending",
            "risk_category": highest_risk_category,
            "confidence": risk_score,
            "moderation_data_full": moderation_data_full,
        }

    def _handle_non_flagged_content(
        self, text: str, moderation_data: Dict
    ) -> ModerationResult:
        spam_score = self.spam_detector.detect_spam(text)

        if spam_score > self.SPAM_THRESHOLD:
            return {
                "status": "to_be_deleted",
                "risk_category": "spam",
                "confidence": spam_score,
                "moderation_data_full": moderation_data,
            }

        return {
            "status": "allowed",
            "risk_category": "appropriate",
            "confidence": 1.0 - spam_score,
            "moderation_data_full": moderation_data,
        }


class GPTSpamDetectorService:
    """
    Helper class that prompts GPT to detect whether a review is spam or not.

    Return a confidence score between 0 and 1.
    """

    def __init__(self):
        self.api_key = settings.OPENAI_API_KEY
        self.api_url = "https://api.openai.com/v1/chat/completions"

    def detect_spam(self, text: str) -> float:
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

            Respond with ONLY a single float point number between 0 and 1 depending on how confident you are that a text is spam.

            """

            payload = {
                "model": "gpt-3.5-turbo",
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a spam detection system. Always respond with only a float point number between 0 and 1.",
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
            spam_score = float(result["choices"][0]["message"]["content"].strip())

            return max(0.0, min(1.0, spam_score))

        except Exception as e:
            logger.error(f"GPT prompt failed: {e}")
            return 0.0

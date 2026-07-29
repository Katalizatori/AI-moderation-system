"""Tests for the /api/reviews/ endpoint.

The list endpoint deliberately exposes only reviews the moderator allowed, so
the flagged-content path is checked from the outside: the review is accepted
and stored, but never served back.
"""

import json

from reviews.models import Review

ENDPOINT = "/api/reviews/"


def post_review(client, payload):
    return client.post(ENDPOINT, data=json.dumps(payload), content_type="application/json")


def test_post_allowed_review_is_created(db, client, stub_moderation):
    stub_moderation(
        result={
            "status": "allowed",
            "risk_category": "appropriate",
            "risk_score": 0.98,
            "moderation_data_full": {"flagged": False},
        }
    )

    response = post_review(client, {"content": "Great product, arrived on time."})

    assert response.status_code == 201
    review = Review.objects.get()
    assert review.content == "Great product, arrived on time."
    assert review.status == "allowed"


def test_flagged_review_is_stored_but_not_listed(db, client, stub_moderation):
    stub_moderation(
        result={
            "status": "to_be_deleted",
            "risk_category": "hate",
            "risk_score": 0.99,
            "moderation_data_full": {"flagged": True},
        }
    )

    create = post_review(client, {"content": "something hateful"})
    assert create.status_code == 201
    assert Review.objects.count() == 1

    listing = client.get(ENDPOINT)
    assert listing.status_code == 200
    assert listing.json() == []


def test_post_empty_content_is_rejected(db, client, stub_moderation):
    stub_moderation()

    response = post_review(client, {"content": ""})

    assert response.status_code == 400
    assert "content" in response.json()
    assert Review.objects.count() == 0


def test_post_without_content_field_is_rejected(db, client, stub_moderation):
    stub_moderation()

    response = post_review(client, {})

    assert response.status_code == 400
    assert "content" in response.json()
    assert Review.objects.count() == 0


def test_list_returns_only_allowed_reviews(db, client, stub_moderation):
    for status, content in [
        ("allowed", "visible one"),
        ("pending", "held for review"),
        ("to_be_deleted", "removed one"),
    ]:
        stub_moderation(
            result={
                "status": status,
                "risk_category": "appropriate",
                "risk_score": 0.5,
                "moderation_data_full": {},
            }
        )
        Review.objects.create(content=content)

    response = client.get(ENDPOINT)

    assert response.status_code == 200
    contents = [item["content"] for item in response.json()]
    assert contents == ["visible one"]


def test_list_is_ordered_newest_first(db, client, stub_moderation):
    stub_moderation(
        result={
            "status": "allowed",
            "risk_category": "appropriate",
            "risk_score": 1.0,
            "moderation_data_full": {},
        }
    )
    Review.objects.create(content="older")
    Review.objects.create(content="newer")

    response = client.get(ENDPOINT)

    contents = [item["content"] for item in response.json()]
    assert contents == ["newer", "older"]


def test_approved_review_cannot_be_edited(db, client, stub_moderation):
    """Regression test for a moderation bypass.

    Update used to be exposed via ModelViewSet with AllowAny, and the signal
    only moderated rows without a pk. A caller could get benign content
    approved and then PATCH in anything, which was then served publicly.
    """
    calls = stub_moderation(
        result={
            "status": "allowed",
            "risk_category": "appropriate",
            "risk_score": 1.0,
            "moderation_data_full": {},
        }
    )
    post_review(client, {"content": "Lovely product, five stars."})
    review = Review.objects.get()

    patch = client.patch(
        f"{ENDPOINT}{review.pk}/",
        data=json.dumps({"content": "ARBITRARY UNMODERATED CONTENT"}),
        content_type="application/json",
    )

    assert patch.status_code == 405
    review.refresh_from_db()
    assert review.content == "Lovely product, five stars."
    assert len(calls) == 1


def test_approved_review_cannot_be_deleted(db, client, stub_moderation):
    stub_moderation(
        result={
            "status": "allowed",
            "risk_category": "appropriate",
            "risk_score": 1.0,
            "moderation_data_full": {},
        }
    )
    post_review(client, {"content": "a review"})
    review = Review.objects.get()

    response = client.delete(f"{ENDPOINT}{review.pk}/")

    assert response.status_code == 405
    assert Review.objects.count() == 1


def test_editing_content_at_the_model_layer_remoderates(db, stub_moderation):
    """Defence in depth: the admin and shell bypass the API, not the signal."""
    calls = stub_moderation(
        result={
            "status": "allowed",
            "risk_category": "appropriate",
            "risk_score": 1.0,
            "moderation_data_full": {},
        }
    )
    review = Review.objects.create(content="original")
    assert len(calls) == 1

    review.content = "swapped in later"
    review.save()

    assert calls == ["original", "swapped in later"]


def test_saving_without_changing_content_does_not_remoderate(db, stub_moderation):
    calls = stub_moderation(
        result={
            "status": "allowed",
            "risk_category": "appropriate",
            "risk_score": 0.9,
            "moderation_data_full": {},
        }
    )
    review = Review.objects.create(content="unchanged")

    review.risk_score = 0.5
    review.save()

    assert len(calls) == 1


def test_list_exposes_moderation_fields_as_read_only(db, client, stub_moderation):
    stub_moderation(
        result={
            "status": "allowed",
            "risk_category": "appropriate",
            "risk_score": 0.77,
            "moderation_data_full": {},
        }
    )
    Review.objects.create(content="a review")

    item = client.get(ENDPOINT).json()[0]

    assert item["status"] == "allowed"
    assert item["risk_score"] == 0.77
    assert "moderation_data_full" not in item

"""Tests for the Review model's defaults, ordering, and string form."""

from reviews.models import Review


def test_defaults_before_moderation_writes_them(db, stub_moderation):
    stub_moderation(
        result={
            "status": "pending",
            "risk_category": "appropriate",
            "risk_score": 0.0,
            "moderation_data_full": {},
        }
    )

    review = Review.objects.create(content="a review")

    assert review.status == "pending"
    assert review.risk_category == "appropriate"
    assert review.risk_score == 0.0
    assert review.moderation_data_full == {}
    assert review.created_at is not None


def test_ordering_is_newest_first(db, stub_moderation):
    stub_moderation()
    first = Review.objects.create(content="first")
    second = Review.objects.create(content="second")

    assert list(Review.objects.all()) == [second, first]


def test_str_shows_category_and_risk_score(db, stub_moderation):
    stub_moderation(
        result={
            "status": "to_be_deleted",
            "risk_category": "spam",
            "risk_score": 0.876,
            "moderation_data_full": {},
        }
    )

    review = Review.objects.create(content="buy things")

    assert str(review) == "spam: 0.88"

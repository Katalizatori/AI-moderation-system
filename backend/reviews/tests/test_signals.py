"""Tests for the pre_save auto_moderate signal.

The signal is what makes every Review.save() reach the network in production,
so these tests pin down when it runs and how it degrades on failure.
"""

from reviews.models import Review


def test_new_review_is_moderated(db, stub_moderation):
    calls = stub_moderation(
        result={
            "status": "to_be_deleted",
            "risk_category": "hate",
            "risk_score": 0.93,
            "moderation_data_full": {"flagged": True},
        }
    )

    review = Review.objects.create(content="something hateful")

    assert calls == ["something hateful"]
    assert review.status == "to_be_deleted"
    assert review.risk_category == "hate"
    assert review.risk_score == 0.93
    assert review.moderation_data_full == {"flagged": True}
    assert review.moderated_at is not None


def test_changed_content_is_remoderated(db, stub_moderation):
    calls = stub_moderation()
    review = Review.objects.create(content="original content")
    assert len(calls) == 1

    review.content = "edited content"
    review.save()

    assert calls == ["original content", "edited content"]


def test_unchanged_content_is_not_remoderated(db, stub_moderation):
    calls = stub_moderation()
    review = Review.objects.create(content="original content")

    review.status = "pending"
    review.save()

    assert len(calls) == 1, "moderation must not re-run when content is untouched"


def test_moderation_failure_falls_back_to_pending(db, stub_moderation):
    stub_moderation(raises=RuntimeError("service exploded"))

    review = Review.objects.create(content="anything")

    assert review.status == "pending"
    assert review.risk_category == "unknown"
    assert review.risk_score == 0.0
    assert review.moderation_data_full == {"error": "service exploded"}
    assert review.moderated_at is not None


def test_moderation_failure_does_not_block_the_save(db, stub_moderation):
    stub_moderation(raises=RuntimeError("service exploded"))

    review = Review.objects.create(content="anything")

    assert Review.objects.filter(pk=review.pk).exists()

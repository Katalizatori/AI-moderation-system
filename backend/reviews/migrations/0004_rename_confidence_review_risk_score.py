from django.db import migrations


def invert_allowed_scores(apps, schema_editor):
    """Convert stored values to the new "higher is worse" meaning.

    The old `confidence` field meant opposite things per branch: risk score on
    flagged content, but `1.0 - spam_score` on approved content. Only the
    approved rows need flipping; deleted and pending rows already stored a
    risk-shaped value.
    """
    Review = apps.get_model("reviews", "Review")
    for review in Review.objects.filter(status="allowed").iterator():
        review.risk_score = 1.0 - review.risk_score
        review.save(update_fields=["risk_score"])


def restore_allowed_scores(apps, schema_editor):
    Review = apps.get_model("reviews", "Review")
    for review in Review.objects.filter(status="allowed").iterator():
        review.risk_score = 1.0 - review.risk_score
        review.save(update_fields=["risk_score"])


class Migration(migrations.Migration):
    dependencies = [
        ("reviews", "0003_alter_review_moderated_at_alter_review_risk_category"),
    ]

    operations = [
        migrations.RenameField(
            model_name="review",
            old_name="confidence",
            new_name="risk_score",
        ),
        migrations.RunPython(invert_allowed_scores, restore_allowed_scores),
    ]

from django.apps import AppConfig

# Registering signals


class ReviewsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "reviews"

    def ready(self):
        # Imported for the side effect of registering the pre_save receiver.
        import reviews.signals  # noqa: F401

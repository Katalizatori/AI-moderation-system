from django.apps import AppConfig

# Registering signals


class ReviewsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "reviews"

    def ready(self):
        import reviews.signals

        print("Signals registered.")

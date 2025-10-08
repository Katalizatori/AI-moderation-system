from django.contrib import admin
from .models import Review


# Register your models here.

# !IMPORTANT: Review status is to be manually changed on the admin dashboard.

class ReviewAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "status",
        "risk_category",
        "confidence",
        "created_at",
    )
    list_filter = ("status", "risk_category", "created_at")
    search_fields = ("content",)
    readonly_fields = ("moderation_data_full", "created_at", "moderated_at")

admin.site.register(Review, ReviewAdmin)

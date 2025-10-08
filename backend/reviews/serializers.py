from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Review

# For reading / displaying the reviews
class ReviewSerializer(serializers.ModelSerializer):

    class Meta:
        model = Review
        fields = [
            "id",
            "content",
            "created_at",
            "status",
            "risk_category",
            "confidence",
            "moderated_at",
        ]
        read_only_fields = [
            "id",
            "created_at",
            "status",
            "risk_category",
            "confidence",
            "moderated_at",
        ]


# For POST only send in the actual content of the review
class ReviewCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Review
        fields = ["content"]

    def create(self, validated_data):
        return super().create(validated_data)

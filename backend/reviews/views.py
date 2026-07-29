# reviews/views.py

from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt  # For development only
from rest_framework import mixins, permissions, viewsets

from .models import Review
from .serializers import ReviewCreateSerializer, ReviewSerializer


# Bypassing / disabling authentication for the sake of simplicity
@method_decorator(csrf_exempt, name="dispatch")
class ReviewViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """Public read and submit only.

    Update and destroy are deliberately not exposed. Moderation runs on
    create, so an editable review would let a caller get benign content
    approved and then swap in whatever they liked.
    """

    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        return Review.objects.filter(status="allowed").order_by("-created_at")

    def get_serializer_class(self):
        if self.request.method == "POST":
            return ReviewCreateSerializer
        return ReviewSerializer

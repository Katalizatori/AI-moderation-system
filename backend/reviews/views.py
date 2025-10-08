# reviews/views.py

from rest_framework import viewsets, permissions
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt # For development only


from .models import Review
from .serializers import ReviewSerializer, ReviewCreateSerializer


# Create your views here.

# Bypassing / disabling authentication for the sake of simplicity
@method_decorator(csrf_exempt, name='dispatch')
class ReviewViewSet(viewsets.ModelViewSet):

    queryset = (
        Review.objects.filter(status="allowed")
        .order_by("-created_at")
    )
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        return Review.objects.filter(status="allowed").order_by("-created_at")

    def get_serializer_class(self):
        if self.request.method == "POST":
            return ReviewCreateSerializer
        return ReviewSerializer

    def perform_create(self, serializer):
        serializer.save()

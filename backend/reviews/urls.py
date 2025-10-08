from rest_framework.routers import DefaultRouter
from .views import ReviewViewSet


# Automatically generating RESTful URL patterns.
router = DefaultRouter()


router.register(r"reviews", ReviewViewSet, basename="reviews")

urlpatterns = router.urls

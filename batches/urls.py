from django.urls import path

from .views import RatioCalculatorView

urlpatterns = [
    path("calculator/", RatioCalculatorView.as_view(), name="ratio_calculator"),
]

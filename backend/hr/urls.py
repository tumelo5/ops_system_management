from django.urls import path
from .views import HRView

urlpatterns = [
    path("employees/", HRView.as_view(), name="employees"),
]
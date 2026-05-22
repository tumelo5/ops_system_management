from django.urls import path
from .views import ClientView, DeviceView, ClientListView

urlpatterns = [
    path("clients/",ClientView.as_view(),name="clients"),
    path("devices/",DeviceView.as_view(),name="devices"),
    path("clients/list/",ClientListView.as_view(),name="clients-list"),
]
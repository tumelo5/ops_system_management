from django.urls import path
from .views import ClientView, DeviceView, ClientListView, ModelListView, ModelVersionListView

urlpatterns = [
    path("clients/", ClientView.as_view(), name="clients"),
    path("devices/", DeviceView.as_view(), name="devices"),
    path("clients/list/", ClientListView.as_view(), name="clients-list"),
    path("models/list/", ModelListView.as_view(), name="models-list"),
    path("versions/list/", ModelVersionListView.as_view(), name="versions-list"),
]
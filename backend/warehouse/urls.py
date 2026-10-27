from django.urls import path
from .views import (ScanDeviceView, ClientListView, 
ModelListView, ModelVersionListView, ScanDeviceView, 
ConfirmDeviceView, ConfirmBulkDevicesView, BulkClientsView, 
BulkClientsLinkingView, ValidateSelectionView, NewVersionView, NewModelView,
ClientListView,
ClientCorrectionView, DeviceModelCorrectionView, DeviceModelVersionCorrectionView,
BatchReassignmentRequestView, BatchLookupView, DeviceRentalView, EndRentalView, ActiveRentalView,
CompanyView,EndRentalsView, RentableCheckView, ClientsAwaitingLinkingView           
)

urlpatterns = [
    path("clients/bulk/base/", BulkClientsView.as_view(), name="clients-bulk-base"),
    path("clients/bulk/links/", BulkClientsLinkingView.as_view(), name="clients-bulk-links"),
    path("clients/awaiting-linking/", ClientsAwaitingLinkingView.as_view(), name="clients-awaiting-linking"),

    # path("clients/", ClientListView.as_view(), name="clients-list"),
    # path("models/", DeviceModelListView.as_view(), name="models-list"),
    # path("versions/", DeviceModelVersionListView.as_view(), name="versions-list"),

    path("clients/existing/validate/", ValidateSelectionView.as_view(), name="clients-existing-validate"),
    path("clients/existing/new-version/", NewVersionView.as_view(), name="clients-existing-new-version"),
    path("clients/existing/new-model/", NewModelView.as_view(), name="clients-existing-new-model"),

    path("devices/", ScanDeviceView.as_view(), name="devices"),
    path("clients/list/", ClientListView.as_view(), name="clients-list"),
    path("models/list/", ModelListView.as_view(), name="models-list"),
    path("versions/list/", ModelVersionListView.as_view(), name="versions-list"),

    path("devices/scan/", ScanDeviceView.as_view(), name="devices-scan"),
    path("devices/confirm/", ConfirmDeviceView.as_view(), name="devices-confirm"),
    path("devices/confirm-bulk/", ConfirmBulkDevicesView.as_view(), name="devices-confirm-bulk"),

    path("batches/<int:batch_id>/reassign-request/", BatchReassignmentRequestView.as_view()),    path("clients/<int:client_id>/correct/", ClientCorrectionView.as_view()),
    path("models/<int:model_id>/correct/", DeviceModelCorrectionView.as_view()),
    path("model-versions/<int:version_id>/correct/", DeviceModelVersionCorrectionView.as_view()),
    path("batches/list/", BatchLookupView.as_view()),

   # POST  - Warehouse assigns company-owned devices to a client (bulk)
    path("devices/rentals/", DeviceRentalView.as_view(), name="device-rental-create"),
    # GET   - ?serial_number=...  scan on Assign Rental -> can this device be rented?
    path("devices/rentals/check/", RentableCheckView.as_view(), name="device-rental-check"),
    # GET   - ?serial_number=...  scan on End Rental -> active rental details
    path("devices/rentals/active/", ActiveRentalView.as_view(), name="device-rental-active"),
    # POST  - { rental_id, end_date }  close ONE rental
    path("devices/rentals/end/", EndRentalView.as_view(), name="device-rental-end"),
    # POST  - { rental_ids, end_date }  close MANY rentals, all-or-nothing
    path("devices/rentals/end/bulk/", EndRentalsView.as_view(), name="device-rental-end-bulk"),
    path("company/", CompanyView.as_view(), name="company"),
]
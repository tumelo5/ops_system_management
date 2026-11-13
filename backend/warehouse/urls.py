from django.urls import path

from .views import (
    # Clients, models, versions, batches
    BulkClientsView,
    BulkClientsLinkingView,
    ClientsAwaitingLinkingView,
    ValidateSelectionView,
    ExistingClientBatchView,
    ClientListView,
    ModelListView,
    ModelVersionListView,

    # Corrections
    ClientCorrectionView,
    DeviceModelCorrectionView,
    DeviceModelVersionCorrectionView,
    BatchCodeLookupView,
    BatchCodeCorrectionView,

    # Devices
    ScanDeviceView,
    
    # Rentals and company
    DeviceRentalView,
    RentableCheckView,
    ActiveRentalView,
    EndRentalView,
    EndRentalsView,
    CompanyView,
)

urlpatterns = [
    # Clients: Add Clients, Linking ---
    path("clients/bulk/base/", BulkClientsView.as_view(), name="clients-bulk-base"),
    path("clients/bulk/links/", BulkClientsLinkingView.as_view(), name="clients-bulk-links"),
    path("clients/awaiting-linking/", ClientsAwaitingLinkingView.as_view(), name="clients-awaiting-linking"),

    # Clients: Existing Client ---
    path("clients/existing/validate/", ValidateSelectionView.as_view(), name="clients-existing-validate"),
    path("clients/existing/batch/", ExistingClientBatchView.as_view(), name="clients-existing-batch"),

    # Dropdown lookups ---
    path("clients/list/", ClientListView.as_view(), name="clients-list"),
    path("models/list/", ModelListView.as_view(), name="models-list"),
    path("versions/list/", ModelVersionListView.as_view(), name="versions-list"),

    # Corrections (Correct Info tab) ---
    path("clients/<int:client_id>/correct/", ClientCorrectionView.as_view(), name="client-correction"),
    path("models/correct/", DeviceModelCorrectionView.as_view(), name="model-correction"),
    path("versions/<int:version_id>/correct/", DeviceModelVersionCorrectionView.as_view(), name="version-correction"),
    path("batch-codes/lookup/", BatchCodeLookupView.as_view(), name="batch-code-lookup"),
    path("batch-codes/<int:batch_id>/correct/", BatchCodeCorrectionView.as_view(), name="batch-code-correction"),

    # Devices: scan and confirm ---
    path("devices/", ScanDeviceView.as_view(), name="devices"),  # same view as devices/scan/, kept for existing callers
    path("devices/scan/", ScanDeviceView.as_view(), name="devices-scan"),

    # Rentals ---
    # POST - Warehouse assigns company-owned devices to a client (bulk)
    path("devices/rentals/", DeviceRentalView.as_view(), name="device-rental-create"),
    # GET  - ?serial_number=...  scan on Assign Rental -> can this device be rented?
    path("devices/rentals/check/", RentableCheckView.as_view(), name="device-rental-check"),
    # GET  - ?serial_number=...  scan on End Rental -> active rental details
    path("devices/rentals/active/", ActiveRentalView.as_view(), name="device-rental-active"),
    # POST - { rental_id, end_date }  close ONE rental
    path("devices/rentals/end/", EndRentalView.as_view(), name="device-rental-end"),
    # POST - { rental_ids, end_date }  close MANY rentals, all-or-nothing
    path("devices/rentals/end/bulk/", EndRentalsView.as_view(), name="device-rental-end-bulk"),

    # Company (the servicing company, set once) ---
    path("company/", CompanyView.as_view(), name="company"),
]
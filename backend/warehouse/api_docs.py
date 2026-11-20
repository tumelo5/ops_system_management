"""
Documentation-only helpers for drf-spectacular (Swagger).

Nothing here is used at request time: these serializers only describe request and
response shapes that the views build by hand, so the Swagger page can show them.
Keep them in step with the views if a payload changes.
"""
from drf_spectacular.utils import OpenApiResponse
from rest_framework import serializers

from .serializers import (
    ClientSerializer,
    EndedRentalSerializer,
)

# Tags: one per section of the Swagger page
CLIENTS = "Clients, models and batches"
CORRECTIONS = "Corrections"
DEVICES = "Devices"
RENTALS = "Rentals"
COMPANY = "Company"


# Error shapes
class ErrorSerializer(serializers.Serializer):
    """The error contract of this API: always a single readable string."""
    error = serializers.CharField()


class DetailSerializer(serializers.Serializer):
    """DRF's own 401/403 body (authentication and permission failures)."""
    detail = serializers.CharField()


class MessageSerializer(serializers.Serializer):
    message = serializers.CharField()


def err(description):
    return OpenApiResponse(ErrorSerializer, description=description)


AUTH_ERRORS = {
    401: OpenApiResponse(DetailSerializer, description="Missing or invalid access token."),
    403: OpenApiResponse(DetailSerializer, description="The user is not a Warehouse agent."),
}


# Clients, models and batches
class BulkClientsRequestSerializer(serializers.Serializer):
    clients = ClientSerializer(many=True)


class LinkItemSerializer(serializers.Serializer):
    client = serializers.IntegerField(help_text="Client id.")
    batch_code = serializers.CharField(max_length=100)
    model = serializers.CharField(max_length=100)
    version = serializers.CharField(max_length=50)


class BulkLinksRequestSerializer(serializers.Serializer):
    links = LinkItemSerializer(many=True)


class BatchOptionSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    batch_code = serializers.CharField()


class ValidateSelectionResponseSerializer(serializers.Serializer):
    batches = BatchOptionSerializer(many=True)


class ModelNameSerializer(serializers.Serializer):
    model = serializers.CharField()


# Devices
class ScanResponseSerializer(serializers.Serializer):
    message = serializers.CharField()
    serial_number = serializers.CharField()


# Corrections
class BatchLookupResponseSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    batch_code = serializers.CharField()
    client_name = serializers.CharField()
    model = serializers.CharField()
    version = serializers.CharField()
    correctable = serializers.BooleanField(
        help_text="False once devices exist under the batch: the code can no longer be corrected."
    )


# Rentals
class CreatedRentalSerializer(serializers.Serializer):
    rental_id = serializers.IntegerField()
    serial_number = serializers.CharField()
    client = serializers.CharField()


class RentalCreateResponseSerializer(serializers.Serializer):
    message = serializers.CharField()
    rentals = CreatedRentalSerializer(many=True)


class EndRentalResponseSerializer(serializers.Serializer):
    message = serializers.CharField()
    rental = EndedRentalSerializer()


class EndRentalsResponseSerializer(serializers.Serializer):
    message = serializers.CharField()
    rentals = EndedRentalSerializer(many=True)


# Company
class CompanyClientSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    client_name = serializers.CharField()


class CompanyStatusSerializer(serializers.Serializer):
    is_set = serializers.BooleanField()
    client = CompanyClientSerializer(allow_null=True)


class CompanySetResponseSerializer(CompanyStatusSerializer):
    message = serializers.CharField()
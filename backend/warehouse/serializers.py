import logging
from datetime import datetime

from django.utils import timezone
from rest_framework import serializers
from rest_framework.settings import api_settings

from .models import (
    Batch,
    Client,
    Device,
    DeviceModelVersion,
    DeviceRental,
    DeviceStaging,
)

logger = logging.getLogger("warehouse.api")

# Server-side caps. The frontend limits are a convenience, these are the real limits.
MAX_CLIENT_ROWS = 5
MAX_RENTAL_ROWS = 50



# Shared normalisation: client names, model names, versions and batch codes
# are stored stripped + lowercase. Every serializer calls this so the rules cannot drift.
def normalize(value):
    return value.strip().lower()


# Bulk (many=True) base: caps the row count, rejects an empty list, and rejects the
# same item appearing twice in one payload. Needs DRF 3.14+ for ListSerializer.max_length.
# A view can still override per call, e.g. Serializer(data=..., many=True, max_length=10).

class CappedListSerializer(serializers.ListSerializer):
    max_rows = None  # None = no cap
    allow_empty_default = False
    duplicate_message = "'{key}' appears more than once."

    default_error_messages = {
        "empty": "Add at least one row.",
        "max_length": "At most {max_length} rows can be submitted at once.",
    }

    @staticmethod
    def duplicate_key(item):
        """Return a hashable key for a validated item, or None to skip the duplicate check."""
        return None

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("allow_empty", self.allow_empty_default)
        if self.max_rows is not None:
            kwargs.setdefault("max_length", self.max_rows)
        super().__init__(*args, **kwargs)

    def to_internal_value(self, data):
        items = super().to_internal_value(data)
        seen = set()
        for item in items:
            key = self.duplicate_key(item)
            if key is None:
                continue
            if key in seen:
                raise serializers.ValidationError(
                    {api_settings.NON_FIELD_ERRORS_KEY: [self.duplicate_message.format(key=key)]}
                )
            seen.add(key)
        return items


class ClientListSerializer(CappedListSerializer):
    max_rows = MAX_CLIENT_ROWS
    duplicate_message = "Client '{key}' appears more than once."

    @staticmethod
    def duplicate_key(item):
        return item.get("client_name")


class BatchListSerializer(CappedListSerializer):
    # No row cap: set max_rows once the Linking form's limit is decided.
    duplicate_message = "Batch code '{key}' appears more than once."

    @staticmethod
    def duplicate_key(item):
        return item.get("batch_code")


class RentalListSerializer(CappedListSerializer):
    max_rows = MAX_RENTAL_ROWS
    duplicate_message = "Device '{key}' appears more than once."

    @staticmethod
    def duplicate_key(item):
        device = item.get("device")
        return device.serial_number if device is not None else None


# Clients
# Incoming data from the client creation form is normalised before it reaches the service.
class ClientSerializer(serializers.ModelSerializer):
    client_name = serializers.CharField(
        max_length=255,
        error_messages={
            "required": "Client name is required.",
            "blank": "Client name is required.",
            "null": "Client name is required.",
            "max_length": "Client name must be 255 characters or fewer.",
        },
    )

    def validate_client_name(self, value):
        normalized = normalize(value)
        logger.debug(f"ClientSerializer | validate_client_name | raw='{value}' normalized='{normalized}'")

        # Friendly read-only check. The DB unique constraint is still the real guard:
        # the service catches IntegrityError inside its own savepoint.
        if Client.objects.filter(client_name=normalized).exists():
            raise serializers.ValidationError(f"Client '{value.strip()}' already exists.")

        return normalized

    class Meta:
        model = Client
        fields = ["client_name"]
        list_serializer_class = ClientListSerializer


# Outgoing data for the client dropdown in batch code creation / rentals
class ClientDropDownSerializer(serializers.ModelSerializer):
    class Meta:
        model = Client
        fields = ["id", "client_name"]


# Batch (Linking / Existing Client). model_version is intentionally not a field here:
# the service receives it separately.
class BatchSerializer(serializers.ModelSerializer):
    batch_code = serializers.CharField(
        max_length=100,
        error_messages={
            "required": "Batch Code is required.",
            "blank": "Batch Code is required.",
            "null": "Batch Code is required.",
            "max_length": "Batch code must be 100 characters or fewer.",
        },
    )

    client = serializers.PrimaryKeyRelatedField(
        queryset=Client.objects.all(),
        error_messages={
            "required": "Client is required for Batch linking.",
            "null": "Client is required.",
            "does_not_exist": "Selected client does not exist.",
            "incorrect_type": "Select a valid client.",
        },
    )

    # The old to_internal_value override was removed: the required/blank/null messages
    # above already cover every case it handled (it ignored missing keys and non-dict input).

    def validate_batch_code(self, value):
        normalized = normalize(value)
        logger.debug(f"BatchSerializer | validate_batch_code | raw='{value}' normalized='{normalized}'")

        if Batch.objects.filter(batch_code=normalized).exists():
            raise serializers.ValidationError(f"Batch code '{value.strip()}' already exists.")

        return normalized

    class Meta:
        model = Batch
        fields = ["client", "batch_code"]
        list_serializer_class = BatchListSerializer


# Model / version (merged table: one DeviceModelVersion row = model + version).
# Versions are shared across clients, so an existing (model, version) is VALID input:
# the service reuses the existing record instead of creating a new one.
class DeviceModelVersionSerializer(serializers.ModelSerializer):
    version = serializers.CharField(
        max_length=50,
        error_messages={
            "required": "Model version is required.",
            "blank": "Model version is required.",
            "null": "Model version is required.",
            "max_length": "Model version must be 50 characters or fewer.",
        },
    )

    model = serializers.CharField(
        max_length=100,
        error_messages={
            "required": "Device model is required.",
            "blank": "Device model is required.",
            "null": "Device model is required.",
            "max_length": "Model name must be 100 characters or fewer.",
        },
    )

    def validate_model(self, value):
        normalized = normalize(value)
        logger.debug(f"DeviceModelVersionSerializer | validate_model | raw='{value}' normalized='{normalized}'")
        return normalized

    def validate_version(self, value):
        normalized = normalize(value)
        logger.debug(f"DeviceModelVersionSerializer | validate_version | raw='{value}' normalized='{normalized}'")
        return normalized

    class Meta:
        model = DeviceModelVersion
        fields = ["model", "version"]
        # An existing (model, version) is valid input: it is reused, not rejected.
        # Without this, DRF adds a UniqueTogetherValidator from the model's unique_together.
        validators = []


# Outgoing: versions of one model (Linking dropdown)
class ModelVersionDropDownSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeviceModelVersion
        fields = ["id", "version"]


# Scanning / confirming
# Case is deliberately left untouched here: the views never normalised serial numbers,
# so the service owns how they are stored and compared. If the service expects uppercase,
# add `return value.upper()` in validate_serial_number below.

class SerialNumberSerializer(serializers.Serializer):
    serial_number = serializers.CharField(
        max_length=100,
        error_messages={
            "required": "Serial number is required.",
            "blank": "Serial number is required.",
            "null": "Serial number is required.",
            "max_length": "Serial number must be 100 characters or fewer.",
        },
    )


class DeviceScanSerializer(SerialNumberSerializer):
    def validate_serial_number(self, value):
        # Format: <batch_code>-<device_id>
        parts = value.split("-")
        if len(parts) < 2 or not parts[0].strip() or not parts[1].strip():
            raise serializers.ValidationError("Invalid serial number.")
        return value


class ConfirmDevicesSerializer(serializers.Serializer):
    serial_numbers = serializers.ListField(
        child=serializers.CharField(
            max_length=100,
            error_messages={
                "blank": "Serial numbers cannot be blank.",
                "max_length": "Serial number must be 100 characters or fewer.",
            },
        ),
        allow_empty=False,
        error_messages={
            "required": "No serial numbers provided.",
            "null": "No serial numbers provided.",
            "empty": "No serial numbers provided.",
            "not_a_list": "serial_numbers must be a list.",
        },
    )


class DeviceStagingSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeviceStaging
        fields = [
            "serial_number",
            "batch_code",
            "client_name",
            "model",
            "version",
            "status",
        ]
        read_only_fields = fields


# Existing Client: check a client's model/version selection
class ValidateSelectionSerializer(serializers.Serializer):
    client = serializers.IntegerField(
        min_value=1,
        error_messages={
            "required": "client and version are required.",
            "null": "client and version are required.",
            "invalid": "client and version must be valid ids.",
            "min_value": "client and version must be valid ids.",
        },
    )
    version = serializers.IntegerField(
        min_value=1,
        error_messages={
            "required": "client and version are required.",
            "null": "client and version are required.",
            "invalid": "client and version must be valid ids.",
            "min_value": "client and version must be valid ids.",
        },
    )


# Corrections (Client / Model / Version / Batch code). Duplicate checks stay in the
# services: they know which record is being corrected, so it can keep its own value.

class ClientCorrectionSerializer(serializers.Serializer):
    client_name = serializers.CharField(
        max_length=255,
        error_messages={
            "required": "Client name is required.",
            "blank": "Client name is required.",
            "null": "Client name is required.",
            "max_length": "Client name must be 255 characters or fewer.",
        },
    )

    def validate_client_name(self, value):
        return normalize(value)


class ModelCorrectionSerializer(serializers.Serializer):
    model = serializers.CharField(
        error_messages={
            "required": "Select a model and enter the corrected name.",
            "blank": "Select a model and enter the corrected name.",
            "null": "Select a model and enter the corrected name.",
        },
    )
    new_model = serializers.CharField(
        max_length=100,
        error_messages={
            "required": "Select a model and enter the corrected name.",
            "blank": "Select a model and enter the corrected name.",
            "null": "Select a model and enter the corrected name.",
            "max_length": "Model name must be 100 characters or fewer.",
        },
    )

    def validate_model(self, value):
        return normalize(value)

    def validate_new_model(self, value):
        return normalize(value)


class VersionCorrectionSerializer(serializers.Serializer):
    # 50 = DeviceModelVersion.version max_length
    version = serializers.CharField(
        max_length=50,
        error_messages={
            "required": "Version is required.",
            "blank": "Version is required.",
            "null": "Version is required.",
            "max_length": "Version must be 50 characters or fewer.",
        },
    )

    def validate_version(self, value):
        return normalize(value)


class BatchCodeCorrectionSerializer(serializers.Serializer):
    batch_code = serializers.CharField(
        max_length=100,
        error_messages={
            "required": "Batch code is required.",
            "blank": "Batch code is required.",
            "null": "Batch code is required.",
            "max_length": "Batch code must be 100 characters or fewer.",
        },
    )

    def validate_batch_code(self, value):
        return normalize(value)


# Rentals

class DeviceRentalSerializer(serializers.ModelSerializer):
    device = serializers.SlugRelatedField(
        slug_field="serial_number",
        queryset=Device.objects.select_related("batch"),
        error_messages={
            "required": "Device is required for rental.",
            "null": "Device is required.",
            "does_not_exist": "No device with serial number '{value}' was found.",
            "invalid": "Invalid serial number.",
        },
    )
    rental_client = serializers.PrimaryKeyRelatedField(
        queryset=Client.objects.all(),
        error_messages={
            "required": "Rental client is required.",
            "null": "Rental client is required.",
            "does_not_exist": "The selected client does not exist.",
            "incorrect_type": "Invalid client.",
        },
    )

    class Meta:
        model = DeviceRental
        fields = ["device", "rental_client", "expected_return_date"]
        list_serializer_class = RentalListSerializer
        extra_kwargs = {
            "expected_return_date": {
                "error_messages": {"invalid": "Expected return date must be a valid date."}
            }
        }

    def validate_expected_return_date(self, value):
        if not value:
            return value
        # Works whether the model field is a DateTimeField or a DateField.
        if isinstance(value, datetime):
            not_future = value <= timezone.now()
        else:
            not_future = value <= timezone.localdate()
        if not_future:
            raise serializers.ValidationError("Expected return date must be in the future.")
        return value


class RentableDeviceSerializer(serializers.ModelSerializer):
    """Response of the scan-time check on Assign Rental.

    Build the queryset with select_related("batch__model_version") to avoid an N+1.
    """

    model = serializers.CharField(source="batch.model_version.model", read_only=True)
    version = serializers.CharField(source="batch.model_version.version", read_only=True)

    class Meta:
        model = Device
        fields = ["serial_number", "model", "version"]


class ActiveRentalSerializer(serializers.ModelSerializer):
    rental_id = serializers.IntegerField(source="id", read_only=True)
    serial_number = serializers.CharField(source="device.serial_number", read_only=True)
    client = serializers.CharField(source="rental_client.client_name", read_only=True)

    class Meta:
        model = DeviceRental
        fields = ["rental_id", "serial_number", "client", "start_date", "expected_return_date"]


# End ONE rental: { rental_id, end_date }. rental_id resolves to the DeviceRental instance.
class EndRentalSerializer(serializers.Serializer):
    rental_id = serializers.PrimaryKeyRelatedField(
        queryset=DeviceRental.objects.all(),
        error_messages={
            "required": "Rental is required.",
            "null": "Rental is required.",
            "does_not_exist": "Rental not found.",
            "incorrect_type": "Invalid rental.",
        },
    )
    end_date = serializers.DateField(
        error_messages={
            "required": "Choose an end date.",
            "invalid": "The end date must be a valid date (YYYY-MM-DD).",
        },
    )


# End MANY rentals with one shared end date.
class EndRentalsSerializer(serializers.Serializer):
    rental_ids = serializers.ListField(
        child=serializers.IntegerField(
            min_value=1,
            error_messages={
                "invalid": "Invalid rental id.",
                "min_value": "Invalid rental id.",
            },
        ),
        allow_empty=False,
        max_length=MAX_RENTAL_ROWS,
        error_messages={
            "required": "Scan at least one device.",
            "empty": "Scan at least one device.",
            "not_a_list": "Rental ids must be a list.",
            "max_length": f"A batch can hold at most {MAX_RENTAL_ROWS} devices.",
        },
    )
    end_date = serializers.DateField(
        error_messages={
            "required": "Choose an end date.",
            "invalid": "The end date must be a valid date (YYYY-MM-DD).",
        },
    )

    def validate_rental_ids(self, value):
        # De-duplicate, keep the scan order.
        return list(dict.fromkeys(value))


class EndedRentalSerializer(serializers.ModelSerializer):
    """Response of the end-rental calls: one entry per rental that was closed."""

    rental_id = serializers.IntegerField(source="id", read_only=True)
    serial_number = serializers.CharField(source="device.serial_number", read_only=True)
    client = serializers.CharField(source="rental_client.client_name", read_only=True)

    class Meta:
        model = DeviceRental
        fields = ["rental_id", "serial_number", "client", "returned_at"]


class SetCompanySerializer(serializers.Serializer):
    client = serializers.PrimaryKeyRelatedField(
        queryset=Client.objects.all(),
        error_messages={
            "required": "Select a client.",
            "null": "Select a client.",
            "does_not_exist": "Selected client does not exist.",
            "incorrect_type": "Select a valid client.",
        },
    )
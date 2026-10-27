from .models import (Client, DeviceModel, 
DeviceStaging, Device, 
Batch, DeviceModelVersion, 
BatchActionRequestGroup, 
DeviceRental
)

from rest_framework import serializers
from rest_framework.validators import UniqueValidator, UniqueTogetherValidator
import logging
from django.utils import timezone
from django.conf import settings
from .services import (CompanyService)

logger = logging.getLogger("warehouse.api")


# Incoming data from the client creation form is normalized to ensure consistency in the database.
class ClientSerializer(serializers.ModelSerializer):
    client_name = serializers.CharField(
        max_length=255,
        error_messages={
            "blank": "Client name is required.",
            "max_length": "Client name must be 255 characters or fewer.",
        }
    )

    def validate_client_name(self, value):
        normalized = value.strip().lower()
        logger.warning(f"ClientSerializer | validate_client_name | raw='{value}' normalized='{normalized}'")
        
        if Client.objects.filter(client_name=normalized).exists():
            raise serializers.ValidationError(f"Client '{value}' already exists.")

        return normalized

    class Meta:
        model = Client
        fields = ['client_name']


# Outgoing data for client retrieval, it includes id and client_name for selection/dropdown in batch code creation form
class ClientDropDownSerializer(serializers.ModelSerializer):
    class Meta:
        model = Client
        fields = ['id', 'client_name']


# Serialization for Batch - incoming data from batch code creation form is normalized to ensure consistency in the database.
class BatchSerializer(serializers.ModelSerializer):

    batch_code = serializers.CharField(
        error_messages={
            "required": "Batch Code is required.",
            "blank":    "Batch Code is required.",
            "null":     "Batch Code is required.",
        }
    )

    client = serializers.PrimaryKeyRelatedField(
        queryset=Client.objects.all(),
        error_messages={
            "required":       "Client is required for Batch linking.",
            "null":           "Client is required.",
            "does_not_exist": "Selected client does not exist.",
        }
    )

    model_version = serializers.PrimaryKeyRelatedField(
        queryset=DeviceModelVersion.objects.all(),
        required=False,
        error_messages={
            "does_not_exist": "Selected device model version does not exist.",
            }
    )

    def to_internal_value(self, data):
        errors = {}
        field_order = ['batch_code', 'client']

        for field in field_order:
            value = data.get(field)
            if not str(value).strip() and value != 0:
                errors[field] = [self.fields[field].error_messages.get('required', f'{field} is required.')]

        if errors:
            raise serializers.ValidationError(errors)
        return super().to_internal_value(data)

    def validate_batch_code(self, value):
        normalized = value.strip().lower()
        logger.warning(f"BatchSerializer | validate_batch_code | raw='{value}' normalized='{normalized}'")

        if Batch.objects.filter(batch_code=normalized).exists():
            raise serializers.ValidationError(f"Batch code '{value}' already exists.")

        return normalized

    class Meta:
        model = Batch
        fields = ['client', 'batch_code', 'model_version']


class DeviceModelSerializer(serializers.ModelSerializer):
    exists_message = "Model '{value}' already exists. Select the existing model instead in Linking section."

    model_name = serializers.CharField(
        max_length=100,
        error_messages={
            "required":   "Model name is required.",
            "null":       "Model name is required.",
            "blank":      "Model name is required.",
            "max_length": "Model name must be 100 characters or fewer.",
        }
    )

    def validate_model_name(self, value):
        normalized = value.strip().lower()
        logger.debug(f"{self.__class__.__name__} | validate_model_name | raw='{value}' normalized='{normalized}'")

        existing = DeviceModel.objects.filter(model_name=normalized)
        if self.instance is not None:          # a correction may keep its own name
            existing = existing.exclude(pk=self.instance.pk)
        if existing.exists():
            raise serializers.ValidationError(
                self.exists_message.format(value=value)
            )
        return normalized

    class Meta:
        model = DeviceModel
        fields = ['model_name', 'model_status']


# Add Clients: the model is optional. Blank or missing means "no model yet, pick it in Linking".
class OptionalDeviceModelSerializer(DeviceModelSerializer):
    exists_message = "Model '{name}' already exists. Leave the model blank and select it in the Linking section."


    model_name = serializers.CharField(
        max_length=100, required=False, allow_blank=True, allow_null=True,
        error_messages={"max_length": "Model name must be 100 characters or fewer."},
    )

    def validate_model_name(self, value):
        if not value or not value.strip():
            return ""
        return super().validate_model_name(value)


# Outgoing data for model version retrieval
class DeviceModelNameSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeviceModel
        fields = ['id', 'model_name']


# Keep your existing imports. UniqueTogetherValidator and ModelVersionListSerializer are
# no longer used: delete the ModelVersionListSerializer class, and the validator import
# if nothing else in the file needs it.


# Incoming data for model version creation.
#
# Versions are shared across clients: "Model X v1" is one record, and many clients'
# batches can point at it. So an existing (model, version) combination is VALID input.
# The service reuses the existing record instead of creating a new one.
# 
class DeviceModelVersionSerializer(serializers.ModelSerializer):
    # The fields that must be present. A class attribute so a subclass can change it.
    required_fields = ['version', 'model']

    version = serializers.CharField(
        error_messages={
            "required": "Model version is required.",
            "blank":    "Model version is required.",
            "null":     "Model version is required.",
        }
    )

    model = serializers.PrimaryKeyRelatedField(
        queryset=DeviceModel.objects.all(),
        error_messages={
            "required":       "Device model is required.",
            "null":           "Device model is required.",
            "does_not_exist": "Selected device model does not exist.",
        }
    )

    def to_internal_value(self, data):
        errors = {}

        for field in self.required_fields:
            value = data.get(field)
            if not value and value != 0:
                errors[field] = [self.fields[field].error_messages.get('required', f'{field} is required.')]

        if errors:
            raise serializers.ValidationError(errors)  # stops here, super() never runs

        return super().to_internal_value(data)

    def validate_version(self, value):
        normalized = value.strip().lower()
        logger.debug(f"{self.__class__.__name__} | validate_version | raw='{value}' normalized='{normalized}'")
        if not normalized:
            raise serializers.ValidationError("Model version is required.")
        return normalized

    class Meta:
        model = DeviceModelVersion
        fields = ['version', 'model', 'status']
        # ModelSerializer adds a UniqueTogetherValidator automatically from the model's
        # unique_together, so it has to be switched off explicitly. The database
        # constraint on (model, version) still guarantees there is only one record.
        validators = []


# Version text for a model that does not exist yet (Case 3: new model + new version).
# Same validation and normalisation as above, but there is no model id to check.
class NewModelVersionSerializer(DeviceModelVersionSerializer):
    model = None                      # removes the inherited field
    required_fields = ['version']

    class Meta(DeviceModelVersionSerializer.Meta):
        fields = ['version']
 

class DeviceScanSerializer(serializers.Serializer):
    serial_number = serializers.CharField(max_length=100)

    def validate_serial_number(self, value):
        normalized = value.strip().upper()
        logger.warning(f"DeviceScanSerializer | validate_serial_number | raw='{value}' normalized='{normalized}'")
        return normalized


class DeviceStagingSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeviceStaging
        fields = [
            'serial_number',
            'batch_code',
            'client_name',
            'model_name',
            'version_name',
            'status',
        ]
        read_only_fields = fields


class ModelVersionDropDownSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeviceModelVersion
        fields = ['id', 'version']


class BatchCorrectionSerializer(serializers.Serializer):
    client_id = serializers.IntegerField(required=False)
    model_version_id = serializers.IntegerField(required=False)
    reason = serializers.CharField(required=False, allow_blank=True, max_length=255)

    def validate(self, data):
        if not data.get('client_id') and not data.get('model_version_id'):
            raise serializers.ValidationError("Provide at least one of client_id or model_version_id.")
        return data


class ReferenceCorrectionSerializer(serializers.Serializer):
    field = serializers.CharField()
    value = serializers.CharField()


class BatchDetailSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    batch_code = serializers.CharField()
    client_name = serializers.CharField(source='client.client_name')
    model_name = serializers.CharField(source='model_version.model.model_name')
    version = serializers.CharField(source='model_version.version')


class BatchReassignmentRequestSerializer(serializers.Serializer):
    client_id = serializers.IntegerField()
    batch_code = serializers.CharField(max_length=100)
    reason = serializers.CharField(max_length=255, allow_blank=False)


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
 
    def validate_expected_return_date(self, value):
        if value and value <= timezone.now():
            raise serializers.ValidationError(
                "Expected return date must be in the future."
            )
        return value
 
 
class RentableDeviceSerializer(serializers.ModelSerializer):
    """Response of the scan-time check on Assign Rental."""
 
    # ASSUMPTION: Batch -> model_version -> model / version. If your scan endpoint
    # already has a device serializer returning serial_number, model_name and
    # version_name, reuse that one instead.
    model_name = serializers.CharField(source="batch.model_version.model.model_name", read_only=True)
    version_name = serializers.CharField(source="batch.model_version.version", read_only=True)
 
    class Meta:
        model = Device
        fields = ["serial_number", "model_name", "version_name"]
 
 
class ActiveRentalSerializer(serializers.ModelSerializer):
    rental_id = serializers.IntegerField(source="id", read_only=True)
    serial_number = serializers.CharField(source="device.serial_number", read_only=True)
    client = serializers.CharField(source="rental_client.client_name", read_only=True)
 
    class Meta:
        model = DeviceRental
        fields = ["rental_id", "serial_number", "client", "start_date", "expected_return_date"]
 
 
class EndRentalsSerializer(serializers.Serializer):
    rental_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        allow_empty=False,
        max_length=50,
        error_messages={
            "required": "Scan at least one device.",
            "empty": "Scan at least one device.",
            "not_a_list": "Rental ids must be a list.",
            "max_length": "A batch can hold at most 50 devices.",
        },
    )
    end_date = serializers.DateField(
        error_messages={
            "required": "Choose an end date.",
            "invalid": "The end date must be a valid date (YYYY-MM-DD).",
        },
    )
 
 
class EndedRentalSerializer(serializers.ModelSerializer):
    """Response of the bulk end: one entry per rental that was closed."""
 
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
        },
    )
 

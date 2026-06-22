from .models import Client, DeviceModel, DeviceStaging, Device, Batch, ModelVersion
from rest_framework import serializers
from rest_framework.validators import UniqueValidator
import logging

logger = logging.getLogger("warehouse.api")


# Incoming data from the client creation form is normalized to ensure consistency in the database.
class ClientSerializer(serializers.ModelSerializer):

    client_name = serializers.CharField(
        error_messages={
            "blank": "Client name is required."
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
            "required":       "Client is required.",
            "null":           "Client is required.",
            "does_not_exist": "Selected client does not exist.",
        }
    )

    model_version = serializers.PrimaryKeyRelatedField(
        queryset=ModelVersion.objects.all(),
        error_messages={
            "required":       "Model version is required.",
            "null":           "Model version is required.",
            "does_not_exist": "Selected model version does not exist.",
        }
    )

    def to_internal_value(self, data):
        errors = {}
        field_order = ['batch_code', 'client', 'model_version']
        for field in field_order:
            value = data.get(field)
            if not value and value != 0:
                errors[field] = [self.fields[field].error_messages.get('required', f'{field} is required.')]
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

    model_name = serializers.CharField(
        error_messages={
            "blank": "Model name is required.",
        }
    )

    def validate_model_name(self, value):
        normalized = value.strip().lower()
        logger.warning(f"DeviceModelSerializer | validate_model_name | raw='{value}' normalized='{normalized}'")
        return normalized

    class Meta:
        model = DeviceModel
        fields = ['model_name', 'model_status']


# Outgoing data for model version retrieval
class DeviceModelNameSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeviceModel
        fields = ['id', 'model_name']


# Incoming data for model version creation.
class ModelVersionSerializer(serializers.ModelSerializer):

    def validate_version(self, value):
        normalized = value.strip().lower()
        logger.warning(f"ModelVersionSerializer | validate_version | raw='{value}' normalized='{normalized}'")
        return normalized

    class Meta:
        model = ModelVersion
        fields = ['model', 'version', 'status']


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
        model = ModelVersion
        fields = ['id', 'version']
from .models import Client, DeviceModel, DeviceStaging, Device, Batch, ModelVersion
from rest_framework import serializers
import logging

logger = logging.getLogger("warehouse.api")


# Incoming data from the client creation form is normalized to ensure consistency in the database.
class ClientSerializer(serializers.ModelSerializer):

    def validate_client_name(self, value):
        normalized = value.strip().lower()
        logger.warning(f"ClientSerializer | validate_client_name | raw='{value}' normalized='{normalized}'")
        return normalized

    # to be reviewed if the status value should be capitalized or not as its already capitalized in the model
    def validate_client_status(self, value):
        normalized = value.strip().capitalize()
        logger.warning(f"ClientSerializer | validate_client_status | raw='{value}' normalized='{normalized}'")
        return normalized

    class Meta:
        model = Client
        fields = ['client_name', 'client_status']


# Outgoing data for client retrieval, it includes id and client_name for selection/dropdown in batch code creation form
class ClientDropDownSerializer(serializers.ModelSerializer):
    class Meta:
        model = Client
        fields = ['id', 'client_name']


# Serialization for Batch - incoming data from batch code creation form is normalized to ensure consistency in the database.
class BatchSerializer(serializers.ModelSerializer):

    def validate_batch_code(self, value):
        normalized = value.strip().lower()
        logger.warning(f"BatchSerializer | validate_batch_code | raw='{value}' normalized='{normalized}'")
        return normalized

    class Meta:
        model = Batch
        fields = ['client', 'batch_code']


class DeviceModelSerializer(serializers.ModelSerializer):

    def validate_model_name(self, value):
        normalized = value.strip().lower()
        logger.warning(f"DeviceModelSerializer | validate_model_name | raw='{value}' normalized='{normalized}'")
        return normalized

    def validate_model_status(self, value):
        normalized = value.strip().capitalize()
        logger.warning(f"DeviceModelSerializer | validate_model_status | raw='{value}' normalized='{normalized}'")
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

    def validate_status(self, value):
        normalized = value.strip().capitalize()
        logger.warning(f"ModelVersionSerializer | validate_status | raw='{value}' normalized='{normalized}'")
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
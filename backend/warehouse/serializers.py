from .models import Client, DeviceModel, DeviceStaging, Device, Batch, ModelVersion
from rest_framework import serializers

# Incoming data from the client creation form is normalized to ensure consistency in the database.
class ClientSerializer(serializers.ModelSerializer):

    def validate_client_name(self, value):
        return value.strip().lower()

    # to be reviewd if the status vaue should be capitalized or not as ts already capitalized in the model
    def validate_client_status(self, value): 
        return value.strip().capitalize()

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
        return value.strip().lower()

    class Meta:
        model = Batch
        fields = ['client', 'batch_code']

class DeviceModelSerializer(serializers.ModelSerializer):

    def validate_model_name(self, value):
        return value.strip().lower()

    def validate_model_status(self, value):
        return value.strip().capitalize()

    class Meta:
        model = DeviceModel
        fields = ['model_name', 'model_status']

# outgoing data for modelversion retrieval
class DeviceModelNameSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeviceModel
        fields = ['id', 'model_name']  # Assuming 'model' is the name of the field in DeviceModel that contains the model name

# Incoming data for model version creation.
class ModelVersionSerializer(serializers.ModelSerializer):

    def validate_version(self, value):
        return value.strip().lower()

    def validate_status(self, value):
        return value.strip().capitalize()

    class Meta:
        model = ModelVersion
        fields = ['model', 'version', 'status']


class DeviceScanSerializer(serializers.Serializer):
    serial_number = serializers.CharField(max_length=100)

    def validate_serial_number(self, value):
        return value.strip().upper() 

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
        

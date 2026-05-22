from .models import Client, DeviceModel, DeviceStaging, Device
from rest_framework import serializers


class ClientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Client
        fields = '__all__'
        read_only_fields = ['id']

    def create(self, validated_data):
        # Set the client_status to match the status of the first device model
        first_device_model = DeviceModel.objects.first()
        if first_device_model:
            validated_data['client_status'] = first_device_model.model_status
        else:
            validated_data['client_status'] = 'Unknown'  # Default status if no device models exist

        return super().create(validated_data)


class DeviceModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeviceModel
        fields = '__all__'
        read_only_fields = ['id']  


class DeviceStagingSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeviceStaging
        fields = '__all__'
        

class DeviceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Device
        fields = '__all__'
        read_only_fields = ['id']



'''
class DeviceSerializer(serializers.ModelSerializer):
    to be created for other departments to use as they 
    will need a few fields from the device table, but not all of them.

''' 
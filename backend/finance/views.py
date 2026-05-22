from rest_framework.viewsets import ModelViewSet
from django.db import transaction
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from rest_framework.exceptions import ValidationError
from .models import Client, DeviceModel, DeviceStaging, Device
from .serializers import ClientSerializer, DeviceModelSerializer, DeviceStagingSerializer, DeviceSerializer
import logging

# 
@action(detail=False, methods=['Post'])
def create_client(self, request):
    data = request.data
    if not data:
        return Response({"success": False, "message": "No data provided."}, status=status.HTTP_400_BAD_REQUEST)
    
   
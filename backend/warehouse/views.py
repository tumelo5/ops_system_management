import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .services import ClientService, DeviceService
from .serializers import (
    ClientSerializer, ClientDropDownSerializer,
    BatchSerializer, DeviceModelSerializer,
    DeviceModelNameSerializer, ModelVersionSerializer,
    DeviceStagingSerializer
)
from backend.common.permissions import IsWarehouseAgent


class ClientView(APIView):
    permission_classes = [IsWarehouseAgent]

    def post(self, request):
        mode = request.data.get("mode")

        handlers = {
            "single_client": self._handle_single_client,
            "bulk_clients":  self._handle_bulk_clients,
        }

        handler = handlers.get(mode)

        if not handler:
            return Response({"error": "Invalid mode"}, status=status.HTTP_400_BAD_REQUEST)

        return handler(request.data)

    def _handle_single_client(self, body):
        step = body.get("step")

        if step == "base":
            client_serializer = ClientSerializer(data=body)
            if not client_serializer.is_valid():
                return Response({"error": client_serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

            model_serializer = DeviceModelSerializer(data=body)
            if not model_serializer.is_valid():
                return Response({"error": model_serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

            client = ClientService.create_single_client(
                client_name=client_serializer.validated_data["client_name"],
                client_status=client_serializer.validated_data["client_status"]
            )

            device_model = ClientService.create_device_model(
                model_name=model_serializer.validated_data["model_name"],
                model_status=model_serializer.validated_data["model_status"]
            )

            all_clients = ClientService.get_clients_names()
            all_models  = ClientService.get_device_models()

            return Response({
                "message": f"{client.client_name} and {device_model.model_name} created successfully.",
                "clients": ClientDropDownSerializer(all_clients, many=True).data,
                "models":  DeviceModelNameSerializer(all_models, many=True).data
            }, status=status.HTTP_201_CREATED)

        if step == "linking":
            batch_serializer = BatchSerializer(data=body)
            if not batch_serializer.is_valid():
                return Response({"error": batch_serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

            version_serializer = ModelVersionSerializer(data=body)
            if not version_serializer.is_valid():
                return Response({"error": version_serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

            model_version = ClientService.create_model_version(
                model=version_serializer.validated_data["model"],
                version=version_serializer.validated_data["version"]
            )

            batch = ClientService.create_client_batchcode(
                client=batch_serializer.validated_data["client"],
                batch_code=batch_serializer.validated_data["batch_code"],
                model_version=model_version
            )

            return Response({
                "message": f"Batch code {batch.batch_code} and version {model_version.version} created successfully."
            }, status=status.HTTP_201_CREATED)

        return Response({"error": "Invalid step"}, status=status.HTTP_400_BAD_REQUEST)

    def _handle_bulk_clients(self, body):
        step = body.get("step")

        if step == "base":
            clients_data = body.get("clients", [])

            for entry in clients_data:
                client_serializer = ClientSerializer(data=entry)
                if not client_serializer.is_valid():
                    return Response({"error": client_serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

                model_serializer = DeviceModelSerializer(data=entry)
                if not model_serializer.is_valid():
                    return Response({"error": model_serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

            try:
                ClientService.create_bulk_base(clients_data)
            except ValueError as e:
                return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

            all_clients = ClientService.get_clients_names()
            all_models  = ClientService.get_device_models()

            return Response({
                "message": f"{len(clients_data)} clients and models created successfully.",
                "clients": ClientDropDownSerializer(all_clients, many=True).data,
                "models":  DeviceModelNameSerializer(all_models, many=True).data
            }, status=status.HTTP_201_CREATED)

        if step == "linking":
            links_data = body.get("links", [])

            for entry in links_data:
                batch_serializer = BatchSerializer(data=entry)
                if not batch_serializer.is_valid():
                    return Response({"error": batch_serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

                version_serializer = ModelVersionSerializer(data=entry)
                if not version_serializer.is_valid():
                    return Response({"error": version_serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

            ClientService.create_bulk_links(links_data)

            return Response({
                "message": f"{len(links_data)} batch codes and versions created successfully."
            }, status=status.HTTP_201_CREATED)

        return Response({"error": "Invalid step"}, status=status.HTTP_400_BAD_REQUEST)


class DeviceView(APIView):
    permission_classes = [IsWarehouseAgent]

    def post(self, request):
        mode = request.data.get("mode")

        handlers = {
            "scan":    self._handle_scan,
            "confirm": self._handle_confirm,
        }

        handler = handlers.get(mode)

        if not handler:
            return Response({"error": "Invalid mode"}, status=status.HTTP_400_BAD_REQUEST)

        return handler(request.data)

    def _handle_scan(self, body):
        serial_number = body.get("serial_number")

        if not serial_number:
            return Response({"error": "Serial number is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            staging = DeviceService.scan_device(serial_number)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        serializer = DeviceStagingSerializer(staging)

        return Response({
            "message": f"Device {staging.serial_number} scanned successfully.",
            "device":  serializer.data
        }, status=status.HTTP_200_OK)

    def _handle_confirm(self, body):
        serial_number = body.get("serial_number")

        if not serial_number:
            return Response({"error": "Serial number is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            device = DeviceService.confirm_device(serial_number)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response({
            "message": f"Device {device.serial_number} confirmed and set to ACTIVE."
        }, status=status.HTTP_201_CREATED)


class ClientListView(APIView):
    permission_classes = [IsWarehouseAgent]

    def get(self, request):
        try:
            clients = ClientService.get_clients_names()
            serializer = ClientDropDownSerializer(clients, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            logging.error(e)
            return Response({"error": "Failed to retrieve clients."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db import transaction
from .services import ClientService, DeviceService
from .serializers import (  
    ClientSerializer, ClientDropDownSerializer,
    BatchSerializer, DeviceModelSerializer,
    DeviceModelNameSerializer, ModelVersionSerializer,
    DeviceStagingSerializer, ModelVersionDropDownSerializer
)
from backend.common.permissions import IsWarehouseAgent

logger = logging.getLogger("warehouse.api")


class ClientView(APIView):
    # permission_classes = [IsWarehouseAgent]

    def post(self, request):
        mode = request.data.get("mode")
        logger.info(f"ClientView POST | user={request.user} | mode={mode}")

        handlers = {
            "single_client": self._handle_single_client,
            "bulk_clients":  self._handle_bulk_clients,
        }

        handler = handlers.get(mode)

        if not handler:
            logger.warning(f"ClientView POST | invalid mode={mode}")
            return Response({"error": "Invalid mode"}, status=status.HTTP_400_BAD_REQUEST)

        return handler(request)

    def _handle_single_client(self, request):
        step = request.data.get("step")
        logger.info(f"_handle_single_client | user={request.user} | step={step}")

        if step == "base":
            client_serializer = ClientSerializer(data=request.data)
            if not client_serializer.is_valid():
                logger.warning(f"_handle_single_client | base | client serializer invalid | errors={client_serializer.errors}")
                return Response({"error": client_serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

            model_serializer = DeviceModelSerializer(data=request.data)
            if not model_serializer.is_valid():
                logger.warning(f"_handle_single_client | base | model serializer invalid | errors={model_serializer.errors}")
                return Response({"error": model_serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

            try:
                with transaction.atomic():
                    client = ClientService.create_single_client(
                        client_name=client_serializer.validated_data["client_name"],
                        client_status=client_serializer.validated_data["client_status"]
                    )

                    device_model = ClientService.create_device_model(
                        model_name=model_serializer.validated_data["model_name"],
                        model_status=model_serializer.validated_data["model_status"]
                    )
            except Exception as e:
                logger.error(f"_handle_single_client | base | transaction failed | error={str(e)}", exc_info=True)
                return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

            logger.info(f"_handle_single_client | base | created client={client.client_name} model={device_model.model_name}")

            all_clients = ClientService.get_clients_names()
            all_models  = ClientService.get_device_models()

            return Response({
                "message": f"{client.client_name} and {device_model.model_name} created successfully.",
                "clients": ClientDropDownSerializer(all_clients, many=True).data,
                "models":  DeviceModelNameSerializer(all_models, many=True).data
            }, status=status.HTTP_201_CREATED)

        if step == "linking":
            batch_serializer = BatchSerializer(data=request.data)
            if not batch_serializer.is_valid():
                logger.warning(f"_handle_single_client | linking | batch serializer invalid | errors={batch_serializer.errors}")
                return Response({"error": batch_serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

            version_serializer = ModelVersionSerializer(data=request.data)
            if not version_serializer.is_valid():
                logger.warning(f"_handle_single_client | linking | version serializer invalid | errors={version_serializer.errors}")
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

            logger.info(f"_handle_single_client | linking | created batch={batch.batch_code} version={model_version.version}")

            return Response({
                "message": f"Batch code {batch.batch_code} and version {model_version.version} created successfully."
            }, status=status.HTTP_201_CREATED)

        logger.warning(f"_handle_single_client | invalid step={step}")
        return Response({"error": "Invalid step"}, status=status.HTTP_400_BAD_REQUEST)

    def _handle_bulk_clients(self, request):
        step = request.data.get("step")
        logger.info(f"_handle_bulk_clients | user={request.user} | step={step}")

        if step == "base":
            clients_data = request.data.get("clients", [])

            for entry in clients_data:
                client_serializer = ClientSerializer(data=entry)
                if not client_serializer.is_valid():
                    logger.warning(f"_handle_bulk_clients | base | client serializer invalid | errors={client_serializer.errors}")
                    return Response({"error": client_serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

                model_serializer = DeviceModelSerializer(data=entry)
                if not model_serializer.is_valid():
                    logger.warning(f"_handle_bulk_clients | base | model serializer invalid | errors={model_serializer.errors}")
                    return Response({"error": model_serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

            try:
                ClientService.create_bulk_base(clients_data)
            except ValueError as e:
                logger.error(f"_handle_bulk_clients | base | failed | error={str(e)}", exc_info=True)
                return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

            logger.info(f"_handle_bulk_clients | base | created {len(clients_data)} clients and models")

            all_clients = ClientService.get_clients_names()
            all_models  = ClientService.get_device_models()

            return Response({
                "message": f"{len(clients_data)} clients and models created successfully.",
                "clients": ClientDropDownSerializer(all_clients, many=True).data,
                "models":  DeviceModelNameSerializer(all_models, many=True).data
            }, status=status.HTTP_201_CREATED)

        if step == "linking":
            links_data = request.data.get("links", [])

            for entry in links_data:
                batch_serializer = BatchSerializer(data=entry)
                if not batch_serializer.is_valid():
                    logger.warning(f"_handle_bulk_clients | linking | batch serializer invalid | errors={batch_serializer.errors}")
                    return Response({"error": batch_serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

                version_serializer = ModelVersionSerializer(data=entry)
                if not version_serializer.is_valid():
                    logger.warning(f"_handle_bulk_clients | linking | version serializer invalid | errors={version_serializer.errors}")
                    return Response({"error": version_serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

            try:
                ClientService.create_bulk_links(links_data)
            except ValueError as e:
                logger.error(f"_handle_bulk_clients | linking | failed | error={str(e)}", exc_info=True)
                return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

            logger.info(f"_handle_bulk_clients | linking | created {len(links_data)} batch codes and versions")

            return Response({
                "message": f"{len(links_data)} batch codes and versions created successfully."
            }, status=status.HTTP_201_CREATED)

        logger.warning(f"_handle_bulk_clients | invalid step={step}")
        return Response({"error": "Invalid step"}, status=status.HTTP_400_BAD_REQUEST)


class DeviceView(APIView):
    # permission_classes = [IsWarehouseAgent]

    def post(self, request):
        mode = request.data.get("mode")
        logger.info(f"DeviceView POST | user={request.user} | mode={mode}")

        handlers = {
            "scan":           self._handle_scan,
            "confirm":        self._handle_confirm,
            "confirm_bulk":   self._handle_confirm_bulk,
        }

        handler = handlers.get(mode)

        if not handler:
            logger.warning(f"DeviceView POST | invalid mode={mode}")
            return Response({"error": "Invalid mode"}, status=status.HTTP_400_BAD_REQUEST)

        return handler(request)

    def _handle_scan(self, request):
        serial_number = request.data.get("serial_number")
        logger.info(f"_handle_scan | user={request.user} | serial_number={serial_number}")

        if not serial_number:
            logger.warning("_handle_scan | serial number missing")
            return Response({"error": "Serial number is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            staging = DeviceService.scan_device(serial_number)
        except ValueError as e:
            logger.error(f"_handle_scan | failed | serial_number={serial_number} | error={str(e)}", exc_info=True)
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        logger.info(f"_handle_scan | success | serial_number={staging.serial_number}")

        serializer = DeviceStagingSerializer(staging)

        return Response({
            "message": f"Device {staging.serial_number} scanned successfully.",
            "device":  serializer.data
        }, status=status.HTTP_200_OK)

    def _handle_confirm(self, request):
        serial_number = request.data.get("serial_number")
        logger.info(f"_handle_confirm | user={request.user} | serial_number={serial_number}")

        if not serial_number:
            logger.warning("_handle_confirm | serial number missing")
            return Response({"error": "Serial number is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            device = DeviceService.confirm_device(serial_number)
        except ValueError as e:
            logger.error(f"_handle_confirm | failed | serial_number={serial_number} | error={str(e)}", exc_info=True)
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        logger.info(f"_handle_confirm | success | serial_number={device.serial_number}")

        return Response({
            "message": f"Device {device.serial_number} confirmed and set to ACTIVE."
        }, status=status.HTTP_201_CREATED)

    def _handle_confirm_bulk(self, request):
        serial_numbers = request.data.get("serial_numbers", [])
        logger.info(f"_handle_confirm_bulk | user={request.user} | count={len(serial_numbers)}")

        if not serial_numbers:
            logger.warning("_handle_confirm_bulk | no serial numbers provided")
            return Response({"error": "No serial numbers provided."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            confirmed = DeviceService.confirm_bulk_devices(serial_numbers)
        except ValueError as e:
            logger.error(f"_handle_confirm_bulk | failed | error={str(e)}", exc_info=True)
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"_handle_confirm_bulk | unexpected failure | error={str(e)}", exc_info=True)
            return Response({"error": "Failed to confirm devices."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        logger.info(f"_handle_confirm_bulk | success | total_confirmed={len(confirmed)}")

        return Response({
            "message": f"{len(confirmed)} devices confirmed and set to ACTIVE."
        }, status=status.HTTP_201_CREATED)


class ClientListView(APIView):
    # permission_classes = [IsWarehouseAgent]

    def get(self, request):
        logger.info(f"ClientListView GET | user={request.user}")
        try:
            clients = ClientService.get_clients_names()
            serializer = ClientDropDownSerializer(clients, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"ClientListView GET | failed | error={str(e)}", exc_info=True)
            return Response({"error": "Failed to retrieve clients."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ModelListView(APIView):
    # permission_classes = [IsWarehouseAgent]

    def get(self, request):
        logger.info(f"ModelListView GET | user={request.user}")
        try:
            models = ClientService.get_all_models()
            serializer = DeviceModelNameSerializer(models, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"ModelListView GET | failed | error={str(e)}", exc_info=True)
            return Response({"error": "Failed to retrieve models."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ModelVersionListView(APIView):
    # permission_classes = [IsWarehouseAgent]

    def get(self, request):
        model_id = request.query_params.get("model")
        logger.info(f"ModelVersionListView GET | user={request.user} | model_id={model_id}")

        if not model_id:
            logger.warning("ModelVersionListView GET | model_id missing")
            return Response({"error": "model parameter is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            versions = ClientService.get_versions_by_model(model_id)
            serializer = ModelVersionDropDownSerializer(versions, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"ModelVersionListView GET | failed | error={str(e)}", exc_info=True)
            return Response({"error": "Failed to retrieve versions."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
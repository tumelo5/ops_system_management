import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .services import ClientService, DeviceService
from .serializers import (
    ClientSerializer, ClientDropDownSerializer,
    BatchSerializer, DeviceModelSerializer,
    DeviceModelNameSerializer, ModelVersionSerializer,
    DeviceStagingSerializer, ModelVersionDropDownSerializer
)
from backend.common.permissions import IsWarehouseAgent

logger = logging.getLogger("warehouse.api")


def _flatten_errors(errors):
    """
    Flatten DRF serializer error dicts into a single readable string.

    DRF's ModelSerializer returns validation errors as a dict e.g.:
        {"client_name": ["client with this client name already exists."]}

    This includes errors raised by auto-generated validators such as
    UniqueValidator, which DRF attaches automatically to fields marked
    unique=True on the model. These errors are caught at the serializer
    layer before the service layer is ever reached.

    Returning the raw dict to the frontend causes React to crash when
    it tries to render an object as a child component. This function
    ensures the API always returns {"error": "<string>"} regardless of
    which code path raises the error, keeping the error contract
    consistent for the frontend.
    """
    for field, errs in errors.items():
        for err in errs:
            return str(err)
    return "validation error."


class ClientView(APIView):
    permission_classes = [IsWarehouseAgent]

    def post(self, request):
        mode = request.data.get("mode")
        logger.info(f"ClientView POST | user={request.user} | mode={mode}")

        handlers = {
            "bulk_clients":    self._handle_bulk_clients,
            "existing_client": self._handle_existing_client,
        }

        handler = handlers.get(mode)

        if not handler:
            logger.warning(f"ClientView POST | invalid mode={mode}")
            return Response({"error": "Invalid mode"}, status=status.HTTP_400_BAD_REQUEST)

        return handler(request)

    # ------------------------------------------------------------------ #
    #  Bulk clients                                                        #
    # ------------------------------------------------------------------ #

    def _handle_bulk_clients(self, request):
        step = request.data.get("step")
        logger.info(f"_handle_bulk_clients | user={request.user} | step={step}")

        if step == "base":
            clients_data = request.data.get("clients", [])

            validated_entries = []

            for entry in clients_data:
                client_serializer = ClientSerializer(data=entry)
                if not client_serializer.is_valid():
                    logger.warning(f"_handle_bulk_clients | base | client serializer invalid | errors={client_serializer.errors}")
                    return Response({"error": _flatten_errors(client_serializer.errors)}, status=status.HTTP_400_BAD_REQUEST)

                model_serializer = DeviceModelSerializer(data=entry)
                if not model_serializer.is_valid():
                    logger.warning(f"_handle_bulk_clients | base | model serializer invalid | errors={model_serializer.errors}")
                    return Response({"error": _flatten_errors(model_serializer.errors)}, status=status.HTTP_400_BAD_REQUEST)

                validated_entries.append({
                    **client_serializer.validated_data,
                    **model_serializer.validated_data
                })

            try:
                ClientService.create_bulk_base(validated_entries)
            except ValueError as e:
                logger.warning(f"_handle_bulk_clients | base | conflict | error={str(e)}")
                return Response({"error": str(e)}, status=status.HTTP_409_CONFLICT)
            except Exception as e:
                logger.error(f"_handle_bulk_clients | base | failed | error={str(e)}", exc_info=True)
                return Response({"error": "Failed to create clients and models."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            logger.info(f"_handle_bulk_clients | base | created {len(validated_entries)} clients and models")

            all_clients = ClientService.get_clients_names()
            all_models  = ClientService.get_device_models()

            return Response({
                "message": f"{len(validated_entries)} clients and models created successfully.",
                "clients": ClientDropDownSerializer(all_clients, many=True).data,
                "models":  DeviceModelNameSerializer(all_models, many=True).data
            }, status=status.HTTP_201_CREATED)

        elif step == "linking":
            links_data = request.data.get("links", [])

            validated_links = []

            for entry in links_data:
                batch_serializer = BatchSerializer(data=entry)
                if not batch_serializer.is_valid():
                    logger.warning(f"_handle_bulk_clients | linking | batch serializer invalid | errors={batch_serializer.errors}")
                    return Response({"error": _flatten_errors(batch_serializer.errors)}, status=status.HTTP_400_BAD_REQUEST)

                version_serializer = ModelVersionSerializer(data=entry)
                if not version_serializer.is_valid():
                    logger.warning(f"_handle_bulk_clients | linking | version serializer invalid | errors={version_serializer.errors}")
                    return Response({"error": _flatten_errors(version_serializer.errors)}, status=status.HTTP_400_BAD_REQUEST)

                validated_links.append({
                    **batch_serializer.validated_data,
                    **version_serializer.validated_data
                })

            try:
                ClientService.create_bulk_links(validated_links)
            except ValueError as e:
                logger.warning(f"_handle_bulk_clients | linking | conflict | error={str(e)}")
                return Response({"error": str(e)}, status=status.HTTP_409_CONFLICT)
            except Exception as e:
                logger.error(f"_handle_bulk_clients | linking | failed | error={str(e)}", exc_info=True)
                return Response({"error": "Failed to create links."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            logger.info(f"_handle_bulk_clients | linking | created {len(validated_links)} batch codes and versions")

            return Response({
                "message": f"{len(validated_links)} batch codes and versions created successfully."
            }, status=status.HTTP_201_CREATED)

        else:
            logger.warning(f"_handle_bulk_clients | invalid step={step}")
            return Response({"error": "Invalid step"}, status=status.HTTP_400_BAD_REQUEST)

    # ------------------------------------------------------------------ #
    #  Existing client                                                     #
    # ------------------------------------------------------------------ #

    def _handle_existing_client(self, request):
        step = request.data.get("step")
        logger.info(f"_handle_existing_client | user={request.user} | step={step}")

        if step == "validate_selection":
            return self._handle_existing_client_validate_selection(request)
        elif step == "new_version":
            return self._handle_existing_client_new_version(request)
        elif step == "new_model":
            return self._handle_existing_client_new_model(request)
        else:
            logger.warning(f"_handle_existing_client | invalid step={step}")
            return Response({"error": "Invalid step"}, status=status.HTTP_400_BAD_REQUEST)

    def _handle_existing_client_validate_selection(self, request):
        """
        Case 1: Validates that a batch exists for the selected client, model, and version.
        Returns the batch code on success so the frontend can display it to the user.
        """
        client_id  = request.data.get("client")
        model_id   = request.data.get("model")
        version_id = request.data.get("version")

        logger.info(f"_handle_existing_client_validate_selection | client_id={client_id} model_id={model_id} version_id={version_id}")

        if not all([client_id, model_id, version_id]):
            logger.warning("_handle_existing_client_validate_selection | missing required fields")
            return Response({"error": "client, model, and version are all required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            batch = ClientService.validate_existing_selection(
                client_id=client_id,
                model_id=model_id,
                version_id=version_id,
            )
        except ValueError as e:
            logger.warning(f"_handle_existing_client_validate_selection | not found | error={str(e)}")
            return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"_handle_existing_client_validate_selection | failed | error={str(e)}", exc_info=True)
            return Response({"error": "Failed to validate selection."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        logger.info(f"_handle_existing_client_validate_selection | success | batch_code={batch.batch_code}")

        return Response({
            "message": f"Selection validated. Batch code '{batch.batch_code}' is ready for scanning.",
            "batch_code": batch.batch_code,
        }, status=status.HTTP_200_OK)

    def _handle_existing_client_new_version(self, request):
        """
        Case 2: Existing client, existing model, new version, new batch code.
        """
        client_id   = request.data.get("client")
        model_id    = request.data.get("model")
        new_version = request.data.get("version")
        batch_code  = request.data.get("batch_code")

        logger.info(f"_handle_existing_client_new_version | client_id={client_id} model_id={model_id} version={new_version} batch_code={batch_code}")

        if not all([client_id, model_id, new_version, batch_code]):
            logger.warning("_handle_existing_client_new_version | missing required fields")
            return Response({"error": "client, model, version, and batch_code are all required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            ClientService.create_existing_client_new_version(
                client_id=client_id,
                model_id=model_id,
                new_version=new_version,
                batch_code=batch_code,
            )
        except ValueError as e:
            logger.warning(f"_handle_existing_client_new_version | conflict | error={str(e)}")
            return Response({"error": str(e)}, status=status.HTTP_409_CONFLICT)
        except Exception as e:
            logger.error(f"_handle_existing_client_new_version | failed | error={str(e)}", exc_info=True)
            return Response({"error": "Failed to create version and batch code."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        logger.info(f"_handle_existing_client_new_version | success | batch_code={batch_code} version={new_version}")

        return Response({
            "message": f"New version '{new_version}' and batch code '{batch_code}' created successfully."
        }, status=status.HTTP_201_CREATED)

    def _handle_existing_client_new_model(self, request):
        """
        Case 3: Existing client, new model, new version, new batch code.
        """
        client_id      = request.data.get("client")
        new_model_name = request.data.get("model_name")
        new_version    = request.data.get("version")
        batch_code     = request.data.get("batch_code")

        logger.info(f"_handle_existing_client_new_model | client_id={client_id} model_name={new_model_name} version={new_version} batch_code={batch_code}")

        if not all([client_id, new_model_name, new_version, batch_code]):
            logger.warning("_handle_existing_client_new_model | missing required fields")
            return Response({"error": "client, model_name, version, and batch_code are all required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            ClientService.create_existing_client_new_model(
                client_id=client_id,
                new_model_name=new_model_name,
                new_version=new_version,
                batch_code=batch_code,
            )
        except ValueError as e:
            logger.warning(f"_handle_existing_client_new_model | conflict | error={str(e)}")
            return Response({"error": str(e)}, status=status.HTTP_409_CONFLICT)
        except Exception as e:
            logger.error(f"_handle_existing_client_new_model | failed | error={str(e)}", exc_info=True)
            return Response({"error": "Failed to create model, version, and batch code."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        logger.info(f"_handle_existing_client_new_model | success | model={new_model_name} version={new_version} batch_code={batch_code}")

        return Response({
            "message": f"New model '{new_model_name}', version '{new_version}', and batch code '{batch_code}' created successfully."
        }, status=status.HTTP_201_CREATED)


class DeviceView(APIView):
    permission_classes = [IsWarehouseAgent]

    def post(self, request):
        mode = request.data.get("mode")
        logger.info(f"DeviceView POST | user={request.user} | mode={mode}")

        handlers = {
            "scan":         self._handle_scan,
            "confirm":      self._handle_confirm,
            "confirm_bulk": self._handle_confirm_bulk,
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

        # SN must follow the format: <batch_code>-<device_id>
        # e.g. "BC001-00123" — both parts must be present and non-empty
        parts = serial_number.strip().split('-')
        if len(parts) < 2 or not parts[0].strip() or not parts[1].strip():
            logger.warning(f"_handle_scan | invalid serial number format | serial_number={serial_number}")
            return Response({"error": "Invalid serial number."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            staging = DeviceService.scan_device(serial_number)
        except ValueError as e:
            logger.warning(f"_handle_scan | conflict | serial_number={serial_number} | error={str(e)}")
            return Response({"error": str(e)}, status=status.HTTP_409_CONFLICT)
        except Exception as e:
            logger.error(f"_handle_scan | failed | serial_number={serial_number} | error={str(e)}", exc_info=True)
            return Response({"error": "Failed to scan device."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        logger.info(f"_handle_scan | success | serial_number={staging.serial_number}")

        serializer = DeviceStagingSerializer(staging)

        return Response({
            "message": f"Device {staging.serial_number} scanned successfully.",
            "device":  serializer.data
        }, status=status.HTTP_201_CREATED)

    def _handle_confirm(self, request):
        serial_number = request.data.get("serial_number")
        logger.info(f"_handle_confirm | user={request.user} | serial_number={serial_number}")

        if not serial_number:
            logger.warning("_handle_confirm | serial number missing")
            return Response({"error": "Serial number is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            device = DeviceService.confirm_device(serial_number)
        except ValueError as e:
            logger.warning(f"_handle_confirm | not found | serial_number={serial_number} | error={str(e)}")
            return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"_handle_confirm | failed | serial_number={serial_number} | error={str(e)}", exc_info=True)
            return Response({"error": "Failed to confirm device."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        logger.info(f"_handle_confirm | success | serial_number={device.serial_number}")

        return Response({
            "message": f"Device {device.serial_number} confirmed and set to ACTIVE."
        }, status=status.HTTP_200_OK)

    def _handle_confirm_bulk(self, request):
        serial_numbers = request.data.get("serial_numbers", [])
        logger.info(f"_handle_confirm_bulk | user={request.user} | count={len(serial_numbers)}")

        if not serial_numbers:
            logger.warning("_handle_confirm_bulk | no serial numbers provided")
            return Response({"error": "No serial numbers provided."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            confirmed = DeviceService.confirm_bulk_devices(serial_numbers)
        except ValueError as e:
            logger.warning(f"_handle_confirm_bulk | not found | error={str(e)}")
            return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"_handle_confirm_bulk | failed | error={str(e)}", exc_info=True)
            return Response({"error": "Failed to confirm devices."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        logger.info(f"_handle_confirm_bulk | success | total_confirmed={len(confirmed)}")

        return Response({
            "message": f"{len(confirmed)} devices confirmed and set to ACTIVE."
        }, status=status.HTTP_200_OK)


class ClientListView(APIView):
    permission_classes = [IsWarehouseAgent]

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
    permission_classes = [IsWarehouseAgent]

    def get(self, request):
        logger.info(f"ModelListView GET | user={request.user}")
        try:
            models = ClientService.get_device_models()
            serializer = DeviceModelNameSerializer(models, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"ModelListView GET | failed | error={str(e)}", exc_info=True)
            return Response({"error": "Failed to retrieve models."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ModelVersionListView(APIView):
    permission_classes = [IsWarehouseAgent]

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


"""
Here's what changed and the reasoning:
Handler dispatch — existing_client added to the handlers dict in ClientView.post(), routing to _handle_existing_client.
_handle_existing_client — thin router, just reads step and delegates to the correct method. Same pattern as _handle_bulk_clients.
_handle_existing_client_new_version (Case 2) — expects client, model, version, batch_code. Explicit all([...]) guard up front so missing fields return a clear 400 before the service is ever called.
_handle_existing_client_new_model (Case 3) — expects client, model_name, version, batch_code. Note model_name not model — there's no model ID to send since it doesn't exist yet.
Both handlers follow the exact same ValueError → 409, Exception → 500 pattern already established everywhere else in the file. Nothing new architecturally.
Next is BulkAddClientForm.jsx — the frontend needs handleExistingLinkingSubmit fixed to send the correct step names (new_version / new_model) with the correct payloads, plus the guard for Case 1 (existing version selected)
"""
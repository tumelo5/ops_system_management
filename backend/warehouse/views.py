import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .services import (
    ClientService, DeviceService,
    DeviceRentalService, RentalConflict,
    DeviceNotFound, CompanyService, CompanyAlreadySet,
    BatchCodeService, CorrectionConflict,
    )
from .serializers import (
    ClientSerializer, ClientDropDownSerializer,
    BatchSerializer, DeviceModelVersionSerializer,
    DeviceStagingSerializer, ModelVersionDropDownSerializer,
    SerialNumberSerializer, DeviceScanSerializer, ConfirmDevicesSerializer,
    ValidateSelectionSerializer,
    ClientCorrectionSerializer, ModelCorrectionSerializer,
    VersionCorrectionSerializer, BatchCodeCorrectionSerializer,
    DeviceRentalSerializer, SetCompanySerializer,
    ActiveRentalSerializer, EndedRentalSerializer,
    EndRentalSerializer, EndRentalsSerializer, RentableDeviceSerializer,
    )
from .models import Client, DeviceModelVersion, Batch
from backend.common.permissions import IsWarehouseAgent

logger = logging.getLogger("warehouse.api")


# To be moved to the common as it will be used in other files as well
def _first_message(errors):
    """Return the first error string found in a (possibly nested) DRF errors structure."""
    if isinstance(errors, dict):
        for value in errors.values():
            message = _first_message(value)
            if message:
                return message
    elif isinstance(errors, (list, tuple)):
        for item in errors:
            message = _first_message(item)
            if message:
                return message
    elif errors:
        return str(errors)
    return None


def _flatten_errors(errors):
    """
    Flatten DRF validation errors into a single readable string.

    DRF returns validation errors as a dict e.g.:
        {"client_name": ["client with this client name already exists."]}

    This includes errors raised by auto-generated validators such as
    UniqueValidator, which DRF attaches automatically to fields marked
    unique=True on the model. These errors are caught at the serializer
    layer before the service layer is ever reached.

    When the serializer is used with many=True, DRF returns a LIST of
    error dicts instead — one per input item, positionally aligned,
    with {} for items that passed validation e.g.:
        [{}, {"client_name": ["already exists."]}, {}]
    List-level errors (empty list, too many rows, duplicate rows) come back
    as {"non_field_errors": [...]}, and ListField errors are keyed by position
    e.g. {"serial_numbers": {0: ["..."]}}. This function returns the first
    error string found in any of these shapes.

    Returning the raw dict/list to the frontend causes React to crash when
    it tries to render an object as a child component. This function
    ensures the API always returns {"error": "<string>"} regardless of
    which code path raises the error, keeping the error contract
    consistent for the frontend.
    """
    return _first_message(errors) or "validation error."


# Helper function to validate multiple serializers and return the first error encountered.
def _first_validation_error(*serializers_list):
    """
    Validate each serializer in order. Returns a 400 Response for the first one that is
    invalid, or None when all of them are valid.
    """
    for serializer in serializers_list:
        if not serializer.is_valid():
            logger.warning(f"{serializer.__class__.__name__} | invalid | errors={serializer.errors}")
            return Response(
                {"error": _flatten_errors(serializer.errors)},
                status=status.HTTP_400_BAD_REQUEST,
            )
    return None


# Handles bulk creation of clients and device models.
class BulkClientsView(APIView):
    permission_classes = [IsWarehouseAgent]

    def post(self, request):
        clients_data = request.data.get("clients", [])
        logger.info(f"BulkClientsView POST | user={request.user} | count={len(clients_data)}")

        client_serializer = ClientSerializer(data=clients_data, many=True)
        if not client_serializer.is_valid():
            logger.warning(f"BulkClientsView POST | client serializer invalid | errors={client_serializer.errors}")
            return Response({"error": _flatten_errors(client_serializer.errors)}, status=status.HTTP_400_BAD_REQUEST)

        validated_entries = client_serializer.validated_data

        try:
            ClientService.create_bulk_base(validated_entries)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_409_CONFLICT)
        except Exception as e:
            logger.error(f"BulkClientsView POST | base | failed | error={str(e)}", exc_info=True)
            return Response({"error": "Failed to create clients."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        logger.info(f"BulkClientsView POST | base | created {len(validated_entries)} clients")

        return Response({
            "message": f"{len(validated_entries)} clients created successfully."
        }, status=status.HTTP_201_CREATED)


# Handles bulk linking of clients, batches, and model versions.
class BulkClientsLinkingView(APIView):
    permission_classes = [IsWarehouseAgent]

    def post(self, request):
        links_data = request.data.get("links", [])

        batch_serializer = BatchSerializer(data=links_data, many=True)
        if not batch_serializer.is_valid():
            logger.warning(f"BulkClientsLinkingView POST | linking | batch serializer invalid | errors={batch_serializer.errors}")
            return Response({"error": _flatten_errors(batch_serializer.errors)}, status=status.HTTP_400_BAD_REQUEST)

        version_serializer = DeviceModelVersionSerializer(data=links_data, many=True)
        if not version_serializer.is_valid():
            logger.warning(f"BulkClientsLinkingView POST | linking | version serializer invalid | errors={version_serializer.errors}")
            return Response({"error": _flatten_errors(version_serializer.errors)}, status=status.HTTP_400_BAD_REQUEST)

        validated_links = [
            {**batch_data, **version_data}
                for batch_data, version_data in zip(batch_serializer.validated_data, version_serializer.validated_data)
            ]

        try:
            ClientService.create_bulk_links(validated_links)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_409_CONFLICT)
        except Exception as e:
            logger.error(f"BulkClientsLinkingView POST | linking | failed | error={str(e)}", exc_info=True)
            return Response({"error": "Failed to create links."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        logger.info(f"BulkClientsLinkingView POST | linking | created {len(validated_links)} batch codes and versions")

        return Response({
            "message": f"{len(validated_links)} batch codes and versions created successfully."
        }, status=status.HTTP_201_CREATED)


class ClientsAwaitingLinkingView(APIView):
    permission_classes = [IsWarehouseAgent]

    def get(self, request):
        try:
            clients = ClientService.get_clients_awaiting_linking()
            return Response(list(clients), status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"ClientsAwaitingLinkingView GET | failed | error={str(e)}", exc_info=True)
            return Response(
                {"error": "Failed to fetch clients awaiting linking."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


# Validates a client's model and version selection for an existing batch.
class ValidateSelectionView(APIView):
    permission_classes = [IsWarehouseAgent]

    def post(self, request):
        """
        Returns the batches this client already has for the selected model and version.
        The list is empty when the client has not bought it yet.
        """
        logger.info(
            f"ValidateSelectionView | user={request.user} | client_id={request.data.get('client')} "
            f"version_id={request.data.get('version')}"
        )

        serializer = ValidateSelectionSerializer(data=request.data)
        error_response = _first_validation_error(serializer)
        if error_response:
            return error_response

        client_id = serializer.validated_data["client"]
        version_id = serializer.validated_data["version"]

        try:
            batches = ClientService.get_client_batches_for_version(client_id, version_id)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"ValidateSelectionView | failed | error={str(e)}", exc_info=True)
            return Response({"error": "Failed to check batches."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response({"batches": batches}, status=status.HTTP_200_OK)


class ExistingClientBatchView(APIView):
    permission_classes = [IsWarehouseAgent]

    def post(self, request):
        """
        Existing client, any model and version, new batch code.
        The product (model and version) is reused if it exists and created if not.
        """
        logger.info(
            f"ExistingClientBatchView | user={request.user} | client_id={request.data.get('client')} "
            f"model={request.data.get('model')} version={request.data.get('version')} "
            f"batch_code={request.data.get('batch_code')}"
        )

        batch_serializer = BatchSerializer(data=request.data)                  # client, batch_code
        product_serializer = DeviceModelVersionSerializer(data=request.data)   # model, version

        error_response = _first_validation_error(batch_serializer, product_serializer)
        if error_response:
            return error_response

        client = batch_serializer.validated_data["client"]
        batch_code = batch_serializer.validated_data["batch_code"]
        model = product_serializer.validated_data["model"]
        version = product_serializer.validated_data["version"]

        try:
            ClientService.create_existing_client_batch(
                client_id=client.id,
                model=model,
                version=version,
                batch_code=batch_code,
            )
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_409_CONFLICT)
        except Exception as e:
            logger.error(f"ExistingClientBatchView | failed | error={str(e)}", exc_info=True)
            return Response({"error": "Failed to create batch code."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        logger.info(f"ExistingClientBatchView | success | batch_code={batch_code} model={model} version={version}")

        return Response({
            "message": f"Batch code '{batch_code}' created for {model} {version}."
        }, status=status.HTTP_201_CREATED)


# Handles device scanning and staging before confirmation.
class ScanDeviceView(APIView):
    permission_classes = [IsWarehouseAgent]

    def post(self, request):
        logger.info(f"ScanDeviceView | user={request.user} | serial_number={request.data.get('serial_number')}")

        # SN must follow the format: <batch_code>-<device_id>
        serializer = DeviceScanSerializer(data=request.data)
        error_response = _first_validation_error(serializer)
        if error_response:
            return error_response

        serial_number = serializer.validated_data["serial_number"]

        try:
            staging = DeviceService.scan_device(serial_number)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_409_CONFLICT)
        except Exception as e:
            logger.error(f"ScanDeviceView | failed | serial_number={serial_number} | error={str(e)}", exc_info=True)
            return Response({"error": "Failed to scan device."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        logger.info(f"ScanDeviceView | success | serial_number={staging.serial_number}")

        return Response({
            "message": f"Device {staging.serial_number} scanned successfully.",
            "device":  DeviceStagingSerializer(staging).data
        }, status=status.HTTP_201_CREATED)


# Handles confirmation of a device and activation.
class ConfirmDeviceView(APIView):
    permission_classes = [IsWarehouseAgent]

    def post(self, request):
        logger.info(f"ConfirmDeviceView | user={request.user} | serial_number={request.data.get('serial_number')}")

        serializer = SerialNumberSerializer(data=request.data)
        error_response = _first_validation_error(serializer)
        if error_response:
            return error_response

        serial_number = serializer.validated_data["serial_number"]

        try:
            device = DeviceService.confirm_device(serial_number)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"ConfirmDeviceView | failed | serial_number={serial_number} | error={str(e)}", exc_info=True)
            return Response({"error": "Failed to confirm device."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        logger.info(f"ConfirmDeviceView | success | serial_number={device.serial_number}")

        return Response({
            "message": f"Device {device.serial_number} confirmed and set to ACTIVE."
        }, status=status.HTTP_200_OK)


# Handles bulk confirmation and activation of devices.
class ConfirmBulkDevicesView(APIView):
    permission_classes = [IsWarehouseAgent]

    def post(self, request):
        logger.info(f"ConfirmBulkDevicesView | user={request.user}")

        serializer = ConfirmDevicesSerializer(data=request.data)
        error_response = _first_validation_error(serializer)
        if error_response:
            return error_response

        serial_numbers = serializer.validated_data["serial_numbers"]

        try:
            confirmed = DeviceService.confirm_bulk_devices(serial_numbers)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"ConfirmBulkDevicesView | failed | error={str(e)}", exc_info=True)
            return Response({"error": "Failed to confirm devices."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        logger.info(f"ConfirmBulkDevicesView | success | total_confirmed={len(confirmed)}")

        return Response({
            "message": f"{len(confirmed)} devices confirmed and set to ACTIVE."
        }, status=status.HTTP_200_OK)



# Reference lookups (Client / Model / Version dropdowns) ---

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
            return Response(list(models), status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"ModelListView GET | failed | error={str(e)}", exc_info=True)
            return Response({"error": "Failed to retrieve models."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ModelVersionListView(APIView):
    permission_classes = [IsWarehouseAgent]

    def get(self, request):
        model = request.query_params.get("model", "").strip().lower()
        logger.info(f"ModelVersionListView GET | user={request.user} | model={model}")

        if not model:
            logger.warning("ModelVersionListView GET | model missing")
            return Response({"error": "model parameter is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            versions = ClientService.get_device_model_versions(model)
            serializer = ModelVersionDropDownSerializer(versions, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"ModelVersionListView GET | failed | error={str(e)}", exc_info=True)
            return Response({"error": "Failed to retrieve versions."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# Reference corrections (Client / Model / Version — always direct, self-service) ---
class ClientCorrectionView(APIView):
    permission_classes = [IsWarehouseAgent]

    def patch(self, request, client_id):
        serializer = ClientCorrectionSerializer(data=request.data)
        error_response = _first_validation_error(serializer)
        if error_response:
            return error_response
        data = serializer.validated_data

        try:
            ClientService.correct_reference(
                Client, client_id, {"client_name": data["client_name"]},
                user=request.user, reason=data.get("reason") or "",
            )
        except Client.DoesNotExist:
            return Response({"error": "Client not found."}, status=status.HTTP_404_NOT_FOUND)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_409_CONFLICT)
        return Response({"message": "Client corrected."}, status=status.HTTP_200_OK)


class DeviceModelCorrectionView(APIView):
    permission_classes = [IsWarehouseAgent]

    def patch(self, request):
        serializer = ModelCorrectionSerializer(data=request.data)
        error_response = _first_validation_error(serializer)
        if error_response:
            return error_response
        data = serializer.validated_data

        try:
            ClientService.rename_model(
                data["model"], data["new_model"], user=request.user, reason=data.get("reason") or "",
            )
        except DeviceModelVersion.DoesNotExist:
            return Response({"error": "Model not found."}, status=status.HTTP_404_NOT_FOUND)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_409_CONFLICT)
        return Response({"message": "Model corrected."}, status=status.HTTP_200_OK)


class DeviceModelVersionCorrectionView(APIView):
    permission_classes = [IsWarehouseAgent]

    def patch(self, request, version_id):
        serializer = VersionCorrectionSerializer(data=request.data)
        error_response = _first_validation_error(serializer)
        if error_response:
            return error_response
        data = serializer.validated_data

        try:
            ClientService.correct_reference(
                DeviceModelVersion, version_id, {"version": data["version"]},
                user=request.user, reason=data.get("reason") or "",
            )
        except DeviceModelVersion.DoesNotExist:
            return Response({"error": "Version not found."}, status=status.HTTP_404_NOT_FOUND)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_409_CONFLICT)
        return Response({"message": "Version corrected."}, status=status.HTTP_200_OK)


class BatchCodeLookupView(APIView):
    permission_classes = [IsWarehouseAgent]

    def get(self, request):
        batch_code = (request.query_params.get("batch_code") or "").strip().lower()
        if not batch_code:
            return Response({"error": "batch_code is required."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            data = BatchCodeService.find_batch(batch_code)
        except Batch.DoesNotExist:
            return Response({"error": f"No batch found with code '{batch_code}'."}, status=status.HTTP_404_NOT_FOUND)
        return Response(data, status=status.HTTP_200_OK)


class BatchCodeCorrectionView(APIView):
    permission_classes = [IsWarehouseAgent]

    def patch(self, request, batch_id):
        serializer = BatchCodeCorrectionSerializer(data=request.data)
        error_response = _first_validation_error(serializer)
        if error_response:
            return error_response
        data = serializer.validated_data

        try:
            BatchCodeService.correct_batch_code(
                batch_id, data["batch_code"], user=request.user, reason=data.get("reason") or "",
            )
        except Batch.DoesNotExist:
            return Response({"error": "Batch not found."}, status=status.HTTP_404_NOT_FOUND)
        except CorrectionConflict as e:
            return Response({"error": str(e)}, status=status.HTTP_409_CONFLICT)
        return Response({"message": "Batch code corrected."}, status=status.HTTP_200_OK)


# Device rental ---
class DeviceRentalView(APIView):
    permission_classes = [IsWarehouseAgent]

    def post(self, request):
        serializer = DeviceRentalSerializer(
            data=request.data, many=True, allow_empty=False, max_length=50
        )
        error_response = _first_validation_error(serializer)
        if error_response:
            return error_response

        try:
            rentals = DeviceRentalService.create_rentals(serializer.validated_data)
        except RentalConflict as e:
            return Response({"error": str(e)}, status=status.HTTP_409_CONFLICT)

        return Response(
            {
                "message": f"{len(rentals)} device(s) rented out.",
                "rentals": [
                    {
                        "rental_id": r.id,
                        "serial_number": r.device.serial_number,
                        "client": r.rental_client.client_name,
                    }
                    for r in rentals
                ],
            },
            status=status.HTTP_201_CREATED,
        )


# Scan-time check on Assign Rental ---
class RentableCheckView(APIView):
    """GET ?serial_number=SN -> 200 device info | 400 | 404 not found | 409 reason."""

    permission_classes = [IsWarehouseAgent]

    def get(self, request):
        serial_number = request.query_params.get("serial_number", "").strip()
        if not serial_number:
            return Response(
                {"error": "serial_number is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            device = DeviceRentalService.check_rentable(serial_number)
        except DeviceNotFound as e:
            return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)
        except RentalConflict as e:
            return Response({"error": str(e)}, status=status.HTTP_409_CONFLICT)
        return Response(RentableDeviceSerializer(device).data)


# Scan on End Rental ---
class ActiveRentalView(APIView):
    permission_classes = [IsWarehouseAgent]

    def get(self, request):
        serial_number = request.query_params.get("serial_number", "").strip()
        if not serial_number:
            return Response(
                {"error": "serial_number is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        rental = DeviceRentalService.get_active_rental(serial_number)
        if rental is None:
            return Response(
                {"error": "This device is not currently on rent."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(ActiveRentalSerializer(rental).data)


# End ONE rental: contract { rental_id, end_date } ---
class EndRentalView(APIView):
    permission_classes = [IsWarehouseAgent]

    def post(self, request):
        serializer = EndRentalSerializer(data=request.data)
        error_response = _first_validation_error(serializer)
        if error_response:
            return error_response
        data = serializer.validated_data
        try:
            rental = DeviceRentalService.end_rental(data["rental_id"].pk, data["end_date"])
        except RentalConflict as e:
            return Response({"error": str(e)}, status=status.HTTP_409_CONFLICT)
        return Response(
            {
                "message": f"Rental ended for {rental.device.serial_number}.",
                "rental": EndedRentalSerializer(rental).data,
            },
            status=status.HTTP_200_OK,
        )


# End MANY rentals, one shared end date, all-or-nothing ---
class EndRentalsView(APIView):
    permission_classes = [IsWarehouseAgent]

    def post(self, request):
        serializer = EndRentalsSerializer(data=request.data)
        error_response = _first_validation_error(serializer)
        if error_response:
            return error_response
        try:
            rentals = DeviceRentalService.end_rentals(
                serializer.validated_data["rental_ids"],
                serializer.validated_data["end_date"],
            )
        except RentalConflict as e:
            return Response({"error": str(e)}, status=status.HTTP_409_CONFLICT)
        return Response(
            {
                "message": f"{len(rentals)} rental(s) ended.",
                "rentals": EndedRentalSerializer(rentals, many=True).data,
            },
            status=status.HTTP_200_OK,
        )


def _company_payload(client):
    return {"is_set": client is not None,
            "client": {"id": client.id, "client_name": client.client_name} if client else None}


class CompanyView(APIView):
    permission_classes = [IsWarehouseAgent]

    def get(self, request):
        return Response(_company_payload(CompanyService.get_company_client_or_none()))

    def post(self, request):
        serializer = SetCompanySerializer(data=request.data)
        error_response = _first_validation_error(serializer)
        if error_response:
            return error_response
        try:
            profile = CompanyService.set_company(client=serializer.validated_data["client"], user=request.user)
        except CompanyAlreadySet as e:
            return Response({"error": str(e)}, status=status.HTTP_409_CONFLICT)
        return Response(
            {"message": f"{profile.client.client_name} is now set as the company.",
             **_company_payload(profile.client)},
            status=status.HTTP_201_CREATED,
        )
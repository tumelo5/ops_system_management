import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from drf_spectacular.utils import (
    extend_schema, OpenApiParameter, OpenApiExample,
)
from .api_docs import (
    CLIENTS, CORRECTIONS, DEVICES, RENTALS, COMPANY,
    AUTH_ERRORS, err, MessageSerializer,
    BulkClientsRequestSerializer, BulkLinksRequestSerializer, LinkItemSerializer,
    ValidateSelectionResponseSerializer, ModelNameSerializer,
    ScanResponseSerializer, BatchLookupResponseSerializer,
    RentalCreateResponseSerializer, EndRentalResponseSerializer, EndRentalsResponseSerializer,
    CompanyStatusSerializer, CompanySetResponseSerializer,
)
from .services import (
    ClientService, DeviceService,
    DeviceRentalService, RentalConflict,
    DeviceNotFound, CompanyService, CompanyAlreadySet,
    BatchCodeService, CorrectionConflict,
    )
from .serializers import (
    ClientSerializer, ClientDropDownSerializer,
    BatchSerializer, DeviceModelVersionSerializer,
    ModelVersionDropDownSerializer,
    DeviceScanSerializer,
    ValidateSelectionSerializer,
    ClientCorrectionSerializer, ModelCorrectionSerializer,
    VersionCorrectionSerializer, BatchCodeCorrectionSerializer,
    DeviceRentalSerializer, SetCompanySerializer,
    ActiveRentalSerializer, EndedRentalSerializer,
    EndRentalsSerializer, RentableDeviceSerializer,
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

    @extend_schema(
        tags=[CLIENTS],
        summary="Create clients in bulk",
        description="Creates several clients in one all-or-nothing request. Names are trimmed and lowercased. "
                    "One duplicate rolls back the whole request.",
        request=BulkClientsRequestSerializer,
        responses={
            201: MessageSerializer,
            400: err("Validation error: empty list, too many rows, duplicate or invalid names."),
            409: err("A client with that name already exists."),
            500: err("Unexpected server error."),
            **AUTH_ERRORS,
        },
        examples=[OpenApiExample(
            "Two clients",
            value={"clients": [{"client_name": "Client One"}, {"client_name": "Client Two"}]},
            request_only=True,
        )],
    )
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

    @extend_schema(
        tags=[CLIENTS],
        summary="Link clients to a batch code, model and version",
        description="Creates each client's FIRST batch. Clients that already have a batch must use "
                    "Existing Client. An existing (model, version) is reused, a new one is created.",
        request=BulkLinksRequestSerializer,
        responses={
            201: MessageSerializer,
            400: err("Validation error: invalid or duplicate batch code, missing client, model or version."),
            409: err("The client already has a batch, or the batch code already exists."),
            500: err("Unexpected server error."),
            **AUTH_ERRORS,
        },
        examples=[OpenApiExample(
            "One link",
            value={"links": [{"client": 1, "batch_code": "demo001", "model": "model-a", "version": "v1"}]},
            request_only=True,
        )],
    )
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

    @extend_schema(
        tags=[CLIENTS],
        summary="Clients that have no batch yet",
        description="The dropdown for the Linking step: only clients without a batch code.",
        responses={
            200: ClientDropDownSerializer(many=True),
            500: err("Unexpected server error."),
            **AUTH_ERRORS,
        },
    )
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

    @extend_schema(
        tags=[CLIENTS],
        summary="Batches a client already has for a model and version",
        description="An empty list means the client has not bought this product yet.",
        request=ValidateSelectionSerializer,
        responses={
            200: ValidateSelectionResponseSerializer,
            400: err("Validation error: client and version are required ids."),
            404: err("The client, or the model and version, does not exist."),
            500: err("Unexpected server error."),
            **AUTH_ERRORS,
        },
    )
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

    @extend_schema(
        tags=[CLIENTS],
        summary="Add a new batch for an existing client",
        description="Any model and version, new batch code. The product (model and version) is reused if it "
                    "exists and created if not.",
        request=LinkItemSerializer,
        responses={
            201: MessageSerializer,
            400: err("Validation error: invalid fields or a batch code that already exists."),
            409: err("The batch code already exists, or the client does not exist."),
            500: err("Unexpected server error."),
            **AUTH_ERRORS,
        },
    )
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


# Handles device scanning: each valid scan is saved straight to Device.
class ScanDeviceView(APIView):
    permission_classes = [IsWarehouseAgent]

    @extend_schema(
        tags=[DEVICES],
        summary="Scan a device",
        description="Matches the serial number to exactly one batch by its batch-code prefix and saves the "
                    "device straight to the Device table. The serial number is trimmed and lowercased.",
        request=DeviceScanSerializer,
        responses={
            201: ScanResponseSerializer,
            400: err("Validation error: serial number missing or too long."),
            409: err("No batch matches, more than one batch matches, or the device already exists."),
            500: err("Unexpected server error."),
            **AUTH_ERRORS,
        },
        examples=[OpenApiExample("Scan", value={"serial_number": "demo00101"}, request_only=True)],
    )
    def post(self, request):
        logger.info(f"ScanDeviceView | user={request.user} | serial_number={request.data.get('serial_number')}")

        # SN must follow the format: <batch_code>-<device_id>
        serializer = DeviceScanSerializer(data=request.data)
        error_response = _first_validation_error(serializer)
        if error_response:
            return error_response

        serial_number = serializer.validated_data["serial_number"]

        try:
            device = DeviceService.scan_device(serial_number)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_409_CONFLICT)
        except Exception as e:
            logger.error(f"ScanDeviceView | failed | serial_number={serial_number} | error={str(e)}", exc_info=True)
            return Response({"error": "Failed to scan device."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        logger.info(f"ScanDeviceView | success | serial_number={serial_number}")

        return Response({
            "message": f"Device {serial_number} scanned successfully.",
            "serial_number": serial_number,
        }, status=status.HTTP_201_CREATED)


# Reference lookups (Client / Model / Version dropdowns) ---

class ClientListView(APIView):
    permission_classes = [IsWarehouseAgent]

    @extend_schema(
        tags=[CLIENTS],
        summary="All clients (dropdown)",
        responses={
            200: ClientDropDownSerializer(many=True),
            500: err("Unexpected server error."),
            **AUTH_ERRORS,
        },
    )
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

    @extend_schema(
        tags=[CLIENTS],
        summary="Distinct model names (dropdown)",
        responses={
            200: ModelNameSerializer(many=True),
            500: err("Unexpected server error."),
            **AUTH_ERRORS,
        },
    )
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

    @extend_schema(
        tags=[CLIENTS],
        summary="Versions of one model (dropdown)",
        parameters=[OpenApiParameter(
            "model", str, OpenApiParameter.QUERY, required=True,
            description="Model name. It is trimmed and lowercased.",
        )],
        responses={
            200: ModelVersionDropDownSerializer(many=True),
            400: err("The model parameter is missing."),
            500: err("Unexpected server error."),
            **AUTH_ERRORS,
        },
    )
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

    @extend_schema(
        tags=[CORRECTIONS],
        summary="Correct a client's name",
        description="Direct correction: the name is changed in place.",
        request=ClientCorrectionSerializer,
        responses={
            200: MessageSerializer,
            400: err("Validation error."),
            404: err("Client not found."),
            409: err("That client name already exists."),
            **AUTH_ERRORS,
        },
    )
    def patch(self, request, client_id):
        serializer = ClientCorrectionSerializer(data=request.data)
        error_response = _first_validation_error(serializer)
        if error_response:
            return error_response
        data = serializer.validated_data

        try:
            ClientService.correct_reference(
                Client, client_id, {"client_name": data["client_name"]},
                user=request.user,
            )
        except Client.DoesNotExist:
            return Response({"error": "Client not found."}, status=status.HTTP_404_NOT_FOUND)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_409_CONFLICT)
        return Response({"message": "Client corrected."}, status=status.HTTP_200_OK)


class DeviceModelCorrectionView(APIView):
    permission_classes = [IsWarehouseAgent]

    @extend_schema(
        tags=[CORRECTIONS],
        summary="Rename a model",
        description="Every version of the model takes the new name.",
        request=ModelCorrectionSerializer,
        responses={
            200: MessageSerializer,
            400: err("Validation error."),
            404: err("Model not found."),
            409: err("A model with the new name already exists."),
            **AUTH_ERRORS,
        },
    )
    def patch(self, request):
        serializer = ModelCorrectionSerializer(data=request.data)
        error_response = _first_validation_error(serializer)
        if error_response:
            return error_response
        data = serializer.validated_data

        try:
            ClientService.rename_model(
                data["model"], data["new_model"], user=request.user,
            )
        except DeviceModelVersion.DoesNotExist:
            return Response({"error": "Model not found."}, status=status.HTTP_404_NOT_FOUND)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_409_CONFLICT)
        return Response({"message": "Model corrected."}, status=status.HTTP_200_OK)


class DeviceModelVersionCorrectionView(APIView):
    permission_classes = [IsWarehouseAgent]

    @extend_schema(
        tags=[CORRECTIONS],
        summary="Correct a version",
        request=VersionCorrectionSerializer,
        responses={
            200: MessageSerializer,
            400: err("Validation error."),
            404: err("Version not found."),
            409: err("That version already exists for the model."),
            **AUTH_ERRORS,
        },
    )
    def patch(self, request, version_id):
        serializer = VersionCorrectionSerializer(data=request.data)
        error_response = _first_validation_error(serializer)
        if error_response:
            return error_response
        data = serializer.validated_data

        try:
            ClientService.correct_reference(
                DeviceModelVersion, version_id, {"version": data["version"]},
                user=request.user,
            )
        except DeviceModelVersion.DoesNotExist:
            return Response({"error": "Version not found."}, status=status.HTTP_404_NOT_FOUND)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_409_CONFLICT)
        return Response({"message": "Version corrected."}, status=status.HTTP_200_OK)


class BatchCodeLookupView(APIView):
    permission_classes = [IsWarehouseAgent]

    @extend_schema(
        tags=[CORRECTIONS],
        summary="Look up a batch by its code",
        description="Used by the correction screen. `correctable` is false once devices exist under the batch.",
        parameters=[OpenApiParameter(
            "batch_code", str, OpenApiParameter.QUERY, required=True,
            description="Batch code. It is trimmed and lowercased.",
        )],
        responses={
            200: BatchLookupResponseSerializer,
            400: err("batch_code is missing."),
            404: err("No batch has that code."),
            **AUTH_ERRORS,
        },
    )
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

    @extend_schema(
        tags=[CORRECTIONS],
        summary="Correct a batch code",
        description="Only allowed while no device has been scanned or registered under the batch: a serial "
                    "number carries its batch code, so a code that real serial numbers use was not a typo.",
        request=BatchCodeCorrectionSerializer,
        responses={
            200: MessageSerializer,
            400: err("Validation error."),
            404: err("Batch not found."),
            409: err("Same code, code already exists, or devices already exist under the batch."),
            **AUTH_ERRORS,
        },
    )
    def patch(self, request, batch_id):
        serializer = BatchCodeCorrectionSerializer(data=request.data)
        error_response = _first_validation_error(serializer)
        if error_response:
            return error_response
        data = serializer.validated_data

        try:
            BatchCodeService.correct_batch_code(
                batch_id, data["batch_code"], user=request.user,
            )
        except Batch.DoesNotExist:
            return Response({"error": "Batch not found."}, status=status.HTTP_404_NOT_FOUND)
        except CorrectionConflict as e:
            return Response({"error": str(e)}, status=status.HTTP_409_CONFLICT)
        return Response({"message": "Batch code corrected."}, status=status.HTTP_200_OK)


# Device rental ---
class DeviceRentalView(APIView):
    permission_classes = [IsWarehouseAgent]

    @extend_schema(
        tags=[RENTALS],
        summary="Assign company-owned devices to a client",
        description="Bulk and all-or-nothing. Each device must belong to the servicing company, be ACTIVE and "
                    "not already rented, and cannot be rented to the company itself. The body is a list.",
        request=DeviceRentalSerializer(many=True),
        responses={
            201: RentalCreateResponseSerializer,
            400: err("Validation error: empty list, too many rows, unknown device or client, duplicate device."),
            409: err("A rental rule was broken, or the company has not been set up."),
            **AUTH_ERRORS,
        },
        examples=[OpenApiExample(
            "One device",
            value=[{"device": "demo00101", "rental_client": 2, "expected_return_date": "2027-03-01"}],
            request_only=True,
        )],
    )
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

    @extend_schema(
        tags=[RENTALS],
        summary="Scan-time check: can this device be rented?",
        description="Read-only. Create Rentals re-checks everything under lock at submit time.",
        parameters=[OpenApiParameter(
            "serial_number", str, OpenApiParameter.QUERY, required=True,
            description="Serial number of the scanned device.",
        )],
        responses={
            200: RentableDeviceSerializer,
            400: err("serial_number is missing."),
            404: err("Device not found."),
            409: err("The device cannot be rented: not company-owned, not active, or already rented."),
            **AUTH_ERRORS,
        },
    )
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

    @extend_schema(
        tags=[RENTALS],
        summary="Scan on End Rental: the device's active rental",
        parameters=[OpenApiParameter(
            "serial_number", str, OpenApiParameter.QUERY, required=True,
            description="Serial number of the scanned device.",
        )],
        responses={
            200: ActiveRentalSerializer,
            400: err("serial_number is missing."),
            404: err("This device is not currently on rent."),
            **AUTH_ERRORS,
        },
    )
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


# End one or many rentals, one shared end date, all-or-nothing ---
class EndRentalsView(APIView):
    permission_classes = [IsWarehouseAgent]

    @extend_schema(
        tags=[RENTALS],
        summary="End one or many rentals",
        description=(
            "Send one rental_id to end a single rental, or several to end them together "
            "with one shared end date. All-or-nothing: if one rental cannot be ended, "
            "none are, and the error names the device. The end date cannot be before "
            "a rental's start or in the future."
        ),
        request=EndRentalsSerializer,
        responses={
            200: EndRentalsResponseSerializer,
            400: err("Validation error: empty list, too many rentals or invalid date."),
            409: err("A rental does not exist, was already ended, or the end date is not allowed."),
            **AUTH_ERRORS,
        },
    )
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

        if len(rentals) == 1:
            message = f"Rental ended for {rentals[0].device.serial_number}."
        else:
            message = f"{len(rentals)} rentals ended."
        return Response(
            {"message": message, "rentals": EndedRentalSerializer(rentals, many=True).data},
            status=status.HTTP_200_OK,
        )


def _company_payload(client):
    return {"is_set": client is not None,
            "client": {"id": client.id, "client_name": client.client_name} if client else None}


class CompanyView(APIView):
    permission_classes = [IsWarehouseAgent]

    @extend_schema(
        tags=[COMPANY],
        summary="Is the servicing company set?",
        responses={200: CompanyStatusSerializer, **AUTH_ERRORS},
    )
    def get(self, request):
        return Response(_company_payload(CompanyService.get_company_client_or_none()))

    @extend_schema(
        tags=[COMPANY],
        summary="Set the servicing company (one time)",
        description="Can be done once. The company cannot be changed afterwards.",
        request=SetCompanySerializer,
        responses={
            201: CompanySetResponseSerializer,
            400: err("Validation error: select a valid client."),
            409: err("The company has already been set."),
            **AUTH_ERRORS,
        },
    )
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
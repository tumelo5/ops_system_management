import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .services import (
    ClientService, DeviceService,
    BatchService,
    DeviceRentalService, RentalConflict,
    DeviceNotFound, CompanyService,
    BatchCodeService,
    )
from .serializers import (
    ClientSerializer, ClientDropDownSerializer,
    BatchSerializer, DeviceModelVersionSerializer,
    DeviceStagingSerializer, ModelVersionDropDownSerializer,
    BatchCorrectionSerializer, ReferenceCorrectionSerializer,
    DeviceRentalSerializer,SetCompanySerializer,
    ActiveRentalSerializer, EndedRentalSerializer,
    EndRentalsSerializer, RentableDeviceSerializer,
    DeviceModelVersionSerializer )
from .models import Client,DeviceModelVersion, Batch
from backend.common.permissions import IsWarehouseAgent
# from core.throttling import BulkWriteThrottle

logger = logging.getLogger("warehouse.api")

# To be moved to the common as it will be used in other files as well
def _flatten_errors(errors):

    # this docstring is for documentation later
    """
    Flatten DRF serializer error dicts into a single readable string.

    DRF's ModelSerializer returns validation errors as a dict e.g.:
        {"client_name": ["client with this client name already exists."]}

    This includes errors raised by auto-generated validators such as
    UniqueValidator, which DRF attaches automatically to fields marked
    unique=True on the model. These errors are caught at the serializer
    layer before the service layer is ever reached.

    When the serializer is used with many=True, DRF returns a LIST of
    error dicts instead — one per input item, positionally aligned,
    with {} for items that passed validation e.g.:
        [{}, {"client_name": ["already exists."]}, {}]
    This function returns the first non-empty error found in that list.

    Returning the raw dict/list to the frontend causes React to crash when
    it tries to render an object as a child component. This function
    ensures the API always returns {"error": "<string>"} regardless of
    which code path raises the error, keeping the error contract
    consistent for the frontend.
    """
    # For function within this file.
    """
    Flatten DRF validation errors into a single readable string.
    Handles both single and many=True serializer errors.
    """
    if isinstance(errors, list):
        for item_errors in errors:
            if item_errors:
                return _flatten_errors(item_errors)
        return "validation error."

    for field, errs in errors.items():
        for err in errs:
            return str(err)
    return "validation error."


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
            logger.warning(f"BulkClientsView POST | base | conflict | error={str(e)}")
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
            logger.warning(f"BulkClientsLinkingView POST | linking | conflict | error={str(e)}")
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
        client_id  = request.data.get("client")
        version_id = request.data.get("version")

        logger.info(f"ValidateSelectionView | user={request.user} | client_id={client_id} version_id={version_id}")

        if not all([client_id, version_id]):
            logger.warning("ValidateSelectionView | missing required fields")
            return Response({"error": "client and version are required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            batches = ClientService.get_client_batches_for_version(client_id, version_id)
        except ValueError as e:
            logger.warning(f"ValidateSelectionView | not found | error={str(e)}")
            return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"ValidateSelectionView | failed | error={str(e)}", exc_info=True)
            return Response({"error": "Failed to check batches."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response({"batches": batches}, status=status.HTTP_200_OK)
        

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
            logger.warning(f"ExistingClientBatchView | conflict | error={str(e)}")
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
        serial_number = request.data.get("serial_number")
        logger.info(f"ScanDeviceView | user={request.user} | serial_number={serial_number}")

        if not serial_number:
            logger.warning("ScanDeviceView | serial number missing")
            return Response({"error": "Serial number is required."}, status=status.HTTP_400_BAD_REQUEST)

        # SN must follow the format: <batch_code>-<device_id>
        parts = serial_number.strip().split('-')
        if len(parts) < 2 or not parts[0].strip() or not parts[1].strip():
            logger.warning(f"ScanDeviceView | invalid serial number format | serial_number={serial_number}")
            return Response({"error": "Invalid serial number."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            staging = DeviceService.scan_device(serial_number)
        except ValueError as e:
            logger.warning(f"ScanDeviceView | conflict | serial_number={serial_number} | error={str(e)}")
            return Response({"error": str(e)}, status=status.HTTP_409_CONFLICT)
        except Exception as e:
            logger.error(f"ScanDeviceView | failed | serial_number={serial_number} | error={str(e)}", exc_info=True)
            return Response({"error": "Failed to scan device."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        logger.info(f"ScanDeviceView | success | serial_number={staging.serial_number}")

        serializer = DeviceStagingSerializer(staging)

        return Response({
            "message": f"Device {staging.serial_number} scanned successfully.",
            "device":  serializer.data
        }, status=status.HTTP_201_CREATED)


# Handles confirmation of a device and activation.
class ConfirmDeviceView(APIView):
    permission_classes = [IsWarehouseAgent]

    def post(self, request):
        serial_number = request.data.get("serial_number")
        logger.info(f"ConfirmDeviceView | user={request.user} | serial_number={serial_number}")

        if not serial_number:
            logger.warning("ConfirmDeviceView | serial number missing")
            return Response({"error": "Serial number is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            device = DeviceService.confirm_device(serial_number)
        except ValueError as e:
            logger.warning(f"ConfirmDeviceView | not found | serial_number={serial_number} | error={str(e)}")
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
        serial_numbers = request.data.get("serial_numbers", [])
        logger.info(f"ConfirmBulkDevicesView | user={request.user} | count={len(serial_numbers)}")

        if not serial_numbers:
            logger.warning("ConfirmBulkDevicesView | no serial numbers provided")
            return Response({"error": "No serial numbers provided."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            confirmed = DeviceService.confirm_bulk_devices(serial_numbers)
        except ValueError as e:
            logger.warning(f"ConfirmBulkDevicesView | not found | error={str(e)}")
            return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"ConfirmBulkDevicesView | failed | error={str(e)}", exc_info=True)
            return Response({"error": "Failed to confirm devices."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        logger.info(f"ConfirmBulkDevicesView | success | total_confirmed={len(confirmed)}")

        return Response({
            "message": f"{len(confirmed)} devices confirmed and set to ACTIVE."
        }, status=status.HTTP_200_OK)



# --- Reference lookups (Client / Model / Version dropdowns) ---

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

# --- Reference corrections (Client / Model / Version — always direct, self-service) ---
class ClientCorrectionView(APIView):
    permission_classes = [IsWarehouseAgent]

    def patch(self, request, client_id):
        new_name = (request.data.get("client_name") or "").strip().lower()
        if not new_name:
            return Response({"error": "Client name is required."}, status=status.HTTP_400_BAD_REQUEST)
        if len(new_name) > 255:
            return Response({"error": "Client name must be 255 characters or fewer."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            ClientService.correct_reference(
                Client, client_id, {"client_name": new_name},
                user=request.user, reason=request.data.get("reason", ""),
            )
        except Client.DoesNotExist:
            return Response({"error": "Client not found."}, status=status.HTTP_404_NOT_FOUND)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_409_CONFLICT)
        return Response({"message": "Client corrected."}, status=status.HTTP_200_OK)



class DeviceModelCorrectionView(APIView):
    permission_classes = [IsWarehouseAgent]

    def patch(self, request):
        old_name = (request.data.get("model") or "").strip().lower()
        new_name = (request.data.get("new_model") or "").strip().lower()
        if not old_name or not new_name:
            return Response({"error": "Select a model and enter the corrected name."}, status=status.HTTP_400_BAD_REQUEST)
        if len(new_name) > 100:
            return Response({"error": "Model name must be 100 characters or fewer."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            ClientService.rename_model(
                old_name, new_name, user=request.user, reason=request.data.get("reason", ""),
            )
        except DeviceModelVersion.DoesNotExist:
            return Response({"error": "Model not found."}, status=status.HTTP_404_NOT_FOUND)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_409_CONFLICT)
        return Response({"message": "Model corrected."}, status=status.HTTP_200_OK)


class DeviceModelVersionCorrectionView(APIView):
    permission_classes = [IsWarehouseAgent]

    def patch(self, request, version_id):
        new_version = (request.data.get("version") or "").strip().lower()
        if not new_version:
            return Response({"error": "Version is required."}, status=status.HTTP_400_BAD_REQUEST)
        if len(new_version) > 50:
            return Response({"error": "Version must be 50 characters or fewer."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            ClientService.correct_reference(
                DeviceModelVersion, version_id, {"version": new_version},
                user=request.user, reason=request.data.get("reason", ""),
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
        new_code = (request.data.get("batch_code") or "").strip().lower()
        if not new_code:
            return Response({"error": "Batch code is required."}, status=status.HTTP_400_BAD_REQUEST)
        if len(new_code) > 100:
            return Response({"error": "Batch code must be 100 characters or fewer."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            BatchCodeService.correct_batch_code(
                batch_id, new_code, user=request.user, reason=request.data.get("reason", ""),
            )
        except Batch.DoesNotExist:
            return Response({"error": "Batch not found."}, status=status.HTTP_404_NOT_FOUND)
        except CorrectionConflict as e:
            return Response({"error": str(e)}, status=status.HTTP_409_CONFLICT)
        return Response({"message": "Batch code corrected."}, status=status.HTTP_200_OK)


# --- Device rental (approval-gated) ---
class DeviceRentalView(APIView):
    permission_classes = [IsWarehouseAgent]
 
    def post(self, request):
        serializer = DeviceRentalSerializer(
            data=request.data, many=True, allow_empty=False, max_length=50
        )
        serializer.is_valid(raise_exception=True)
 
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
 
 
# --- Scan-time check on Assign Rental (NEW) ---
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
 
 
# --- Scan on End Rental (UNCHANGED) ---
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
 
 
# --- End ONE rental: the documented contract { rental_id, end_date } (RESTORED, replaces my old version) ---
class EndRentalView(APIView):
    permission_classes = [IsWarehouseAgent]
 
    def post(self, request):
        serializer = EndRentalSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
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
 
 
# --- End MANY rentals, one shared end date, all-or-nothing (NEW) ---
class EndRentalsView(APIView):
    permission_classes = [IsWarehouseAgent]
 
    def post(self, request):
        serializer = EndRentalsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
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
        serializer.is_valid(raise_exception=True)
        try:
            profile = CompanyService.set_company(client=serializer.validated_data["client"], user=request.user)
        except CompanyAlreadySet as e:
            return Response({"error": str(e)}, status=status.HTTP_409_CONFLICT)
        return Response(
            {"message": f"{profile.client.client_name} is now set as the company.",
             **_company_payload(profile.client)},
            status=status.HTTP_201_CREATED,
        )
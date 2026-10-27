import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .services import (
    ClientService, DeviceService,
    BatchService, BatchActionService,
    DeviceRentalService, RentalConflict, DeviceNotFound, CompanyService,
    )
from .serializers import (
    ClientSerializer, ClientDropDownSerializer,
    BatchSerializer, DeviceModelSerializer,
    DeviceModelNameSerializer, DeviceModelVersionSerializer,
    DeviceStagingSerializer, ModelVersionDropDownSerializer,
    BatchCorrectionSerializer, ReferenceCorrectionSerializer,
    BatchDetailSerializer, BatchReassignmentRequestSerializer,
    DeviceRentalSerializer,SetCompanySerializer,
    ActiveRentalSerializer, EndedRentalSerializer,
    EndRentalsSerializer, RentableDeviceSerializer, OptionalDeviceModelSerializer)
from .models import Client, DeviceModel, DeviceModelVersion, Batch
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
        logger.info(f"BulkClientsView POST | user={request.user} | count={len(request.data.get('clients', []))}")

        clients_data = request.data.get("clients", [])

        client_serializer = ClientSerializer(data=clients_data, many=True)
        if not client_serializer.is_valid():
            logger.warning(f"BulkClientsView POST | client serializer invalid | errors={client_serializer.errors}")
            return Response({"error": _flatten_errors(client_serializer.errors)}, status=status.HTTP_400_BAD_REQUEST)

        model_serializer = OptionalDeviceModelSerializer(data=clients_data, many=True)
        if not model_serializer.is_valid():
            logger.warning(f"BulkClientsView POST | model serializer invalid | errors={model_serializer.errors}")
            return Response({"error": _flatten_errors(model_serializer.errors)}, status=status.HTTP_400_BAD_REQUEST)

        validated_entries = [
            {**client_data, **model_data}
                for client_data, model_data in zip(client_serializer.validated_data, model_serializer.validated_data)
            ]

        try:
            ClientService.create_bulk_base(validated_entries)
        except ValueError as e:
            logger.warning(f"BulkClientsView POST | base | conflict | error={str(e)}")
            print(str(e))
            return Response({"error": str(e)}, status=status.HTTP_409_CONFLICT)
        except Exception as e:
            logger.error(f"BulkClientsView POST | base | failed | error={str(e)}", exc_info=True)
            return Response({"error": "Failed to create clients and models."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        logger.info(f"BulkClientsView POST | base | created {len(validated_entries)} clients and models")

        return Response({
            "message": f"{len(validated_entries)} clients and models created successfully."
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
        Case 1: Validates that a batch exists for the selected client, model, and version.
        Returns the batch code on success so the frontend can display it to the user.
        """
        client_id  = request.data.get("client")
        model_id   = request.data.get("model")
        version_id = request.data.get("version")

        logger.info(f"ValidateSelectionView | user={request.user} | client_id={client_id} model_id={model_id} version_id={version_id}")

        if not all([client_id, model_id, version_id]):
            logger.warning("ValidateSelectionView | missing required fields")
            return Response({"error": "client, model, and version are all required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            batch = ClientService.validate_existing_selection(
                client_id=client_id,
                model_id=model_id,
                version_id=version_id,
            )
        except ValueError as e:
            logger.warning(f"ValidateSelectionView | not found | error={str(e)}")
            return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"ValidateSelectionView | failed | error={str(e)}", exc_info=True)
            return Response({"error": "Failed to validate selection."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        logger.info(f"ValidateSelectionView | success | batch_code={batch.batch_code}")

        return Response({
            "message": f"Selection validated. Batch code '{batch.batch_code}' is ready for scanning.",
            "batch_code": batch.batch_code,
        }, status=status.HTTP_200_OK)

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
# --- Handles creation of new models/versions and their associated batches for existing clients ---
class NewVersionView(APIView):
    permission_classes = [IsWarehouseAgent]
 
    def post(self, request):
        """
        Case 2: Existing client, existing model, new version, new batch code.
        """
        logger.info(
            f"NewVersionView | user={request.user} | client_id={request.data.get('client')} "
            f"model_id={request.data.get('model')} version={request.data.get('version')} "
            f"batch_code={request.data.get('batch_code')}"
        )
 
        batch_serializer = BatchSerializer(data=request.data)                 # client, batch_code
        version_serializer = DeviceModelVersionSerializer(data=request.data)  # model, version
 
        error_response = _first_validation_error(batch_serializer, version_serializer)
        if error_response:
            return error_response
 
        client = batch_serializer.validated_data["client"]
        batch_code = batch_serializer.validated_data["batch_code"]
        model = version_serializer.validated_data["model"]
        new_version = version_serializer.validated_data["version"]
 
        try:
            ClientService.create_existing_client_new_version(
                client_id=client.id,
                model_id=model.id,
                new_version=new_version,
                batch_code=batch_code,
            )
        except ValueError as e:
            logger.warning(f"NewVersionView | conflict | error={str(e)}")
            return Response({"error": str(e)}, status=status.HTTP_409_CONFLICT)
        except Exception as e:
            logger.error(f"NewVersionView | failed | error={str(e)}", exc_info=True)
            return Response({"error": "Failed to create version and batch code."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
 
        logger.info(f"NewVersionView | success | batch_code={batch_code} version={new_version}")
 
        return Response({
            "message": f"New version '{new_version}' and batch code '{batch_code}' created successfully."
        }, status=status.HTTP_201_CREATED)


class NewModelView(APIView):
    permission_classes = [IsWarehouseAgent]
 
    def post(self, request):
        """
        Case 3: Existing client, new model, new version, new batch code.
        """
        logger.info(
            f"NewModelView | user={request.user} | client_id={request.data.get('client')} "
            f"model_name={request.data.get('model_name')} version={request.data.get('version')} "
            f"batch_code={request.data.get('batch_code')}"
        )
 
        batch_serializer = BatchSerializer(data=request.data)                   # client, batch_code
        model_serializer = DeviceModelSerializer(data=request.data)             # model_name (must not exist yet)
        version_serializer = NewModelVersionSerializer(data=request.data)       # version only
 
        error_response = _first_validation_error(batch_serializer, model_serializer, version_serializer)
        if error_response:
            return error_response
 
        client = batch_serializer.validated_data["client"]
        batch_code = batch_serializer.validated_data["batch_code"]
        new_model_name = model_serializer.validated_data["model_name"]
        new_version = version_serializer.validated_data["version"]
 
        try:
            ClientService.create_existing_client_new_model(
                client_id=client.id,
                new_model_name=new_model_name,
                new_version=new_version,
                batch_code=batch_code,
            )
        except ValueError as e:
            logger.warning(f"NewModelView | conflict | error={str(e)}")
            return Response({"error": str(e)}, status=status.HTTP_409_CONFLICT)
        except Exception as e:
            logger.error(f"NewModelView | failed | error={str(e)}", exc_info=True)
            return Response({"error": "Failed to create model, version, and batch code."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
 
        logger.info(f"NewModelView | success | model={new_model_name} version={new_version} batch_code={batch_code}")
 
        return Response({
            "message": f"New model '{new_model_name}', version '{new_version}', and batch code '{batch_code}' created successfully."
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
            versions = ClientService.get_device_model_versions(model_id)
            serializer = ModelVersionDropDownSerializer(versions, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"ModelVersionListView GET | failed | error={str(e)}", exc_info=True)
            return Response({"error": "Failed to retrieve versions."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# --- Reference corrections (Client / Model / Version — always direct, self-service) ---
class ClientCorrectionView(APIView):
    permission_classes = [IsWarehouseAgent]

    def patch(self, request, client_id):
        try:
            ClientService.correct_reference(
                Client, client_id,
                {"client_name": request.data.get("client_name")},
                user=request.user,
                reason=request.data.get("reason", ""),
            )
        except Client.DoesNotExist:
            return Response({"error": "Client not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response({"message": "Client corrected."}, status=status.HTTP_200_OK)


class DeviceModelCorrectionView(APIView):
    permission_classes = [IsWarehouseAgent]

    def patch(self, request, model_id):
        try:
            instance = DeviceModel.objects.get(id=model_id)
        except DeviceModel.DoesNotExist:
            return Response({"error": "Model not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = DeviceModelSerializer(
            instance, data={"model_name": request.data.get("model_name")}, partial=True
        )
        error_response = _first_validation_error(serializer)
        if error_response:
            return error_response

        try:
            ClientService.correct_reference(
                DeviceModel, model_id,
                {"model_name": serializer.validated_data["model_name"]},
                user=request.user,
                reason=request.data.get("reason", ""),
            )
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_409_CONFLICT)
        return Response({"message": "Model corrected."}, status=status.HTTP_200_OK)

class DeviceModelVersionCorrectionView(APIView):
    permission_classes = [IsWarehouseAgent]

    def patch(self, request, version_id):
        try:
            ClientService.correct_reference(
                DeviceModelVersion, version_id,
                {"version": request.data.get("version")},
                user=request.user,
                reason=request.data.get("reason", ""),
            )
        except DeviceModelVersion.DoesNotExist:
            return Response({"error": "Version not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response({"message": "Version corrected."}, status=status.HTTP_200_OK)



# --- Batch lookup & reassignment (approval-gated) ---
class BatchLookupView(APIView):
    permission_classes = [IsWarehouseAgent]

    def get(self, request):
        batch_code = request.query_params.get('batch_code')
        if not batch_code:
            return Response({"error": "batch_code is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            batch = BatchService.get_batch_by_code(batch_code)
        except Batch.DoesNotExist:
            return Response({"error": f"No batch found with code '{batch_code}'."}, status=status.HTTP_404_NOT_FOUND)

        return Response(BatchDetailSerializer(batch).data, status=status.HTTP_200_OK)


class BatchReassignmentRequestView(APIView):
    permission_classes = [IsWarehouseAgent]  # tighten to Manager later

    def post(self, request, batch_id):
        serializer = BatchReassignmentRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            group = BatchActionService.submit_reassignment_request(
                manager=request.user,
                batch_id=batch_id,
                client_id=serializer.validated_data["client_id"],
                batch_code=serializer.validated_data["batch_code"],
                reason=serializer.validated_data["reason"],
            )
        except Batch.DoesNotExist:
            return Response({"error": "Batch not found."}, status=status.HTTP_404_NOT_FOUND)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_409_CONFLICT)

        return Response({
            "message": "Reassignment request submitted — awaiting Finance approval.",
            "group_id": group.id,
        }, status=status.HTTP_201_CREATED)


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
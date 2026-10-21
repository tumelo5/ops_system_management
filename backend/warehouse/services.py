from django.db import transaction
from .models import (
    Client, Batch, DeviceModel, 
    DeviceModelVersion, Device, 
    DeviceStaging, BatchCorrection,
    BatchActionRequestGroup, BatchActionRequest,
    DeviceRental, CompanyProfile
)
import logging
from django.db import IntegrityError
from django.utils import timezone
from django.conf import settings
from datetime import timedelta

logger = logging.getLogger("warehouse.services")

class ClientService:

    @staticmethod
    @transaction.atomic
    def create_bulk_base(clients_data):
        # The created (created = []) list is not in use, look inot it for code cleaning
        logger.info(f"create_bulk_base | starting | count={len(clients_data)}")
        created = []

        for entry in clients_data:
            try:
                client = Client.objects.create(client_name=entry["client_name"])
            except IntegrityError:
                logger.warning(f"create_bulk_base | client already exists | client_name={entry['client_name']}")
                raise ValueError(f"Client '{entry['client_name']}' already exists.")

            try:
                device_model = DeviceModel.objects.create(model_name=entry["model_name"])
            except IntegrityError:
                logger.warning(f"create_bulk_base | model already exists | model_name={entry['model_name']}")
                raise ValueError(f"Model '{entry['model_name']}' already exists.")

            created.append({"client": client, "device_model": device_model})
            logger.info(f"create_bulk_base | created client={client.client_name} model={device_model.model_name}")

        logger.info(f"create_bulk_base | success | total_created={len(created)}")
        return created

    @staticmethod
    @transaction.atomic
    def create_bulk_links(links_data):

        logger.info(f"create_bulk_links | starting | count={len(links_data)}")
        created = []

        for entry in links_data:

            # NEW: Linking is only for a client's first batch.
            # Any further batch must go through Existing Client.
            if Batch.objects.filter(client=entry["client"]).exists():
                logger.warning(f"create_bulk_links | client already has a batch | client={entry['client']}")
                raise ValueError(
                    f"Client '{entry['client'].client_name}' already has a batch code. "
                    "Use Existing Client to add more."
                )

            try:
                model_version = DeviceModelVersion.objects.create(model=entry["model"], version=entry["version"])
            except IntegrityError:
                logger.warning(f"create_bulk_links | version already exists | model={entry['model']} version={entry['version']}")
                raise ValueError(f"Version '{entry['version']}' already exists for this model.")

            try:
                batch = Batch.objects.create(client=entry["client"], batch_code=entry["batch_code"], model_version=model_version)
            except IntegrityError:
                logger.warning(f"create_bulk_links | batch code already exists | batch_code={entry['batch_code']}")
                raise ValueError(f"Batch code '{entry['batch_code']}' already exists.")

            created.append({"batch": batch, "model_version": model_version})
            logger.info(f"create_bulk_links | created batch={batch.batch_code} version={model_version.version}")

        logger.info(f"create_bulk_links | success | total_created={len(created)}")
        return created

    @staticmethod
    @transaction.atomic
    def create_existing_client_new_version(client_id, model_id, new_version, batch_code):
        """
        Case 2: Existing client, existing model, new version → new batch code.

        Looks up the client and model by ID (both must already exist),
        creates a new ModelVersion, then creates a new Batch linking
        the client to that version.
        """
        logger.info(f"create_existing_client_new_version | client_id={client_id} model_id={model_id} new_version={new_version} batch_code={batch_code}")

        try:
            client = Client.objects.get(id=client_id)
        except Client.DoesNotExist:
            logger.warning(f"create_existing_client_new_version | client not found | client_id={client_id}")
            raise ValueError(f"Client with id '{client_id}' does not exist.")

        try:
            model = DeviceModel.objects.get(id=model_id)
        except DeviceModel.DoesNotExist:
            logger.warning(f"create_existing_client_new_version | model not found | model_id={model_id}")
            raise ValueError(f"Device model with id '{model_id}' does not exist.")

        try:
            model_version = DeviceModelVersion.objects.create(model=model, version=new_version)
        except IntegrityError:
            logger.warning(f"create_existing_client_new_version | version already exists | model={model} version={new_version}")
            raise ValueError(f"Version '{new_version}' already exists for model '{model.model_name}'.")

        try:
            batch = Batch.objects.create(client=client, batch_code=batch_code, model_version=model_version)
        except IntegrityError:
            logger.warning(f"create_existing_client_new_version | batch code already exists | batch_code={batch_code}")
            raise ValueError(f"Batch code '{batch_code}' already exists.")

        logger.info(f"create_existing_client_new_version | success | batch_id={batch.id} version_id={model_version.id}")
        return batch

    @staticmethod
    @transaction.atomic
    def create_existing_client_new_model(client_id, new_model_name, new_version, batch_code):
        """
        Case 3: Existing client, new model, new version → new batch code.

        Looks up the client by ID (must already exist), creates a new
        DeviceModel, a new ModelVersion under it, then creates a new
        Batch linking the client to that version.
        """
        logger.info(f"create_existing_client_new_model | client_id={client_id} new_model_name={new_model_name} new_version={new_version} batch_code={batch_code}")

        try:
            client = Client.objects.get(id=client_id)
        except Client.DoesNotExist:
            logger.warning(f"create_existing_client_new_model | client not found | client_id={client_id}")
            raise ValueError(f"Client with id '{client_id}' does not exist.")

        # DeviceModel is intentionally not unique-checked by name —
        # the same model name can exist across different clients.
        model = DeviceModel.objects.create(model_name=new_model_name)
        model_version = DeviceModelVersion.objects.create(model=model, version=new_version)

        try:
            batch = Batch.objects.create(client=client, batch_code=batch_code, model_version=model_version)
        except IntegrityError:
            logger.warning(f"create_existing_client_new_model | batch code already exists | batch_code={batch_code}")
            raise ValueError(f"Batch code '{batch_code}' already exists.")

        logger.info(f"create_existing_client_new_model | success | batch_id={batch.id} model_id={model.id} version_id={model_version.id}")
        return batch

    @staticmethod
    def create_device_model(model_name):
        # NOTE: model_name is intentionally NOT unique-checked here.
        # Different clients may have devices with the same model name (e.g. both use "Model X").
        # Uniqueness is enforced at the ModelVersion level via unique_together (model, version).
        logger.info(f"create_device_model | model_name={model_name}")

        device_model = DeviceModel.objects.create(
            model_name=model_name
        )

        logger.info(f"create_device_model | success | model_id={device_model.id} model_name={device_model.model_name}")
        return device_model

    @staticmethod
    def create_client_batchcode(client, batch_code, model_version):
        logger.info(f"create_client_batchcode | batch_code={batch_code} client={client}")

        try:
            batch = Batch.objects.create(
                client=client,
                batch_code=batch_code,
                model_version=model_version
            )
        except IntegrityError:
            logger.warning(f"create_client_batchcode | batch code already exists | batch_code={batch_code}")
            raise ValueError(f"Batch code '{batch_code}' already exists and is linked to another client.")

        logger.info(f"create_client_batchcode | success | batch_id={batch.id} batch_code={batch.batch_code}")
        return batch

    @staticmethod
    def create_model_version(model, version):
        logger.info(f"create_model_version | model={model} version={version}")

        try:
            model_version = DeviceModelVersion.objects.create(model=model, version=version)
        except IntegrityError:
            logger.warning(f"create_model_version | version already exists | model={model} version={version}")
            raise ValueError(f"Version '{version}' already exists for this model.")

        logger.info(f"create_model_version | success | version_id={model_version.id} version={model_version.version}")
        return model_version

    @staticmethod
    def get_clients_names():
        logger.info("get_clients_names | fetching all clients")
        return Client.objects.values('id', 'client_name').order_by('client_name')

    @staticmethod
    def get_clients_awaiting_linking():
        logger.info("get_clients_awaiting_linking | fetching clients without a batch")
        return (
            Client.objects.filter(batches__isnull=True)
            .values('id', 'client_name')
            .order_by('client_name')
        )

    @staticmethod
    def get_device_models():
        logger.info("get_device_models | fetching all device models")
        return DeviceModel.objects.values('id', 'model_name').order_by('model_name')

    @staticmethod
    def get_device_model_versions(model_id):
        logger.info(f"get_device_model_versions | model_id={model_id}")
        return DeviceModelVersion.objects.filter(model_id=model_id).values('id', 'version').order_by('version')

    @staticmethod
    def validate_existing_selection(client_id, model_id, version_id):
        """
        Case 1: Validates that a batch exists for the given client, model, and version.

        Called before unlocking the scan section to surface missing batch
        errors early rather than letting the scan reject an unknown batch code.
        """
        logger.info(f"validate_existing_selection | client_id={client_id} model_id={model_id} version_id={version_id}")

        try:
            client = Client.objects.get(id=client_id)
        except Client.DoesNotExist:
            logger.warning(f"validate_existing_selection | client not found | client_id={client_id}")
            raise ValueError(f"Client with id '{client_id}' does not exist.")

        try:
            version = DeviceModelVersion.objects.select_related('model').get(id=version_id, model_id=model_id)
        except DeviceModelVersion.DoesNotExist:
            logger.warning(f"validate_existing_selection | version not found | version_id={version_id} model_id={model_id}")
            raise ValueError(f"Version does not exist for the selected model.")

        try:
            batch = Batch.objects.get(client=client, model_version=version)
        except Batch.DoesNotExist:
            logger.warning(f"validate_existing_selection | no batch found | client_id={client_id} version_id={version_id}")
            raise ValueError(f"No batch found for this client and model version.")

        logger.info(f"validate_existing_selection | success | batch_code={batch.batch_code}")
        return batch

    @staticmethod
    def correct_reference(model_class, instance_id, new_data, user, reason=""):
        with transaction.atomic():
            instance = model_class.objects.select_for_update().get(id=instance_id)

            for field, value in new_data.items():
                setattr(instance, field, value)

            instance.correction_count += 1
            instance.last_corrected_by = user
            instance.last_corrected_at = timezone.now()
            instance.save(update_fields=list(new_data.keys()) + ['correction_count', 'last_corrected_by', 'last_corrected_at'])

            logger.info(f"correct_reference | {model_class.__name__} | id={instance_id} | by={user} | reason={reason}")
            return instance


class DeviceService:

    @staticmethod
    def scan_device(serial_number):
        logger.info(f"scan_device | serial_number={serial_number}")

        batch_code = serial_number.split('-')[0]
        logger.info(f"scan_device | extracted batch_code={batch_code}")

        try:
            batch = Batch.objects.select_related(
                'client',
                'model_version__model'
            ).get(batch_code=batch_code)
        except Batch.DoesNotExist:
            logger.warning(f"scan_device | batch not found | batch_code={batch_code}")
            raise ValueError(f"No batch found for batch code '{batch_code}'.")

        try:
            staging = DeviceStaging.objects.create(
                serial_number=serial_number,
                batch_code=batch.batch_code,
                client_name=batch.client.client_name,
                model_name=batch.model_version.model.model_name,
                version_name=batch.model_version.version,
                status='PENDING'
            )
        except IntegrityError:
            logger.warning(f"scan_device | serial number already exists or staged | serial_number={serial_number}")
            raise ValueError(f"Device '{serial_number}' already exists or has already been scanned.")

        logger.info(f"scan_device | success | staging_id={staging.id} serial_number={staging.serial_number}")
        return staging

    @staticmethod
    @transaction.atomic
    def confirm_device(serial_number):
        logger.info(f"confirm_device | serial_number={serial_number}")

        try:
            staging = DeviceStaging.objects.select_for_update().get(serial_number=serial_number, status='PENDING')
        except DeviceStaging.DoesNotExist:
            logger.warning(f"confirm_device | no pending staging record | serial_number={serial_number}")
            raise ValueError(f"No pending staging record found for '{serial_number}'.")

        batch = Batch.objects.select_related('model_version__model').get(batch_code=staging.batch_code)

        device = Device.objects.create(
            serial_number=staging.serial_number,
            batch=batch,
            model=batch.model_version.model,
            version=batch.model_version,
            device_status='ACTIVE'
        )

        staging.status = 'PROCESSED'
        staging.save()

        logger.info(f"confirm_device | success | device_id={device.id} serial_number={device.serial_number}")
        return device

    @staticmethod
    @transaction.atomic
    def confirm_bulk_devices(serial_numbers):
        logger.info(f"confirm_bulk_devices | starting | count={len(serial_numbers)}")

        staging_map = {
            s.serial_number: s
            for s in DeviceStaging.objects.select_for_update().filter(
                serial_number__in=serial_numbers,
                status='PENDING'
            )
        }

        missing = [sn for sn in serial_numbers if sn not in staging_map]
        if missing:
            logger.warning(f"confirm_bulk_devices | missing staging records | serial_numbers={missing}")
            raise ValueError(f"No pending staging record found for: {', '.join(missing)}.")

        batch_codes = {s.batch_code for s in staging_map.values()}
        batch_map = {
            b.batch_code: b
            for b in Batch.objects.select_related('model_version__model').filter(batch_code__in=batch_codes)
        }

        confirmed = []

        for serial_number in serial_numbers:
            staging = staging_map[serial_number]
            batch   = batch_map[staging.batch_code]

            device = Device.objects.create(
                serial_number=staging.serial_number,
                batch=batch,
                model=batch.model_version.model,
                version=batch.model_version,
                device_status='ACTIVE'
            )

            confirmed.append(device)
            logger.info(f"confirm_bulk_devices | confirmed | device_id={device.id} serial_number={device.serial_number}")

        DeviceStaging.objects.filter(serial_number__in=serial_numbers).update(status='PROCESSED')

        logger.info(f"confirm_bulk_devices | success | total_confirmed={len(confirmed)}")
        return confirmed


class BatchService:

    @staticmethod
    def get_batch_by_code(batch_code):
        logger.info(f"get_batch_by_code | batch_code={batch_code}")
        try:
            batch = Batch.objects.select_related('client', 'model_version__model').get(batch_code=batch_code)
        except Batch.DoesNotExist:
            logger.warning(f"get_batch_by_code | not found | batch_code={batch_code}")
            raise
        logger.info(f"get_batch_by_code | success | batch_id={batch.id}")
        return batch


    @staticmethod
    def flag_downstream_records(batch):
        # Repairs example — same pattern for other departments
        stale_repairs = RepairRecord.objects.filter(
            device__batch=batch,
            batch_verified_at__lt=batch.corrected_at
        )
        stale_repairs.update(needs_reverification=True)

    
    @staticmethod
    def reassign_batch(item, reviewer):   # was _apply_reassignment
        old_batch = item.batch
        try:
            new_batch = Batch.objects.create(
                client_id=item.proposed_client_id,
                batch_code=item.proposed_batch_code,
                model_version=old_batch.model_version,
            )
        except IntegrityError:
            raise ValueError(f"Batch code '{item.proposed_batch_code}' already exists.")

        moved = Device.objects.filter(batch=old_batch).update(batch=new_batch)
        logger.info(f"reassign_batch | old={old_batch.batch_code} | new={new_batch.batch_code} | devices_moved={moved}")


class BatchActionService:

    @staticmethod
    @transaction.atomic
    def submit_group(manager, items):
        """
        Manager bundles up every reassignment found during one review pass
        into a single group. Nothing is applied yet — this only logs the
        request and puts it in Finance's queue.

        items: list of dicts, each shaped like:
            {
                "batch_id": int,
                "proposed_client_id": int,
                "proposed_batch_code": str,
                "reason": str,
            }
        """
        if not items:
            raise ValueError("At least one reassignment is required.")

        group = BatchActionRequestGroup.objects.create(
            submitted_by=manager,
            status=BatchActionRequestGroup.Status.PENDING,
        )

        request_objects = []
        for item in items:
            batch_id = item.get("batch_id")
            reason = item.get("reason", "").strip()

            if not reason:
                raise ValueError("Every item in the request needs a reason.")
            if not item.get("proposed_client_id"):
                raise ValueError("A reassignment needs a proposed client.")
            if not item.get("proposed_batch_code"):
                raise ValueError("A reassignment needs a new batch code for the receiving client.")

            request_objects.append(BatchActionRequest(
                group=group,
                batch_id=batch_id,
                proposed_client_id=item.get("proposed_client_id"),
                proposed_batch_code=item.get("proposed_batch_code"),
                reason=reason,
            ))

        BatchActionRequest.objects.bulk_create(request_objects)

        logger.info(f"submit_group | group_id={group.id} | items={len(request_objects)} | by={manager}")

        # ⚠ still deferred — see earlier note
        # NotificationService.notify_department('finance', f"New reassignment request group #{group.id} pending review.")

        return group


    @staticmethod
    def reject_group(group_id, reviewer, reason):
        if not reason or not reason.strip():
            raise ValueError("A rejection reason is required.")

        with transaction.atomic():
            group = BatchActionRequestGroup.objects.select_for_update().get(id=group_id)
            if group.status != BatchActionRequestGroup.Status.PENDING:
                raise ValueError("This request has already been reviewed.")

            group.status = BatchActionRequestGroup.Status.REJECTED
            group.rejection_reason = reason.strip()
            group.reviewed_by = reviewer
            group.reviewed_at = timezone.now()
            group.save(update_fields=['status', 'rejection_reason', 'reviewed_by', 'reviewed_at'])

            logger.info(f"reject_group | group_id={group.id} | by={reviewer}")
            return group

    @staticmethod
    @transaction.atomic
    def approve_group(group_id, reviewer):
        group = BatchActionRequestGroup.objects.select_for_update().get(id=group_id)
        if group.status != BatchActionRequestGroup.Status.PENDING:
            raise ValueError("This request has already been reviewed.")

        items = list(group.items.select_related('batch').all())
        if not items:
            raise ValueError("This group has no items to apply.")

        for item in items:
            BatchService.reassign_batch(item, reviewer)  # renamed, see below

        group.status = BatchActionRequestGroup.Status.APPROVED
        group.reviewed_by = reviewer
        group.reviewed_at = timezone.now()
        group.save(update_fields=['status', 'reviewed_by', 'reviewed_at'])
        return group


    @staticmethod
    def get_pending_groups():
        logger.info("get_pending_groups | fetching Finance review queue")
        return BatchActionRequestGroup.objects.filter(
            status=BatchActionRequestGroup.Status.PENDING
        ).select_related('submitted_by').prefetch_related('items').order_by('created_at')

    @staticmethod
    def submit_reassignment_request(manager, batch_id, client_id, batch_code, reason):
        return BatchActionService.submit_group(
            manager=manager,
            items=[{
                "batch_id": batch_id,
                "proposed_client_id": client_id,
                "proposed_batch_code": batch_code,
                "reason": reason,
            }],
         )


class RentalConflict(Exception):
    """A rental rule was broken (the view turns this into HTTP 409)."""


class DeviceNotFound(Exception):
    """The serial number doesn't match any device (the view turns this into HTTP 404)."""


class DeviceRentalService:
    # ------------------------------------------------------------------
    # Ownership
    # ------------------------------------------------------------------
    @staticmethod
    def is_company_owned(device, company=None):
        """
        A device is company-owned when its Batch belongs to the company's own
        Client row (Device -> Batch -> Client). Reads the CURRENT batch, so if
        a batch is ever reassigned to another client the device stops being
        rentable automatically. Kept in one place so the definition of
        "company-owned" can change without touching callers.
        """
        if company is None:
            company = CompanyService.get_company_client()
        return device.batch.client_id == company.pk

    # ------------------------------------------------------------------
    # Assigning rentals
    # ------------------------------------------------------------------
    @staticmethod
    def _assert_rentable(device, company, rental_client=None):
        """One rule set, used at scan time (check_rentable) and at submit time (create_rentals)."""
        if not DeviceRentalService.is_company_owned(device, company):
            raise RentalConflict(
                f"Device '{device.serial_number}' is not company-owned and cannot be rented."
            )
        if rental_client is not None and rental_client.pk == company.pk:
            raise RentalConflict("A device cannot be rented to the company that owns it.")
        if device.device_status != "ACTIVE":
            raise RentalConflict(
                f"Device '{device.serial_number}' is not available for rental."
            )
        if DeviceRental.objects.filter(device=device, returned_at__isnull=True).exists():
            raise RentalConflict(
                f"Device '{device.serial_number}' is already rented out."
            )

    @staticmethod
    def check_rentable(serial_number):
        """Read-only scan-time check. create_rentals re-checks everything under lock."""
        sn = serial_number.strip()
        device = Device.objects.select_related("batch").filter(serial_number=sn).first()
        if device is None:
            raise DeviceNotFound(f"Device '{sn}' was not found.")
        company = CompanyService.get_company_client()  # 409 if not set up yet
        DeviceRentalService._assert_rentable(device, company)
        return device

    @staticmethod
    def create_rentals(items):
        """
        items: list of validated dicts {device, rental_client, expected_return_date}
        All-or-nothing. Rejects the same device appearing twice in one request.
        """
        device_ids = [i["device"].pk for i in items]
        if len(device_ids) != len(set(device_ids)):
            raise RentalConflict("The same device appears more than once in this request.")

        company = CompanyService.get_company_client()  # 409 if not set up yet

        created = []
        with transaction.atomic():
            # Lock the device rows in a stable order to avoid deadlocks.
            # of=("self",) locks only the Device rows, not the joined Batch.
            locked = {
                d.pk: d
                for d in Device.objects.select_related("batch")
                .select_for_update(of=("self",))
                .filter(pk__in=device_ids)
                .order_by("pk")
            }
            for item in items:
                device = locked[item["device"].pk]
                DeviceRentalService._assert_rentable(
                    device, company, rental_client=item["rental_client"]
                )
                created.append(
                    DeviceRental.objects.create(
                        device=device,
                        rental_client=item["rental_client"],
                        expected_return_date=item.get("expected_return_date"),
                    )
                )
        return created

    # ------------------------------------------------------------------
    # Looking up and ending rentals
    # ------------------------------------------------------------------
    @staticmethod
    def get_active_rental(serial_number):
        return (
            DeviceRental.objects.select_related("device", "rental_client")
            .filter(device__serial_number=serial_number.strip(), returned_at__isnull=True)
            .first()
        )

    @staticmethod
    def _assert_can_end(rental, end_date):
        """The end-date rules, shared by end_rental and end_rentals."""
        if rental.returned_at is not None:
            raise RentalConflict("This rental has already been ended.")
        if end_date < timezone.localtime(rental.start_date).date():
            raise RentalConflict("End date cannot be before the rental start date.")
        if end_date > timezone.localdate():
            raise RentalConflict("End date cannot be in the future.")
        # TODO when Repairs/Production exist: a rental can never end while the
        # device is on a processing line. Refuse here.

    @staticmethod
    def end_rental(rental_id, end_date):
        """Close one rental using the end date the Warehouse agent selected."""
        with transaction.atomic():
            rental = (
                DeviceRental.objects.select_for_update(of=("self",))
                .select_related("device", "rental_client")
                .get(pk=rental_id)
            )
            DeviceRentalService._assert_can_end(rental, end_date)
            rental.returned_at = end_date
            rental.save(update_fields=["returned_at"])
        return rental

    @staticmethod
    def end_rentals(rental_ids, end_date):
        """Close many rentals with one shared end date. All-or-nothing."""
        ids = list(rental_ids)
        if len(ids) != len(set(ids)):
            raise RentalConflict("The same rental appears more than once in this request.")

        with transaction.atomic():
            # Lock the rental rows in a stable order to avoid deadlocks.
            locked = {
                r.pk: r
                for r in DeviceRental.objects.select_related("device", "rental_client")
                .select_for_update(of=("self",))
                .filter(pk__in=ids)
                .order_by("pk")
            }

            ended = []
            for rental_id in ids:
                rental = locked.get(rental_id)
                if rental is None:
                    raise RentalConflict(f"Rental {rental_id} does not exist.")
                try:
                    DeviceRentalService._assert_can_end(rental, end_date)
                except RentalConflict as e:
                    # name the device so the agent knows which one blocked the batch
                    raise RentalConflict(f"{rental.device.serial_number}: {e}") from e
                rental.returned_at = end_date
                ended.append(rental)

            DeviceRental.objects.bulk_update(ended, ["returned_at"])
        return ended

    # ------------------------------------------------------------------
    # Who is the operational client for a device? (Repairs, Production)
    # ------------------------------------------------------------------
    @staticmethod
    def resolve_operational_client(serial_number):
        """
        Rental-first resolution, per the functional design:
        Device must exist -> active rental client -> else Batch client.
        Returns (client, source) where source is "RENTAL" or "BATCH".
        """
        try:
            device = Device.objects.select_related("batch__client").get(
                serial_number=serial_number
            )
        except Device.DoesNotExist:
            raise DeviceNotFound(f"Serial number '{serial_number}' is not a valid device.")

        rental = (
            DeviceRental.objects.select_related("rental_client")
            .filter(device=device, returned_at__isnull=True)
            .first()
        )
        if rental:
            return rental.rental_client, "RENTAL"
        return device.batch.client, "BATCH"
  

class CompanyService:
    @staticmethod
    def get_company_client_or_none():
        profile = CompanyProfile.objects.select_related("client").first()
        return profile.client if profile else None
 
    @classmethod
    def get_company_client(cls):
        client = cls.get_company_client_or_none()
        if client is None:
            raise RentalConflict("The servicing company has not been set up yet.")
        return client
 
    @classmethod
    def set_company(cls, *, client, user):
        """One-time. The unique constraints make a second call fail even in a race."""
        try:
            with transaction.atomic():
                return CompanyProfile.objects.create(client=client, set_by=user)
        except IntegrityError:
            raise CompanyAlreadySet("The company has already been set and can't be changed.")
            raise RentalConflict("The servicing compnay has not been set up yet.")


class CompanyAlreadySet(Exception):
    """The company was already chosen and can't be changed."""


"""
create_existing_client_new_version (Case 2)

Looks up client and model by ID with explicit DoesNotExist checks — IDs come from the frontend dropdowns so they should always exist, but we guard anyway and raise a clean ValueError rather than letting Django throw a 500
Checks ModelVersion uniqueness before creating — same guard already established in create_bulk_links
Checks batch_code uniqueness — same pattern
Both creates (ModelVersion → Batch) happen inside transaction.atomic, so a batch failure rolls back the version too

create_existing_client_new_model (Case 3)

Only looks up client by ID — the model doesn't exist yet
DeviceModel name is intentionally not unique-checked, matching the comment already in create_device_model — same model name can legitimately exist across different clients
Batch code uniqueness still checked
Three creates (DeviceModel → ModelVersion → Batch) all atomic
"""
import logging
from datetime import timedelta  # REVIEW: unused

from django.conf import settings  # REVIEW: unused
from django.db import IntegrityError, transaction
from django.utils import timezone

from .models import (
    Client, Batch,
    DeviceModelVersion, Device,
    BatchCorrection,
    DeviceRental, CompanyProfile,
)

logger = logging.getLogger("warehouse.services")


# Exceptions
class RentalConflict(Exception):
    """A rental rule was broken (the view turns this into HTTP 409)."""


class DeviceNotFound(Exception):
    """The serial number doesn't match any device (the view turns this into HTTP 404)."""


class CompanyAlreadySet(Exception):
    """The company was already chosen and can't be changed."""


class CorrectionConflict(Exception):
    """A correction was refused because of a rule (the view turns this into HTTP 409)."""


# Clients, models, versions and batches
class ClientService:

    # -------------------------------------------------------------------------
    # Internal helpers
    # -------------------------------------------------------------------------

    @staticmethod
    def _resolve_model_version(model, version):
        """
        Return the version record for (model, version): the existing one if there is one,
        a new one only the first time it is needed. Returns (model_version, created).
        """
        model_version, created = DeviceModelVersion.objects.get_or_create(model=model, version=version)
        logger.info(
            f"_resolve_model_version | model={model} version={model_version.version} created={created}"
        )
        return model_version, created

    @staticmethod
    def _create_batch(client, batch_code, model_version):
        """
        Create a batch for the client and product. A client can have several batches for the
        same model and version (repeat orders); each needs its own unique batch code.
        """
        try:
            # savepoint, so a duplicate does not poison the surrounding transaction
            with transaction.atomic():
                batch = Batch.objects.create(client=client, batch_code=batch_code, model_version=model_version)
        except IntegrityError:
            logger.warning(f"_create_batch | batch code already exists | batch_code={batch_code}")
            raise ValueError(f"Batch code '{batch_code}' already exists.")

        logger.info(f"_create_batch | created batch_id={batch.id} batch_code={batch.batch_code}")
        return batch

    # -------------------------------------------------------------------------
    # Add Clients: base step and linking step
    # -------------------------------------------------------------------------

    @staticmethod
    @transaction.atomic
    def create_bulk_base(clients_data):
        logger.info(f"create_bulk_base | starting | count={len(clients_data)}")
        created = []

        for entry in clients_data:
            try:
                client = Client.objects.create(client_name=entry["client_name"])
            except IntegrityError:
                logger.warning(f"create_bulk_base | client already exists | client_name={entry['client_name']}")
                raise ValueError(f"Client '{entry['client_name']}' already exists.")

            created.append(client)
            logger.info(f"create_bulk_base | created client={client.client_name}")

        logger.info(f"create_bulk_base | success | total_created={len(created)}")
        return created

    @staticmethod
    @transaction.atomic
    def create_bulk_links(links_data):

        logger.info(f"create_bulk_links | starting | count={len(links_data)}")
        created = []

        for entry in links_data:

            # Linking is only for a client's first batch.
            # Any further batch must go through Existing Client.
            if Batch.objects.filter(client=entry["client"]).exists():
                logger.warning(f"create_bulk_links | client already has a batch | client={entry['client']}")
                raise ValueError(
                    f"Client '{entry['client'].client_name}' already has a batch code. "
                    "Use Existing Client to add more."
                )

            model_version, _ = ClientService._resolve_model_version(entry["model"], entry["version"])
            batch = ClientService._create_batch(entry["client"], entry["batch_code"], model_version)

            created.append({"batch": batch, "model_version": model_version})
            logger.info(f"create_bulk_links | created batch={batch.batch_code} version={model_version.version}")

        logger.info(f"create_bulk_links | success | total_created={len(created)}")
        return created

    # -------------------------------------------------------------------------
    # Existing Client
    # -------------------------------------------------------------------------

    @staticmethod
    @transaction.atomic
    def create_existing_client_batch(client_id, model, version, batch_code):
        """Existing client, any model and version, new batch code. The product is reused if it exists."""
        logger.info(f"create_existing_client_batch | client_id={client_id} model={model} version={version} batch_code={batch_code}")
        try:
            client = Client.objects.get(id=client_id)
        except Client.DoesNotExist:
            logger.warning(f"create_existing_client_batch | client not found | client_id={client_id}")
            raise ValueError(f"Client with id '{client_id}' does not exist.")

        model_version, _ = ClientService._resolve_model_version(model, version)
        batch = ClientService._create_batch(client, batch_code, model_version)

        logger.info(f"create_existing_client_batch | success | batch_id={batch.id} version_id={model_version.id}")
        return batch

    @staticmethod
    def get_client_batches_for_version(client_id, version_id):
        """
        The batches a client already has for a product (model and version), oldest first.
        An empty list means the client has not bought this product yet.
        """
        logger.info(f"get_client_batches_for_version | client_id={client_id} version_id={version_id}")

        if not Client.objects.filter(id=client_id).exists():
            logger.warning(f"get_client_batches_for_version | client not found | client_id={client_id}")
            raise ValueError(f"Client with id '{client_id}' does not exist.")

        if not DeviceModelVersion.objects.filter(id=version_id).exists():
            logger.warning(f"get_client_batches_for_version | version not found | version_id={version_id}")
            raise ValueError("Selected model and version do not exist.")

        return list(
            Batch.objects.filter(client_id=client_id, model_version_id=version_id)
            .order_by('id')
            .values('id', 'batch_code')
        )

    # -------------------------------------------------------------------------
    # Lookups (dropdowns and lists)
    # -------------------------------------------------------------------------

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
        logger.info("get_device_models | fetching distinct model names")
        return DeviceModelVersion.objects.values('model').distinct().order_by('model')

    @staticmethod
    def get_device_model_versions(model):
        logger.info(f"get_device_model_versions | model={model}")
        return (
            DeviceModelVersion.objects.filter(model=model)
            .values('id', 'version')
            .order_by('version')
        )

    # -------------------------------------------------------------------------
    # Reference corrections (client, model, version)
    # -------------------------------------------------------------------------

    @staticmethod
    def correct_reference(model_class, instance_id, new_data, user, reason=""):
        try:
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
        except IntegrityError:
            logger.warning(f"correct_reference | duplicate | {model_class.__name__} | id={instance_id} | new_data={new_data}")
            raise ValueError("That value already exists.")

    @staticmethod
    def rename_model(old_name, new_name, user, reason=""):
        """Rename a model: every (model, version) row of that model takes the new name."""
        try:
            with transaction.atomic():
                rows = list(DeviceModelVersion.objects.select_for_update().filter(model=old_name))
                if not rows:
                    raise DeviceModelVersion.DoesNotExist
                    logger.warning(f"rename_model | model not found | old_name={old_name}")
                if DeviceModelVersion.objects.filter(model=new_name).exists():
                    logger.warning(f"rename_model | name already exists | {old_name} -> {new_name}")
                    raise ValueError(f"A model named '{new_name}' already exists.")

                now = timezone.now()
                for row in rows:
                    row.model = new_name
                    row.correction_count += 1
                    row.last_corrected_by = user
                    row.last_corrected_at = now
                DeviceModelVersion.objects.bulk_update(
                    rows, ['model', 'correction_count', 'last_corrected_by', 'last_corrected_at']
                )
                logger.info(f"rename_model | {old_name} -> {new_name} | rows={len(rows)} | by={user} | reason={reason}")
        except IntegrityError:
            logger.warning(f"rename_model | duplicate | {old_name} -> {new_name}")
            raise ValueError("That model name already exists.")

    # -------------------------------------------------------------------------
    # Single-record helpers (kept for existing callers)
    # -------------------------------------------------------------------------

    @staticmethod
    def create_device_model(model):
        # REVIEW: _create_model does not exist on this class, so this raises AttributeError if called
        return ClientService._create_model(model)

    @staticmethod
    def create_client_batchcode(client, batch_code, model_version):
        return ClientService._create_batch(client, batch_code, model_version)

    @staticmethod
    def create_model_version(model, version):
        model_version, _ = ClientService._resolve_model_version(model, version)
        return model_version


# Devices: scanning and confirming
class DeviceService:

    # Scanning

    @staticmethod
    def scan_device(serial_number):
        logger.info(f"scan_device | serial_number={serial_number}")

        batch_code = serial_number.split('-')[0]
        logger.info(f"scan_device | extracted batch_code={batch_code}")

        try:
            batch = Batch.objects.select_related(
                'client',
                'model_version'
            ).get(batch_code=batch_code)
        except Batch.DoesNotExist:
            logger.warning(f"scan_device | batch not found | batch_code={batch_code}")
            raise ValueError(f"No batch found for batch code '{batch_code}'.")

        try:
            # savepoint, so a duplicate does not poison the surrounding transaction
            with transaction.atomic():
                Device.objects.create(
                    serial_number=serial_number,
                    batch=batch,
                    device_status='ACTIVE'
                )
        except IntegrityError:
            logger.warning(f"scan_device | serial number already exists | serial_number={serial_number}")
            raise ValueError(f"Device '{serial_number}' already exists.")

        logger.info(f"scan_device | success | serial_number={serial_number}")
        


# Batch corrections
class BatchService:

    @staticmethod
    def flag_downstream_records(batch):
        # REVIEW: RepairRecord is not imported or defined yet (Repairs isn't built)
        # Repairs example — same pattern for other departments
        stale_repairs = RepairRecord.objects.filter(
            device__batch=batch,
            batch_verified_at__lt=batch.corrected_at
        )
        stale_repairs.update(needs_reverification=True)

    @staticmethod
    def correct_batch_code(batch_id, new_code, user, reason=""):
        # REVIEW: duplicate of BatchCodeService.correct_batch_code below, which has the
        # shared _is_in_use check. Confirm which one the view calls before removing either.
        """
        Fix a mistyped batch code. Allowed only while nothing has been scanned or registered
        under it: a serial number carries its batch code, so a code that real serial numbers
        already use was not a typo.
        """
        try:
            with transaction.atomic():
                batch = Batch.objects.select_for_update().get(id=batch_id)
                old_code = batch.batch_code

                if new_code == old_code:
                    logger.warning(f"correct_batch_code | same code | batch_id={batch_id} | code={old_code}")
                    raise CorrectionConflict("The new batch code is the same as the current one.")

                if Device.objects.filter(batch=batch).exists():
                    logger.warning(f"correct_batch_code | in use, not correctable | batch_id={batch_id} | code={old_code}")
                    raise CorrectionConflict(
                        "Devices have already been scanned or registered under this batch code, so it can't be corrected."
                    )

                batch.batch_code = new_code
                batch.correction_count += 1
                batch.corrected_at = timezone.now()
                batch.save(update_fields=['batch_code', 'correction_count', 'corrected_at'])

                logger.info(f"correct_batch_code | batch_id={batch_id} | {old_code} -> {new_code} | by={user} | reason={reason}")
                return batch
        except IntegrityError:
            logger.warning(f"correct_batch_code | duplicate | batch_id={batch_id} | new_code={new_code}")
            raise CorrectionConflict(f"Batch code '{new_code}' already exists.")


class BatchCodeService:
    """Looking up and correcting a batch's code. Independent of the reassignment feature."""

    @staticmethod
    def _is_in_use(batch):
        """
        True once a device or a scan exists under the batch. A serial number carries its batch
        code, so a code that real serial numbers already use was not a typo.
        """
        return (
            Device.objects.filter(batch=batch).exists()
        )

    @staticmethod
    def find_batch(batch_code):
        """Look a batch up by its code, for the correction screen. Raises Batch.DoesNotExist."""
        batch = Batch.objects.select_related('client', 'model_version').get(batch_code=batch_code)
        return {
            "id": batch.id,
            "batch_code": batch.batch_code,
            "client_name": batch.client.client_name,
            "model": batch.model_version.model,
            "version": batch.model_version.version,
            "correctable": not BatchCodeService._is_in_use(batch),
        }

    @staticmethod
    def correct_batch_code(batch_id, new_code, user, reason=""):
        """Fix a mistyped batch code, only while nothing has been scanned or registered under it."""
        try:
            with transaction.atomic():
                batch = Batch.objects.select_for_update().get(id=batch_id)
                old_code = batch.batch_code

                if new_code == old_code:
                    raise CorrectionConflict("The new batch code is the same as the current one.")

                if BatchCodeService._is_in_use(batch):
                    raise CorrectionConflict(
                        "Devices have already been scanned or registered under this batch code, so it can't be corrected."
                    )

                batch.batch_code = new_code
                batch.correction_count += 1
                batch.corrected_at = timezone.now()
                batch.save(update_fields=['batch_code', 'correction_count', 'corrected_at'])

                logger.info(f"correct_batch_code | batch_id={batch_id} | {old_code} -> {new_code} | by={user} | reason={reason}")
                return batch
        except IntegrityError:
            logger.warning(f"correct_batch_code | duplicate | batch_id={batch_id} | new_code={new_code}")
            raise CorrectionConflict(f"Batch code '{new_code}' already exists.")


# Company (the servicing company, set once)
class CompanyService:

    @staticmethod
    def get_company_client_or_none():
        profile = CompanyProfile.objects.select_related("client").first()
        return profile.client if profile else None

    @classmethod
    def get_company_client(cls):
        client = cls.get_company_client_or_none()
        if client is None:
            logger.warning("get_company_client | company not set up yet")
            raise RentalConflict("The servicing company has not been set up yet.")
        return client

    @classmethod
    def set_company(cls, *, client, user):
        """One-time. The unique constraints make a second call fail even in a race."""

        logger.info(f"set_company | client_id={client.pk} | by={user}")
        try:
            with transaction.atomic():
                return CompanyProfile.objects.create(client=client, set_by=user)
        except IntegrityError:
            logger.warning(f"set_company | already set | attempted_client_id={client.pk} | by={user}")
            raise CompanyAlreadySet("The company has already been set and can't be changed.")
            # REVIEW: the line below is unreachable (it follows a raise) and has a typo ("compnay")
            raise RentalConflict("The servicing compnay has not been set up yet.")


# Rentals
class DeviceRentalService:

    # -------------------------------------------------------------------------
    # Ownership
    # -------------------------------------------------------------------------

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

    # -------------------------------------------------------------------------
    # Assigning rentals
    # -------------------------------------------------------------------------

    @staticmethod
    def _assert_rentable(device, company, rental_client=None):
        """One rule set, used at scan time (check_rentable) and at submit time (create_rentals)."""
        if not DeviceRentalService.is_company_owned(device, company):
            logger.warning(f"_assert_rentable | not company-owned | serial_number={device.serial_number}")
            raise RentalConflict(
                f"Device '{device.serial_number}' is not company-owned and cannot be rented."
            )
        if rental_client is not None and rental_client.pk == company.pk:
            logger.warning(f"_assert_rentable | rental client is the owner | serial_number={device.serial_number}")
            raise RentalConflict("A device cannot be rented to the company that owns it.")
        if device.device_status != "ACTIVE":
            logger.warning(f"_assert_rentable | device not active | serial_number={device.serial_number} status={device.device_status}")
            raise RentalConflict(
                f"Device '{device.serial_number}' is not available for rental."
            )
        if DeviceRental.objects.filter(device=device, returned_at__isnull=True).exists():
            logger.warning(f"_assert_rentable | already rented | serial_number={device.serial_number}")
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
            logger.warning(f"create_rentals | duplicate devices | device_ids={device_ids}")
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
            logger.info(f"create_rentals | success | count={len(created)} rental_ids={[r.pk for r in created]}")
        return created

    # -------------------------------------------------------------------------
    # Looking up and ending rentals
    # -------------------------------------------------------------------------

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
            logger.warning(f"_assert_can_end | rental already ended | rental_id={rental.pk}")
            raise RentalConflict("This rental has already been ended.")
        if end_date < timezone.localtime(rental.start_date).date():
            logger.warning(f"_assert_can_end | end date is before rental start date | date={end_date}" )
            raise RentalConflict("End date cannot be before the rental start date.")
        if end_date > timezone.localdate():
            logger.warning(f"_assert_can_end | end date is in the future | date={end_date}" )
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
            logger.info(f"end_rental | success | rental_id={rental_id} end_date={end_date}")
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
            logger.info(f"end_rentals | success | count={len(ended)} end_date={end_date}")       
        return ended

    # -------------------------------------------------------------------------
    # Operational client (used by Repairs, Production)
    # -------------------------------------------------------------------------

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
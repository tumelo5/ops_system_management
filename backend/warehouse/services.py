from django.db import transaction
from .models import Client, Batch, DeviceModel, ModelVersion, Device, DeviceStaging
import logging

logger = logging.getLogger("warehouse.services")


class ClientService:

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

        if Batch.objects.filter(batch_code=batch_code).exists():
            logger.warning(f"create_client_batchcode | batch code already exists | batch_code={batch_code}")
            raise ValueError(f"Batch code '{batch_code}' already exists and is linked to another client.")

        batch = Batch.objects.create(
            client=client,
            batch_code=batch_code,
            model_version=model_version
        )

        logger.info(f"create_client_batchcode | success | batch_id={batch.id} batch_code={batch.batch_code}")
        return batch

    @staticmethod
    def create_model_version(model, version):
        logger.info(f"create_model_version | model={model} version={version}")

        if ModelVersion.objects.filter(model=model, version=version).exists():
            logger.warning(f"create_model_version | version already exists | model={model} version={version}")
            raise ValueError(f"Version '{version}' already exists for this model.")

        model_version = ModelVersion.objects.create(model=model, version=version)

        logger.info(f"create_model_version | success | version_id={model_version.id} version={model_version.version}")
        return model_version

    @staticmethod
    def get_clients_names():
        logger.info("get_clients_names | fetching all clients")
        return Client.objects.values('id', 'client_name').order_by('client_name')

    @staticmethod
    def get_device_models():
        logger.info("get_device_models | fetching all device models")
        return DeviceModel.objects.values('id', 'model_name').order_by('model_name')

    @staticmethod
    def get_versions_by_model(model_id):
        logger.info(f"get_versions_by_model | model_id={model_id}")
        return ModelVersion.objects.filter(model_id=model_id).values('id', 'version').order_by('version')

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
            version = ModelVersion.objects.select_related('model').get(id=version_id, model_id=model_id)
        except ModelVersion.DoesNotExist:
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
    @transaction.atomic
    def create_bulk_base(clients_data):
        logger.info(f"create_bulk_base | starting | count={len(clients_data)}")
        created = []

        for entry in clients_data:
            if Client.objects.filter(client_name=entry["client_name"]).exists():
                logger.warning(f"create_bulk_base | client already exists | client_name={entry['client_name']}")
                raise ValueError(f"Client '{entry['client_name']}' already exists.")

            client = Client.objects.create(
                client_name=entry["client_name"],
            )

            device_model = DeviceModel.objects.create(
                model_name=entry["model_name"],
            )

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
            batch_code = entry["batch_code"]
            version    = entry["version"]
            model      = entry["model"]
            client     = entry["client"]

            if Batch.objects.filter(batch_code=batch_code).exists():
                logger.warning(f"create_bulk_links | batch code already exists | batch_code={batch_code}")
                raise ValueError(f"Batch code '{batch_code}' already exists.")

            if ModelVersion.objects.filter(model=model, version=version).exists():
                logger.warning(f"create_bulk_links | version already exists | model={model} version={version}")
                raise ValueError(f"Version '{version}' already exists for this model.")

            model_version = ModelVersion.objects.create(model=model, version=version)
            batch = Batch.objects.create(client=client, batch_code=batch_code, model_version=model_version)

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

        if ModelVersion.objects.filter(model=model, version=new_version).exists():
            logger.warning(f"create_existing_client_new_version | version already exists | model={model} version={new_version}")
            raise ValueError(f"Version '{new_version}' already exists for model '{model.model_name}'.")

        if Batch.objects.filter(batch_code=batch_code).exists():
            logger.warning(f"create_existing_client_new_version | batch code already exists | batch_code={batch_code}")
            raise ValueError(f"Batch code '{batch_code}' already exists.")

        model_version = ModelVersion.objects.create(model=model, version=new_version)
        batch = Batch.objects.create(client=client, batch_code=batch_code, model_version=model_version)

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

        if Batch.objects.filter(batch_code=batch_code).exists():
            logger.warning(f"create_existing_client_new_model | batch code already exists | batch_code={batch_code}")
            raise ValueError(f"Batch code '{batch_code}' already exists.")

        # DeviceModel is intentionally not unique-checked by name —
        # the same model name can exist across different clients.
        model = DeviceModel.objects.create(model_name=new_model_name)
        model_version = ModelVersion.objects.create(model=model, version=new_version)
        batch = Batch.objects.create(client=client, batch_code=batch_code, model_version=model_version)

        logger.info(f"create_existing_client_new_model | success | batch_id={batch.id} model_id={model.id} version_id={model_version.id}")
        return batch


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

        if Device.objects.filter(serial_number=serial_number).exists():
            logger.warning(f"scan_device | serial number already exists | serial_number={serial_number}")
            raise ValueError(f"Device '{serial_number}' already exists.")

        if DeviceStaging.objects.filter(serial_number=serial_number, status='PENDING').exists():
            logger.warning(f"scan_device | serial number already staged | serial_number={serial_number}")
            raise ValueError(f"Device '{serial_number}' has already been scanned and is pending confirmation.")

        staging = DeviceStaging.objects.create(
            serial_number=serial_number,
            batch_code=batch.batch_code,
            client_name=batch.client.client_name,
            model_name=batch.model_version.model.model_name,
            version_name=batch.model_version.version,
            status='PENDING'
        )

        logger.info(f"scan_device | success | staging_id={staging.id} serial_number={staging.serial_number}")
        return staging

    @staticmethod
    @transaction.atomic
    def confirm_device(serial_number):
        logger.info(f"confirm_device | serial_number={serial_number}")

        try:
            staging = DeviceStaging.objects.get(serial_number=serial_number, status='PENDING')
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
            for s in DeviceStaging.objects.filter(
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
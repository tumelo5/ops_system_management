from django.db import transaction
from .models import Client, Batch, DeviceModel, ModelVersion, Device, DeviceStaging
import logging

logger = logging.getLogger("warehouse.services")


class ClientService:

    @staticmethod
    def create_single_client(client_name, client_status):
        logger.info(f"create_single_client | client_name={client_name}")

        if Client.objects.filter(client_name=client_name).exists():
            logger.warning(f"create_single_client | client already exists | client_name={client_name}")
            raise ValueError(f"Client with name '{client_name}' already exists.")

        client = Client.objects.create(
            client_name=client_name,
            client_status=client_status
        )

        logger.info(f"create_single_client | success | client_id={client.id} client_name={client.client_name}")
        return client


    @staticmethod
    def create_device_model(model_name, model_status):
        logger.info(f"create_device_model | model_name={model_name}")

        # if DeviceModel.objects.filter(model_name=model_name).exists():
        #     logger.warning(f"create_device_model | model already exists | model_name={model_name}")
        #     raise ValueError(f"Device model '{model_name}' already exists.")

        device_model = DeviceModel.objects.create(
            model_name=model_name,
            model_status=model_status
        )

        logger.info(f"create_device_model | success | model_id={device_model.id} model_name={device_model.model_name}")
        return device_model


    @staticmethod
    def create_client_batchcode(client, batch_code, model_version):
        logger.info(f"create_client_batchcode | batch_code={batch_code} client={client}")

        if Batch.objects.filter(batch_code=batch_code).exists():
            logger.warning(f"create_client_batchcode | batch code already exists | batch_code={batch_code}")
            raise ValueError(f"Batch code '{batch_code}' already exists and linked to another client.")

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

        model_version = ModelVersion.objects.create(
            model=model,
            version=version
        )

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
    def get_all_models():
        logger.info("get_all_models | fetching all device models")
        return DeviceModel.objects.values('id', 'model_name').order_by('model_name')


    @staticmethod
    def get_versions_by_model(model_id):
        logger.info(f"get_versions_by_model | model_id={model_id}")
        return ModelVersion.objects.filter(model_id=model_id).values('id', 'version').order_by('version')


    @staticmethod
    @transaction.atomic
    def create_bulk_base(clients_data):
        logger.info(f"create_bulk_base | starting | count={len(clients_data)}")
        created = []

        for entry in clients_data:
            if Client.objects.filter(client_name=entry["client_name"]).exists():
                logger.warning(f"create_bulk_base | client already exists | client_name={entry['client_name']}")
                raise ValueError(f"Client '{entry['client_name']}' already exists.")

            if DeviceModel.objects.filter(model_name=entry["model_name"]).exists():
                logger.warning(f"create_bulk_base | model already exists | model_name={entry['model_name']}")
                raise ValueError(f"Device model '{entry['model_name']}' already exists.")

            client = Client.objects.create(
                client_name=entry["client_name"],
                client_status=entry["client_status"]
            )

            device_model = DeviceModel.objects.create(
                model_name=entry["model_name"],
                model_status=entry["model_status"]
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
            if Batch.objects.filter(batch_code=entry["batch_code"]).exists():
                logger.warning(f"create_bulk_links | batch code already exists | batch_code={entry['batch_code']}")
                raise ValueError(f"Batch code '{entry['batch_code']}' already exists.")

            if ModelVersion.objects.filter(model=entry["model"], version=entry["version"]).exists():
                logger.warning(f"create_bulk_links | version already exists | model={entry['model']} version={entry['version']}")
                raise ValueError(f"Version '{entry['version']}' already exists for this model.")

            model_version = ModelVersion.objects.create(
                model=entry["model"],
                version=entry["version"]
            )

            batch = Batch.objects.create(
                client=entry["client"],
                batch_code=entry["batch_code"],
                model_version=model_version
            )

            created.append({"batch": batch, "model_version": model_version})
            logger.info(f"create_bulk_links | created batch={batch.batch_code} version={model_version.version}")

        logger.info(f"create_bulk_links | success | total_created={len(created)}")
        return created


   


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
            raise ValueError(f"Device with serial number '{serial_number}' already exists.")

        if DeviceStaging.objects.filter(serial_number=serial_number, status='PENDING').exists():
            logger.warning(f"scan_device | serial number already staged | serial_number={serial_number}")
            raise ValueError(f"Device '{serial_number}' has already been scanned and is pending confirmation.")

        try:
            staging = DeviceStaging.objects.create(
                serial_number=serial_number,
                batch_code=batch.batch_code,
                client_name=batch.client.client_name,
                model_name=batch.model_version.model.model_name,
                version_name=batch.model_version.version,
                status='PENDING'
            )
        except Exception as e:
            logger.error(f"scan_device | staging creation failed | serial_number={serial_number} | error={str(e)}", exc_info=True)
            raise

        logger.info(f"scan_device | success | staging_id={staging.id} serial_number={staging.serial_number}")
        return staging


    @staticmethod
    @transaction.atomic
    def confirm_device(serial_number):
        logger.info(f"confirm_device | serial_number={serial_number}")

        try:
            staging = DeviceStaging.objects.get(
                serial_number=serial_number,
                status='PENDING'
            )
        except DeviceStaging.DoesNotExist:
            logger.warning(f"confirm_device | no pending staging record | serial_number={serial_number}")
            raise ValueError(f"No pending staging record found for '{serial_number}'.")

        try:
            batch = Batch.objects.select_related(
                'model_version__model'
            ).get(batch_code=staging.batch_code)
        except Exception as e:
            logger.error(f"confirm_device | batch lookup failed | serial_number={serial_number} | error={str(e)}", exc_info=True)
            raise

        try:
            device = Device.objects.create(
                serial_number=staging.serial_number,
                batch=batch,
                model=batch.model_version.model,
                version=batch.model_version,
                device_status='ACTIVE'
            )

            staging.status = 'PROCESSED'
            staging.save()
        except Exception as e:
            logger.error(f"confirm_device | device creation failed | serial_number={serial_number} | error={str(e)}", exc_info=True)
            raise

        logger.info(f"confirm_device | success | device_id={device.id} serial_number={device.serial_number}")
        return device


    @staticmethod
    @transaction.atomic
    def confirm_bulk_devices(serial_numbers):
        logger.info(f"confirm_bulk_devices | starting | count={len(serial_numbers)}")
        confirmed = []

        for serial_number in serial_numbers:
            logger.info(f"confirm_bulk_devices | processing | serial_number={serial_number}")

            try:
                staging = DeviceStaging.objects.get(
                    serial_number=serial_number,
                    status='PENDING'
                )
            except DeviceStaging.DoesNotExist:
                logger.warning(f"confirm_bulk_devices | no pending staging record | serial_number={serial_number}")
                raise ValueError(f"No pending staging record found for '{serial_number}'.")

            try:
                batch = Batch.objects.select_related(
                    'model_version__model'
                ).get(batch_code=staging.batch_code)
            except Exception as e:
                logger.error(f"confirm_bulk_devices | batch lookup failed | serial_number={serial_number} | error={str(e)}", exc_info=True)
                raise

            device = Device.objects.create(
                serial_number=staging.serial_number,
                batch=batch,
                model=batch.model_version.model,
                version=batch.model_version,
                device_status='ACTIVE'
            )

            staging.status = 'PROCESSED'
            staging.save()

            confirmed.append(device)
            logger.info(f"confirm_bulk_devices | confirmed | device_id={device.id} serial_number={device.serial_number}")

        logger.info(f"confirm_bulk_devices | success | total_confirmed={len(confirmed)}")
        return confirmed
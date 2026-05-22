from django.db import transaction
from .models import Client, Batch, DeviceModel, ModelVersion, Device, DeviceStaging
import logging


class ClientService:

    @staticmethod
    def create_single_client(client_name, client_status):
        if Client.objects.filter(client_name=client_name).exists():
            raise ValueError(f"Client with name '{client_name}' already exists.")

        return Client.objects.create(
            client_name=client_name,
            client_status=client_status
        )


    @staticmethod
    def create_device_model(model_name, model_status):
        return DeviceModel.objects.create(
            model_name=model_name,
            model_status=model_status
        )


    @staticmethod
    def create_client_batchcode(client, batch_code, model_version):
        return Batch.objects.create(
            client=client,
            batch_code=batch_code,
            model_version=model_version  # linked silently
        )


    @staticmethod
    def create_model_version(model, version):
        return ModelVersion.objects.create(
            model=model,
            version=version
        )


    @staticmethod
    def get_clients_names():
        return Client.objects.values('id', 'client_name').order_by('client_name')


    @staticmethod
    def get_device_models():
        return DeviceModel.objects.values('id', 'model_name').order_by('model_name')


    @staticmethod
    @transaction.atomic
    def create_bulk_base(clients_data):
        created = []

        for entry in clients_data:
            if Client.objects.filter(client_name=entry["client_name"]).exists():
                raise ValueError(f"Client '{entry['client_name']}' already exists.")

            client = Client.objects.create(
                client_name=entry["client_name"],
                client_status=entry["client_status"]
            )

            device_model = DeviceModel.objects.create(
                model_name=entry["model_name"],
                model_status=entry["model_status"]
            )

            created.append({"client": client, "device_model": device_model})

        return created


    @staticmethod
    @transaction.atomic
    def create_bulk_links(links_data):
        created = []

        for entry in links_data:
            model_version = ModelVersion.objects.create(
                model=entry["model"],
                version=entry["version"]
            )

            batch = Batch.objects.create(
                client=entry["client"],
                batch_code=entry["batch_code"],
                model_version=model_version  # linked silently
            )

            created.append({"batch": batch, "model_version": model_version})

        return created


class DeviceService:

    @staticmethod
    def scan_device(serial_number):
        """
        Receives a scanned SN, extracts batch code, looks up all related
        data and writes a human readable snapshot to DeviceStaging.
        """

        # Extract batch code from SN — everything before the first '-'
        # e.g. "ABC123-00001" → "ABC123"
        batch_code = serial_number.split('-')[0]

        # Look up batch and traverse relationships
        try:
            batch = Batch.objects.select_related(
                'client',
                'model_version__model'
            ).get(batch_code=batch_code)
        except Batch.DoesNotExist:
            raise ValueError(f"No batch found for batch code '{batch_code}'.")

        # Check if SN already exists
        if Device.objects.filter(serial_number=serial_number).exists():
            raise ValueError(f"Device with serial number '{serial_number}' already exists.")

        # Write human readable snapshot to staging
        staging = DeviceStaging.objects.create(
            serial_number=serial_number,
            batch_code=batch.batch_code,
            client_name=batch.client.client_name,
            model_name=batch.model_version.model.model_name,
            version_name=batch.model_version.version,
            status='PENDING'
        )

        return staging


    @staticmethod
    @transaction.atomic
    def confirm_device(serial_number):
        """
        Takes a PENDING staging record, writes the final Device record
        and marks the staging record as PROCESSED.
        """

        # Get staging record
        try:
            staging = DeviceStaging.objects.get(
                serial_number=serial_number,
                status='PENDING'
            )
        except DeviceStaging.DoesNotExist:
            raise ValueError(f"No pending staging record found for '{serial_number}'.")

        # Get batch with all relationships
        batch = Batch.objects.select_related(
            'model_version__model'
        ).get(batch_code=staging.batch_code)

        # Write final device record
        device = Device.objects.create(
            serial_number=staging.serial_number,
            batch=batch,
            model=batch.model_version.model,
            version=batch.model_version,
            device_status='ACTIVE'
        )

        # Mark staging as processed
        staging.status = 'PROCESSED'
        staging.save()

        return device
"""
Shared builders for the warehouse tests.

Every test needs the same chain:  Client -> DeviceModelVersion -> Batch -> Device.
Build it here, once, so a model change (like the model/version merge) is a one-file fix.

Rules:
- Plain functions, no extra dependency.
- Defaults are unique and already normalised (stripped + lowercase), the way the
  serializers store them. Pass explicit values when a test cares about them.
- Default batch codes are 5 characters, zero-padded, so two default codes can never be
  a prefix of each other (which would make scans ambiguous by accident).
"""
import itertools
from django.contrib.auth import get_user_model
from ..models import Batch, Client, CompanyProfile, Device, DeviceModelVersion, DeviceRental


WAREHOUSE_DEPARTMENT = "warehouse"
OTHER_DEPARTMENT = "finance"

_counter = itertools.count(1)


def _n():
    return next(_counter)


def make_user(department=WAREHOUSE_DEPARTMENT, username=None, **extra):
    User = get_user_model()
    return User.objects.create_user(
        username=username or f"user{_n()}",
        password="pass12345",
        department=department,
        **extra,
    )


def make_client(client_name=None, **extra):
    return Client.objects.create(client_name=client_name or f"client{_n()}", **extra)


def make_model_version(model=None, version=None, **extra):
    n = _n()
    return DeviceModelVersion.objects.create(
        model=model or f"model{n}",
        version=version or f"v{n}",
        **extra,
    )


def make_batch(batch_code=None, client=None, model_version=None):
    return Batch.objects.create(
        batch_code=batch_code if batch_code is not None else f"b{_n():04d}",
        client=client or make_client(),
        model_version=model_version or make_model_version(),
    )


def make_device(serial_number=None, batch=None, **extra):
    batch = batch or make_batch()
    return Device.objects.create(
        serial_number=serial_number or f"{batch.batch_code}{_n():05d}",
        batch=batch,
        **extra,
    )


def make_company(client=None, user=None):
    """The servicing company (single-row CompanyProfile)."""
    return CompanyProfile.objects.create(client=client or make_client(), set_by=user)


def make_rental(device, rental_client=None, returned_at=None, **extra):
    """returned_at=None means the rental is active."""
    return DeviceRental.objects.create(
        device=device,
        rental_client=rental_client or make_client(),
        returned_at=returned_at,
        **extra,
    )
from django.conf import settings
from django.db import models
from django.db.models import Q


# Reusable for model classes using status
class Status(models.TextChoices):
    ACTIVE = "Active", "Active"
    INACTIVE = "Inactive", "Inactive"
    SUSPENDED = "Suspended", "Suspended"


# Never deleted, only deactivated via their status, to preserve historical data.
# Corrections are applied in place; correction_count / last_corrected_* record who and when.

# CLIENT
# - client_status: client can be deactivated but not deleted. Default is 'Active'.
class Client(models.Model):
    client_name = models.CharField(max_length=255, blank=False, unique=True)
    client_status = models.CharField(
        max_length=50,
        choices=Status.choices,
        default=Status.ACTIVE,
    )

    # Correction tracking
    correction_count = models.PositiveIntegerField(default=0)
    last_corrected_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='+'
    )
    last_corrected_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['client_name']

    def __str__(self):
        return f"{self.client_name} | {self.client_status}"


# MODEL VERSION (one row = model + version)
# - status: version can be discontinued but not deleted. Default is 'Active'.
class DeviceModelVersion(models.Model):
    model = models.CharField(max_length=100, blank=False)
    version = models.CharField(max_length=50, blank=False)
    status = models.CharField(
        max_length=50,
        choices=Status.choices,
        default=Status.ACTIVE,
    )

    # Correction tracking
    correction_count = models.PositiveIntegerField(default=0)
    last_corrected_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='+'
    )
    last_corrected_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('model', 'version')  # Ensure unique version per model

    def __str__(self):
        return f"{self.model} {self.version} | {self.status}"



# Warehouse: Batch, Device
# BATCH
# Ownership chain: Device -> Batch -> Client / DeviceModelVersion
class Batch(models.Model):
    batch_code = models.CharField(max_length=100, blank=False, unique=True)
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='batches')
    model_version = models.ForeignKey(
        DeviceModelVersion, on_delete=models.CASCADE, related_name='batches', blank=False
    )

    # Correction tracking
    corrected_at = models.DateTimeField(null=True, blank=True)
    correction_count = models.PositiveIntegerField(default=0)

    class Meta:
        # A client can have several batches for the same product (repeat orders);
        # each batch is told apart by its unique batch_code.
        indexes = [models.Index(fields=['client', 'model_version'])]

    def __str__(self):
        return f"{self.batch_code} ({self.client.client_name})"


# DEVICE
# One permanent row per serial number. Client and model/version are reached through batch.
class Device(models.Model):

    STATUS_CHOICES = [
        ('ACTIVE', 'Active'),
        ('SCRAPPED', 'Scrapped'),
        ('DECOMMISSIONED', 'Decommissioned'),
    ]

    serial_number = models.CharField(max_length=100, unique=True, null=False, blank=False)
    batch = models.ForeignKey(Batch, on_delete=models.PROTECT, null=False, blank=False)

    # End-of-life states only (scrapped / decommissioned)
    device_status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='ACTIVE')

    # Audit
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.serial_number} | {self.device_status}"


# DEVICE STAGING (HUMAN-READABLE SNAPSHOT, NO FKs)
# Flat snapshot of a scanned device, shown before confirmation.
# To be revisited: devices can be saved without user confirmation, and this table holds data that isn't needed.
class DeviceStaging(models.Model):
    serial_number = models.CharField(max_length=100, unique=True)

    # Human-readable snapshot taken at scan time (no FKs)
    model = models.CharField(max_length=100)
    version = models.CharField(max_length=50)
    batch_code = models.CharField(max_length=100)
    client_name = models.CharField(max_length=100)

    # Validation
    status = models.CharField(max_length=50, default='PENDING')
    error_message = models.TextField(null=True, blank=True)

    # Audit: when the device was scanned
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.serial_number} | {self.status}"



# Rentals and company
# DEVICE RENTAL
# Device -> DeviceRental -> Client. Renting never changes the Device or its Batch.
class DeviceRental(models.Model):
    device = models.ForeignKey(Device, on_delete=models.PROTECT, related_name="rentals")
    rental_client = models.ForeignKey(Client, on_delete=models.PROTECT, related_name="rentals")
    start_date = models.DateTimeField(auto_now_add=True)
    expected_return_date = models.DateTimeField(null=True, blank=True)

    # Rental end date, picked by the Warehouse agent when the device is scanned
    # back in. NULL = rental is still active (this is the single source of truth).
    returned_at = models.DateField(null=True, blank=True)
    ended_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="ended_rentals",
    )
    end_note = models.CharField(max_length=255, blank=True, default="")

    class Meta:
        constraints = [
            # DB-level guarantee: at most one active rental per device,
            # even if two requests race past the serializer check.
            models.UniqueConstraint(
                fields=["device"],
                condition=Q(returned_at__isnull=True),
                name="uniq_active_rental_per_device",
            )
        ]
        indexes = [models.Index(fields=["device", "returned_at"])]

    @property
    def is_active(self):
        return self.returned_at is None

    def __str__(self):
        return f"Rental of {self.device.serial_number} by {self.rental_client.client_name}"


# COMPANY PROFILE
# The servicing company, set once. The database itself allows only one row.
class CompanyProfile(models.Model):
    # unique + default True = only one row can exist
    singleton = models.BooleanField(default=True, unique=True, editable=False)
    client = models.OneToOneField("Client", on_delete=models.PROTECT, related_name="company_profile")
    set_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    set_at = models.DateTimeField(auto_now_add=True)

    def delete(self, *args, **kwargs):
        raise RuntimeError("The company can't be unset. Change it in the database if you must.")


# Legacy

# BATCH CORRECTION
class BatchCorrection(models.Model):
    batch = models.ForeignKey(Batch, on_delete=models.CASCADE, related_name='corrections')
    corrected_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    field_changed = models.CharField(max_length=50)  # 'client' or 'model_version'
    old_value_id = models.PositiveIntegerField()
    new_value_id = models.PositiveIntegerField()
    corrected_at = models.DateTimeField(auto_now_add=True)
    reason = models.CharField(max_length=255, blank=True)
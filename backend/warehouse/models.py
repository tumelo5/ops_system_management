from django.db import models
from backend.authentication.models import CustomUser
from django.db.models import Q
from django.conf import settings


# Reusable for model classes using status
class Status(models.TextChoices):
    ACTIVE = "Active", "Active"
    INACTIVE = "Inactive", "Inactive"
    SUSPENDED = "Suspended", "Suspended"


# CLIENT
# - client_status: client can be deactivated but not deleted, to preserve historical data integrity. Default is 'Active'.
class Client(models.Model):
    client_name = models.CharField(max_length=255, blank=False, unique=True)
    client_status = models.CharField(
        max_length=50,
        choices=Status.choices,
        default=Status.ACTIVE
    )
    correction_count = models.PositiveIntegerField(default=0)
    last_corrected_by = models.ForeignKey(CustomUser, null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
    last_corrected_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.client_name} | {self.client_status}"

    class Meta:
        ordering = ['client_name']


# DEVICE MODEL
# - model_status: model can be discontinued but not deleted, to preserve historical data integrity. Default is 'Active'.
class DeviceModel(models.Model):
    model_name = models.CharField(max_length=100,unique=True, blank=False)
    model_status = models.CharField(
        max_length=50,
        choices=Status.choices,
        default=Status.ACTIVE
    )
    correction_count = models.PositiveIntegerField(default=0)
    last_corrected_by = models.ForeignKey(CustomUser, null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
    last_corrected_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.model_name} | {self.model_status}"


# MODEL VERSION
# - status: version status can be discontinued but not deleted, to preserve historical data integrity. Default is 'Active'.
class DeviceModelVersion(models.Model):
    model = models.ForeignKey(DeviceModel, on_delete=models.CASCADE, related_name='versions')
    version = models.CharField(max_length=50, blank=False)
    status = models.CharField(
        max_length=50,
        choices=Status.choices,
        default=Status.ACTIVE
    )
    correction_count = models.PositiveIntegerField(default=0)
    last_corrected_by = models.ForeignKey(CustomUser, null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
    last_corrected_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('model', 'version')  # Ensure unique version per model

    def __str__(self):
        return f"{self.model.model_name} {self.version} | {self.status}"


# BATCH
class Batch(models.Model):
    batch_code = models.CharField(max_length=100, blank=False, unique=True)
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='batches')
    model_version = models.ForeignKey(DeviceModelVersion, on_delete=models.CASCADE, related_name='batches', blank=False)
    corrected_at = models.DateTimeField(null=True, blank=True  )
    correction_count = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ('model_version', 'client')  # Ensure unique batch code per client

    def __str__(self):
        return f"{self.batch_code} ({self.client.client_name})"


# DEVICE STAGING (HUMAN-READABLE SNAPSHOT — NO FKs)
# - Stores a flat snapshot of scanned device info for confirmation.
# - created_at: used as the audit timestamp for when the device was scanned.
class DeviceStaging(models.Model):
    serial_number = models.CharField(max_length=100, unique=True)

    # Human-readable fields (NO FK) — snapshot at time of scan
    model_name = models.CharField(max_length=100)
    version_name = models.CharField(max_length=50)
    batch_code = models.CharField(max_length=100)
    client_name = models.CharField(max_length=100)

    # Validation
    status = models.CharField(max_length=50, default='PENDING')
    error_message = models.TextField(null=True, blank=True)

    # Audit
    created_at = models.DateTimeField(auto_now_add=True)  # FIX: added — records when device was scanned

    def __str__(self):
        return f"{self.serial_number} | {self.status}"


# DEVICE
class Device(models.Model):

    STATUS_CHOICES = [
        ('ACTIVE', 'Active'),
        ('SCRAPPED', 'Scrapped'),
        ('DECOMMISSIONED', 'Decommissioned'),
    ]

    serial_number = models.CharField(max_length=100, unique=True, null=False, blank=False)

    # Relationships
    model = models.ForeignKey(DeviceModel, on_delete=models.PROTECT, null=False, blank=False)
    version = models.ForeignKey(DeviceModelVersion, on_delete=models.PROTECT, null=False, blank=False)
    batch = models.ForeignKey(Batch, on_delete=models.PROTECT, null=False, blank=False)

    # Status
    device_status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='ACTIVE')

    # Audit
    created_at = models.DateTimeField(auto_now_add=True)

    # created_by_emp = models.ForeignKey(Employee, on_delete=models.PROTECT, related_name='devices_created')

    def __str__(self):
        return f"{self.serial_number} | {self.device_status}"


class BatchCorrection(models.Model):
    batch = models.ForeignKey(Batch, on_delete=models.CASCADE, related_name='corrections')
    corrected_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True)
    field_changed = models.CharField(max_length=50)  # 'client' or 'model_version'
    old_value_id = models.PositiveIntegerField()
    new_value_id = models.PositiveIntegerField()
    corrected_at = models.DateTimeField(auto_now_add=True)
    reason = models.CharField(max_length=255, blank=True)


# BATCH ACTION REQUESTS used for bulk corrections/reassignments, submitted and approved together.
class BatchActionRequestGroup(models.Model):
    """
    One manager review pass — may contain several individual
    corrections/reassignments, submitted and approved together.
    Finance approves or rejects the whole group; no partial approval.
    """
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        APPROVED = 'APPROVED', 'Approved'
        REJECTED = 'REJECTED', 'Rejected'

    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    submitted_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, related_name='+')
    created_at = models.DateTimeField(auto_now_add=True)
    reviewed_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    reviewed_at = models.DateTimeField(null=True, blank=True)


# BATCH ACTION REQUEST for a single correction/reassignment
class BatchActionRequest(models.Model):
    group = models.ForeignKey(BatchActionRequestGroup, on_delete=models.CASCADE, related_name='items')
    batch = models.ForeignKey(Batch, on_delete=models.CASCADE, related_name='action_requests')
    proposed_client = models.ForeignKey(Client, on_delete=models.SET_NULL, null=True, related_name='+')
    proposed_batch_code = models.CharField(max_length=100)
    reason = models.CharField(max_length=255)
    # request_type and proposed_model_version removed — reassignment-only, no branching needed


# DEVICE RENTAL
class DeviceRental(models.Model):
    device = models.ForeignKey(
        Device, on_delete=models.PROTECT, related_name="rentals"
    )
    rental_client = models.ForeignKey(
        Client, on_delete=models.PROTECT, related_name="rentals"
    )
    start_date = models.DateTimeField(auto_now_add=True)
    expected_return_date = models.DateTimeField(null=True, blank=True)
    # Rental end date, picked by the Warehouse agent when the device is scanned
    # back in. NULL = rental is still active (this is the single source of truth).
    returned_at = models.DateField(null=True, blank=True)
    ended_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,related_name="ended_rentals"
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


class CompanyProfile(models.Model):
    # unique + default True = the database itself allows only one row
    singleton = models.BooleanField(default=True, unique=True, editable=False)
    client = models.OneToOneField("Client", on_delete=models.PROTECT, related_name="company_profile")
    set_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    set_at = models.DateTimeField(auto_now_add=True)
 
    def delete(self, *args, **kwargs):
        raise RuntimeError("The company can't be unset. Change it in the database if you must.")
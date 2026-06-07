from django.db import models


# CLIENT
# - client_status: client can be deactivated but not deleted, to preserve historical data integrity. Default is 'Active'.
class Client(models.Model):
    client_name = models.CharField(max_length=100, unique=True, null=False, blank=False)
    client_status = models.CharField(default='Active')

    def __str__(self):
        return f"{self.client_name} | {self.client_status}"

    class Meta:
        ordering = ['client_name']


# DEVICE MODEL
# - model_status: model can be discontinued but not deleted, to preserve historical data integrity. Default is 'Active'.
class DeviceModel(models.Model):
    model_name = models.CharField(max_length=100, unique=False, null=False, blank=False)
    model_status = models.CharField(default='Active')

    def __str__(self):
        return f"{self.model_name} | {self.model_status}"


# MODEL VERSION
# - status: version status can be discontinued but not deleted, to preserve historical data integrity. Default is 'Active'.  
class ModelVersion(models.Model):
    model = models.ForeignKey(DeviceModel, on_delete=models.CASCADE, related_name='versions')
    version = models.CharField(max_length=50, null=False, blank=False)
    status = models.CharField(max_length=50, default='Active')

    class Meta:
        unique_together = ('model', 'version') # Ensure unique version per model

    def __str__(self):
        return f"{self.model.model_name} {self.version} | {self.status}"


# BATCH
class Batch(models.Model):
    batch_code = models.CharField(max_length=100, unique=True, null=False, blank=False)
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='batches')
    model_version = models.ForeignKey(ModelVersion, on_delete=models.CASCADE, related_name='batches', null=True, blank=True)  

    def __str__(self):
        return f"{self.batch_code} ({self.client.client_name})"


# DEVICE STAGING (USER-FACING, NO FK)
class DeviceStaging(models.Model):
    serial_number = models.CharField(max_length=100, unique=True)

    # Human-readable fields (NO FK)
    model_name = models.CharField(max_length=100)
    version_name = models.CharField(max_length=50)
    batch_code = models.CharField(max_length=100)
    client_name = models.CharField(max_length=100)

    # Validation
    status = models.CharField(max_length=50, default='PENDING')
    error_message = models.TextField(null=True, blank=True)

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
    version = models.ForeignKey(ModelVersion, on_delete=models.PROTECT, null=False, blank=False)
    batch = models.ForeignKey(Batch, on_delete=models.PROTECT, null=False, blank=False)

    # Status
    device_status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='ACTIVE')

    # Audit
    created_at = models.DateTimeField(auto_now_add=True)

    # created_by_emp = models.ForeignKey(Employee, on_delete=models.PROTECT, related_name='devices_created')

    def __str__(self):
        return f"{self.serial_number} | {self.device_status}"

    
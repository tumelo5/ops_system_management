# from django.db import models
# from backend.hr.models import Employee


# class Client(models.Model):
#     # Client's name
#     client_name = models.CharField(max_length=100, null=False, blank=False)
    
#     # Unique code for tracking and reporting
#     batch_code = models.IntegerField(unique=True, null=False, blank=False)
    
#     # Current status of the client (default: Active)
#     status = models.CharField(max_length=50, default='Active')

#     def __str__(self):
#         # Clean display for admin and shell
#         return f"{self.client_name} | Status: {self.status}"

#     class Meta:
#         verbose_name = 'Client'
#         verbose_name_plural = 'Clients'
#         ordering = ['client_name']  # Optional: makes queries ordered by name by default


    


# # DeviceModel represents the different models of devices that can be tracked in the system.
# class DeviceModel(models.Model):
#     model = models.CharField(max_length=100, null=False, blank=False, unique=True)
#     model_status = models.CharField(max_length=50, default='Active') # To be populated in DeviceStaging when SN is scanned.

#     def __str__(self):
#         return self.model
    
#     class Meta:
#         verbose_name = 'Model'
#         verbose_name_plural = 'Models'


# # Temporarily stores devices for staging before they are moved to the Device table.
# class DeviceStaging(models.Model):
#     serial_number = models.CharField(max_length=100, unique=True, null=False, blank=False)
    
#     # Link to the DeviceModel this staging device belongs to
#     model = models.ForeignKey(
#         DeviceModel,
#         on_delete=models.CASCADE,
#         related_name='staging_model'  # DeviceModel.staging_model.all()
#     )
    
#     # Status of the model, fetched automatically from DeviceModel
#     model_status = models.ForeignKey(
#         DeviceModel,  # points to the DeviceModel table to fetch current status
#         on_delete=models.CASCADE,
#         related_name='staging_model_status',
#         default=None, 
#     )
#     # Main client linked to this staging device
#     client = models.ForeignKey(
#         Client,
#         on_delete=models.CASCADE,
#         related_name='staging_client'  # Client.staging_client.all()
#     )
    
#     # Status of the client, fetched automatically from Client table
#     client_status = models.ForeignKey(
#         Client,
#         on_delete=models.CASCADE,
#         related_name='staging_status'  # Client.staging_status.all()
#     )


#     def __str__(self):
#         return f"{self.serial_number} | Model: {self.model} | Client: {self.client} | Status: {self.client_status}"

    
#     class Meta:
#         verbose_name = 'Device Staging'
#         verbose_name_plural = 'Device Staging'


# # Stores new devices that are added to the system after being scanned in staging.
# class Device(models.Model):
#     # Unique serial number for the device (from staging)
#     serial_number = models.CharField(max_length=100, unique=True, null=False, blank=False)
    
#     # Device model name (mirrors staging)
#     model = models.CharField(max_length=100, null=False, blank=False, unique=True)
#     model_status = models.CharField(max_length=50)  # mirrors staging model status
    
#     # Client information (mirrors staging)
#     client_name = models.CharField(max_length=100, null=False, blank=False)
#     client_status = models.CharField(max_length=50, default='Active')  # mirrors staging client status
    
#     # Editable field only via Repairs trigger; tracks device lifecycle (e.g., Active, Inactive, Discontinued)
#     device_status = models.CharField(max_length=50)
    
#     # Employee who added the device
#     created_by_emp = models.ForeignKey(Employee, on_delete=models.PROTECT, related_name='created_devices')
    
#     # Timestamp when device was added to the system
#     created_at = models.DateTimeField(auto_now_add=True)
    
#     def __str__(self):
#         return f"{self.client_name} - {self.model}"
    
#     class Meta:
#         verbose_name = 'Device'
#         verbose_name_plural = 'Devices'

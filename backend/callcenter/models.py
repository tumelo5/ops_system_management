from django.db import models


# Pre-filled table
class DeviceLog(models.Model):
    serial_number = models.CharField(max_length=100, null=False)
    status_logged = models.CharField(max_length=100, blank=False, null=False)
    date_logged = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.serial_number} | {self.status_logged}"


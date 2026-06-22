from django.contrib.auth.models import AbstractUser
from django.db import models


class Department(models.TextChoices):
    WAREHOUSE = "warehouse", "Warehouse"
    REPAIRS = "repairs", "Repairs"
    STORES = "stores", "Stores"
    FINANCE = "finance", "Finance"


class CustomUser(AbstractUser):
    """
    Custom user model that extends Django's AbstractUser.
    Each user is assigned to a department, which controls
    which part of the system they can access.
    """
    department = models.CharField(
        max_length=50,
        choices=Department.choices,
        blank=True,
        null=True,
        help_text="The department this user belongs to. Leave blank for unassigned users."
    )
    is_demo = models.BooleanField(
        default=False,
        help_text="Flags this user as a demo account for employer previews."
    )

    def __str__(self):
        dept = self.department if self.department else "Unassigned"
        return f"{self.username} ({dept})"

    @property
    def is_assigned(self):
        """Returns True if the user has a department assigned."""
        return bool(self.department)
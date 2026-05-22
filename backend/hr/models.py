from django.contrib.auth.models import AbstractUser
from django.db import models


class Employee(AbstractUser):

    DEPARTMENTS = [
        ("warehouse", "Warehouse"),
        ("hr",        "Human Resources"),
    ]

    department  = models.CharField(max_length=50, choices=DEPARTMENTS, blank=True, null=True)
    title       = models.CharField(max_length=100, blank=True, null=True)
    employee_id = models.CharField(max_length=20, unique=True, blank=True, null=True)

    def __str__(self):
        return f"{self.get_full_name()} — {self.department or 'No Department'}"
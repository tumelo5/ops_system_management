from django.db import models

class Employee(models.Model):
    EMPLOYMENT_STATUS = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
    ]

    TITLES_CHOICES = [
        ('Manager', 'Manager'),
        ('Supervisor', 'Supervisor'),
        ('Staff', 'Staff'),
        ('Intern', 'Intern'),
        ('Fin_clerk', 'Finance Clerk'),
        ('HR_specialist', 'HR Specialist'),
        ('Warehouse_A', 'Warehouse Agent'),
        ('Repair_technician', 'Repair Technician'),
        ('QC_A', 'Quality Control Agent'),
        ('Prod_BA_A', 'Production BankA Agent'),
        ('Prod_BB_A', 'Production BankB Agent'),
        ('Prod_BC_A', 'Production BankC Agent'),
    ]

    DEPARTMENTS_CHOICES = [
        ('HR', 'Human Resources'),
        ('FIN', 'Finance'),
        ('WAR', 'Warehouse'),
        ('REPC', 'Repairs Centre'),
        ('QC', 'Quality Control'),
        ('BER', 'Beyond Ergonomical Repair'),
        ('PROD_BA', 'BankA'),
        ('PROD_BB', 'BankB'),
        ('PROD_BC', 'BankC'),
    ]
    full_name = models.CharField(max_length=100, null=False, blank=False)
    title = models.CharField(max_length=100,null=False, blank=False, choices=TITLES_CHOICES, default='Staff')
    department = models.CharField(max_length=100, null=False, blank=False, choices=DEPARTMENTS_CHOICES, default='HR')
    employment_status = models.CharField(max_length=20, null=False, blank=False, choices=EMPLOYMENT_STATUS, default='active')
    email = models.EmailField(unique=True, null=False, blank=False)
    password = models.CharField(max_length=128, null=True)

    # Returns the string representation of the Employee
    def __str__(self):
        return self.full_name
    # Meta information for the Employee model, to be looked into, inline with class fields
    class Meta:
        verbose_name = 'Employee'
        verbose_name_plural = 'Employees'
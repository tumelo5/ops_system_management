from rest_framework import serializers
from .models import Employee


# HR uses this to register a new employee
class EmployeeRegistrationSerializer(serializers.ModelSerializer):

    password = serializers.CharField(write_only=True)  # never returned in response

    class Meta:
        model  = Employee
        fields = [
            "username",
            "password",
            "first_name",
            "last_name",
            "email",
            "department",
            "title",
            "employee_id",
        ]


# Read-only — for returning employee info in responses
class EmployeeSerializer(serializers.ModelSerializer):

    class Meta:
        model  = Employee
        fields = [
            "id",
            "username",
            "first_name",
            "last_name",
            "email",
            "department",
            "title",
            "employee_id",
        ]
        read_only_fields = fields  # nothing is editable through this serializer
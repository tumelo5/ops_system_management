
from .models import Employee
# hr/services.py

class HRService:

    @staticmethod
    def register_employee(data):
        password = data.pop("password")
        employee = Employee(**data)
        employee.set_password(password)  # hashing lives here now
        employee.save()
        return employee
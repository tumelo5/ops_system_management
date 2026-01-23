from .models import Employee
from rest_framework import serializers

class EmployeeSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    full_name = serializers.CharField(max_length=100)
    title = serializers.ChoiceField(choices=Employee.TITLES_CHOICES, default='Staff')
    department = serializers.ChoiceField(choices=Employee.DEPARTMENTS_CHOICES, default='HR')
    employment_status = serializers.ChoiceField(choices=Employee.EMPLOYMENT_STATUS, default='active')
    email = serializers.EmailField()
    password = serializers.CharField(max_length=128, write_only=True, required=False)

    def create(self, validated_data):
        return Employee.objects.create(**validated_data)

    def update(self, instance, validated_data):
        instance.full_name = validated_data.get('full_name', instance.full_name)
        instance.title = validated_data.get('title', instance.title)
        instance.department = validated_data.get('department', instance.department)
        instance.employment_status = validated_data.get('employment_status', instance.employment_status)
        instance.email = validated_data.get('email', instance.email)
        if 'password' in validated_data:
            instance.password = validated_data['password']
        instance.save()
        return instance
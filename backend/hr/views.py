from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .serializers import EmployeeRegistrationSerializer, EmployeeSerializer
from .services import HRService
from backend.common.permissions import IsHRStaff


class HRView(APIView):
    permission_classes = [IsHRStaff]

    def post(self, request):
        mode = request.data.get("mode")

        handlers = {
            "register_employee": self._handle_register_employee,
        }

        handler = handlers.get(mode)

        if not handler:
            return Response({"error": "Invalid mode"}, status=status.HTTP_400_BAD_REQUEST)

        return handler(request.data)

    def _handle_register_employee(self, body):
        serializer = EmployeeRegistrationSerializer(data=body)
        if not serializer.is_valid():
            return Response({"error": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        employee = HRService.register_employee(serializer.validated_data)

        return Response({
            "message": f"{employee.get_full_name()} registered successfully.",
            "employee": EmployeeSerializer(employee).data
        }, status=status.HTTP_201_CREATED)
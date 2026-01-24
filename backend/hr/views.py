
from rest_framework.viewsets import ModelViewSet
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Employee
from .serializers import EmployeeSerializer

class EmployeeViewSet(ModelViewSet):
    # TODO: Add authentication/permissions, logging, and transaction safety for production
    queryset = Employee.objects.all()
    serializer_class = EmployeeSerializer


    # /employees/by-department/?department=IT
    @action(detail=False, methods=['get']) 
    def by_department(self, request):
        department = request.query_params.get('department')
        if not department:
            return Response({"error": "Department is required."}, status=400)
         
        qs = self.queryset.filter(department=department)
        if not qs.exists():
            return Response({"message": "No employees found in the specified department."}, status=404)
        
        return Response(self.get_serializer(qs, many=True).data)


    # /employees/search/?q=john
    @action(detail=False, methods=['get'])
    def search(self, request):
        q = request.query_params.get('q', '').strip()
        if not q:
            return Response({"error": "Search query parameter 'q' is required."}, status=400)

        qs = self.queryset.filter(full_name__icontains=q)
        if not qs.exists():
            return Response({"message": "No employees."}, status=404)

        return Response(self.get_serializer(qs, many=True).data)


    # /employees/bulk-create/
    @action(detail=False, methods=['post'])
    def bulk_create(self, request):
        if not request.data:
            return Response({"error": "No data provided."}, status=400)
        
        serializer = self.get_serializer(data=request.data, many=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response( {"message": f"{len(serializer.data)} employees created successfully.", "employees": serializer.data})


    # /employees/bulk-delete/
    @action(detail=False, methods=['delete'])
    def bulk_delete(self, request):
        ids = request.data.get('ids', [])
        if not ids:
            return Response({"error": "No IDs provided."}, status=400)
        
        deleted_count, _ = self.queryset.filter(id__in=ids).delete()
        if deleted_count == 0:
            return Response({"message": "No employees found for the provided IDs."}, status=404)
        return Response({"message": f"{deleted_count} employees deleted successfully."})

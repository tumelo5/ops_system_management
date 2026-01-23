
from rest_framework.viewsets import ModelViewSet
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Employee
from .serializers import EmployeeSerializer

class EmployeeViewSet(ModelViewSet):
    queryset = Employee.objects.all()
    serializer_class = EmployeeSerializer

    # /employees/by-department/?department=IT
    # URL: /employees/by-department/?department=IT
    @action(detail=False, methods=['get']) # registeres a custom route, only allows GET requests
    def by_department(self, request):
        department = request.query_params.get('department')
        qs = self.queryset.filter(department=department)
        return Response(self.get_serializer(qs, many=True).data)

    # /employees/by-status/?status=Active
    @action(detail=False, methods=['get'])
    def by_status(self, request):
        status = request.query_params.get('status')
        qs = self.queryset.filter(employment_status=status)
        return Response(self.get_serializer(qs, many=True).data)

    # /employees/search/?q=john
    @action(detail=False, methods=['get'])
    def search(self, request):
        q = request.query_params.get('q', '')
        qs = self.queryset.filter(full_name__icontains=q)
        return Response(self.get_serializer(qs, many=True).data)

   
    # to be looked into, if needed or otherwise remove.
    # /employees/statuses/
    @action(detail=False, methods=['get'])
    def statuses(self, request):
        return Response({'statuses': [s[0] for s in Employee.EMPLOYMENT_STATUS]})

    # /employees/bulk-create/
    @action(detail=False, methods=['post'])
    def bulk_create(self, request):
        serializer = self.get_serializer(data=request.data, many=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=201)

    # /employees/bulk-delete/
    @action(detail=False, methods=['delete'])
    def bulk_delete(self, request):
        ids = request.data.get('ids', [])
        self.queryset.filter(id__in=ids).delete()
        return Response(status=204)

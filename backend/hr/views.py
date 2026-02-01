from rest_framework.viewsets import ModelViewSet
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from rest_framework import status
from django.db import transaction
import logging
from .models import Employee
from .serializers import EmployeeSerializer

logger = logging.getLogger(__name__)

class EmployeeViewSet(ModelViewSet):
    # TODO: Add authentication/permissions, logging, and transaction safety for production
    queryset = Employee.objects.all()
    serializer_class = EmployeeSerializer
    max_bulk_size = 10  # Limit for bulk operations


    # /employees/by-department/?department=IT
    @action(detail=False, methods=['get']) 
    def by_department(self, request):
        department = request.query_params.get('department')
        if not department:
            return Response({"message": "Department is required."}, status=400)
         
        qs = self.queryset.filter(department=department)
        if not qs.exists():
            return Response({"message": "No employees found in the specified department."}, status=404)
        
        return Response(self.get_serializer(qs, many=True).data)


    # /employees/search/?q=john
    @action(detail=False, methods=['get'])
    def search(self, request):
        q = request.query_params.get('q', '').strip()
        if not q:
            return Response({"message": "Search query parameter 'q' is required."}, status=400)

        qs = self.queryset.filter(full_name__icontains=q)
        if not qs.exists():
            return Response({"message": "No employees."}, status=404)

        return Response(self.get_serializer(qs, many=True).data)


    # /employees/bulk-create/
    @action(detail=False, methods=['post'])
    def bulk_create(self, request):
        # Normalize data: single object → list
        data = request.data
        if not data:
            return Response({"success": False, "message": "No data provided."}, status=status.HTTP_400_BAD_REQUEST)
        if isinstance(data, dict):
            data = [data]
        if len(data) == 0:
            return Response({"success": False, "message": "Employee list cannot be empty."}, status=status.HTTP_400_BAD_REQUEST)
        if len(data) > self.max_bulk_size:
            return Response({"success": False, "message": f"Cannot create more than {self.max_bulk_size} employees at once."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            with transaction.atomic():
                serializer = self.get_serializer(data=data, many=True, context={"request": request})
                serializer.is_valid(raise_exception=True)
                serializer.save()
                logger.info(f"{len(serializer.data)} employees created by {request.user.username}.")
                return Response({
                    "success": True,
                    "message": f"{len(serializer.data)} employees created successfully.",
                    "count": len(serializer.data),
                    "data": serializer.data
                }, status=status.HTTP_201_CREATED)

        except ValidationError as e:
            return Response({"success": False, "message": "Validation failed.", "errors": e.detail}, status=status.HTTP_400_BAD_REQUEST)

        except Exception:
            logger.exception(f"Bulk create failed by {request.user.username}")
            return Response({"success": False, "message": "Bulk create failed."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


    # /employees/bulk-delete/
    @action(detail=False, methods=['delete'])
    def bulk_delete(self, request):
        ids = request.data.get('ids', [])
        if not ids:
            return Response({"success": False, "message": "No IDs provided."}, status=status.HTTP_400_BAD_REQUEST)
        if len(ids) > self.max_bulk_size:
            return Response(
                {"success": False, "message": f"Max {self.max_bulk_size} employees allowed per request."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            with transaction.atomic():
                queryset = self.queryset.filter(id__in=ids)
                deleted_count = queryset.count()
                deleted_ids = list(queryset.values_list('id', flat=True))
                queryset.delete()

                not_found_ids = [i for i in ids if i not in deleted_ids]

                if deleted_count == 0:
                    return Response(
                        {"success": False, "message": "No employees found for the provided IDs."},
                        status=status.HTTP_404_NOT_FOUND
                    )

                logger.info(f"{deleted_count} employees deleted by {request.user.username}. Missing IDs: {not_found_ids}")
                
                return Response(
                    {
                        "success": True,
                        "message": f"{deleted_count} employees deleted successfully.",
                        "deleted_ids": deleted_ids,
                        "not_found_ids": not_found_ids,
                        "count": deleted_count
                    },
                    status=status.HTTP_200_OK
                )

        except Exception:
            logger.exception(f"Bulk delete failed by {request.user.username}")
            return Response({"success": False, "message": "Bulk delete failed."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

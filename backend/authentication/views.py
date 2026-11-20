from drf_spectacular.utils import extend_schema
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import serializers, status
from rest_framework_simplejwt.tokens import RefreshToken


# Documentation only: these describe request and response shapes for Swagger.
class LogoutRequestSerializer(serializers.Serializer):
    refresh = serializers.CharField(help_text="The refresh token that was issued at login.")


class LogoutResponseSerializer(serializers.Serializer):
    message = serializers.CharField()


class AuthErrorSerializer(serializers.Serializer):
    error = serializers.CharField()


class AuthDetailSerializer(serializers.Serializer):
    detail = serializers.CharField()


class MeResponseSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    username = serializers.CharField()
    full_name = serializers.CharField()
    email = serializers.CharField(allow_blank=True)
    department = serializers.CharField(allow_blank=True, allow_null=True)
    is_demo = serializers.BooleanField()


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Authentication"],
        summary="Log out",
        description="Blacklists the refresh token so it can no longer be used.",
        request=LogoutRequestSerializer,
        responses={
            200: LogoutResponseSerializer,
            400: AuthErrorSerializer,
            401: AuthDetailSerializer,
        },
    )
    def post(self, request):
        try:
            refresh_token = request.data.get("refresh")
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response(
                {"message": "Logged out successfully."},
                status=status.HTTP_200_OK
            )
        except Exception:
            return Response(
                {"error": "Invalid token."},
                status=status.HTTP_400_BAD_REQUEST
            )


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Authentication"],
        summary="Who am I",
        description="The logged-in user's details, read from the access token.",
        responses={
            200: MeResponseSerializer,
            401: AuthDetailSerializer,
        },
    )
    def get(self, request):
        user = request.user
        return Response({
            "id": user.id,
            "username": user.username,
            "full_name": user.get_full_name(),
            "email": user.email,
            "department": user.department,
            "is_demo": user.is_demo,
        })
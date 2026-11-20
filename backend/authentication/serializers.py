from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiResponse
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework import serializers


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        # Embed extra claims into the JWT
        token["department"] = user.department or ""
        token["full_name"] = user.get_full_name()
        token["is_demo"] = user.is_demo
        return token

    def validate(self, attrs):
        data = super().validate(attrs)

        user = self.user

        # Reject login if user has no department assigned
        if not user.is_assigned:
            raise serializers.ValidationError(
                "Your account is not assigned to a department. "
                "Please contact your administrator."
            )

        # Return user info alongside the tokens
        data["department"] = user.department
        data["full_name"] = user.get_full_name()
        data["is_demo"] = user.is_demo

        return data


# Documentation only: describes the login response so Swagger does not show the
# request fields (username, password) as the response.
class LoginResponseSerializer(serializers.Serializer):
    access = serializers.CharField(help_text="Short-lived access token. Send it as 'Authorization: Bearer <token>'.")
    refresh = serializers.CharField(help_text="Long-lived token used to get a new access token and to log out.")
    department = serializers.CharField()
    full_name = serializers.CharField()
    is_demo = serializers.BooleanField()


@extend_schema_view(
    post=extend_schema(
        tags=["Authentication"],
        summary="Log in",
        description="Returns an access and a refresh token plus the user's department. The department is "
                    "also embedded in the token. Accounts without a department are rejected.",
        responses={
            200: LoginResponseSerializer,
            400: OpenApiResponse(description="The account is not assigned to a department."),
            401: OpenApiResponse(description="Wrong username or password."),
        },
    )
)
class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer

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


class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer
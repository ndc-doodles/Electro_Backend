from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.exceptions import AuthenticationFailed
from retailapp.models import Customer, Administrator

class CustomJWTAuthentication(JWTAuthentication):
    def get_user(self, validated_token):
        try:
            user_id = validated_token["user_id"]
        except KeyError:
            raise AuthenticationFailed("User ID missing from token")

        try:
            return Customer.objects.get(id=user_id)
        except Customer.DoesNotExist:
            try:
                return Administrator.objects.get(id=user_id)
            except Administrator.DoesNotExist:
                raise AuthenticationFailed("User not found")


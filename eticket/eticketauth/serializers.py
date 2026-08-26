from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth import get_user_model

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = "__all__"




class RegisterSerializer(serializers.ModelSerializer):
    fullName = serializers.CharField(required=True)
    phone = serializers.CharField(required=True)
    email = serializers.EmailField(required=True)
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = [
            "fullName",
            "phone",
            "email",
            "password",
        ]

    def validate(self, attrs):
        email = attrs.get("email")
        phone = attrs.get("phone")

        if User.objects.filter(email=email).exists():
            raise serializers.ValidationError({
                "email": "Email already exists."
            })

        if User.objects.filter(phone=phone).exists():
            raise serializers.ValidationError({
                "phone": "Phone number already exists."
            })

        return attrs

    def create(self, validated_data):
        user = User.objects.create_user(
            email=validated_data["email"],
            fullName=validated_data["fullName"],
            phone=validated_data["phone"],
            password=validated_data["password"],
        )
        return user

class PhoneTokenObtainPairSerializer(TokenObtainPairSerializer):
    username = serializers.CharField(required=False, allow_blank=True)
    phone = serializers.CharField(required=False, allow_blank=True)
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        username = attrs.get("username")
        phone = attrs.get("phone")
        password = attrs.get("password")

        if phone:
            try:
                user = User.objects.get(phone=phone)
            except User.DoesNotExist:
                raise serializers.ValidationError("Invalid phone or password.")
        elif username:
            try:
                user = User.objects.get(username=username)
            except User.DoesNotExist:
                raise serializers.ValidationError("Invalid username or password.")
        else:
            raise serializers.ValidationError(
                "Provide either username or phone."
            )

        if not user.check_password(password):
            raise serializers.ValidationError("Invalid credentials.")

        refresh = self.get_token(user)

        return {
            "refresh": str(refresh),
            "access": str(refresh.access_token),
            "user": {
                "id": user.id,
                "fullName": f'{user.fullName}',
                "email": user.email,
                "phone": user.phone,
                "role": user.role,
            },
        }
    
# class PhoneTokenObtainPairSerializer(TokenObtainPairSerializer):
#     username = serializers.CharField(required=False)
#     phone = serializers.CharField(required=False)
#     password = serializers.CharField(write_only=True)

#     def validate(self, attrs):
#         username = attrs.get("username")
#         phone = attrs.get("phone")
#         password = attrs.get("password")

#         user = None

#         if phone:
#             try:
#                 user = User.objects.get(phone=phone)
#             except User.DoesNotExist:
#                 raise serializers.ValidationError("Invalid phone or password.")

#         elif username:
#             try:
#                 user = User.objects.get(username=username)
#             except User.DoesNotExist:
#                 raise serializers.ValidationError("Invalid username or password.")

#         else:
#             raise serializers.ValidationError(
#                 "Provide either username or phone."
#             )

#         if not user.check_password(password):
#             raise serializers.ValidationError("Invalid credentials.")

#         refresh = self.get_token(user)

#         return {
#             "refresh": str(refresh),
#             "access": str(refresh.access_token),
#             "user": {
#                 "id": user.id,
#                 "username": user.username,
#                 "email": user.email,
#                 "phone": user.phone,
#                 "role": user.role,
#             },
#         }
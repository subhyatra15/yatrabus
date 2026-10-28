from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework import serializers


from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from django.conf import settings
from django.contrib.auth import get_user_model

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()
    fullName = serializers.CharField(
        source="full_name",
        required=False,
        allow_blank=True,
    )
    emergencyContact = serializers.CharField(
        source="emergency_contact",
        required=False,
        allow_blank=True,
    )
    emergencyName = serializers.CharField(
        source="emergency_name",
        required=False,
        allow_blank=True,
    )

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "fullName",
            "phone",
            "address",
            "image",
            "emergencyContact",
            "emergencyName",
            "role",
            "date_joined",
        ]
        read_only_fields = ["id", "email", "role", "date_joined"]

    def get_image(self, obj):
        image = obj.image
        if not image or not image.name:
            return None
        try:
            return image.url
        except (ValueError, AttributeError):
            return None




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



class GoogleAuthSerializer(serializers.Serializer):
    id_token = serializers.CharField()
    role = serializers.ChoiceField(choices=['P', 'D'], required=False, default='P')

    def validate_id_token(self, value):
        try:
            info = id_token.verify_oauth2_token(
                value,
                google_requests.Request(),
                settings.GOOGLE_CLIENT_ID,
            )
        except Exception as e:
            raise serializers.ValidationError(f"Invalid Google token: {str(e)}")

        if not info.get("email_verified"):
            raise serializers.ValidationError("Google email not verified.")

        self.google_info = info
        return value

    def create(self, validated_data):
        info = self.google_info
        email = info["email"]
        google_id = info["sub"]
        full_name = info.get("name", "")
        picture = info.get("picture")

        user = User.objects.filter(email=email).first()

        if user is None:
            user = User.objects.create(
                email=email,
                fullName=full_name,
                phone=f"g_{google_id[:13]}",  
                google_id=google_id,
                role=validated_data.get("role", "P"),
            )
            user.set_unusable_password()
            user.save()
        else:
            if not user.google_id:
                user.google_id = google_id
                if not user.fullName and full_name:
                    user.fullName = full_name
                user.save()

        return user, picture
from rest_framework import permissions, viewsets,status,generics ,views
from rest_framework.permissions import AllowAny
from django.contrib.auth import get_user_model
from .serializers import UserSerializer,PhoneTokenObtainPairSerializer
# eticketauth/views.py
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.response import Response
from .serializers import RegisterSerializer


User = get_user_model()

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all().order_by("-date_joined")
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]
    # permission_classes = [AllowAny]



class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)

        if serializer.is_valid():
            user = serializer.save()

            return Response(
                {
                    "success": True,
                    "message": "User registered successfully.",
                    "data": {
                        "id": user.id,
                        "fullName": user.fullName,
                        "email": user.email,
                        "phone": user.phone,
                    },
                },
                status=status.HTTP_201_CREATED,
            )

        return Response(
            {
                "success": False,
                "message": "Registration failed.",
                "errors": serializer.errors,
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

class PhoneLoginView(TokenObtainPairView):
    serializer_class = PhoneTokenObtainPairSerializer



class VerifyTokenView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user

        refresh = RefreshToken.for_user(user)

        return Response({
            "success": True,
            "refresh": str(refresh),
            "access": str(refresh.access_token),
            "user": {
                "id": user.id,
                "fullName": user.fullName,
                "phone": user.phone,
                "email": user.email,
                "role": user.role,
            }
        })


# Auth Me
class AuthMeView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        return Response({
            "success": True,
            "user": {
                "id": user.id,
                "fullName": user.fullName,
                "phone": user.phone,
                "email": user.email,
                "role": user.role,
            }
        })
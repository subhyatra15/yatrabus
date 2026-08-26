from django.urls import include, path
from rest_framework import routers
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView 
)

from .views import UserViewSet,PhoneLoginView,RegisterView,VerifyTokenView,AuthMeView

router = routers.DefaultRouter()
router.register(r"users", UserViewSet)

urlpatterns = [
    path("", include(router.urls)),
    path("login/", PhoneLoginView.as_view(), name="login"),
    path("register/", RegisterView.as_view(), name="register"),
    path("refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("verify-token/", VerifyTokenView.as_view(), name="verify-token"),
    path("auth/me/", AuthMeView.as_view(), name="auth-me"),

]
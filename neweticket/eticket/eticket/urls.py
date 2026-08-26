"""
URL configuration for eticket project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf.urls.static import static
from django.conf import settings

urlpatterns = [
    path('admin/', admin.site.urls),
    path("api/v1/", include("eticketauth.urls")),
    path("api/v1/", include("bus.urls")),
    path("api/v1/", include("seat.urls")),
    path("api/v1/", include("city.urls")),
    path("api/v1/", include("routes.urls")),
    path("api/v1/", include("schedule.urls")),
    path("api/v1/", include("booking.urls")),
    path("api/v1/", include("payment.urls")),
    path("api/v1/", include("hiace.urls")),
    path("api/v1/", include("dashboard.urls")),
    path("api/v1/", include("appsettings.urls")),
    path(
        "api/v1/",
        include("bus_location.urls"),
    ),

]+ static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

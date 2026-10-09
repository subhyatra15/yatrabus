# eticket/appconfig/serializers.py
from rest_framework import serializers
from .models import AppVersionConfig


class AppVersionConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = AppVersionConfig
        fields = "__all__"
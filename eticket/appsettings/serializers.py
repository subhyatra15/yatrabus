from rest_framework import serializers
from .models import Settings

class SettingsSerializers(serializers.ModelSerializer):
    class Meta:
        model = Settings
        fields = "__all__"

        
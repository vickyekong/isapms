from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from apps.accounts.models import AuditLog, Notification, SystemSetting, User


class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False, allow_blank=False)
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "password",
            "first_name",
            "last_name",
            "full_name",
            "role",
            "phone",
            "is_active",
            "is_sample",
            "last_login",
            "created_at",
        ]
        read_only_fields = ["is_sample", "last_login", "created_at"]

    def get_full_name(self, obj):
        return obj.get_full_name()

    def validate_password(self, value):
        validate_password(value)
        return value

    def validate_role(self, value):
        if value not in User.Role.values:
            raise serializers.ValidationError("Select a valid role.")
        return value

    def create(self, validated_data):
        password = validated_data.pop("password", None)
        if not password:
            raise serializers.ValidationError({"password": "A password is required."})
        return User.objects.create_user(password=password, **validated_data)

    def update(self, instance, validated_data):
        password = validated_data.pop("password", None)
        for field, value in validated_data.items():
            setattr(instance, field, value)
        if password:
            instance.set_password(password)
        instance.save()
        return instance


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ["id", "title", "message", "category", "is_read", "link", "created_at"]
        read_only_fields = fields


class AuditLogSerializer(serializers.ModelSerializer):
    actor_name = serializers.SerializerMethodField()

    class Meta:
        model = AuditLog
        fields = ["id", "actor", "actor_name", "action", "entity", "entity_id", "description", "metadata", "ip_address", "created_at"]

    def get_actor_name(self, obj):
        return obj.actor.get_full_name() if obj.actor else "System"


class SystemSettingSerializer(serializers.ModelSerializer):
    class Meta:
        model = SystemSetting
        fields = ["id", "key", "value", "description", "updated_at"]
        read_only_fields = ["key", "updated_at"]


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()


class PasswordResetConfirmSerializer(serializers.Serializer):
    uid = serializers.CharField()
    token = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate_password(self, value):
        validate_password(value)
        return value

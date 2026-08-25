from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from .models import Employee

class StrictFieldsMixin:
    """Extra/unknown fields ko reject karne ke liye common logic"""
    def validate(self, data):
        allowed_fields = set(self.fields.keys())
        incoming_fields = set(self.initial_data.keys())
        unknown_fields = incoming_fields - allowed_fields

        if unknown_fields:
            raise serializers.ValidationError(
                f"Unexpected fields: {', '.join(unknown_fields)}"
            )
        return super().validate(data)

class EmployeeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Employee
        fields = [
            "id", "name", "email", "phone",
            "department", "designation", "salary",
            "joining_date", "is_active", "created_at"
        ]
        read_only_fields = ["is_active", "created_at"]


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])

    class Meta:
        model = Employee
        fields = ["name", "email", "password", "phone", "department", "designation", "salary", "joining_date"]

    def validate(self, data):
        allowed_fields = set(self.fields.keys())
        incoming_fields = set(self.initial_data.keys())
        unknown_fields = incoming_fields - allowed_fields

        if unknown_fields:
            raise serializers.ValidationError(f"Unexpected fields: {', '.join(unknown_fields)}")

        return data

    def validate_email(self, value):
        if Employee.objects.filter(email=value).exists():
            raise serializers.ValidationError("Email already registered.")
        return value

    def validate_phone(self, value):
        if value and (not value.isdigit() or len(value) != 12):
            raise serializers.ValidationError("Phone number must be exactly 12 digits.")
        return value

    def create(self, validated_data):
        return Employee.objects.create_user(**validated_data)


class LoginSerializer(StrictFieldsMixin, serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, validators=[validate_password])

class SendOTPSerializer(serializers.Serializer):
    email = serializers.EmailField()

class VerifyOTPSerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp = serializers.CharField(max_length=6)

class ResetPasswordWithOTPSerializer(serializers.Serializer):
    email = serializers.EmailField()
    new_password = serializers.CharField(write_only=True, validators=[validate_password])
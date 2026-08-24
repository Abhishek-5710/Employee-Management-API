from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from .models import Employee


class EmployeeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Employee
        fields = [
            "id", "name", "email", "phone",
            "department", "designation", "salary",
            "joining_date", "is_active", "created_at"
        ]
        read_only_fields = ["is_active", "created_at"]

    def validate_phone(self, value):
        if value and (not value.isdigit() or len(value) != 12):
            raise serializers.ValidationError("Phone number must be exactly 12 digits.")
        return value


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])

    class Meta:
        model = Employee
        fields = [
            "name", "email", "password", "phone",
            "department", "designation", "salary", "joining_date"
        ]

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


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
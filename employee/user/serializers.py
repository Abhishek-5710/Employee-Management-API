from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from .models import Employee,Attendance
import base64
import uuid
from django.core.files.base import ContentFile

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

class Base64ImageField(serializers.ImageField):
    def to_internal_value(self, data):
        if isinstance(data, str) and data.startswith("data:image"):
            format_part, imgstr = data.split(";base64,")
            ext = format_part.split("/")[-1]
            file_name = f"{uuid.uuid4()}.{ext}"
            data = ContentFile(base64.b64decode(imgstr), name=file_name) #text (Base64 string) ko wapas binary image data mein convert karta hai
        return super().to_internal_value(data)

class EmployeeSerializer(serializers.ModelSerializer):
    profile_picture = Base64ImageField(required=False)
    today_attendance = serializers.SerializerMethodField()

    class Meta:
        model = Employee
        fields = [
            "id", "name", "email", "phone","profile_picture",
            "department", "designation", "salary",
            "joining_date", "is_active", "created_at"
        ]
        read_only_fields = ["is_active", "created_at"]

    def get_today_attendance(self, obj):
        from django.utils import timezone
        today = timezone.now().date()
        attendance = Attendance.objects.filter(employee=obj, date=today).first()
        if attendance:
          return {
            "punch_in": attendance.punch_in,
            "punch_out": attendance.punch_out,
            "break_in": attendance.break_in,
            "break_out": attendance.break_out,
            "auto_punched_out": attendance.auto_punched_out,
            "total_timing": attendance.total_timing
        }
        return None

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


class AttendanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Attendance
        fields = ["id", "employee", "date", "punch_in", "punch_out", "breaks_in", "break_out", "break_out", "total_timing"]
        read_only_fields = ["employee", "date", "punch_in", "punch_out", "breaks_in", "break_out", "total_timing"]

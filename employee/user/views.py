from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.core.mail import send_mail
from .models import Employee
from .serializers import EmployeeSerializer, RegisterSerializer, LoginSerializer,ChangePasswordSerializer,SendOTPSerializer, VerifyOTPSerializer, ResetPasswordWithOTPSerializer
from django.core.mail import send_mail
from .models import Employee, EmailOTP
from django.utils import timezone
from datetime import timedelta
from rest_framework.decorators import api_view, throttle_classes
from rest_framework.throttling import ScopedRateThrottle
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

token_generator = PasswordResetTokenGenerator()
from .permissions import IsHR, IsHROrManager, IsSelfOrHR

class EmployeeViewSet(viewsets.ModelViewSet):
    queryset = Employee.objects.all()
    serializer_class = EmployeeSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend,SearchFilter, OrderingFilter]
    filterset_fields = ["department", "designation", "is_active"]
    search_fields = ["name", "email", "phone"]
    ordering_fields = ["salary", "joining_date", "created_at"]

  #get_permissions() check karta hai action allowed hai ya nahi → agar allowed, 
  # get_queryset() decide karta hai kaunsa data dikhega.
    def get_queryset(self):
        user = self.request.user
        if user.groups.filter(name__in=["HR", "Manager"]).exists():
            return Employee.objects.all()   # HR/Manager sabko dekh sakte hain
        return Employee.objects.filter(id=user.id)   # normal employee sirf khud ko

    def get_permissions(self): #kaunsa action allowed hai decide karta hai.
        if self.action in ["destroy"]:
            return [IsAuthenticated(), IsHR()]   # sirf HR delete kar sake
        elif self.action in ["update", "partial_update"]:
            return [IsAuthenticated(), IsSelfOrHR()]   # khud ya HR edit kare
        return [IsAuthenticated()]   # list/retrieve sabke liye (queryset khud filter karega)

@api_view(["POST"])
def register(request):
    serializer = RegisterSerializer(data=request.data)
    if serializer.is_valid():
        employee = serializer.save()
        return Response(
            {
                "message": "Employee registered successfully",
                "employee": {"name": employee.name, "email": employee.email, "phone": employee.phone}
            },
            status=status.HTTP_201_CREATED
        )
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

MAX_FAILED_ATTEMPTS = 5
LOCKOUT_DURATION_MINUTES = 15

@api_view(["POST"])
@throttle_classes([ScopedRateThrottle])
def login(request):
    login.throttle_scope = "login"
    serializer = LoginSerializer(data=request.data)
    if serializer.is_valid():
        email = serializer.validated_data["email"]
        password = serializer.validated_data["password"]

        try:
            employee = Employee.objects.get(email=email)
        except Employee.DoesNotExist:
            return Response({"message": "Invalid email or password"}, status=status.HTTP_401_UNAUTHORIZED)

        # Check karo account locked hai ya nahi
        if employee.locked_until and timezone.now() < employee.locked_until: #check karta hai ki abhi bhi lock period chal raha hai ya khatam ho gaya
            remaining = (employee.locked_until - timezone.now()).seconds // 60
            return Response(
                {"message": f"Account locked. Try again after {remaining} minutes."},
                status=status.HTTP_403_FORBIDDEN
            )

        authenticated_employee = authenticate(email=email, password=password)

        if authenticated_employee is not None:
            # Login successful — counter reset karo
            employee.failed_login_attempts = 0
            employee.locked_until = None
            employee.save()

            refresh = RefreshToken.for_user(employee)
            return Response(
                {
                    "message": "Login successful",
                    "name": employee.name,
                    "email": employee.email,
                    "access": str(refresh.access_token),
                    "refresh": str(refresh)
                },
                status=status.HTTP_200_OK
            )
        else:
            # Galat password — counter badhao
            employee.failed_login_attempts += 1

            if employee.failed_login_attempts >= MAX_FAILED_ATTEMPTS:
                employee.locked_until = timezone.now() + timedelta(minutes=LOCKOUT_DURATION_MINUTES)
                employee.save()
                return Response(
                    {"message": f"Account locked due to too many failed attempts. Try again after {LOCKOUT_DURATION_MINUTES} minutes."},
                    status=status.HTTP_403_FORBIDDEN
                )

            employee.save()
            attempts_left = MAX_FAILED_ATTEMPTS - employee.failed_login_attempts
            return Response(
                {"message": f"Invalid email or password. {attempts_left} attempts left."},
                status=status.HTTP_401_UNAUTHORIZED
            )

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# access token ko copy karo or profile api me authorization me Bearer Token field me daalo
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def profile(request):
    return Response({
        "name": request.user.name,
        "email": request.user.email,
        "phone": request.user.phone,
        "department": request.user.department,
        "designation": request.user.designation
    })

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def change_password(request):
    serializer = ChangePasswordSerializer(data=request.data)
    if serializer.is_valid():
        old_password = serializer.validated_data["old_password"]
        new_password = serializer.validated_data["new_password"]

        if not request.user.check_password(old_password):
            return Response({"message": "Old password is incorrect"}, status=status.HTTP_400_BAD_REQUEST)

        request.user.set_password(new_password)
        request.user.save()
        return Response({"message": "Password changed successfully"}, status=status.HTTP_200_OK)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(["POST"])
def send_otp(request):
    serializer = SendOTPSerializer(data=request.data)
    if serializer.is_valid():
        email = serializer.validated_data["email"]

        try:
            employee = Employee.objects.get(email=email)
        except Employee.DoesNotExist:
            return Response({"message": "No account found with this email"}, status=status.HTTP_404_NOT_FOUND)

        # Purane OTPs clean karo, sirf latest wala valid rahe
        EmailOTP.objects.filter(employee=employee).delete()

        otp_code = EmailOTP.generate_otp()
        EmailOTP.objects.create(employee=employee, otp=otp_code)

        send_mail(
            subject="Your OTP Code",
            message=f"Your OTP is {otp_code}. It is valid for 5 minutes.",
            from_email=None,
            recipient_list=[email],
        )

        return Response({"message": "OTP sent to your email"}, status=status.HTTP_200_OK)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
def verify_otp(request):
    serializer = VerifyOTPSerializer(data=request.data)
    if serializer.is_valid():
        email = serializer.validated_data["email"]
        otp_code = serializer.validated_data["otp"]

        try:
            employee = Employee.objects.get(email=email)
            otp_obj = EmailOTP.objects.filter(employee=employee, otp=otp_code).latest("created_at")
        except (Employee.DoesNotExist, EmailOTP.DoesNotExist):
            return Response({"message": "Invalid OTP"}, status=status.HTTP_400_BAD_REQUEST)

        if otp_obj.is_expired():
            return Response({"message": "OTP has expired"}, status=status.HTTP_400_BAD_REQUEST)

        otp_obj.is_verified = True
        otp_obj.save()

        return Response({"message": "OTP verified successfully"}, status=status.HTTP_200_OK)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
def reset_password_with_otp(request):
    serializer = ResetPasswordWithOTPSerializer(data=request.data)
    if serializer.is_valid():
        email = serializer.validated_data["email"]
        new_password = serializer.validated_data["new_password"]

        try:
            employee = Employee.objects.get(email=email)
            otp_obj = EmailOTP.objects.filter(employee=employee, is_verified=True).latest("created_at")
        except (Employee.DoesNotExist, EmailOTP.DoesNotExist):
            return Response({"message": "OTP verification required first"}, status=status.HTTP_400_BAD_REQUEST)

        if otp_obj.is_expired():
            return Response({"message": "OTP expired, please request a new one"}, status=status.HTTP_400_BAD_REQUEST)

        employee.set_password(new_password)
        employee.save()

        otp_obj.delete()   # OTP use ho gaya, ab delete kar do (dobara use na ho)

        return Response({"message": "Password reset successful"}, status=status.HTTP_200_OK)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
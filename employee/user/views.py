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
from .models import Employee, Attendance, EmailOTP
from .serializers import EmployeeSerializer, RegisterSerializer, LoginSerializer,ChangePasswordSerializer,SendOTPSerializer, VerifyOTPSerializer, ResetPasswordWithOTPSerializer, AttendanceSerializer
from django.core.mail import send_mail
from django.utils import timezone
from datetime import timedelta
from rest_framework.decorators import api_view, throttle_classes
from rest_framework.throttling import ScopedRateThrottle
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from .tasks import send_otp_email
from rest_framework.parsers import MultiPartParser, FormParser #for profile picture 

token_generator = PasswordResetTokenGenerator()
from .permissions import IsHR, IsHROrManager, IsSelfOrHR
from django.utils.translation import gettext as _  #i18n for language
from .filters import AttendanceFilter
from .utils import calculate_age_details
from datetime import datetime
# from django.core.cache import cache

# @api_view(["GET"])
# def get_all_employees_cached(request):
#     cached_data = cache.get("all_employees")   # <- ye actual caching logic hai

#     if cached_data is not None:
#         return Response(cached_data)

#     employees = Employee.objects.all()
#     serializer = EmployeeSerializer(employees, many=True)
#     data = serializer.data

#     cache.set("all_employees", data, timeout=300)   # <- ye actual caching logic hai

#     return Response(data)

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
                "message": _("Employee registered successfully"),
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
                {"message": _(f"Account locked. Try again after {remaining} minutes.")},
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
                    "message": _("Login successful"),
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

        send_otp_email.delay(email, otp_code)
        
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


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def upload_profile_picture(request):
    employee = request.user
    if "profile_picture" not in request.FILES:   # "profile_picture" key of uploading image
        return Response({"message": "No file uploaded"}, status=status.HTTP_400_BAD_REQUEST)

    employee.profile_picture = request.FILES["profile_picture"]
    employee.save()

    return Response(
        {
            "message": "Profile picture uploaded successfully",
            "url": request.build_absolute_uri(employee.profile_picture.url)
        },
        status=status.HTTP_200_OK
    )

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def punch(request, punch_type):

    employee = request.user
    today = timezone.localtime(timezone.now()).date()

    attendance = Attendance.objects.filter(
        employee=employee,
        date=today
    ).first()

    if punch_type == "in":

        # Already punched in today
        if attendance:
            return Response(
                {
                    "message": "You have already punched in today"
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        attendance = Attendance.objects.create(
            employee=employee,
            date=today,
            punch_in=timezone.now()
        )

        return Response(
            {
                "message": "Punched in successfully",
                "status": "punched_in"
            },
            status=status.HTTP_201_CREATED
        )

    elif punch_type == "out":

        # Must punch in first
        if not attendance:
            return Response(
                {
                    "message": "You must punch in first"
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # Already punched out
        if attendance.punch_out is not None:
            return Response(
                {
                    "message": "You have already punched out today"
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # Check if a break is still open
        if len(attendance.break_in) > len(attendance.break_out):
            return Response(
                {
                    "message": "You must break out before punching out"
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # Punch out
        attendance.punch_out = timezone.now()

        # Calculate total working time
        total_timing = (
            attendance.punch_out - attendance.punch_in
        )

        # Subtract break time
        for i in range(len(attendance.break_in)):

            if i < len(attendance.break_out):

                break_in_dt = datetime.fromisoformat(
                    attendance.break_in[i]
                )

                break_out_dt = datetime.fromisoformat(
                    attendance.break_out[i]
                )

                total_timing -= (
                    break_out_dt - break_in_dt
                )

        attendance.total_timing = total_timing

        attendance.save(
            update_fields=[
                "punch_out",
                "total_timing"
            ]
        )

        return Response(
            {
                "message": "Punched out successfully",
                "status": "punched_out",
                "total_timing": str(attendance.total_timing)
            },
            status=status.HTTP_200_OK
        )
    else:

        return Response(
            {
                "message": "Invalid punch type. Use in or out"
            },
            status=status.HTTP_400_BAD_REQUEST
        )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def break_toggle(request, break_type):

    employee = request.user
    today = timezone.now().date()

    attendance = Attendance.objects.filter(
        employee=employee,
        date=today
    ).first()

    if not attendance:
        return Response(
            {"message": "You must punch in first"},
            status=status.HTTP_400_BAD_REQUEST
        )

    if attendance.punch_out is not None:
        return Response(
            {"message": "You have already punched out today"},
            status=status.HTTP_400_BAD_REQUEST
        )

    break_in_list = attendance.break_in
    break_out_list = attendance.break_out

    # BREAK IN
    if break_type == "break_in":

        if len(break_in_list) > len(break_out_list):
            return Response(
                {"message": "You are already on break"},
                status=status.HTTP_400_BAD_REQUEST
            )

        break_in_list.append(
            timezone.localtime(timezone.now()).isoformat()
        )

        attendance.break_in = break_in_list

        attendance.save(
            update_fields=["break_in"]
        )

        return Response(
            {
                "message": "Break in successfully",
                "status": "break_in",
                "break_in": break_in_list,
                "break_out": break_out_list
            },
            status=status.HTTP_201_CREATED
        )

    # BREAK OUT
    elif break_type == "break_out":

        if len(break_in_list) <= len(break_out_list):
            return Response(
                {"message": "You are not currently on break"},
                status=status.HTTP_400_BAD_REQUEST
            )

        break_out_list.append(
            timezone.localtime(timezone.now()).isoformat()
        )

        attendance.break_out = break_out_list

        attendance.save(
            update_fields=["break_out"]
        )

        return Response(
            {
                "message": "Break out successfully",
                "status": "break_out",
                "break_in": break_in_list,
                "break_out": break_out_list
            },
            status=status.HTTP_200_OK
        )

    # INVALID BREAK TYPE
    else:
        return Response(
            {"message": "Invalid break type. Use break_in or break_out"},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    
class AttendanceViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = AttendanceSerializer
    permission_classes = [IsAuthenticated]

    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_class = AttendanceFilter
    ordering_fields = ["date", "punch_in", "punch_out"]

    def get_queryset(self):
        user = self.request.user
        if user.groups.filter(name__in=["HR", "Manager"]).exists():
            return Attendance.objects.all()
        return Attendance.objects.filter(employee=user)


@api_view(["POST"])
def age_calculator(request):
    dob_string = request.data.get("date_of_birth")
    calculate_on_string = request.data.get("calculate_on")

    if not dob_string:
        return Response(
            {"message": "date_of_birth is required (format: YYYY-MM-DD)"},
            status=status.HTTP_400_BAD_REQUEST
        )

    if not calculate_on_string:
        return Response(
            {"message": "calculate_on is required (format: YYYY-MM-DD)"},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        dob = datetime.strptime(dob_string, "%Y-%m-%d").date()
        calculate_on = datetime.strptime(
            calculate_on_string, "%Y-%m-%d"
        ).date()
    except ValueError:
        return Response(
            {"message": "Invalid date format. Use YYYY-MM-DD"},
            status=status.HTTP_400_BAD_REQUEST
        )

    if dob > calculate_on:
        return Response(
            {"message": "Date of birth cannot be after calculation date"},
            status=status.HTTP_400_BAD_REQUEST
        )

    result = calculate_age_details(dob, calculate_on)

    return Response(
        result,
        status=status.HTTP_200_OK
    )
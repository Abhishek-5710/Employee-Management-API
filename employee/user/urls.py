from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView
from user.views import (
    EmployeeViewSet,
    register,
    login,
    profile,
    change_password,
    send_otp,
    verify_otp,
    reset_password_with_otp,
    upload_profile_picture,
    punch,
    AttendanceViewSet,
    age_calculator,
    break_toggle,
)

router = DefaultRouter()
router.register("employees", EmployeeViewSet)
router.register("attendance", AttendanceViewSet, basename="attendance")

urlpatterns = [
    path("attendance/punch/", punch),          # sirf punch in/out
    path("attendance/break/", break_toggle),
    path("", include(router.urls)),
    path("register/", register),
    path("login/", login),
    path("token/refresh/", TokenRefreshView.as_view()), #class ko URL ke liye callable view banana and use only in class based-view
    path("profile/", profile),
    path("change-password/", change_password), # Reset-PASS
    path("send-otp/", send_otp),
    path("verify-otp/", verify_otp),
    path("reset-password-otp/", reset_password_with_otp), # Forget-PASS
    path("upload-profile-picture/", upload_profile_picture),
    # path("punch-in/", punch_in),
    # path("punch-out/", punch_out),
    # path("my-attendance/", my_attendance),
    path("age-calculator/", age_calculator),
]
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView
from user.views import EmployeeViewSet, register, login, profile,change_password, send_otp, verify_otp, reset_password_with_otp

router = DefaultRouter()
router.register("employees", EmployeeViewSet)

urlpatterns = [
    path("", include(router.urls)),
    path("register/", register),
    path("login/", login),
    path("token/refresh/", TokenRefreshView.as_view()),
    path("profile/", profile),
    path("change-password/", change_password), # Reset-PASS
    path("send-otp/", send_otp),
    path("verify-otp/", verify_otp),
    path("reset-password-otp/", reset_password_with_otp), # Forget-PASS
]
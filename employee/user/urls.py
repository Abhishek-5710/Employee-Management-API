from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView
from user.views import EmployeeViewSet, register, login, profile

router = DefaultRouter()
router.register("employees", EmployeeViewSet)

urlpatterns = [
    path("", include(router.urls)),
    path("register/", register),
    path("login/", login),
    path("token/refresh/", TokenRefreshView.as_view()),
    path("profile/", profile),
]
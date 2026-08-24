from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate

from .models import Employee
from .serializers import EmployeeSerializer, RegisterSerializer, LoginSerializer


class EmployeeViewSet(viewsets.ModelViewSet):
    queryset = Employee.objects.all()
    serializer_class = EmployeeSerializer
    permission_classes = [IsAuthenticated]


@api_view(["POST"])
def register(request):
    serializer = RegisterSerializer(data=request.data)
    if serializer.is_valid():
        employee = serializer.save()
        return Response(
            {
                "message": "Employee registered successfully",
                "employee": {"name": employee.name, "email": employee.email}
            },
            status=status.HTTP_201_CREATED
        )
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
def login(request):
    serializer = LoginSerializer(data=request.data)
    if serializer.is_valid():
        email = serializer.validated_data["email"]
        password = serializer.validated_data["password"]

        employee = authenticate(email=email, password=password)

        if employee is not None:
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
        return Response(
            {"message": "Invalid email or password"},
            status=status.HTTP_401_UNAUTHORIZED
        )
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


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
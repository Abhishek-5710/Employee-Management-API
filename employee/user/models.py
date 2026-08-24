from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.core.validators import RegexValidator


# Ye class sirf ek kaam karti hai: employee banate waqt password ko hash (secure) karna
class EmployeeManager(BaseUserManager):

    def create_user(self, email, name, password=None, **extra_fields):
        if not email:
            raise ValueError("Email is required")
        email = self.normalize_email(email)
        employee = self.model(email=email, name=name, **extra_fields)
        employee.set_password(password)   # <- password yahan hash hota hai
        employee.save(using=self._db)
        return employee

    # Ye sirf "python manage.py createsuperuser" command chalane pe use hoti hai
    def create_superuser(self, email, name, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return self.create_user(email, name, password, **extra_fields)


# AbstractBaseUser aur PermissionsMixin se "password handling" aur "admin permissions" udhaar li
class Employee(AbstractBaseUser, PermissionsMixin):

    name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    phone = models.CharField(
        max_length=12,
        validators=[RegexValidator(regex=r'^\d{12}$', message="Phone number must be exactly 12 digits.")],
        blank=True,
        null=True
    )
    department = models.CharField(max_length=100, blank=True, null=True)
    designation = models.CharField(max_length=100, blank=True, null=True)
    salary = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    joining_date = models.DateField(blank=True, null=True)

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)   # admin panel access ke liye zaroori
    created_at = models.DateTimeField(auto_now_add=True)

    USERNAME_FIELD = "email"       # login email se hoga
    REQUIRED_FIELDS = ["name"]     # superuser banate waqt name bhi maangega

    objects = EmployeeManager()    # password-hashing wala manager attach kiya

    def __str__(self):
        return self.name
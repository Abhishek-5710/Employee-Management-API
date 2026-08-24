from django.test import TestCase
from rest_framework.test import APIClient
from .models import Employee

class EmployeeTests(TestCase):
    def setUp(self):
        # har test se pehle ye chalega -- ek employee pehle hi ban jayegi 
        self.client = APIClient()
        self.employee = Employee.objects.create_user(
            name = "Abhi",
            email = "abhi5710@gmail.com",
            phone = "916352074492",
            password = "abhishek5710"
        )
#"Bas maan lo ki ye self.employee already login hai — 
# password check mat karo, token bhi mat banao, seedha is request ko authenticated treat karo."
        self.client.force_authenticate(user=self.employee)
    
    def test_employee_list(self):
        response = self.client.get("/api/employees/")
        self.assertEqual(response.status_code, 200)

    def test_create_employee(self):
        # this is checking the new employee is create or not 
        data = {"name":"Utsav", "email":"utsav123@gmail.com", "phone":"911234567890"}
        response = self.client.post("/api/employees/", data)
        self.assertEqual(response.status_code, 201)

    def test_invalid_phone_rejected(self):
        data = {"name": "test user", "email": "test@gmail.com", "phone": "1232454"}
        response = self.client.post("/api/employees/", data)
        self.assertEqual(response.status_code, 400)
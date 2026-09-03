from celery import shared_task
from django.core.mail import send_mail
from django.core.management import call_command

#ye decorator kisi bhi normal function ko "Celery task" bana deta hai
@shared_task
def send_otp_email(email, otp_code):
    send_mail(
        subject="Your OTP Code",
        message=f"Your OTP is {otp_code}. It is valid for 5 minutes.",
        from_email=None,
        recipient_list=[email],
    )

@shared_task
def run_auto_punch_out():
    call_command("auto_punch_out")
import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "employee.settings")

app = Celery("employee")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()  #Celery ko batata hai ki har app ke tasks.py file jaha bhi background tasks defined honge

# # 1. WSL (Ubuntu) terminal:
# wsl
# sudo service redis-server start  --terminal-1

# # 2. Windows Terminal 1:
# python manage.py runserver  --terminal-2

# # 3. Windows Terminal 2:
# celery -A employee worker --loglevel=info --pool=solo --terminal-3

# # 4. Postman se testing

app.conf.beat_schedule = {
    "auto-punch-out-daily": {
        "task": "user.tasks.run_auto_punch_out",
        "schedule": crontab(hour=23, minute=50),   # har raat 11:50 PM
    },
}
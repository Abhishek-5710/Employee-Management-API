from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from user.models import Attendance

class Command(BaseCommand):
    help = "Automatically punch-out employees who forgot to punch out on previous days"

    def handle(self, *args, **kwargs):
        today = timezone.now().date()

        # Purane din ke wo records dhoondo jinka punch_out abhi tak nahi hua
        pending_records = Attendance.objects.filter(
            date__lt=today,
            punch_out__isnull=True
        )

        count = 0
        for record in pending_records:
            # Default: us din raat 11:59 PM ko auto punch-out kar do
            auto_time = timezone.datetime.combine(record.date, timezone.datetime.max.time())
            auto_time = timezone.make_aware(auto_time)

            record.punch_out = auto_time
            record.auto_punched_out = True
            record.save()
            count += 1

        self.stdout.write(self.style.SUCCESS(f"Auto punched-out {count} record(s)"))
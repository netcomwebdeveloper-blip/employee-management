from django.core.management.base import BaseCommand
from django.utils import timezone
from core.models import EmployeeProfile, MonthlyLeaveCredit


class Command(BaseCommand):
    help = 'Add one casual leave balance for this month to all active employees once'

    def handle(self, *args, **kwargs):
        today = timezone.localdate()
        count = 0

        for emp in EmployeeProfile.objects.filter(is_active_employee=True):
            credit, created = MonthlyLeaveCredit.objects.get_or_create(
                employee=emp,
                year=today.year,
                month=today.month,
                defaults={'casual_added': 1}
            )
            if created:
                emp.casual_leave_balance += 1
                emp.save()
                count += 1

        self.stdout.write(self.style.SUCCESS(f'Monthly casual leave added for {count} employees.'))

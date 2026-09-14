import time
from datetime import datetime

from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Eslatma va 'kelmadi' vazifalarini doimiy fon rejimida ishga tushiradi"

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("Scheduler ishga tushdi..."))

        last_reminder_run_date = None

        while True:
            now = datetime.now()

            # Har kuni soat 18:00 da (bir kunda faqat bir marta) eslatmalar
            if now.hour == 18 and last_reminder_run_date != now.date():
                self.stdout.write(f"[{now}] Eslatmalar yuborilmoqda...")
                call_command("send_reminders")
                last_reminder_run_date = now.date()

            # Har 5 daqiqada "kelmadi" tekshiruvi
            if now.minute % 5 == 0:
                call_command("mark_noshow")

            time.sleep(60)
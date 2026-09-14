from datetime import datetime

from django.core.management.base import BaseCommand
from django.utils import timezone

from accounts.models import Appointment


class Command(BaseCommand):
    help = (
        "Qabul vaqti o'tib ketgan va 'keldi' deb belgilanmagan "
        "navbatlarni 'kelmadi' holatiga o'tkazadi"
    )

    def handle(self, *args, **options):
        now = timezone.now()
        current_tz = timezone.get_current_timezone()

        candidates = Appointment.objects.filter(
            status="band",
        ).select_related("slot")

        updated_count = 0

        for appointment in candidates:
            slot = appointment.slot
            naive_dt = datetime.combine(slot.date, slot.end_time)
            aware_dt = timezone.make_aware(naive_dt, current_tz)

            if now > aware_dt:
                appointment.status = "kelmadi"
                appointment.save(update_fields=["status"])
                updated_count += 1

        self.stdout.write(
            self.style.SUCCESS(f"{updated_count} ta navbat 'kelmadi' ga o'tkazildi.")
        )
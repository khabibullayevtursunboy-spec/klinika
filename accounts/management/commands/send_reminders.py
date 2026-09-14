from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from accounts.models import Appointment
from accounts.telegram_utils import send_telegram_message


class Command(BaseCommand):
    help = "Ertaga bo'ladigan navbatlar uchun bemorlarga eslatma yuboradi"

    def handle(self, *args, **options):
        tomorrow = (timezone.now() + timedelta(days=1)).date()

        appointments = Appointment.objects.filter(
            slot__date=tomorrow,
            status="band",
            reminder_sent_at__isnull=True,
        ).select_related("slot", "slot__doctor", "slot__doctor__user", "patient")

        sent_count = 0

        for appointment in appointments:
            patient = appointment.patient
            chat_id = patient.telegram_id

            if not chat_id:
                continue

            slot = appointment.slot
            doctor = slot.doctor
            doctor_name = doctor.user.get_full_name() or doctor.user.username

            text = (
                "🔔 *Eslatma!*\n\n"
                "Ertaga sizda qabul bor:\n"
                f"🩺 Shifokor: {doctor_name}\n"
                f"📅 Sana: {slot.date}\n"
                f"⏰ Vaqt: {slot.start_time.strftime('%H:%M')}\n"
                f"🚪 Xona: {doctor.room}\n\n"
                "Agar kela olmasangiz, iltimos oldindan bekor qiling."
            )

            reply_markup = {
                "inline_keyboard": [
                    [
                        {
                            "text": "❌ Bekor qilaman",
                            "callback_data": f"remindcancel_{appointment.id}",
                        }
                    ]
                ]
            }

            success = send_telegram_message(chat_id, text, reply_markup=reply_markup)

            if success:
                appointment.reminder_sent_at = timezone.now()
                appointment.save(update_fields=["reminder_sent_at"])
                sent_count += 1

        self.stdout.write(
            self.style.SUCCESS(f"{sent_count} ta eslatma yuborildi.")
        )
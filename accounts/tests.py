import threading
from django.test import TestCase
from django.db import IntegrityError, transaction
from your_app.models import Slot, Appointment, User

class SlotConcurrencyTestCase(TestCase):
    def setUp(self):
        # Bemorlar va slot yaratib olamiz
        self.patient1 = User.objects.create(username="p1", role="bemor")
        self.patient2 = User.objects.create(username="p2", role="bemor")
        # Slot yaratish kodi...

    def test_concurrent_appointment_booking(self):
        results = []

        def book_slot(patient):
            try:
                with transaction.atomic():
                    slot = Slot.objects.select_for_update().get(id=self.slot.id)
                    if not slot.is_available:
                        raise ValueError("Slot band")
                    
                    Appointment.objects.create(slot=slot, patient=patient)
                    slot.is_available = False
                    slot.save()
                    results.append("SUCCESS")
            except (IntegrityError, ValueError):
                results.append("FAILED")

        # Ikkita parallel potok (thread) yuboramiz
        t1 = threading.Thread(target=book_slot, args=(self.patient1,))
        t2 = threading.Thread(target=book_slot, args=(self.patient2,))

        t1.start()
        t2.start()
        t1.join()
        t2.join()

        # Natijada 1 ta SUCCESS va 1 ta FAILED bo'lishi shart
        self.assertEqual(results.count("SUCCESS"), 1)
        self.assertEqual(results.count("FAILED"), 1)
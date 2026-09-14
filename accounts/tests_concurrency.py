import threading

from django.test import TransactionTestCase
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from accounts.models import Appointment, Doctor, Slot, Speciality, User


class ParallelBookingTestCase(TransactionTestCase):
    """
    PDF §7 talabi: ikkita bemor bir vaqtning o'zida bitta slotni
    band qilishga uringanda, faqat bittasi muvaffaqiyatli bo'lishi kerak.
    """

    def setUp(self):
        self.speciality = Speciality.objects.create(name="Test yo'nalish")

        self.doctor_user = User.objects.create_user(
            username="test_doctor", password="pass12345", role="shifokor"
        )
        self.doctor = Doctor.objects.create(
            user=self.doctor_user,
            speciality=self.speciality,
            room="1",
            price=10000,
        )

        self.slot = Slot.objects.create(
            doctor=self.doctor,
            date=timezone.now().date() + timezone.timedelta(days=1),
            start_time="10:00",
            end_time="10:20",
            is_available=True,
        )

        self.patient1 = User.objects.create_user(
            username="patient1", password="pass12345", role="bemor"
        )
        self.patient2 = User.objects.create_user(
            username="patient2", password="pass12345", role="bemor"
        )

        self.results = {}

    def _book_slot(self, patient, key):
        client = APIClient()
        token = str(RefreshToken.for_user(patient).access_token)
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        response = client.post(
            "/api/appointments/create/",
            {"slot": self.slot.id, "complaint": "test"},
            format="json",
        )

        self.results[key] = response.status_code

    def test_two_patients_booking_same_slot_simultaneously(self):
        thread1 = threading.Thread(
            target=self._book_slot, args=(self.patient1, "patient1")
        )
        thread2 = threading.Thread(
            target=self._book_slot, args=(self.patient2, "patient2")
        )

        thread1.start()
        thread2.start()

        thread1.join()
        thread2.join()

        statuses = list(self.results.values())

        success_count = sum(1 for s in statuses if s in [200, 201])
        conflict_count = sum(1 for s in statuses if s in [400, 409])

        self.assertEqual(
            success_count, 1,
            f"Faqat bitta so'rov muvaffaqiyatli bo'lishi kerak edi, natija: {self.results}"
        )
        self.assertEqual(
            conflict_count, 1,
            f"Bitta so'rov konflikt bilan rad etilishi kerak edi, natija: {self.results}"
        )

        appointments_count = Appointment.objects.filter(slot=self.slot).count()
        self.assertEqual(
            appointments_count, 1,
            "Bazada aynan bitta navbat bo'lishi kerak, ikkitasi emas!"
        )

        self.slot.refresh_from_db()
        self.assertFalse(
            self.slot.is_available,
            "Band qilingandan keyin slot 'band' bo'lishi kerak"
        )
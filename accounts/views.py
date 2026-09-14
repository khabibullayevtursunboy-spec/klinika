from datetime import datetime, time, timedelta
from django.db import transaction
from django.db.utils import IntegrityError
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, generics, permissions, status
from rest_framework.exceptions import ValidationError, APIException
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.tokens import RefreshToken

from .models import Appointment, Doctor, Schedule, Slot, Speciality, User, Visit
from .serializers import (
    AppointmentSerializer,
    AppointmentStatusSerializer,
    DoctorSerializer,
    ScheduleSerializer,
    SlotSerializer,
    SpecialitySerializer,
    VisitSerializer,
)
from .telegram_utils import send_telegram_message


class ConflictError(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = "Bu vaqt endigina band qilindi."
    default_code = "conflict"


class IsRegistrator(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == "registrator"


class IsDoctor(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == "shifokor"


class IsPatient(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == "bemor"


class SpecialityListView(generics.ListAPIView):
    queryset = Speciality.objects.filter(is_active=True)
    serializer_class = SpecialitySerializer
    permission_classes = [permissions.AllowAny]


class DoctorListCreateView(generics.ListCreateAPIView):
    queryset = Doctor.objects.all()
    serializer_class = DoctorSerializer
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_fields = ["speciality", "is_active"]
    search_fields = [
        "user__first_name",
        "user__last_name",
        "user__username",
    ]

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsRegistrator()]
        return [permissions.AllowAny()]


class DoctorUpdateView(generics.UpdateAPIView):
    queryset = Doctor.objects.all()
    serializer_class = DoctorSerializer
    permission_classes = [IsRegistrator]
    http_method_names = ["patch"]


class ScheduleListCreateView(generics.ListCreateAPIView):
    serializer_class = ScheduleSerializer

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsRegistrator()]
        return [permissions.IsAuthenticated()]

    def get_queryset(self):
        queryset = Schedule.objects.all()
        doctor = self.request.query_params.get("doctor")
        start_date = self.request.query_params.get("start_date")
        end_date = self.request.query_params.get("end_date")

        if doctor:
            queryset = queryset.filter(doctor_id=doctor)
        if start_date and end_date:
            queryset = queryset.filter(date__range=[start_date, end_date])
        return queryset


class GenerateSlotsView(APIView):
    permission_classes = [IsRegistrator]

    def post(self, request, id):
        try:
            schedule = Schedule.objects.get(pk=id)
        except Schedule.DoesNotExist:
            return Response(
                {"error": "Jadval topilmadi."},
                status=status.HTTP_404_NOT_FOUND,
            )

        doctor = schedule.doctor
        slot_minutes = doctor.slot_minutes
        start_time = schedule.start_time
        end_time = schedule.end_time
        break_start = schedule.break_start
        break_end = schedule.break_end
        date = schedule.date

        current_time = datetime.combine(date, start_time)
        end_datetime = datetime.combine(date, end_time)

        slots_created = 0
        while current_time + timedelta(minutes=slot_minutes) <= end_datetime:
            slot_start = current_time.time()
            slot_end = (current_time + timedelta(minutes=slot_minutes)).time()

            if break_start and break_end:
                if not (slot_end <= break_start or slot_start >= break_end):
                    current_time += timedelta(minutes=slot_minutes)
                    continue

            Slot.objects.get_or_create(
                doctor=doctor,
                date=date,
                start_time=slot_start,
                defaults={"end_time": slot_end, "is_available": True},
            )
            slots_created += 1
            current_time += timedelta(minutes=slot_minutes)

        return Response(
            {
                "message": f"Muvaffaqiyatli {slots_created} ta slot generatsiya qilindi."
            },
            status=status.HTTP_201_CREATED,
        )


class SlotListView(generics.ListAPIView):
    serializer_class = SlotSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        doctor = self.request.query_params.get("doctor")
        date = self.request.query_params.get("date")

        if not doctor or not date:
            return Slot.objects.none()

        return Slot.objects.filter(
            doctor_id=doctor, date=date, is_available=True
        )


class AvailableDaysView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        doctor_id = request.query_params.get("doctor")
        if not doctor_id:
            return Response(
                {"error": "Doctor ID ko'rsatilishi shart."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        today = timezone.now().date()
        future_date = today + timedelta(days=14)

        available_days = (
            Slot.objects.filter(
                doctor_id=doctor_id,
                date__range=[today, future_date],
                is_available=True,
            )
            .values_list("date", flat=True)
            .distinct()
        )

        return Response(list(available_days))


class AppointmentCreateView(generics.CreateAPIView):
    serializer_class = AppointmentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        slot_id = self.request.data.get("slot")

        if self.request.user.role == "bemor":
            patient = self.request.user
        else:
            patient_id = self.request.data.get("patient")
            if not patient_id:
                raise ValidationError(
                    {"error": "Siz bemor emassiz. JSON ichida 'patient' ID sini kiriting."}
                )

            try:
                patient = User.objects.get(id=patient_id, role="bemor")
            except User.DoesNotExist:
                raise ValidationError({"error": "Bunday ID li bemor topilmadi."})

        slot = Slot.objects.filter(pk=slot_id).first()
        if not slot or slot.date < timezone.now().date():
            raise ValidationError(
                {"error": "O'tgan sanaga navbat olib bo'lmaydi yoki slot topilmadi."}
            )

        existing_active = Appointment.objects.filter(
            patient=patient,
            slot__doctor=slot.doctor,
            slot__date=slot.date,
            status="band",
        ).exists()

        if existing_active:
            raise ValidationError(
                {
                    "error": "Sizda bu shifokorga ushbu kunda allaqachon faol navbat mavjud."
                }
            )

        try:
            with transaction.atomic():
                locked_slot = Slot.objects.select_for_update().get(
                    pk=slot_id, is_available=True
                )
                locked_slot.is_available = False
                locked_slot.save()

                appointment = serializer.save(
                    slot=locked_slot, patient=patient, status="band"
                )
        except Slot.DoesNotExist:
            raise ConflictError("Bu vaqt endigina band qilindi yoki mavjud emas.")
        except IntegrityError:
            raise ConflictError("Bu vaqt endigina band qilindi.")

        self._notify_doctor(appointment)

    def _notify_doctor(self, appointment):
        doctor_user = appointment.slot.doctor.user
        chat_id = doctor_user.telegram_id

        if not chat_id:
            return

        patient = appointment.patient
        patient_name = patient.get_full_name() or patient.username
        slot = appointment.slot

        text = (
            "🔔 *Yangi navbat!*\n\n"
            f"👤 Bemor: {patient_name}\n"
            f"📞 Tel: {patient.phone}\n"
            f"📅 Sana: {slot.date}\n"
            f"⏰ Vaqt: {slot.start_time.strftime('%H:%M')}\n"
            f"📝 Shikoyat: {appointment.complaint or 'Yo' + chr(0x02bb) + 'q'}"
        )

        send_telegram_message(chat_id, text)


class AppointmentListView(generics.ListAPIView):
    serializer_class = AppointmentSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["slot__date", "slot__doctor", "status"]

    def get_queryset(self):
        user = self.request.user
        queryset = Appointment.objects.all()

        if user.role == "bemor":
            queryset = queryset.filter(patient=user)
        elif user.role == "shifokor":
            queryset = queryset.filter(slot__doctor__user=user)

        return queryset


class MyAppointmentListView(generics.ListAPIView):
    serializer_class = AppointmentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Appointment.objects.filter(patient=self.request.user)


class AppointmentCancelView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, id):
        try:
            appointment = Appointment.objects.get(pk=id)
        except Appointment.DoesNotExist:
            return Response(
                {"error": "Navbat topilmadi."}, status=status.HTTP_404_NOT_FOUND
            )

        if request.user.role == "bemor" and appointment.patient != request.user:
            return Response(
                {"error": "Ruxsat etilmagan."},
                status=status.HTTP_403_FORBIDDEN,
            )

        naive_datetime = datetime.combine(
            appointment.slot.date, appointment.slot.start_time
        )

        current_tz = timezone.get_current_timezone()
        appointment_datetime = timezone.make_aware(naive_datetime, current_tz)

        if timezone.now() + timedelta(hours=2) > appointment_datetime:
            return Response(
                {
                    "error": "Qabul vaqtidan 2 soatdan kam vaqt qolganda navbatni bekor qilib bo'lmaydi."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            slot = appointment.slot
            slot.is_available = True
            slot.save()

            appointment.status = "bekor"
            appointment.cancelled_at = timezone.now()
            appointment.save()

        return Response(
            {"message": "Navbat muvaffaqiyatli bekor qilindi."},
            status=status.HTTP_200_OK,
        )


class AppointmentStatusUpdateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, id):
        try:
            if request.user.role == "shifokor":
                appointment = Appointment.objects.get(
                    pk=id, slot__doctor__user=request.user
                )
            else:
                appointment = Appointment.objects.get(pk=id)
        except Appointment.DoesNotExist:
            return Response(
                {"error": "Navbat topilmadi."}, status=status.HTTP_404_NOT_FOUND
            )

        status_val = request.data.get("status")
        if status_val not in ["keldi", "kelmadi"]:
            return Response(
                {"error": "Noto'g'ri status."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        appointment.status = status_val
        appointment.save()
        return Response({"message": f"Navbat statusi '{status_val}' ga o'zgardi."})


class VisitCreateView(generics.CreateAPIView):
    queryset = Visit.objects.all()
    serializer_class = VisitSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        appointment = serializer.validated_data.get("appointment")
        if self.request.user.role == "shifokor" and appointment.slot.doctor.user != self.request.user:
            raise ValidationError(
                {"error": "Bu o'zga shifokorning qabuli uchun yozuv yozolmaysiz."}
            )
        serializer.save()


class DailyReportView(APIView):
    permission_classes = [IsRegistrator]

    def get(self, request):
        date = request.query_params.get("date", timezone.now().date())
        doctors = Doctor.objects.all()
        report_data = []

        for doctor in doctors:
            appointments = Appointment.objects.filter(
                slot__doctor=doctor, slot__date=date, status="keldi"
            )
            count = appointments.count()
            total_income = count * doctor.price
            report_data.append(
                {
                    "doctor": doctor.user.get_full_name() or doctor.user.username,
                    "completed_appointments": count,
                    "total_income": total_income,
                }
            )

        return Response(report_data)


class NoShowReportView(APIView):
    permission_classes = [IsRegistrator]

    def get(self, request):
        start_date = request.query_params.get("start_date")
        end_date = request.query_params.get("end_date")

        queryset = Appointment.objects.filter(status="kelmadi")
        if start_date and end_date:
            queryset = queryset.filter(slot__date__range=[start_date, end_date])

        count = queryset.count()
        serializer = AppointmentSerializer(queryset, many=True)
        return Response({"no_show_count": count, "appointments": serializer.data})


class TelegramAuthView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        phone = request.data.get("phone")
        telegram_id = request.data.get("telegram_id")

        if not phone:
            return Response(
                {"detail": "Telefon raqam talab qilinadi."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = None
        if telegram_id:
            user = User.objects.filter(telegram_id=telegram_id).first()

        if user:
            user.phone = phone
            user.save()
        else:
            user, created = User.objects.get_or_create(
                phone=phone,
                defaults={
                    "username": f"user_{phone}",
                    "role": "bemor",
                },
            )
            if telegram_id:
                conflict = User.objects.filter(telegram_id=telegram_id).exclude(pk=user.pk).exists()
                if not conflict:
                    user.telegram_id = telegram_id
                    user.save()

        refresh = RefreshToken.for_user(user)

        return Response({
            "refresh": str(refresh),
            "access": str(refresh.access_token),
            "user_id": user.id,
            "role": user.role,
        }, status=status.HTTP_200_OK)


class DevSwitchRoleView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        from django.conf import settings

        telegram_id = request.data.get("telegram_id")
        new_role = request.data.get("role")

        if not telegram_id or not new_role:
            return Response(
                {"detail": "telegram_id va role talab qilinadi."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            telegram_id = int(telegram_id)
        except (TypeError, ValueError):
            return Response(
                {"detail": "telegram_id noto'g'ri."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if telegram_id not in settings.DEV_TELEGRAM_IDS:
            return Response(
                {"detail": "Ruxsat etilmagan."},
                status=status.HTTP_403_FORBIDDEN,
            )

        if new_role not in dict(User.ROLE_CHOICES):
            return Response(
                {"detail": "Noto'g'ri rol."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            user = User.objects.get(telegram_id=telegram_id)
        except User.DoesNotExist:
            return Response(
                {"detail": "Foydalanuvchi topilmadi. Avval /start bosing."},
                status=status.HTTP_404_NOT_FOUND,
            )

        user.role = new_role
        user.save(update_fields=["role"])

        refresh = RefreshToken.for_user(user)

        return Response({
            "refresh": str(refresh),
            "access": str(refresh.access_token),
            "user_id": user.id,
            "role": user.role,
        }, status=status.HTTP_200_OK)
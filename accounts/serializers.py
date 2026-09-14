from django.utils import timezone
from rest_framework import serializers

from .models import Appointment, Doctor, Schedule, Slot, Speciality, User, Visit


class UserSerializer(serializers.ModelSerializer):

    class Meta:
        model = User
        fields = ('id', 'username', 'role', 'phone', 'telegram_id')


class SpecialitySerializer(serializers.ModelSerializer):

    class Meta:
        model = Speciality
        fields = ('id', 'name', 'is_active')


class DoctorSerializer(serializers.ModelSerializer):
    user_details = UserSerializer(source='user', read_only=True)
    speciality_name = serializers.CharField(
        source='speciality.name', read_only=True
    )

    class Meta:
        model = Doctor
        fields = (
            'id',
            'user',
            'user_details',
            'speciality',
            'speciality_name',
            'room',
            'slot_minutes',
            'price',
            'is_active',
        )


class ScheduleSerializer(serializers.ModelSerializer):

    class Meta:
        model = Schedule
        fields = (
            'id',
            'doctor',
            'date',
            'start_time',
            'end_time',
            'break_start',
            'break_end',
        )

    def validate_date(self, value):
        if value < timezone.now().date():
            raise serializers.ValidationError("O'tgan sanaga ish jadvalini kiritib bo'lmaydi.")
        return value

    def validate(self, data):
        if data.get('end_time') <= data.get('start_time'):
            raise serializers.ValidationError({
                'end_time': "Tugash vaqti boshlanish vaqtidan katta bo'lishi kerak."
            })
        return data


class SlotSerializer(serializers.ModelSerializer):

    class Meta:
        model = Slot
        fields = ('id', 'doctor', 'date', 'start_time', 'end_time', 'is_available')


class AppointmentSerializer(serializers.ModelSerializer):

    class Meta:
        model = Appointment
        fields = (
            'id',
            'slot',
            'patient',
            'status',
            'complaint',
            'created_at',
            'cancelled_at',
            'reminder_sent_at',
        )
        read_only_fields = (
            'patient',
            'status',
            'cancelled_at',
            'reminder_sent_at',
        )

    def validate_slot(self, value):
        if not value.is_available:
            raise serializers.ValidationError('Bu slot allaqachon band qilingan.')
        if value.date < timezone.now().date():
            raise serializers.ValidationError("O'tgan sanaga navbat olib bo'lmaydi.")
        return value

    def validate(self, data):
        slot = data.get('slot')
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            patient = request.user
            existing = Appointment.objects.filter(
                patient=patient,
                slot__doctor=slot.doctor,
                slot__date=slot.date,
                status__in=['band', 'keldi'],
            ).exists()
            if existing:
                raise serializers.ValidationError(
                    "Sizning bu shifokorda ushbu kunda allaqachon faol navbatingiz mavjud."
                )
        return data


class VisitSerializer(serializers.ModelSerializer):

    class Meta:
        model = Visit
        fields = (
            'id',
            'appointment',
            'diagnosis',
            'recommendation',
            'created_at',
        )
        read_only_fields = ('created_at',)


class AppointmentStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = Appointment
        fields = ('status',)
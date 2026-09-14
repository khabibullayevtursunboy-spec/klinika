from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Speciality, Doctor, Schedule, Slot, Appointment, Visit

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'role', 'phone', 'telegram_id', 'is_staff')
    list_filter = ('role', 'is_staff', 'is_active')
    search_fields = ('username', 'first_name', 'last_name', 'phone', 'telegram_id')
    
    
    fieldsets = UserAdmin.fieldsets + (
        ('Qo\'shimcha ma\'lumotlar', {'fields': ('role', 'phone', 'telegram_id')}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Qo\'shimcha ma\'lumotlar', {'fields': ('role', 'phone', 'telegram_id')}),
    )

@admin.register(Speciality)
class SpecialityAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name',)

@admin.register(Doctor)
class DoctorAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'speciality', 'room', 'slot_minutes', 'price', 'is_active')
    list_filter = ('is_active', 'speciality')
    search_fields = ('user__username', 'user__first_name', 'user__last_name', 'room')

@admin.register(Schedule)
class ScheduleAdmin(admin.ModelAdmin):
    list_display = ('id', 'doctor', 'date', 'start_time', 'end_time', 'break_start', 'break_end')
    list_filter = ('date', 'doctor')
    search_fields = ('doctor__user__username', 'doctor__user__first_name', 'doctor__user__last_name')

@admin.register(Slot)
class SlotAdmin(admin.ModelAdmin):
    list_display = ('id', 'doctor', 'date', 'start_time', 'end_time', 'is_available')
    list_filter = ('is_available', 'date', 'doctor')
    search_fields = ('doctor__user__username',)

@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ('id', 'slot', 'patient', 'status', 'created_at', 'cancelled_at')
    list_filter = ('status', 'slot__date')
    search_fields = ('patient__username', 'patient__first_name', 'patient__last_name', 'slot__doctor__user__username')

@admin.register(Visit)
class VisitAdmin(admin.ModelAdmin):
    list_display = ('id', 'appointment', 'created_at')
    search_fields = ('appointment__patient__username', 'diagnosis')
    list_filter = ('created_at',)
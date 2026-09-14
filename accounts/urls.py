from django.urls import path
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

from .views import (
    AppointmentCancelView,
    AppointmentCreateView,
    AppointmentListView,
    AppointmentStatusUpdateView,
    AvailableDaysView,
    DailyReportView,
    DoctorListCreateView,
    DoctorUpdateView,
    GenerateSlotsView,
    MyAppointmentListView,
    NoShowReportView,
    ScheduleListCreateView,
    SlotListView,
    SpecialityListView,
    VisitCreateView,
    TelegramAuthView,
)

app_name = 'accounts'

urlpatterns = [
    
    path('auth/login/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    
    path('specialities/', SpecialityListView.as_view(), name='speciality_list'),

    
    path('doctors/', DoctorListCreateView.as_view(), name='doctor_list_create'),
    path('doctors/<int:pk>/', DoctorUpdateView.as_view(), name='doctor_update'),

    
    path('schedules/', ScheduleListCreateView.as_view(), name='schedule_list_create'),
    path('schedules/<int:id>/generate-slots/', GenerateSlotsView.as_view(), name='generate_slots'),
    path('slots/', SlotListView.as_view(), name='slot_list'),
    path('slots/available-days/', AvailableDaysView.as_view(), name='available_days'),

    
    path('appointments/', AppointmentListView.as_view(), name='appointment_list'),
    path('appointments/create/', AppointmentCreateView.as_view(), name='appointment_create'),
    path('my-appointments/', MyAppointmentListView.as_view(), name='my_appointments'),
    path('appointments/my/', MyAppointmentListView.as_view(), name='my_appointments_alias'),
    path('appointments/<int:id>/cancel/', AppointmentCancelView.as_view(), name='appointment_cancel'),
    path('appointments/<int:id>/status/', AppointmentStatusUpdateView.as_view(), name='appointment_status_update'),

    
    path('visits/', VisitCreateView.as_view(), name='visit_create'),

    
    path('reports/daily/', DailyReportView.as_view(), name='daily_report'),
    path('reports/no-show/', NoShowReportView.as_view(), name='no_show_report'),
    path('auth/telegram/', TelegramAuthView.as_view(), name='telegram_auth'),
]
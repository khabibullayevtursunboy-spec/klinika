from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class User(AbstractUser):
  ROLE_CHOICES = (
      ("registrator", "Registrator"),
      ("shifokor", "Shifokor"),
      ("bemor", "Bemor"),
  )

  role = models.CharField(
      max_length=20,
      choices=ROLE_CHOICES,
      default="bemor",
      verbose_name="Roli",
  )

  phone = models.CharField(
      max_length=20,
      verbose_name="Telefon raqami",
  )

  telegram_id = models.BigIntegerField(
      null=True,
      unique=True,
      blank=True,
      verbose_name="Telegram ID",
  )

  class Meta:
    verbose_name = "Foydalanuvchi"
    verbose_name_plural = "Foydalanuvchilar"

  def __str__(self):
    return f"{self.username} ({self.get_role_display()})"


class Speciality(models.Model):
  name = models.CharField(
      max_length=100,
      unique=True,
      verbose_name="Yo'nalish nomi",
  )

  is_active = models.BooleanField(
      default=True,
      verbose_name="Faolmi",
  )

  class Meta:
    verbose_name = "Yo'nalish"
    verbose_name_plural = "Yo'nalishlar"

  def __str__(self):
    return self.name


class Doctor(models.Model):
  user = models.OneToOneField(
      User,
      on_delete=models.CASCADE,
      verbose_name="Foydalanuvchi",
  )

  speciality = models.ForeignKey(
      Speciality,
      on_delete=models.PROTECT,
      verbose_name="Mutaxassisligi",
  )

  room = models.CharField(
      max_length=20,
      verbose_name="Xona raqami",
  )

  slot_minutes = models.PositiveSmallIntegerField(
      default=20,
      verbose_name="Slot vaqti (daqiqa)",
  )

  price = models.DecimalField(
      max_digits=10,
      decimal_places=2,
      verbose_name="Narxi",
  )

  is_active = models.BooleanField(
      default=True,
      verbose_name="Faolmi",
  )

  class Meta:
    verbose_name = "Shifokor"
    verbose_name_plural = "Shifokorlar"

  def __str__(self):
    full_name = self.user.get_full_name() or self.user.username
    return f"Shifokor: {full_name} - {self.speciality.name}"


class Schedule(models.Model):
  doctor = models.ForeignKey(
      Doctor,
      on_delete=models.CASCADE,
      verbose_name="Shifokor",
  )

  date = models.DateField(
      db_index=True,
      verbose_name="Sana",
  )

  start_time = models.TimeField(
      verbose_name="Boshlanish vaqti",
  )

  end_time = models.TimeField(
      verbose_name="Tugash vaqti",
  )

  break_start = models.TimeField(
      null=True,
      blank=True,
      verbose_name="Tanaffus boshlanishi",
  )

  break_end = models.TimeField(
      null=True,
      blank=True,
      verbose_name="Tanaffus tugashi",
  )

  class Meta:
    unique_together = (
        "doctor",
        "date",
    )
    verbose_name = "Ish jadvali"
    verbose_name_plural = "Ish jadvallari"

  def clean(self):
    super().clean()

    if self.date and self.date < timezone.now().date():
      raise ValidationError("O'tgan sanaga ish jadvalini kiritib bo'lmaydi.")

    if self.start_time and self.end_time:
      if self.end_time <= self.start_time:
        raise ValidationError(
            "Ish tugash vaqti boshlanish vaqtidan keyin bo'lishi kerak."
        )

    if self.break_start and self.break_end:
      if self.break_end <= self.break_start:
        raise ValidationError(
            "Tanaffus tugash vaqti boshlanish vaqtidan keyin bo'lishi kerak."
        )

      if self.start_time and self.end_time:
        if not (
            self.start_time <= self.break_start <= self.end_time
            and self.start_time <= self.break_end <= self.end_time
        ):
          raise ValidationError("Tanaffus ish vaqtining ichida bo'lishi kerak.")

  def save(self, *args, **kwargs):
    self.full_clean()
    super().save(*args, **kwargs)

  def __str__(self):
    return f"{self.doctor} | {self.date} ({self.start_time} - {self.end_time})"


class Slot(models.Model):
  doctor = models.ForeignKey(
      Doctor,
      on_delete=models.CASCADE,
      verbose_name="Shifokor",
  )

  date = models.DateField(
      db_index=True,
      verbose_name="Sana",
  )

  start_time = models.TimeField(
      verbose_name="Boshlanish vaqti",
  )

  end_time = models.TimeField(
      verbose_name="Tugash vaqti",
  )

  is_available = models.BooleanField(
      default=True,
      verbose_name="Bo'shmi",
  )

  class Meta:
    unique_together = (
        "doctor",
        "date",
        "start_time",
    )
    indexes = [
        models.Index(
            fields=[
                "doctor",
                "date",
                "is_available",
            ]
        ),
    ]
    verbose_name = "Slot (Bo'sh vaqt)"
    verbose_name_plural = "Slotlar (Bo'sh vaqtlar)"

  def __str__(self):
    status = "Bo'sh" if self.is_available else "Band"
    return f"{self.doctor.user.username} | {self.date} {self.start_time} [{status}]"


class Appointment(models.Model):
  STATUS_CHOICES = (
      ("band", "Band"),
      ("keldi", "Keldi"),
      ("kelmadi", "Kelmadi"),
      ("bekor", "Bekor qilingan"),
  )

  slot = models.OneToOneField(
      Slot,
      on_delete=models.PROTECT,
      verbose_name="Slot",
  )

  patient = models.ForeignKey(
      User,
      on_delete=models.PROTECT,
      verbose_name="Bemor",
  )

  status = models.CharField(
      max_length=20,
      choices=STATUS_CHOICES,
      default="band",
      verbose_name="Holati",
  )

  complaint = models.TextField(
      blank=True,
      verbose_name="Shikoyati",
  )

  created_at = models.DateTimeField(
      auto_now_add=True,
      verbose_name="Yaratilgan vaqt",
  )

  cancelled_at = models.DateTimeField(
      null=True,
      blank=True,
      verbose_name="Bekor qilingan vaqt",
  )

  reminder_sent_at = models.DateTimeField(
      null=True,
      blank=True,
      verbose_name="Eslatma yuborilgan vaqt",
  )

  class Meta:
    verbose_name = "Navbat"
    verbose_name_plural = "Navbatlar"

  def __str__(self):
    return f"Bemor: {self.patient.username} -> Slot: {self.slot}"


class Visit(models.Model):
  appointment = models.OneToOneField(
      Appointment,
      on_delete=models.CASCADE,
      verbose_name="Navbat",
  )

  diagnosis = models.TextField(
      verbose_name="Tashxis",
  )

  recommendation = models.TextField(
      blank=True,
      verbose_name="Tavsiya",
  )

  created_at = models.DateTimeField(
      auto_now_add=True,
      verbose_name="Yaratilgan vaqt",
  )

  class Meta:
    verbose_name = "Qabul yozuvi"
    verbose_name_plural = "Qabul yozuvlari"

  def __str__(self):
    return f"Qabul natijasi: {self.appointment.patient.username} ({self.created_at.date()})"
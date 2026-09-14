klinika navbati telegram bot orqali navbat olish tizimi bemorlar yoziladi shifokorlar boshqaradi registrator django adminda kiritadi

texnologiyalar django rest postgresql aiogram 3 jwt

ornatish
git clone repo-url
cd klinika-navbat
python -m venv venv
source venv/bin/activate
pip install -r requirementstxt

sozlash va ishga tushirish
cp envexample env
python managepy migrate
python managepy createsuperuser
python managepy runserver
python -m botmain
python managepy run_scheduler

boshlangich sozlamalar django adminda
1 yonalishlar
2 foydalanuvchilar role shifokor
3 shifokorlar yonalish xona narx
4 ish jadvallari va slotlar

Metod	Manzil	Tavsif
POST	/api/auth/login/	JWT token olish (username/password orqali, TokenObtainPairView)
POST	/api/auth/refresh/	JWT tokenni yangilash
POST	/api/auth/telegram/	Telefon + telegram_id orqali ro'yxatdan o'tish/kirish (bot ishlatadi)
GET	/api/specialities/	Faol yo'nalishlar ro'yxati (pagination bilan)
GET	/api/doctors/  shifokorlar
POST	/api/doctors/ yangi shifokor qoshish
PATCH	/api/doctors/{id}/	  shifokorni tahrirlash
GET	/api/schedules/  jadvallar royhati
POST	/api/schedules/  yangi jadval kiritish
POST	/api/schedules/{id}/generate-slots/        jadvaldagi slotlarni generatsiya qilish
GET	/api/slots/  bo'sh slotlar
GET	/api/slots/available-days/  shifokorni yaqin 14 kundagi bosh kunlari
POST	/api/appointments/create/   slotni band qilish
GET	/api/appointments/ rolga qarab navbatlar
GET	/api/my-appointments/  bemorni navbatlari

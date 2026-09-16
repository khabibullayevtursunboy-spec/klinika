from datetime import date, timedelta

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from bot.api import api_client
from bot.keyboards.inline import appointment_action_keyboard, next_day_keyboard

router = Router()


class DoctorFSM(StatesGroup):
    waiting_diagnosis = State()


def _format_appointment_text(app: dict) -> str:
    slot = app.get("slot")
    start_time = app.get("start_time") or "-"
    patient_name = app.get("patient_name") or "-"
    complaint = app.get("complaint") or "Yo'q"

    return (
        f"⏰ {start_time}\n"
        f"👤 {patient_name}\n"
        f"📝 Shikoyat: {complaint}"
    )


async def _show_appointments_for_date(message_or_callback, state: FSMContext, target_date: date, edit: bool = False):
    fsm_data = await state.get_data()
    token = fsm_data.get("token")

    if not token:
        text = "❌ Foydalanuvchi tokeni topilmadi.\n\nIltimos, /start bosib qaytadan kiring."
        if edit:
            await message_or_callback.message.edit_text(text)
        else:
            await message_or_callback.answer(text)
        return

    date_str = target_date.isoformat()
    appointments = await api_client.get_doctor_appointments(token, date_str)

    active = [a for a in appointments if a.get("status") == "band"]

    if not active:
        text = f"📅 {date_str}\n\nUshbu kunga faol navbatlar yo'q."
        if edit:
            await message_or_callback.message.edit_text(text, reply_markup=next_day_keyboard())
        else:
            await message_or_callback.answer(text, reply_markup=next_day_keyboard())
        return

    active.sort(key=lambda a: a.get("start_time") or "")

    header_text = f"📅 {date_str} — {len(active)} ta faol navbat"
    if edit:
        await message_or_callback.message.edit_text(header_text)
        target_send = message_or_callback.message.answer
    else:
        await message_or_callback.answer(header_text)
        target_send = message_or_callback.answer

    for app in active:
        app_id = app.get("id")
        text = _format_appointment_text(app)
        await target_send(text, reply_markup=appointment_action_keyboard(app_id))

    await target_send("⬇️ Boshqa kunni ko'rish:", reply_markup=next_day_keyboard())

    await state.update_data(doctor_current_date=date_str)


@router.message(F.text == "📋 Bugungi qabul")
async def show_today_appointments(message: Message, state: FSMContext):
    await _show_appointments_for_date(message, state, date.today())


@router.message(F.text.in_({"📊 Bugungi hisobot", "📊 Hisobot", "/report"}))
async def show_doctor_report(message: Message, state: FSMContext):
    fsm_data = await state.get_data()
    token = fsm_data.get("token")

    if not token:
        await message.answer("❌ Foydalanuvchi tokeni topilmadi.\n\nIltimos, /start bosib qaytadan kiring.")
        return

    today_str = date.today().isoformat()
    
    wait_msg = await message.answer("🔄 Hisobot shakllantirilmoqda...")

    report_data = await api_client.get_doctor_daily_report(token, today_str)

    if report_data and isinstance(report_data, dict):
        total = report_data.get("total_appointments", 0)
        completed = report_data.get("completed", 0)
        missed = report_data.get("missed", 0)
        pending = report_data.get("pending", 0)
        visits_count = report_data.get("visits_count", 0)
    else:
        appointments = await api_client.get_doctor_appointments(token, today_str)
        
        total = len(appointments)
        completed = sum(1 for a in appointments if a.get("status") == "keldi")
        missed = sum(1 for a in appointments if a.get("status") == "kelmadi")
        pending = sum(1 for a in appointments if a.get("status") == "band")
        visits_count = sum(1 for a in appointments if a.get("has_visit") or a.get("diagnosis"))

    report_text = (
        f"📊 **BUGUNGI HISOBOT ({today_str})**\n\n"
        f"🔹 **Jami yozilganlar:** {total} ta\n"
        f"✅ **Kelgan bemorlar:** {completed} ta\n"
        f"❌ **Kelmagan bemorlar:** {missed} ta\n"
        f"⏳ **Kutilayotganlar:** {pending} ta\n"
        f"📝 **Qo'yilgan tashxislar:** {visits_count} ta\n\n"
    )

    if total > 0:
        attendance_rate = round((completed / total) * 100, 1)
        report_text += f"📈 **Davomat ko'rsatkichi:** {attendance_rate}%"
    else:
        report_text += "📈 **Davomat ko'rsatkichi:** Ma'lumot yo'q"

    await wait_msg.edit_text(report_text, parse_mode="Markdown")


@router.callback_query(F.data == "doc_nextday")
async def show_next_day_appointments(callback: CallbackQuery, state: FSMContext):
    fsm_data = await state.get_data()
    current_date_str = fsm_data.get("doctor_current_date")

    if current_date_str:
        current_date = date.fromisoformat(current_date_str)
    else:
        current_date = date.today()

    next_date = current_date + timedelta(days=1)

    await callback.message.answer(f"📅 {next_date.isoformat()} kunini yuklayapman...")
    await _show_appointments_for_date(callback, state, next_date, edit=False)
    await callback.answer()


@router.callback_query(F.data.startswith("docstatus_"))
async def process_doctor_status(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split("_")
    if len(parts) != 3:
        await callback.answer("❌ Ma'lumot noto'g'ri.", show_alert=True)
        return

    app_id = int(parts[1])
    new_status = parts[2]  

    fsm_data = await state.get_data()
    token = fsm_data.get("token")

    if not token:
        await callback.message.answer(
            "❌ Foydalanuvchi tokeni topilmadi.\n\nIltimos, /start bosib qaytadan kiring."
        )
        await callback.answer()
        return

    if new_status == "kelmadi":
        status_code, response = await api_client.update_appointment_status(
            token, app_id, "kelmadi"
        )

        if status_code in [200, 201]:
            await callback.message.edit_text(
                callback.message.text + "\n\n❌ Belgilandi: KELMADI"
            )
        else:
            err_msg = response.get("error", response.get("detail", "Xatolik yuz berdi.")) if isinstance(response, dict) else "Xatolik yuz berdi."
            await callback.message.answer(f"❌ Xatolik: {err_msg}")

        await callback.answer()
        return

    status_code, response = await api_client.update_appointment_status(
        token, app_id, "keldi"
    )

    if status_code not in [200, 201]:
        err_msg = response.get("error", response.get("detail", "Xatolik yuz berdi.")) if isinstance(response, dict) else "Xatolik yuz berdi."
        await callback.message.answer(f"❌ Xatolik: {err_msg}")
        await callback.answer()
        return

    await callback.message.edit_text(
        callback.message.text + "\n\n✅ Belgilandi: KELDI"
    )

    await state.update_data(pending_visit_appointment_id=app_id)
    await state.set_state(DoctorFSM.waiting_diagnosis)

    await callback.message.answer(
        "📝 Tashxisni yozing (masalan: 'O'RVI, dam olish tavsiya etildi'):"
    )

    await callback.answer()


@router.message(DoctorFSM.waiting_diagnosis)
async def process_diagnosis(message: Message, state: FSMContext):
    diagnosis_text = (message.text or "").strip()

    if not diagnosis_text:
        await message.answer("❌ Tashxis matni bo'sh bo'lmasligi kerak. Qaytadan yozing:")
        return

    fsm_data = await state.get_data()
    token = fsm_data.get("token")
    app_id = fsm_data.get("pending_visit_appointment_id")

    if not token or not app_id:
        await message.answer(
            "❌ Ma'lumot topilmadi. Iltimos, qaytadan urinib ko'ring."
        )
        await state.update_data(pending_visit_appointment_id=None)
        await state.set_state(None)
        return

    status_code, response = await api_client.create_visit(
        token, app_id, diagnosis_text
    )

    if status_code in [200, 201]:
        await message.answer("✅ Tashxis muvaffaqiyatli saqlandi.")
    else:
        err_msg = response.get("error", response.get("detail", "Xatolik yuz berdi.")) if isinstance(response, dict) else "Xatolik yuz berdi."
        await message.answer(f"❌ Xatolik: {err_msg}")

    await state.update_data(pending_visit_appointment_id=None)
    await state.set_state(None)
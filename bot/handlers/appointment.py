from aiogram import F, Router
from aiogram.enums import ParseMode
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from bot.api import api_client
from bot.keyboards.inline import (
    build_inline_keyboard,
    confirm_keyboard,
    doctors_pagination_keyboard,
    specialities_pagination_keyboard,
)

router = Router()


class AppointmentFSM(StatesGroup):
    speciality = State()
    doctor = State()
    date = State()
    slot = State()
    complaint = State()
    confirm = State()


async def reset_flow_keep_token(state: FSMContext):
    data = await state.get_data()
    token = data.get("token")
    await state.clear()
    if token:
        await state.update_data(token=token)


@router.message(F.text.contains("Navbat olish"))
async def start_appointment(message: Message, state: FSMContext):
    data = await state.get_data()
    token = data.get("token")

    if not token:
        await message.answer(
            "❌ Foydalanuvchi tokeni topilmadi.\n\n"
            "Iltimos, /start buyrug'ini bosing va qaytadan urinib ko'ring."
        )
        return

    await state.update_data(token=token)

    await _show_specialities_page(message, state, page=1)


async def _show_specialities_page(source, state: FSMContext, page: int, edit: bool = False):
    result = await api_client.get_specialities(page=page)
    specialities = result["results"]

    if not specialities:
        if page == 1:
            text = "Hozircha faol yo'nalishlar topilmadi."
            if edit:
                await source.message.edit_text(text)
            else:
                await source.answer(text)
            await reset_flow_keep_token(state)
        else:
            await source.answer("Boshqa yo'nalish yo'q.", show_alert=True)
        return

    kb = build_inline_keyboard(specialities, "speciality")

    pagination_row = specialities_pagination_keyboard(
        page, result["has_next"], result["has_previous"]
    )
    if pagination_row:
        kb.inline_keyboard.extend(pagination_row.inline_keyboard)

    text = f"Kerakli yo'nalishni tanlang (sahifa {page}):"

    if edit:
        await source.message.edit_text(text, reply_markup=kb)
    else:
        await source.answer(text, reply_markup=kb)

    await state.update_data(specialities_page=page)
    await state.set_state(AppointmentFSM.speciality)


@router.callback_query(
    AppointmentFSM.speciality,
    F.data.startswith("specpage_")
)
async def process_specialities_pagination(callback: CallbackQuery, state: FSMContext):
    try:
        page = int(callback.data.split("_")[1])
    except (IndexError, ValueError):
        await callback.answer("❌ Xatolik.", show_alert=True)
        return

    await _show_specialities_page(callback, state, page, edit=True)
    await callback.answer()


@router.callback_query(
    AppointmentFSM.speciality,
    F.data.startswith("spec_")
)
async def process_speciality(
    callback: CallbackQuery,
    state: FSMContext
):
    try:
        spec_id = int(
            callback.data.split("_")[1]
        )
    except (IndexError, ValueError):
        await callback.answer(
            "❌ Noto'g'ri yo'nalish.",
            show_alert=True
        )
        return

    data = await state.get_data()

    if not data.get("token"):
        await callback.message.edit_text(
            "❌ Foydalanuvchi tokeni topilmadi.\n\n"
            "Iltimos, /start bosib qaytadan kiring."
        )
        await reset_flow_keep_token(state)
        await callback.answer()
        return

    await state.update_data(speciality_id=spec_id)

    await _show_doctors_page(callback, state, spec_id, page=1)

    await callback.answer()


async def _show_doctors_page(callback: CallbackQuery, state: FSMContext, spec_id: int, page: int):
    result = await api_client.get_doctors(speciality_id=spec_id, page=page)
    doctors = result["results"]

    if not doctors:
        if page == 1:
            await callback.message.edit_text(
                "Ushbu yo'nalishda shifokorlar topilmadi."
            )
            await reset_flow_keep_token(state)
        else:
            await callback.answer("Boshqa shifokor yo'q.", show_alert=True)
        return

    kb = build_inline_keyboard(doctors, "doctor")

    pagination_row = doctors_pagination_keyboard(
        page, result["has_next"], result["has_previous"]
    )
    if pagination_row:
        kb.inline_keyboard.extend(pagination_row.inline_keyboard)

    await callback.message.edit_text(
        f"Shifokorni tanlang (sahifa {page}):",
        reply_markup=kb
    )

    await state.update_data(doctors_page=page)
    await state.set_state(AppointmentFSM.doctor)


@router.callback_query(
    AppointmentFSM.doctor,
    F.data.startswith("docpage_")
)
async def process_doctors_pagination(
    callback: CallbackQuery,
    state: FSMContext
):
    try:
        page = int(callback.data.split("_")[1])
    except (IndexError, ValueError):
        await callback.answer("❌ Xatolik.", show_alert=True)
        return

    data = await state.get_data()
    spec_id = data.get("speciality_id")

    if not spec_id:
        await callback.message.edit_text(
            "❌ Yo'nalish ma'lumoti topilmadi.\n"
            "Iltimos, navbat olishni qaytadan boshlang."
        )
        await reset_flow_keep_token(state)
        await callback.answer()
        return

    await _show_doctors_page(callback, state, spec_id, page)
    await callback.answer()


@router.callback_query(
    AppointmentFSM.doctor,
    F.data.startswith("doc_")
)
async def process_doctor(
    callback: CallbackQuery,
    state: FSMContext
):
    try:
        doc_id = int(
            callback.data.split("_")[1]
        )
    except (IndexError, ValueError):
        await callback.answer(
            "❌ Noto'g'ri shifokor.",
            show_alert=True
        )
        return

    await state.update_data(
        doctor_id=doc_id
    )

    data = await state.get_data()

    if not data.get("token"):
        await callback.message.edit_text(
            "❌ Foydalanuvchi tokeni topilmadi.\n\n"
            "Iltimos, /start bosib qaytadan kiring."
        )

        await reset_flow_keep_token(state)
        await callback.answer()
        return

    days = await api_client.get_available_days(
        doc_id
    )

    if not days:
        await callback.message.edit_text(
            "Ushbu shifokorda yaqin 14 kunda "
            "bo'sh vaqtlar yo'q."
        )

        await reset_flow_keep_token(state)
        await callback.answer()
        return

    kb = build_inline_keyboard(
        days,
        "date"
    )

    await callback.message.edit_text(
        "Qabul kunini tanlang:",
        reply_markup=kb
    )

    await state.set_state(
        AppointmentFSM.date
    )

    await callback.answer()


@router.callback_query(
    AppointmentFSM.date,
    F.data.startswith("date_")
)
async def process_date(
    callback: CallbackQuery,
    state: FSMContext
):
    try:
        selected_date = callback.data.split(
            "_",
            1
        )[1]
    except IndexError:
        await callback.answer(
            "❌ Sana noto'g'ri.",
            show_alert=True
        )
        return

    await state.update_data(
        date=selected_date
    )

    data = await state.get_data()

    doctor_id = data.get("doctor_id")

    if not doctor_id:
        await callback.message.edit_text(
            "❌ Shifokor ma'lumoti topilmadi.\n"
            "Iltimos, navbat olishni qaytadan boshlang."
        )

        await reset_flow_keep_token(state)
        await callback.answer()
        return

    slots = await api_client.get_slots(
        doctor_id,
        selected_date
    )

    if not slots:
        await callback.message.edit_text(
            "Ushbu kunda bo'sh slotlar qolmagan."
        )

        await reset_flow_keep_token(state)
        await callback.answer()
        return

    kb = build_inline_keyboard(
        slots,
        "slot"
    )

    await callback.message.edit_text(
        "Bo'sh vaqtni tanlang:",
        reply_markup=kb
    )

    await state.set_state(
        AppointmentFSM.slot
    )

    await callback.answer()


@router.callback_query(
    AppointmentFSM.slot,
    F.data.startswith("slot_")
)
async def process_slot(
    callback: CallbackQuery,
    state: FSMContext
):
    parts = callback.data.split("_")

    if len(parts) < 3:
        await callback.answer(
            "❌ Slot ma'lumoti noto'g'ri.",
            show_alert=True
        )
        return

    try:
        slot_id = int(parts[1])
    except ValueError:
        await callback.answer(
            "❌ Slot ID noto'g'ri.",
            show_alert=True
        )
        return

    start_time = "_".join(parts[2:])

    await state.update_data(
        slot_id=slot_id,
        start_time=start_time
    )

    await callback.message.edit_text(
        "Shikoyatingiz bo'lsa yozib yuboring "
        "(yoki 'O'tkazib yuborish' deb yozing):"
    )

    await state.set_state(
        AppointmentFSM.complaint
    )

    await callback.answer()


@router.message(
    AppointmentFSM.complaint
)
async def process_complaint(
    message: Message,
    state: FSMContext
):
    complaint_text = (
        message.text or ""
    ).strip()

    skip_words = {
        "o'tkazib yuborish",
        "otkazib yuborish",
        "o'tkazib yuborish.",
        "otkazib yuborish.",
        "-"
    }

    if complaint_text.lower() in skip_words:
        complaint_text = ""

    await state.update_data(
        complaint=complaint_text
    )

    data = await state.get_data()

    display_complaint = (
        complaint_text
        if complaint_text
        else "Yo'q"
    )

    text = (
        "<b>📌 Navbat ma'lumotlarini tasdiqlang:</b>\n\n"
        f"📅 Sana: {data.get('date', '-')}\n"
        f"⏰ Vaqt: {data.get('start_time', '-')}\n"
        f"📝 Shikoyat: {display_complaint}\n\n"
        "Navbatni tasdiqlaysizmi?"
    )

    await message.answer(
        text,
        reply_markup=confirm_keyboard(),
        parse_mode=ParseMode.HTML
    )

    await state.set_state(
        AppointmentFSM.confirm
    )


def _extract_error_message(response):
    if not isinstance(response, dict):
        return "Xatolik yuz berdi."

    if "error" in response:
        return response["error"]

    if "detail" in response:
        return response["detail"]

    if "non_field_errors" in response:
        nfe = response["non_field_errors"]
        if isinstance(nfe, list) and nfe:
            return nfe[0]
        if isinstance(nfe, str):
            return nfe

    for value in response.values():
        if isinstance(value, list) and value:
            return value[0]
        if isinstance(value, str) and value:
            return value

    return "Xatolik yuz berdi."


@router.callback_query(
    AppointmentFSM.confirm,
    F.data == "confirm_app"
)
async def confirm_appointment(
    callback: CallbackQuery,
    state: FSMContext
):
    data = await state.get_data()

    token = data.get("token")

    if not token:
        await callback.message.edit_text(
            "❌ Xatolik: Foydalanuvchi tokeni topilmadi.\n\n"
            "Iltimos, /start bosib qaytadan kiring."
        )

        await reset_flow_keep_token(state)
        await callback.answer()
        return

    slot_id = data.get("slot_id")

    if not slot_id:
        await callback.message.edit_text(
            "❌ Slot ma'lumoti topilmadi.\n"
            "Iltimos, navbat olishni qaytadan boshlang."
        )

        await reset_flow_keep_token(state)
        await callback.answer()
        return

    complaint = data.get(
        "complaint",
        ""
    )

    status_code, response = (
        await api_client.create_appointment(
            token=token,
            slot_id=slot_id,
            complaint=complaint,
        )
    )

    if status_code in [200, 201]:
        await callback.message.edit_text(
            "✅ Navbatingiz muvaffaqiyatli "
            "band qilindi!"
        )

    else:
        err_msg = _extract_error_message(response)

        await callback.message.edit_text(
            "❌ Bu vaqt band bo'lib qoldi "
            "yoki xatolik yuz berdi.\n\n"
            f"Sabab: {err_msg}\n\n"
            "Iltimos, qaytadan urinib ko'ring."
        )

    await reset_flow_keep_token(state)
    await callback.answer()


@router.callback_query(
    AppointmentFSM.confirm,
    F.data == "cancel_app"
)
async def cancel_appointment_creation(
    callback: CallbackQuery,
    state: FSMContext
):
    await callback.message.edit_text(
        "❌ Navbat olish bekor qilindi."
    )

    await reset_flow_keep_token(state)
    await callback.answer()
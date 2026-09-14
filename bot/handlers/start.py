from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.filters import CommandStart
from aiogram.types import Message
from bot.api import api_client
from bot.keyboards.inline import (
    phone_keyboard,
    main_menu_keyboard,
    doctor_menu_keyboard,
)

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "Xush kelibsiz! Klinika botidan foydalanish uchun telefon raqamingizni yuboring:",
        reply_markup=phone_keyboard(),
    )


@router.message(F.contact)
async def process_contact(message: Message, state: FSMContext):
    phone = message.contact.phone_number
    telegram_id = message.from_user.id

    status_code, response = await api_client.login_or_register(
        phone=phone, telegram_id=telegram_id
    )

    if status_code not in [200, 201]:
        await message.answer(
            "❌ Tizimga ulanishda xatolik yuz berdi. Iltimos, qaytadan /start ni bosing."
        )
        return

    token = response.get("access") or response.get("token")
    role = response.get("role")

    await state.update_data(token=token, role=role)

    if role == "shifokor":
        await message.answer(
            "Xush kelibsiz, Doktor!\n\n"
            "Bugungi qabullaringizni ko'rish uchun tugmani bosing.",
            reply_markup=doctor_menu_keyboard(),
        )
    else:
        await message.answer(
            f"Raqamingiz qabul qilindi: {phone}\n"
            "Asosiy menyudan bo'limni tanlang:",
            reply_markup=main_menu_keyboard(),
        )
from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from bot.api import api_client

router = Router()


def _confirm_cancel_keyboard(app_id: int):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Ha, bekor qilaman",
                    callback_data=f"cancelyes_{app_id}",
                ),
                InlineKeyboardButton(
                    text="❌ Yo'q",
                    callback_data=f"cancelno_{app_id}",
                ),
            ]
        ]
    )


@router.message(F.text.in_(["📋 Mening navbatlarim", "❌ Bekor qilish"]))
async def show_my_appointments(message: Message, state: FSMContext):
    data = await state.get_data()
    token = data.get("token")

    if not token:
        await message.answer(
            "❌ Foydalanuvchi tokeni topilmadi.\n\n"
            "Iltimos, /start bosib qaytadan kiring."
        )
        return

    appointments = await api_client.get_my_appointments(token)

    if not appointments:
        await message.answer("Sizda hali faol navbatlar mavjud emas.")
        return

    for app in appointments:
        app_id = app.get("id")
        status_val = app.get("status")

        text = f"🆔 **Navbat #{app_id}**\n📊 Status: {status_val}\n"

        kb = None
        if status_val == "band":
            kb = InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="❌ Bekor qilish",
                            callback_data=f"cancelapp_{app_id}",
                        )
                    ]
                ]
            )

        await message.answer(text, reply_markup=kb, parse_mode="Markdown")


@router.callback_query(F.data.startswith("cancelapp_"))
async def ask_cancel_confirmation(callback: CallbackQuery, state: FSMContext):
    app_id = int(callback.data.split("_")[1])

    current_text = callback.message.text or ""
    new_text = current_text + "\n\n⚠️ Rostdan ham bekor qilmoqchimisiz?"

    await callback.message.edit_text(
        new_text,
        reply_markup=_confirm_cancel_keyboard(app_id),
        parse_mode="Markdown",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("cancelno_"))
async def decline_cancel_appointment(callback: CallbackQuery, state: FSMContext):
    app_id = int(callback.data.split("_")[1])

    text = f"🆔 **Navbat #{app_id}**\n📊 Status: band\n\n✅ Navbat saqlanib qoldi."

    await callback.message.edit_text(text, parse_mode="Markdown")
    await callback.answer()


@router.callback_query(F.data.startswith("cancelyes_"))
async def process_cancel_appointment(callback: CallbackQuery, state: FSMContext):
    app_id = int(callback.data.split("_")[1])

    data = await state.get_data()
    token = data.get("token")

    if not token:
        await callback.message.edit_text(
            "❌ Foydalanuvchi tokeni topilmadi.\n\n"
            "Iltimos, /start bosib qaytadan kiring."
        )
        await callback.answer()
        return

    status_code, response = await api_client.cancel_appointment(token, app_id)

    if status_code == 200:
        await callback.message.edit_text(
            f"✅ Navbat #{app_id} muvaffaqiyatli bekor qilindi."
        )
    else:
        if isinstance(response, dict):
            err_msg = response.get(
                "error", response.get("detail", "Bekor qilib bo'lmadi.")
            )
        else:
            err_msg = "Bekor qilib bo'lmadi."

        await callback.message.edit_text(
            f"❌ Xatolik: {err_msg}\n"
            f"📞 Qat'iy bekor qilish bo'yicha registrator bilan bog'laning: +998 90 123 45 67"
        )

    await callback.answer()


@router.callback_query(F.data.startswith("remindcancel_"))
async def process_reminder_cancel(callback: CallbackQuery, state: FSMContext):
    app_id = int(callback.data.split("_")[1])

    data = await state.get_data()
    token = data.get("token")

    if not token:
        await callback.message.answer(
            "❌ Sizni tanib bo'lmadi. Iltimos, /start bosib qaytadan kiring, "
            "so'ng qaytadan urinib ko'ring."
        )
        await callback.answer()
        return

    status_code, response = await api_client.cancel_appointment(token, app_id)

    if status_code == 200:
        await callback.message.answer("✅ Navbat muvaffaqiyatli bekor qilindi.")
    else:
        if isinstance(response, dict):
            err_msg = response.get(
                "error", response.get("detail", "Bekor qilib bo'lmadi.")
            )
        else:
            err_msg = "Bekor qilib bo'lmadi."

        await callback.message.answer(f"❌ Xatolik: {err_msg}")

    await callback.answer()
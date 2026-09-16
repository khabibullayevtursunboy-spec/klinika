from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)


def phone_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(
                    text="📱 Telefon raqamni yuborish",
                    request_contact=True,
                    style="success",  # Ko'k rang
                )
            ]
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def main_menu_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(
                    text="📅 Navbat olish",
                    style="success",  # Yashil rang
                )
            ],
            [
                KeyboardButton(
                    text="📋 Mening navbatlarim",
                    style="success",  # Ko'k rang
                ),
                KeyboardButton(
                    text="❌ Bekor qilish",
                    style="danger",  # Qizil rang
                ),
            ],
        ],
        resize_keyboard=True,
    )


def build_inline_keyboard(items, item_type):
    builder = []

    if item_type == "speciality":
        for spec in items:
            builder.append(
                [
                    InlineKeyboardButton(
                        text=spec["name"],
                        callback_data=f"spec_{spec['id']}",
                        style="primary",
                    )
                ]
            )

    elif item_type == "doctor":
        for doc in items:
            user_details = doc.get("user_details") or {}
            full_name = (
                f"{user_details.get('first_name', '')} {user_details.get('last_name', '')}".strip()
                or user_details.get("username")
                or "Shifokor"
            )
            btn_text = f"{full_name} ({doc.get('room', '')}-xona, {doc.get('price', '')} so'm)"
            builder.append(
                [
                    InlineKeyboardButton(
                        text=btn_text,
                        callback_data=f"doc_{doc['id']}",
                        style="primary",
                    )
                ]
            )

    elif item_type == "date":
        row = []
        for day in items:
            row.append(
                InlineKeyboardButton(
                    text=day, callback_data=f"date_{day}", style="primary"
                )
            )
            if len(row) == 2:
                builder.append(row)
                row = []
        if row:
            builder.append(row)

    elif item_type == "slot":
        row = []
        for slot in items:
            start_time = slot["start_time"][:5]
            row.append(
                InlineKeyboardButton(
                    text=start_time,
                    callback_data=f"slot_{slot['id']}_{start_time}",
                    style="success",
                )
            )
            if len(row) == 3:
                builder.append(row)
                row = []
        if row:
            builder.append(row)

    return InlineKeyboardMarkup(inline_keyboard=builder)


def confirm_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Tasdiqlash",
                    callback_data="confirm_app",
                    style="success",  # Yashil rang
                ),
                InlineKeyboardButton(
                    text="❌ Bekor qilish",
                    callback_data="cancel_app",
                    style="danger",  # Qizil rang
                ),
            ]
        ]
    )


def doctor_menu_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(
                    text="📋 Bugungi qabul",
                    style="primary",
                ),
                KeyboardButton(
                    text="📊 Bugungi hisobot",
                    style="primary",
                ),
            ],
        ],
        resize_keyboard=True,
    )


def appointment_action_keyboard(appointment_id: int):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Keldi",
                    callback_data=f"docstatus_{appointment_id}_keldi",
                    style="success",  # Yashil rang
                ),
                InlineKeyboardButton(
                    text="❌ Kelmadi",
                    callback_data=f"docstatus_{appointment_id}_kelmadi",
                    style="danger",  # Qizil rang
                ),
            ]
        ]
    )


def next_day_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="➡️ Ertangi kun",
                    callback_data="doc_nextday",
                    style="primary",
                )
            ]
        ]
    )


def _pagination_row(prefix: str, page: int, has_next: bool, has_previous: bool):
    row = []
    if has_previous:
        row.append(
            InlineKeyboardButton(
                text="⬅️ Oldingi",
                callback_data=f"{prefix}_{page - 1}",
                style="primary",
            )
        )
    if has_next:
        row.append(
            InlineKeyboardButton(
                text="Keyingi ➡️",
                callback_data=f"{prefix}_{page + 1}",
                style="primary",
            )
        )
    if not row:
        return None
    return InlineKeyboardMarkup(inline_keyboard=[row])


def doctors_pagination_keyboard(page: int, has_next: bool, has_previous: bool):
    return _pagination_row("docpage", page, has_next, has_previous)


def specialities_pagination_keyboard(page: int, has_next: bool, has_previous: bool):
    return _pagination_row("specpage", page, has_next, has_previous)